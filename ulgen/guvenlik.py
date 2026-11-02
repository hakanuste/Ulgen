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

# Çalıştırılması onay gerektiren komut adları
TEHLIKELI_KOMUTLAR = frozenset({
    "rm", "rmdir", "unlink", "del", "erase", "srm", "shred", "format",
    "mkfs", "newfs", "fdisk", "diskutil", "dd", "sudo", "su", "doas",
    "chmod", "chown", "chgrp", "mv", "kill", "killall", "pkill",
    "shutdown", "reboot", "halt", "launchctl", "crontab", "osascript",
    "defaults", "csrutil", "nvram", "tmutil", "ln", "truncate", "sh",
    "bash", "zsh", "eval", "exec", "curl", "wget", "scp", "ssh", "nc",
})

# Erişimi onay gerektiren kritik yollar
KRITIK_YOLLAR = (
    "/etc", "/system", "/library", "/usr", "/bin", "/sbin", "/private",
    "/var", "/dev", "/volumes", "/applications",
)

KRITIK_ONEKLER = (".ssh", ".gnupg", ".aws", ".config/gcloud", ".kube")

BIRLESIK_KOMUT = re.compile(r"[;&|`><]|\$\(")

SAYI_SOZCUKLERI = {
    "sıfır": "0", "sifir": "0", "bir": "1", "iki": "2", "üç": "3", "uc": "3",
    "dört": "4", "dort": "4", "beş": "5", "bes": "5", "altı": "6",
    "alti": "6", "yedi": "7", "sekiz": "8", "dokuz": "9",
}


def _kritik_yol_mu(parca):
    """Bir komut argümanı kritik bir yolu gösteriyor mu?"""
    if not parca or parca.startswith("-"):
        return False
    yol = os.path.realpath(os.path.expanduser(parca))
    kucuk = yol.lower()
    for kritik in KRITIK_YOLLAR:
        if kucuk == kritik or kucuk.startswith(kritik + "/"):
            return True
    ev = ayar.EV.lower()
    for onek in KRITIK_ONEKLER:
        if kucuk.startswith(os.path.join(ev, onek)):
            return True
    gizli = (ayar.ANAHTAR_DOSYASI, ayar.AYAR_DOSYASI, ayar.HAFIZA_DOSYASI)
    return any(yol == os.path.realpath(g) for g in gizli)


def komut_analiz(komut):
    """Komutu inceler. (tehlikeli_mi, neden) çifti döndürür."""
    if BIRLESIK_KOMUT.search(komut):
        return True, "birleşik komut, yönlendirme ya da alt komut içeriyor"
    try:
        parcalar = shlex.split(komut)
    except ValueError:
        return True, "komut ayrıştırılamadı"
    if not parcalar:
        return True, "boş komut"
    ad = os.path.basename(parcalar[0]).lower()
    if ad in TEHLIKELI_KOMUTLAR:
        return True, "'%s' tehlikeli bir komut" % ad
    for parca in parcalar[1:]:
        if _kritik_yol_mu(parca):
            return True, "kritik bir sistem yoluna erişiyor"
    return False, ""


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
