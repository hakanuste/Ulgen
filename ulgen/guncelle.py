"""Kendini güncelleme: GitHub deposundan ya da yerel bir zip dosyasından.

Yalnız kod (``ulgen/``) ve birkaç kök dosya değişir; ortam (venv), veri,
yedekler ve anahtarlar korunur. Eski kod ``eski/guncelleme-ZAMAN`` altına
yedeklenir ve ``geri_al()`` ile geri getirilebilir. Zip içindeki her yol
denetlenir (dışarı taşan yol reddedilir), tüm .py dosyaları derlenebilirlik
için denenir. Yalnız https://github.com adresleri kullanılır."""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

from . import ag, ayar

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AZAMI_BAYT = 40 * 1024 * 1024
KOK_DOSYALARI = ("requirements.txt", "requirements-ses.txt", "CHANGELOG.md",
                 "PROJECT_STATUS.md", "ARCHITECTURE.md", "INSTALLATION.md",
                 "KURULUM.txt", "SAGLIK_KESTIRME.md", "SECURITY_REPORT.md",
                 "TEST_DEVICE.md", "TEST_REPORT.md", "ROADMAP.md",
                 "Ülgen Kur.command")
DEPO_DESENI = re.compile(r"^(?!\.)(?!.*\.\.)[A-Za-z0-9_.-]{1,60}/[A-Za-z0-9_.-]{1,100}$")
DAL_DESENI = re.compile(r"^[A-Za-z0-9_./-]{1,60}$")
SURUM_DESENI = re.compile(r'__surum__\s*=\s*"([^"]+)"')


class GuncellemeHatasi(Exception):
    pass


def kurulu_surum():
    from . import __surum__
    return __surum__


def _surum_oku(metin):
    e = SURUM_DESENI.search(metin)
    return e.group(1) if e else None


def surum_anahtari(s):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", s))


def _token():
    from . import gizli
    return gizli.sir_oku("github") or ayar.yukle().get("github_anahtar", "")


def _al(adres, token="", azami=AZAMI_BAYT):
    if not adres.startswith("https://") or \
            adres.split("/")[2] not in ("api.github.com", "codeload.github.com",
                                        "raw.githubusercontent.com"):
        raise GuncellemeHatasi("yalnız github.com adresleri kullanılır")
    istek = urllib.request.Request(adres)
    istek.add_header("User-Agent", "ulgen-guncelle")
    if token:
        istek.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(istek, timeout=60,
                                    context=ag.baglam()) as r:
            veri = r.read(azami + 1)
    except Exception as hata:
        raise GuncellemeHatasi("indirilemedi: %s" % hata) from hata
    if len(veri) > azami:
        raise GuncellemeHatasi("dosya çok büyük")
    return veri


def ayarlar():
    a = ayar.yukle()
    depo, dal = str(a.get("guncelleme_depo", "")), str(
        a.get("guncelleme_dal", "main"))
    if not DEPO_DESENI.match(depo):
        raise GuncellemeHatasi("Depo ayarlı değil (örn. kullanici/Ulgen).")
    if not DAL_DESENI.match(dal) or ".." in dal:
        raise GuncellemeHatasi("Dal adı geçersiz.")
    return depo, dal


def uzak_surum():
    depo, dal = ayarlar()
    token = _token()
    if token:
        adres = "https://api.github.com/repos/%s/contents/ulgen/__init__.py?ref=%s" % (depo, dal)
        veri = _al(adres, token, 100000)
        import base64
        import json
        veri = base64.b64decode(json.loads(veri)["content"])
    else:
        veri = _al("https://raw.githubusercontent.com/%s/%s/ulgen/__init__.py"
                   % (depo, dal), "", 100000)
    s = _surum_oku(veri.decode("utf-8", "replace"))
    if not s:
        raise GuncellemeHatasi("Depoda sürüm bulunamadı.")
    return s


def durum():
    kurulu = kurulu_surum()
    try:
        uzak = uzak_surum()
    except GuncellemeHatasi as hata:
        return {"kurulu": kurulu, "uzak": None, "yeni_var": False,
                "hata": str(hata)}
    return {"kurulu": kurulu, "uzak": uzak, "hata": "",
            "yeni_var": surum_anahtari(uzak) > surum_anahtari(kurulu)}


def _zip_indir():
    depo, dal = ayarlar()
    token = _token()
    if token:
        adres = "https://api.github.com/repos/%s/zipball/%s" % (depo, dal)
    else:
        adres = "https://codeload.github.com/%s/zip/refs/heads/%s" % (depo, dal)
    veri = _al(adres, token)
    gecici = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    gecici.write(veri)
    gecici.close()
    return gecici.name


