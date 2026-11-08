"""Oturumlu okuyucu: giriş gerektiren sayfaları kullanıcının KENDİ girişiyle okur.

Şifre Ülgen'e hiç girmez ve saklanmaz. Akış:
  1. ``giris: <adres>``  -> ayrı bir tarayıcı penceresi açılır; kullanıcı siteye
     kendisi giriş yapar ve pencereyi kapatır. Oturum çerezleri yalnız bu
     Mac'te ``~/ÜlgenVeri/tarayici`` profilinde kalır.
  2. ``oturumlu oku: <adres>`` -> aynı profille ekransız (headless) açılır,
     sayfanın METNİ okunur. Tıklama, form gönderme, indirme YOKTUR (salt okuma).
Yalnızca kullanıcının ``kaynak ekle`` ile eklediği alan adları okunur.
Sonuçlar kişisel veri sayılır (buluta gitmez). İsteğe bağlı bileşen:
``pip install playwright && playwright install chromium``.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

from . import ayar

PROFIL = os.path.join(ayar.KLASOR, "tarayici")
AZAMI_KARAKTER = 20000
ZAMAN_ASIMI_MS = 30000
_KILIT = threading.Lock()
KOMUT_GIRIS = re.compile(r"^\s*giri[sş]\s*[:\-]\s*(\S+)\s*$", re.IGNORECASE)
KOMUT_OKU = re.compile(r"^\s*oturumlu\s+oku\s*[:\-]\s*(\S+)\s*$",
                       re.IGNORECASE)
YUKLE_IPUCU = ("Bu özellik için bir kez şunu çalıştırın: ~/Ülgen/ortam/bin/pip "
               "install playwright && ~/Ülgen/ortam/bin/playwright install "
               "chromium")


def hazir_mi():
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def profil_var_mi():
    return os.path.isdir(PROFIL) and bool(os.listdir(PROFIL))


def alan_izinli_mi(adres):
    """Yalnız kullanıcının eklediği alan adları (herhangi bir uzman için)."""
    from .uzmanlar import UZMANLAR, _alan, kullanici_kaynaklari
    ana = _alan(adres)
    for ad in UZMANLAR:
        for k in kullanici_kaynaklari(ad):
            a = _alan(k)
            if a and (ana == a or ana.endswith("." + a)):
                return True
    return False


def _tam(adres):
    return adres if "://" in adres else "https://" + adres


def _profil_hazirla():
    os.makedirs(PROFIL, mode=0o700, exist_ok=True)
    try:
        os.chmod(PROFIL, 0o700)
    except OSError:
        pass


def _cerez_yolu():
    return os.path.join(PROFIL, "cerezler.json")


def _cerez_yukle(ctx):
    """Oturum çerezleri (süresiz olanlar tarayıcı kapanınca silinir)."""
    try:
        with open(_cerez_yolu(), "r", encoding="utf-8") as f:
            ctx.add_cookies(json.load(f))
    except (OSError, ValueError):
        pass
    except Exception:
        pass


def _cerez_kaydet(ctx):
    try:
        cerezler = ctx.cookies()
        yol = _cerez_yolu()
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(cerezler, f)
        os.chmod(yol, 0o600)
    except Exception:
        pass


def giris(adres, bekle_sn=900):
    """Görünür pencere açar; kullanıcı pencereyi kapatana dek bekler."""
    from playwright.sync_api import sync_playwright
    _profil_hazirla()
    with _KILIT, sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFIL, headless=False)
        _cerez_yukle(ctx)
        sayfa = ctx.pages[0] if ctx.pages else ctx.new_page()
        sayfa.goto(_tam(adres), timeout=ZAMAN_ASIMI_MS)
        son = time.time() + bekle_sn
        while ctx.pages and time.time() < son:
            _cerez_kaydet(ctx)           # pencere kapanmadan önce de kaydet
            time.sleep(2)
        try:
            ctx.close()
        except Exception:
            pass


def oku(adres, ekransiz=True):
    """Sayfanın görünen metnini döndürür (salt okuma)."""
    from playwright.sync_api import sync_playwright
    _profil_hazirla()
    with _KILIT, sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFIL, headless=ekransiz,
                                                   accept_downloads=False)
        try:
            _cerez_yukle(ctx)
            sayfa = ctx.pages[0] if ctx.pages else ctx.new_page()
            sayfa.goto(_tam(adres), timeout=ZAMAN_ASIMI_MS,
                       wait_until="domcontentloaded")
            try:
                sayfa.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            metin = sayfa.inner_text("body")
            baslik = sayfa.title()
            _cerez_kaydet(ctx)
        finally:
            ctx.close()
    metin = re.sub(r"\n{3,}", "\n\n", metin).strip()
    return "%s\n%s" % (baslik, metin[:AZAMI_KARAKTER])


def oturumlu_oku(adres):
    """Araç/komut girişi: izin, güvenlik ve bileşen denetimleriyle okur."""
    from .ajanlar import adres_guvenli_mi
    if not hazir_mi():
        return "Oturumlu okuyucu kurulu değil. " + YUKLE_IPUCU
    if not adres_guvenli_mi(_tam(adres)):
        return "Bu adres güvenlik nedeniyle okunamaz."
    if not alan_izinli_mi(adres):
        return ("Bu site eklenmemiş. Önce: 'kaynak ekle: AKÇA %s' (ya da "
                "başka bir uzman)." % (urlparse(_tam(adres)).hostname or adres))
    if not profil_var_mi():
        return "Henüz giriş yapılmadı. Önce: 'giris: %s'" % adres
    try:
        return oku(adres)
    except Exception as hata:
        return "Sayfa okunamadı: %s" % str(hata)[:160]


def giris_baslat(adres):
    """Girişi ayrı süreçte başlatır (sunucu kilitlenmesin)."""
    from .ajanlar import adres_guvenli_mi
    if not hazir_mi():
        return "Oturumlu okuyucu kurulu değil. " + YUKLE_IPUCU
    if not adres_guvenli_mi(_tam(adres)):
        return "Bu adres güvenlik nedeniyle açılamaz."
    if not alan_izinli_mi(adres):
        return ("Bu site eklenmemiş. Önce: 'kaynak ekle: AKÇA %s'"
                % (urlparse(_tam(adres)).hostname or adres))
    subprocess.Popen([sys.executable, "-m", "ulgen.oturum", "giris",
                      _tam(adres)], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return ("Bir tarayıcı penceresi açılıyor. Siteye KENDİNİZ giriş yapın "
            "(şifreyi Ülgen görmez), sonra pencereyi kapatın. Ardından: "
            "'oturumlu oku: %s'" % adres)


def komut(metin):
    e = KOMUT_GIRIS.match(metin or "")
    if e:
        return giris_baslat(e.group(1))
    e = KOMUT_OKU.match(metin or "")
    if e:
        return oturumlu_oku(e.group(1))
    return None


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "giris":
        giris(sys.argv[2])
