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


def hazirlik_hatasi(adres, giris_gerekli=True):
    """Okumadan önce denetimler; sorun varsa kullanıcıya iletisi, yoksa None."""
    from .ajanlar import adres_guvenli_mi
    if not hazir_mi():
        return "Oturumlu okuyucu kurulu değil. " + YUKLE_IPUCU
    if not adres_guvenli_mi(_tam(adres)):
        return "Bu adres güvenlik nedeniyle okunamaz."
    if not alan_izinli_mi(adres):
        return ("Bu site eklenmemiş. Önce: 'kaynak ekle: AKÇA %s' (ya da "
                "başka bir uzman)." % (urlparse(_tam(adres)).hostname or adres))
    if giris_gerekli and not profil_var_mi():
        return "Henüz giriş yapılmadı. Önce: 'giris: %s'" % adres
    return None


SATIRLAR_BETIGI = """() => {
  const sat = [...document.querySelectorAll('tr, [role="row"]')];
  return sat.map(r => [...r.querySelectorAll(
      'td, th, [role="cell"], [role="gridcell"], [role="columnheader"]')]
    .map(c => { const v = c.querySelector('svg');
      return {t: (c.innerText || '').trim(),
              s: v ? v.outerHTML.replace(/\\s+/g, '').slice(0, 400) : ''}; }))
    .filter(r => r.length);
}"""
BAGLANTILAR_BETIGI = """() => [...document.querySelectorAll('a[href]')]
    .map(a => a.getAttribute('href'))"""


class Okuyucu:
    """Tek tarayıcı oturumunda birçok sayfa okur (salt okuma, ekransız)."""

    def __init__(self, bekleme_sn=3.0):
        self.bekleme = bekleme_sn

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        _profil_hazirla()
        _KILIT.acquire()
        try:
            self._p = sync_playwright().start()
            self.ctx = self._p.chromium.launch_persistent_context(
                PROFIL, headless=True, accept_downloads=False)
            _cerez_yukle(self.ctx)
            self.sayfa = (self.ctx.pages[0] if self.ctx.pages
                          else self.ctx.new_page())
        except BaseException:
            _KILIT.release()
            raise
        return self

    def __exit__(self, *a):
        try:
            _cerez_kaydet(self.ctx)
            self.ctx.close()
            self._p.stop()
        finally:
            _KILIT.release()

    def ac(self, adres):
        self.sayfa.goto(_tam(adres), timeout=ZAMAN_ASIMI_MS,
                        wait_until="domcontentloaded")
        try:
            self.sayfa.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    def kaydir_ve_satirlar(self, adim=12):
        """Sanal (kaydırdıkça yüklenen) tablolar için kaydırıp satır toplar."""
        gorulen, sirali = set(), []
        for _ in range(adim):
            for r in self.sayfa.evaluate(SATIRLAR_BETIGI):
                anahtar = tuple(c["t"] for c in r)
                if anahtar not in gorulen:
                    gorulen.add(anahtar)
                    sirali.append(r)
            onceki = len(gorulen)
            self.sayfa.evaluate("""() => {
              const k = [...document.querySelectorAll('*')].filter(e =>
                e.scrollHeight > e.clientHeight + 40 &&
                /(auto|scroll)/.test(getComputedStyle(e).overflowY));
              k.forEach(e => e.scrollBy(0, e.clientHeight * 0.8));
              window.scrollBy(0, window.innerHeight * 0.8); }""")
            self.sayfa.wait_for_timeout(500)
            yeni = {tuple(c["t"] for c in r)
                    for r in self.sayfa.evaluate(SATIRLAR_BETIGI)}
            if not (yeni - gorulen) and len(gorulen) == onceki:
                break
        return sirali

    def metin(self):
        return self.sayfa.inner_text("body")

    def baglantilar(self):
        return self.sayfa.evaluate(BAGLANTILAR_BETIGI)


def oturumlu_oku(adres):
    """Araç/komut girişi: izin, güvenlik ve bileşen denetimleriyle okur."""
    sorun = hazirlik_hatasi(adres)
    if sorun:
        return sorun
    try:
        return oku(adres)
    except Exception as hata:
        return "Sayfa okunamadı: %s" % str(hata)[:160]


