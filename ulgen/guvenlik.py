"""Ajan güvenlik duvarı (guardrails) ve onay yöneticisi.

Terminal komutu çalıştıran ya da dosya ezen her işlev önce buradaki filtreden
geçer. Tehlikeli bulunan işlem ÇALIŞTIRILMAZ; kullanıcıdan yazılı (ya da
sesli) 'ONAY <4 haneli kod>' istenir. Onay yalnızca kullanıcının kendi
mesajıyla verilebilir; modelin ürettiği metin onay yerine geçmez. Bu,
istem enjeksiyonu (prompt injection) saldırılarına karşı ana korumadır.
"""

import os
import re
import secrets
import shlex
import threading
import time

from . import ayar

# İZİN LİSTESİ: yalnızca bu komutlar (ve güvenli bağımsız değişkenleri)
# onaysız çalışır. Listede olmayan HER komut ONAY ister. Kara liste yöntemi
# atlatılabildiği için (python -c, find -delete, git clean...) bırakıldı.
SALT_OKUNUR = frozenset({
    "ls", "pwd", "date", "whoami", "uname", "df", "du", "uptime", "wc",
    "head", "tail", "cat", "grep", "file", "stat", "echo", "which",
    "sw_vers", "hostname", "id", "ps", "pmset", "cal",
})

# Argüman olarak yol alan komutlar (yollar kritik yol denetiminden geçer)
YOL_ALAN = frozenset({"ls", "du", "wc", "head", "tail", "cat", "grep",
                      "file", "stat"})

# Gizli ya da kritik yollar
KRITIK_YOLLAR = (
    "/etc", "/system", "/library", "/usr", "/bin", "/sbin", "/private",
    "/var", "/dev", "/volumes", "/applications",
)

KRITIK_ONEKLER = (".ssh", ".gnupg", ".aws", ".config", ".kube", ".netrc",
                  ".zsh_history", ".bash_history", "library/keychains",
                  "library/cookies", "library/safari")

# ~/ÜlgenVeri içinde okumaya açık alt klasörler
ACIK_ALT_KLASORLER = ("dosyalar", "saglik")

BIRLESIK_KOMUT = re.compile(r"[;&|`><]|\$\(")

SAYI_SOZCUKLERI = {
    "sıfır": "0", "sifir": "0", "bir": "1", "iki": "2", "üç": "3", "uc": "3",
    "dört": "4", "dort": "4", "beş": "5", "bes": "5", "altı": "6",
    "alti": "6", "yedi": "7", "sekiz": "8", "dokuz": "9",
}


def _kritik_yol_mu(parca):
    """Bir komut argümanı kritik ya da gizli bir yolu gösteriyor mu?"""
    if not parca or parca.startswith("-"):
        return False
    yol = os.path.realpath(os.path.expanduser(parca))
    kucuk = yol.lower()
    for kritik in KRITIK_YOLLAR:
        if kucuk == kritik or kucuk.startswith(kritik + "/"):
            return True
    ev = os.path.realpath(ayar.EV).lower()
    for onek in KRITIK_ONEKLER:
        if kucuk.startswith(os.path.join(ev, onek)):
            return True
    veri = os.path.realpath(ayar.KLASOR)
    if yol == veri or yol.startswith(veri + os.sep):
        for acik in ACIK_ALT_KLASORLER:
            alt = os.path.join(veri, acik)
            if yol == alt or yol.startswith(alt + os.sep):
                return False
        return True
    return False


def _kapsayici_mi(parca):
    """Yol, ÜlgenVeri klasörünü içine alan bir üst klasör mü? (grep -r gibi)"""
    if not parca or parca.startswith("-"):
        return False
    yol = os.path.realpath(os.path.expanduser(parca))
    veri = os.path.realpath(ayar.KLASOR)
    return veri == yol or veri.startswith(yol.rstrip(os.sep) + os.sep)