def _on_ek(z):
    """Zip içinde ``ulgen/__init__.py``'nin bulunduğu üst klasör öneki."""
    for ad in z.namelist():
        if ad.endswith("ulgen/__init__.py") and ad.count("/") <= 2:
            return ad[:-len("ulgen/__init__.py")]
    raise GuncellemeHatasi("Zip içinde ulgen/__init__.py yok.")


def _guvenli_yol(hedef_kok, goreli):
    yol = os.path.normpath(os.path.join(hedef_kok, goreli))
    if not (yol == hedef_kok or yol.startswith(hedef_kok + os.sep)):
        raise GuncellemeHatasi("zip içinde güvensiz yol: %s" % goreli)
    return yol


def _sha(yol):
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def calistirilabilir_yap(kok):
    """.command ve .sh dosyalarına çalıştırma izni verir (zip açılırken izin kaybolur)."""
    for dizin, _, dosyalar in os.walk(kok):
        if os.sep + "ortam" in dizin + os.sep or os.sep + "eski" in dizin + os.sep:
            continue
        for d in dosyalar:
            if d.endswith((".command", ".sh")):
                yol = os.path.join(dizin, d)
                try:
                    os.chmod(yol, os.stat(yol).st_mode | 0o111)
                except OSError:
                    pass


def uygula_zip(zip_yolu, kok=KOK, bagimlilik_kur=True):
    """Zip'teki kodu kuruluma uygular; {'eski','yeni','yedek'} döndürür."""
    zaman = time.strftime("%Y%m%d-%H%M%S")
    gecici = tempfile.mkdtemp(prefix="ulgen-guncelle-")
    try:
        try:
            z = zipfile.ZipFile(zip_yolu)
        except zipfile.BadZipFile as hata:
            raise GuncellemeHatasi("Zip dosyası bozuk.") from hata
        with z:
            onek = _on_ek(z)
            toplam = 0
            for bilgi in z.infolist():
                if not bilgi.filename.startswith(onek) or bilgi.is_dir():
                    continue
                goreli = bilgi.filename[len(onek):]
                if not (goreli.startswith("ulgen/") or goreli in KOK_DOSYALARI):
                    continue
                if "__pycache__" in goreli or goreli.endswith(".pyc"):
                    continue
                toplam += bilgi.file_size
                if toplam > AZAMI_BAYT * 3:
                    raise GuncellemeHatasi("zip çok büyük")
                hedef = _guvenli_yol(gecici, goreli)
                os.makedirs(os.path.dirname(hedef), exist_ok=True)
                with z.open(bilgi) as kaynak, open(hedef, "wb") as cikti:
                    shutil.copyfileobj(kaynak, cikti)
        yeni_paket = os.path.join(gecici, "ulgen")
        init = os.path.join(yeni_paket, "__init__.py")
        if not os.path.isfile(init):
            raise GuncellemeHatasi("Zip içinde ulgen/__init__.py yok.")
        with open(init, encoding="utf-8") as f:
            yeni_surum = _surum_oku(f.read())
        if not yeni_surum:
            raise GuncellemeHatasi("Zip'te sürüm numarası yok.")
        for dizin, _, dosyalar in os.walk(yeni_paket):    # derlenebilir mi?
            for d in dosyalar:
                if d.endswith(".py"):
                    yol = os.path.join(dizin, d)
                    try:
                        with open(yol, "rb") as f:
                            compile(f.read(), yol, "exec", dont_inherit=True)
                    except (SyntaxError, ValueError) as hata:
                        raise GuncellemeHatasi("Kod derlenemedi, güncelleme "
                                               "iptal: %s: %s" % (d, hata)) from hata
        eski_surum = kurulu_surum()
        eski_req = _sha(os.path.join(kok, "requirements.txt"))
        yedek = os.path.join(kok, "eski", "guncelleme-" + zaman)
        sayac = 1
        while os.path.exists(yedek):                 # aynı saniyede ikinci güncelleme
            sayac += 1
            yedek = os.path.join(kok, "eski", "guncelleme-%s-%d" % (zaman, sayac))
        os.makedirs(yedek)
        mevcut = os.path.join(kok, "ulgen")
        if os.path.isdir(mevcut):
            shutil.copytree(mevcut, os.path.join(yedek, "ulgen"),
                            ignore=shutil.ignore_patterns("__pycache__"))
        for ad in KOK_DOSYALARI:
            if os.path.isfile(os.path.join(kok, ad)):
                shutil.copy2(os.path.join(kok, ad), os.path.join(yedek, ad))
        # kodu değiştir: eskiyi kenara al, yeniyi yerine koy; olmazsa geri al
        kenar = os.path.join(kok, ".ulgen-eski-" + zaman)
        try:
            if os.path.isdir(mevcut):
                os.rename(mevcut, kenar)
            shutil.copytree(yeni_paket, mevcut)
        except Exception as hata:
            shutil.rmtree(mevcut, ignore_errors=True)
            if os.path.isdir(kenar):
                os.rename(kenar, mevcut)
            raise GuncellemeHatasi("Dosyalar yerleştirilemedi, eski kod "
                                   "geri konuldu: %s" % hata) from hata
        shutil.rmtree(kenar, ignore_errors=True)
        for ad in KOK_DOSYALARI:
            kaynak = os.path.join(gecici, ad)
            if os.path.isfile(kaynak):
                shutil.copy2(kaynak, os.path.join(kok, ad))
        calistirilabilir_yap(kok)
        if bagimlilik_kur and eski_req != _sha(os.path.join(kok, "requirements.txt")):
            _bagimlilik_kur(kok)
        eskiyi_temizle(kok)
        return {"eski": eski_surum, "yeni": yeni_surum, "yedek": yedek}
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _bagimlilik_kur(kok):
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                        os.path.join(kok, "requirements.txt")],
                       timeout=900, check=False, capture_output=True)
    except (OSError, subprocess.TimeoutExpired):
        pass