FINANS_ALAN = re.compile(r"fintables|isyatirim|matriks|foreks|kap\.org|borsa|yatirim|"
                         r"menkul|invest|finans|bloomberg|tradingview|midas|"
                         r"garantibbva|akbank|ziraat|qnb|ykyatirim|gedik", re.IGNORECASE)


BEKLE_SN = 6        # pencere açılmadan süreç ölürse yakalamak için


def _hata_ozeti(gunluk):
    """Günlükteki hatayı sade Türkçe öneriyle döndürür."""
    try:
        with open(gunluk, encoding="utf-8", errors="replace") as f:
            metin = f.read()[-3000:]
    except OSError:
        metin = ""
    son = [s for s in metin.strip().splitlines() if s.strip()][-1:] or [""]
    if "Executable doesn't exist" in metin or "playwright install" in metin:
        oneri = ("Chromium indirilmemiş. Terminal'de: ~/Ülgen/ortam/bin/python -m "
                 "playwright install chromium")
    elif "No module named" in metin:
        oneri = ("Playwright Ülgen'in ortamına kurulmamış. Terminal'de: "
                 "~/Ülgen/ortam/bin/python -m pip install playwright")
    elif "Host system is missing" in metin or "not supported" in metin.lower() \
            or "unsupported" in metin.lower():
        oneri = ("Bu macOS sürümü Playwright'ın bu sürümünü desteklemiyor olabilir; "
                 "hata satırını Claude'a iletin.")
    elif "ProcessSingleton" in metin or "SingletonLock" in metin:
        oneri = ("Önceki bir giriş penceresi hâlâ açık görünüyor; onu kapatıp "
                 "yeniden deneyin.")
    else:
        oneri = "Ayrıntı: %s (tam günlük: %s)" % (son[0][:200], gunluk)
    return oneri


def uzman_tahmin(alan):
    """Site adından uzman: finans siteleri AKÇA; yoksa None."""
    return "AKÇA" if FINANS_ALAN.search(alan or "") else None


def giris_baslat(adres):
    """Girişi ayrı süreçte başlatır (sunucu kilitlenmesin)."""
    from .ajanlar import adres_guvenli_mi
    if not hazir_mi():
        return "Oturumlu okuyucu kurulu değil. " + YUKLE_IPUCU
    if not adres_guvenli_mi(_tam(adres)):
        return "Bu adres güvenlik nedeniyle açılamaz."
    ek = ""
    if not alan_izinli_mi(adres):
        # 'giris:' yazmak o siteye girme izni demektir: siteyi uygun uzmanın
        # kaynaklarına kendiliğinden ekle (finans siteleri AKÇA'ya).
        alan = urlparse(_tam(adres)).hostname or adres
        uzman = uzman_tahmin(alan)
        if not uzman:
            return ("Bu siteyi hangi uzmana ekleyeyim? Örnek: 'kaynak ekle: "
                    "AKÇA %s', sonra yeniden 'giris: %s'." % (alan, adres))
        from . import uzmanlar
        ek = uzmanlar.komut("kaynak ekle: %s %s" % (uzman, alan)) + "\n"
    # Hata gizli kalmasın: çıktı günlüğe yazılır; süreç hemen ölürse neden
    # sohbette söylenir. Çalışma klasörü paketin bulunduğu yer (modül bulunsun).
    gunluk = os.path.join(ayar.KLASOR, "oturum_giris.log")
    with open(gunluk, "w", encoding="utf-8") as g:
        surec = subprocess.Popen(
            [sys.executable, "-m", "ulgen.oturum", "giris", _tam(adres)],
            stdout=g, stderr=subprocess.STDOUT, start_new_session=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for _ in range(BEKLE_SN * 2):
        if surec.poll() is not None:
            break
        time.sleep(0.5)
    if surec.poll() is not None:
        return ek + "Giriş penceresi açılamadı.\n" + _hata_ozeti(gunluk)
    return ek + ("Bir tarayıcı penceresi açılıyor. Siteye KENDİNİZ giriş "
                 "yapın (şifreyi Ülgen görmez), sonra pencereyi kapatın. "
                 "Ardından: 'oturumlu oku: %s'" % adres)


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
