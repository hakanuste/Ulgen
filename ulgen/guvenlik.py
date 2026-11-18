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
    r"parola|password|maaş|maas|borcum|banka\s*hesab|sağl[ıi]k|"
    r"tapu|parsel|arazim|arsam|adresim|konumum|ev\s*adres)", re.IGNORECASE)


def duyarli_mi(metin):
    """Metin sağlık/kimlik/finans/parola gibi duyarlı veri içeriyor mu?

    Sezgiseldir (anahtar sözcük). Yanlış negatif olabilir; kesin koruma
    değil, ek bir önlemdir.
    """
    return bool(DUYARLI_DESENI.search(metin or ""))


# Her zaman kişisel olan: kimlik, parola, para, mülk, adres
_KIMLIK_SOZ = re.compile(
    r"\b(tc\s*kimlik|kimlik\s*no|iban|kredi\s*kart|kart\s*numaras|şifre|sifre|"
    r"parola|password|maaş|maas|borcum|banka\s*hesab|tapu|parsel|arazim|"
    r"arsam|adresim|konumum|ev\s*adres)", re.IGNORECASE)
# Sağlık sözcükleri: tek başına genel bilgi sorusudur ("İbn Sina sarılığı
# nasıl tedavi eder?"); BİRİNCİ TEKİL iyelikle (ilacım, tansiyonum,
# hastalığım, ilaçlarımı) ya da "benim/bende/kullandığım" ile kişiseldir.
_SAGLIK_KOK = (r"(ilaç|ilac|hap|tansiyon|şeker|seker|insülin|insulin|teşhis|"
               r"teshis|tedavi|reçete|recete|hastalı|hastalığ|hastalig|kanser|"
               r"ameliyat|doz|nabz|nabız|nabiz|uyku|ağrı|agri|sağlığ|saglig|"
               r"kolesterol|tahlil|migren|alerji|tahlil|kan\s*değer)")
_SAGLIK_IYELIK = re.compile(
    r"\b" + _SAGLIK_KOK + r"\w*?(ım|im|um|üm|m)"
    r"(ı|i|u|ü|a|e|da|de|dan|den|la|le|ın|in|un|ün)?\b", re.IGNORECASE)
_BEN = re.compile(r"\b(benim|bende|bana|kullandığım|kullandigim|içtiğim|"
                  r"ictigim|aldığım|aldigim|olduğum|oldugum)\b", re.IGNORECASE)
_SAGLIK = re.compile(r"\b" + _SAGLIK_KOK, re.IGNORECASE)


def _kayitli_ilaclar():
    """İlaçlar sayfasına kaydettiğiniz ilaç adları (küçük harf)."""
    try:
        from . import veritabani
        return [r["ad"].strip().lower() for r in veritabani.sorgu(
            "SELECT ad FROM ilac", (), True) if (r["ad"] or "").strip()]
    except Exception:
        return []


def kisisel_mi(metin):
    """Soru SİZE ait kişisel veri mi içeriyor (buluta gitmemeli)?

    Genel sağlık/bitki/tarih soruları kişisel sayılmaz. Kişisel olan:
    kimlik/parola/banka/adres/tapu; birinci tekil iyelikli sağlık sözcüğü
    ("ilacım", "tansiyonum"); "benim/bende/kullandığım" + sağlık sözcüğü;
    İlaçlar sayfasına kaydettiğiniz bir ilacın adı."""
    m = metin or ""
    if _KIMLIK_SOZ.search(m) or _SAGLIK_IYELIK.search(m):
        return True
    if _BEN.search(m) and _SAGLIK.search(m):
        return True
    kucuk = m.lower()
    return any(len(ad) >= 3 and re.search(r"\b%s" % re.escape(ad), kucuk)
               for ad in _kayitli_ilaclar())


# Kimlik bilgisi kalıpları: metin içinde "[gizli]" ile örtülür
_KIMLIK_KALIPLARI = (
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),                  # e-posta
    re.compile(r"\bTR\s?\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.I),  # IBAN
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),                      # kart
    re.compile(r"\b[1-9]\d{10}\b"),                                  # TC no
    re.compile(r"(?:\+90[\s-]?|\b0)?5\d{2}[\s-]?\d{3}[\s-]?\d{2}"
               r"[\s-]?\d{2}\b"),                                    # cep tel
)


def kisisel_ayikla(metin):
    """Buluta gidecek metinden kişisel verileri ayıklar.

    Sağlık, ilaç, kimlik, parola, banka, adres, tapu gibi duyarlı sözcük
    geçen satırlar tümüyle atılır; kalan satırlardaki e-posta, telefon,
    IBAN, kart ve TC kimlik numaraları "[gizli]" ile örtülür. Notun geri
    kalanı (ölçüler, kılavuz bilgisi, teknik konular) olduğu gibi kalır.
    """
    satirlar = []
    for satir in (metin or "").splitlines():
        if DUYARLI_DESENI.search(satir):
            continue
        for kalip in _KIMLIK_KALIPLARI:
            satir = kalip.sub("[gizli]", satir)
        satirlar.append(satir)
    return "\n".join(satirlar).strip()


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