def depodan_guncelle(kok=KOK):
    zip_yolu = _zip_indir()
    try:
        return uygula_zip(zip_yolu, kok)
    finally:
        try:
            os.remove(zip_yolu)
        except OSError:
            pass


ESKI_KURALLARI = (("guncelleme-", 3), ("Ülgen.app-", 1), ("ulgen-", 1))


def eskiyi_temizle(kok=KOK):
    """``eski/`` içinde birikenleri budar: güncelleme yedeklerinden en yeni 3,
    eski uygulama simgesinden ve eski kod kopyasından en yeni 1 kalır. Silinen
    adları döndürür. Hata olursa sessizce geçer (güncellemeyi bozmaz)."""
    klasor = os.path.join(kok, "eski")
    if not os.path.isdir(klasor):
        return []
    silinen = []
    for onek, sakla in ESKI_KURALLARI:
        adlar = sorted((a for a in os.listdir(klasor) if a.startswith(onek)),
                       reverse=True)
        for ad in adlar[sakla:]:
            yol = os.path.join(klasor, ad)
            try:
                if os.path.isdir(yol) and not os.path.islink(yol):
                    shutil.rmtree(yol)
                else:
                    os.remove(yol)
                silinen.append(ad)
            except OSError:
                pass
    return silinen


def yedekler(kok=KOK):
    klasor = os.path.join(kok, "eski")
    if not os.path.isdir(klasor):
        return []
    return sorted(d for d in os.listdir(klasor)
                  if d.startswith("guncelleme-")
                  and os.path.isdir(os.path.join(klasor, d, "ulgen")))


def geri_al(kok=KOK):
    """En yeni güncelleme yedeğindeki kodu geri koyar."""
    liste = yedekler(kok)
    if not liste:
        raise GuncellemeHatasi("Geri alınacak güncelleme yedeği yok.")
    son = os.path.join(kok, "eski", liste[-1])
    zaman = time.strftime("%Y%m%d-%H%M%S")
    mevcut = os.path.join(kok, "ulgen")
    kenar = os.path.join(kok, ".ulgen-geri-" + zaman)
    if os.path.isdir(mevcut):
        os.rename(mevcut, kenar)
    try:
        shutil.copytree(os.path.join(son, "ulgen"), mevcut)
    except Exception as hata:
        shutil.rmtree(mevcut, ignore_errors=True)
        if os.path.isdir(kenar):
            os.rename(kenar, mevcut)
        raise GuncellemeHatasi("Geri alınamadı: %s" % hata) from hata
    shutil.rmtree(kenar, ignore_errors=True)
    for ad in KOK_DOSYALARI:
        if os.path.isfile(os.path.join(son, ad)):
            shutil.copy2(os.path.join(son, ad), os.path.join(kok, ad))
    return liste[-1]


def yeniden_baslat():
    """Servisi (launchd) kısa gecikmeyle yeniden başlatır; Mac dışında False."""
    if sys.platform != "darwin":
        return False
    try:
        subprocess.Popen(
            ["/bin/sh", "-c", "sleep 2; /bin/launchctl kickstart -k gui/%d/"
             "com.ulgen.sunucu" % os.getuid()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        return True
    except OSError:
        return False
