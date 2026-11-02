"""Şifreleme ve sır (anahtar/parola) saklama.

  * Hafıza dosyası ve CA anahtarı AES-256-GCM ile şifrelenir ("ULGEN2:").
    Eski Fernet kayıtları ("ULGEN1:") okunur ve ilk yazışta yenilenir.
  * Ana anahtar (32 bayt) macOS Anahtar Zinciri'nde (Keychain) tutulur;
    olmazsa ~/ÜlgenVeri/bellek.anahtar dosyasında (izin 600).
  * API anahtarları gibi sırlar Anahtar Zinciri'ne yazılır; Mac dışında
    ana anahtarla şifreli ``sirlar.bin`` dosyasına.
Bilgisayarınıza oturum açmış biri için tam koruma değildir; dosya yedeği
ya da disk kopyası ele geçirenlere karşı korur.
"""

import base64
import json
import os
import subprocess
import sys
import time

from . import ayar

ONEK = b"ULGEN1:"      # eski Fernet biçimi (yalnızca okunur)
ONEK2 = b"ULGEN2:"     # AES-256-GCM
HIZMET = "ulgen-bellek"
SIR_HIZMETI = "ulgen-sir-"


def _anahtar_dosyasi():
    return os.path.join(ayar.KLASOR, "bellek.anahtar")


def _sirlar_dosyasi():
    return os.path.join(ayar.KLASOR, "sirlar.bin")


class AnahtarYok(Exception):
    """Dosya şifreli ama anahtar bulunamadı ya da çözülemedi."""


def kullanilabilir_mi():
    try:
        import cryptography.hazmat.primitives.ciphers.aead  # noqa: F401
        return True
    except ImportError:
        return False


# ------------------------------------------------------- Anahtar Zinciri

def _zincirden_oku(hizmet):
    if sys.platform != "darwin":
        return None
    try:
        sonuc = subprocess.run(
            ["security", "find-generic-password", "-s", hizmet, "-w"],
            capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    deger = sonuc.stdout.strip()
    return deger if sonuc.returncode == 0 and deger else None


def _zincire_yaz(hizmet, deger):
    # Not: -w değeri komut satırında kısa süre aynı kullanıcının süreçlerince
    # görülebilir (ps). macOS'ta betikten yazmanın başka yolu yoktur.
    if sys.platform != "darwin":
        return False
    try:
        sonuc = subprocess.run(
            ["security", "add-generic-password", "-U", "-s", hizmet,
             "-a", "ulgen", "-w", deger],
            capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return sonuc.returncode == 0


# --------------------------------------------------------- ana anahtar

def _anahtar_coz(metin):
    ham = base64.urlsafe_b64decode(metin.strip() + "=" * (-len(metin) % 4))
    if len(ham) != 32:
        raise AnahtarYok("Anahtar uzunluğu geçersiz.")
    return ham


def ana_anahtar(olustur=True):
    """32 baytlık ana anahtarı verir; yoksa (olustur ise) üretir."""
    metin = _zincirden_oku(HIZMET)
    if metin:
        return _anahtar_coz(metin)
    dosya = _anahtar_dosyasi()
    if os.path.exists(dosya):
        with open(dosya, "r", encoding="ascii") as f:
            return _anahtar_coz(f.read())
    if not olustur:
        raise AnahtarYok("Şifreleme anahtarı bulunamadı.")
    ham = os.urandom(32)
    metin = base64.urlsafe_b64encode(ham).decode("ascii")
    if not _zincire_yaz(HIZMET, metin):
        ayar.klasor_hazirla()
        with open(dosya, "w", encoding="ascii") as f:
            f.write(metin)
        os.chmod(dosya, 0o600)
    return ham


# ----------------------------------------------------------- şifreleme

def aes_sifrele(anahtar, veri, ilgili=b""):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    return nonce + AESGCM(anahtar).encrypt(nonce, veri, ilgili)


def aes_coz(anahtar, veri, ilgili=b""):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(veri) < 28:
        raise AnahtarYok("Şifreli veri bozuk.")
    try:
        return AESGCM(anahtar).decrypt(veri[:12], veri[12:], ilgili)
    except InvalidTag as hata:
        raise AnahtarYok("Veri çözülemedi (yanlış anahtar ya da bozuk "
                         "dosya).") from hata


def sifrele(veri):
    """Baytları AES-256-GCM ile şifreler (kütüphane yoksa düz döner)."""
    if not kullanilabilir_mi():
        return veri
    return ONEK2 + aes_sifrele(ana_anahtar(), veri)


def coz(veri):
    """Şifreliyse çözer; düz yazıysa olduğu gibi döndürür."""
    if veri.startswith(ONEK2):
        if not kullanilabilir_mi():
            raise AnahtarYok("'cryptography' kütüphanesi yüklü değil.")
        return aes_coz(ana_anahtar(False), veri[len(ONEK2):])
    if veri.startswith(ONEK):
        try:
            from cryptography.fernet import Fernet, InvalidToken
        except ImportError as hata:
            raise AnahtarYok("'cryptography' yüklü değil.") from hata
        anahtar = base64.urlsafe_b64encode(ana_anahtar(False))
        try:
            return Fernet(anahtar).decrypt(veri[len(ONEK):])
        except (InvalidToken, ValueError) as hata:
            raise AnahtarYok("Hafıza dosyası çözülemedi.") from hata
    return veri


def sifreli_mi(veri):
    return veri.startswith(ONEK2)


# ---------------------------------------------------------------- sırlar

_SIR_ONBELLEK = {}


def _sirlari_oku():
    try:
        with open(_sirlar_dosyasi(), "rb") as f:
            return json.loads(coz(f.read()).decode("utf-8"))
    except (OSError, ValueError, AnahtarYok):
        return {}


def sir_yaz(ad, deger):
    """Sırrı Anahtar Zinciri'ne (olmazsa şifreli dosyaya) yazar."""
    _SIR_ONBELLEK.pop(ad, None)
    if _zincire_yaz(SIR_HIZMETI + ad, deger):
        return "anahtar zinciri"
    ayar.klasor_hazirla()
    sirlar = _sirlari_oku()
    sirlar[ad] = deger
    ham = json.dumps(sirlar).encode("utf-8")
    gecici = _sirlar_dosyasi() + ".tmp"
    with open(gecici, "wb") as f:
        f.write(sifrele(ham))
    os.chmod(gecici, 0o600)
    os.replace(gecici, _sirlar_dosyasi())
    return "şifreli dosya"


def sir_oku(ad):
    """Sırrı verir (60 sn önbellekli); yoksa boş metin."""
    simdi = time.time()
    onbellek = _SIR_ONBELLEK.get(ad)
    if onbellek and simdi - onbellek[0] < 60:
        return onbellek[1]
    deger = _zincirden_oku(SIR_HIZMETI + ad) or _sirlari_oku().get(ad, "")
    _SIR_ONBELLEK[ad] = (simdi, deger)
    return deger
