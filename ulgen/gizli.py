"""Hafıza dosyasını diskte şifreleme (Fernet / AES, ücretsiz 'cryptography').

Anahtar önce macOS Anahtar Zinciri'nde (Keychain) saklanır; olmazsa
~/ÜlgenVeri/bellek.anahtar dosyasında (yalnızca sizin okuyabileceğiniz
izinle). Amaç: dosya yedeğe, buluta ya da başkasının eline geçerse düz
yazı olarak okunmasın. Bilgisayarınıza girmiş biri için tam koruma değildir.
"""

import os
import subprocess
import sys

from . import ayar

ONEK = b"ULGEN1:"
HIZMET = "ulgen-bellek"
ANAHTAR_DOSYASI = os.path.join(ayar.KLASOR, "bellek.anahtar")


class AnahtarYok(Exception):
    """Dosya şifreli ama anahtar bulunamadı ya da çözülemedi."""


def kullanilabilir_mi():
    try:
        import cryptography.fernet  # noqa: F401
        return True
    except ImportError:
        return False


def _zincirden_oku():
    if sys.platform != "darwin":
        return None
    try:
        sonuc = subprocess.run(
            ["security", "find-generic-password", "-s", HIZMET, "-w"],
            capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    anahtar = sonuc.stdout.strip()
    return anahtar.encode() if sonuc.returncode == 0 and anahtar else None


def _zincire_yaz(anahtar):
    if sys.platform != "darwin":
        return False
    try:
        sonuc = subprocess.run(
            ["security", "add-generic-password", "-U", "-s", HIZMET,
             "-a", "ulgen", "-w", anahtar.decode()],
            capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return sonuc.returncode == 0


def anahtar_al(olustur=True):
    """Şifreleme anahtarını verir; yoksa (olustur ise) üretir."""
    from cryptography.fernet import Fernet
    anahtar = _zincirden_oku()
    if anahtar:
        return anahtar
    if os.path.exists(ANAHTAR_DOSYASI):
        with open(ANAHTAR_DOSYASI, "rb") as dosya:
            return dosya.read().strip()
    if not olustur:
        raise AnahtarYok("Şifreleme anahtarı bulunamadı.")
    anahtar = Fernet.generate_key()
    if not _zincire_yaz(anahtar):
        ayar.klasor_hazirla()
        with open(ANAHTAR_DOSYASI, "wb") as dosya:
            dosya.write(anahtar)
        os.chmod(ANAHTAR_DOSYASI, 0o600)
    return anahtar


def sifrele(veri):
    """Baytları şifreler (kütüphane yoksa olduğu gibi döndürür)."""
    if not kullanilabilir_mi():
        return veri
    from cryptography.fernet import Fernet
    return ONEK + Fernet(anahtar_al()).encrypt(veri)


def coz(veri):
    """Şifreliyse çözer; düz yazıysa olduğu gibi döndürür."""
    if not veri.startswith(ONEK):
        return veri
    if not kullanilabilir_mi():
        raise AnahtarYok("'cryptography' kütüphanesi yüklü değil.")
    from cryptography.fernet import Fernet, InvalidToken
    try:
        return Fernet(anahtar_al(False)).decrypt(veri[len(ONEK):])
    except (InvalidToken, ValueError) as hata:
        raise AnahtarYok("Hafıza dosyası çözülemedi.") from hata