def komut_analiz(komut):
    """Komutu inceler. (onay_gerekli_mi, neden) çifti döndürür."""
    if BIRLESIK_KOMUT.search(komut):
        return True, "birleşik komut, yönlendirme ya da alt komut içeriyor"
    try:
        parcalar = shlex.split(komut)
    except ValueError:
        return True, "komut ayrıştırılamadı"
    if not parcalar:
        return True, "boş komut"
    ad = parcalar[0]
    if os.sep in ad or ad not in SALT_OKUNUR:
        return True, "'%s' izin listesinde değil" % os.path.basename(ad)
    args = parcalar[1:]
    if ad == "date" and any(not a.startswith("+") for a in args):
        return True, "'date' yalnızca biçim (+...) bağımsız değişkeniyle"
    if ad == "pmset" and (not args or args[0] != "-g"):
        return True, "'pmset' yalnızca -g (okuma) ile"
    for arg in args:
        if ad in YOL_ALAN and _kritik_yol_mu(arg):
            return True, "gizli ya da kritik bir yola erişiyor"
        if ad == "grep" and _kapsayici_mi(arg):
            return True, "gizli verileri de kapsayan bir klasörde arıyor"
    return False, ""


DUYARLI_DESENI = re.compile(
    r"\b(ilaç|ilac|hap\b|tansiyon|insülin|insulin|şeker hastal|teşhis|tedavi|"
    r"reçete|recete|hastal[ıi]k|kanser|ameliyat|doz\b|nab[ıi]z|uyku|"
    r"tc\s*kimlik|kimlik\s*no|iban|kredi\s*kart|kart\s*numaras|şifre|sifre|"
    r"parola|password|maaş|maas|borcum|banka\s*hesab|sağl[ıi]k)", re.IGNORECASE)


def duyarli_mi(metin):
    """Metin sağlık/kimlik/finans/parola gibi duyarlı veri içeriyor mu?

    Sezgiseldir (anahtar sözcük). Yanlış negatif olabilir; kesin koruma
    değil, ek bir önlemdir.
    """
    return bool(DUYARLI_DESENI.search(metin or ""))


def kod_ayikla(metin):
    """'onay 1234' ya da 'onay bir iki üç dört' ifadesinden kodu çıkarır."""
    kucuk = metin.lower().strip()
    eslesme = re.match(r"^onay\s+(.+)$", kucuk)
    if not eslesme:
        return None
    kalan = eslesme.group(1)
    for sozcuk, rakam in SAYI_SOZCUKLERI.items():
        kalan = re.sub(r"\b%s\b" % sozcuk, rakam, kalan)
    rakamlar = re.sub(r"\D", "", kalan)
    return rakamlar if len(rakamlar) == 4 else None


class OnayIstegi(Exception):
    """Bir işlem onay beklerken fırlatılır; ``mesaj`` kullanıcıya gösterilir."""

    def __init__(self, mesaj):
        super().__init__(mesaj)
        self.mesaj = mesaj


class OnayYoneticisi:
    """Onay bekleyen işlemleri tutar. Her kod tek kullanımlık ve süreli."""

    SURE = 120

    def __init__(self):
        self._bekleyen = {}
        self._kilit = threading.Lock()

    def iste(self, aciklama, islev):
        """İşlemi bekletir ve OnayIstegi fırlatır (çalıştırmaz)."""
        kod = "%04d" % (secrets.randbelow(9000) + 1000)
        with self._kilit:
            self._temizle()
            self._bekleyen[kod] = (time.time() + self.SURE, aciklama, islev)
        raise OnayIstegi(
            "Bu işlem tehlikeli olabilir: %s\nÇalıştırmak için iki dakika "
            "içinde şunu yazın ya da söyleyin: ONAY %s\nVazgeçmek için: "
            "İPTAL" % (aciklama, kod))

    def _temizle(self):
        simdi = time.time()
        for kod in [k for k, (son, _, _) in self._bekleyen.items()
                    if son < simdi]:
            del self._bekleyen[kod]

    def onayla(self, kod):
        """Kod doğruysa bekleyen işlemi çalıştırıp sonucunu döndürür."""
        with self._kilit:
            self._temizle()
            kayit = self._bekleyen.pop(kod, None)
        if kayit is None:
            return "Bu onay kodu geçersiz ya da süresi dolmuş."
        try:
            return kayit[2]()
        except OSError as hata:
            return "İşlem tamamlanamadı: %s" % hata

    def iptal(self):
        """Bekleyen tüm işlemleri iptal eder; iptal edilen sayıyı verir."""
        with self._kilit:
            sayi = len(self._bekleyen)
            self._bekleyen.clear()
        return sayi

    def bekleyen_var_mi(self):
        with self._kilit:
            self._temizle()
            return bool(self._bekleyen)
