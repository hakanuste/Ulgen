"""Kod penceresi: arayüzde kod yazıp çalıştırma (Python, Node, Bash).

DİKKAT: Bu bir kum havuzu DEĞİLDİR. Çalıştırılan kod sizin kullanıcı
yetkinizle çalışır ve dosyalarınıza erişebilir. Bu yüzden:
  * Çalıştırma yalnızca açıkça basılan "Çalıştır" düğmesiyle olur; Ülgen'in
    modeli bu modülü çağıramaz (araç kaydında yoktur).
  * Mac'in kendisinden (127.0.0.1) çalışır; iPhone'dan (uzaktan) yalnızca
    ayar.json'da ``uzaktan_kod_calistir: true`` ise.
  * Kodlar ``~/ÜlgenVeri/kod`` klasöründe tutulur; dosya adı doğrulanır, dışarı
    çıkılamaz. Silme yoktur (Ülgen kullanıcı verisi silmez).
  * Ortam değişkenleri (API anahtarları vb.) alt sürece geçirilmez; çıktı ve
    süre sınırlıdır; zaman aşımında süreç grubu öldürülür.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from . import ayar, veritabani

DILLER = {
    "python": {"uzanti": ".py", "komut": lambda: [sys.executable, "-u"]},
    "node": {"uzanti": ".js", "komut": lambda: [shutil.which("node") or "node"]},
    "bash": {"uzanti": ".sh", "komut": lambda: [shutil.which("bash") or "bash"]},
}
AD_DESENI = re.compile(r"^[\w][\w.\- ]{0,58}\.(py|js|sh|txt|md)$")
UZANTI_DIL = {".py": "python", ".js": "node", ".sh": "bash"}
AZAMI_KOD = 200000
CIKTI_SINIRI = 20000
VARSAYILAN_SURE = 30
AZAMI_SURE = 120

_KILIT = threading.Lock()      # aynı anda tek çalıştırma


class KodHatasi(Exception):
    pass


def klasor():
    yol = os.path.join(ayar.KLASOR, "kod")
    os.makedirs(yol, mode=0o700, exist_ok=True)
    return yol


def _yol(ad):
    ad = (ad or "").strip()
    if not AD_DESENI.match(ad) or ".." in ad:
        raise KodHatasi("Geçersiz dosya adı. Harf/rakam/_-. kullanın; "
                        "uzantı .py .js .sh .txt .md olmalı.")
    return os.path.join(klasor(), ad)


def liste():
    return sorted(a for a in os.listdir(klasor()) if AD_DESENI.match(a))


def oku(ad):
    try:
        with open(_yol(ad), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise KodHatasi("Dosya yok.") from None


def kaydet(ad, icerik):
    """Kaydeder. Var olan dosya ezilirse eski sürüm .yedek olarak saklanır."""
    if len(icerik) > AZAMI_KOD:
        raise KodHatasi("Kod çok uzun.")
    yol = _yol(ad)
    if os.path.exists(yol):
        eski = os.path.join(klasor(), "_surumler")
        os.makedirs(eski, mode=0o700, exist_ok=True)
        shutil.copy2(yol, os.path.join(
            eski, "%s.%d" % (os.path.basename(yol), int(time.time()))))
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(icerik)
    os.chmod(gecici, 0o600)
    os.replace(gecici, yol)
    return os.path.basename(yol)


def _ortam():
    """Alt sürece yalnızca zararsız değişkenler geçirilir."""
    ortam = {k: v for k, v in os.environ.items()
             if k in ("PATH", "LANG", "LC_ALL", "TMPDIR")}
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    ortam["PYTHONIOENCODING"] = "utf-8"
    return ortam


def calistir(icerik, dil="python", sure=VARSAYILAN_SURE, uzaktan=False):
    """Kodu çalıştırır; {cikis, cikti, sure_sn, zaman_asimi} döndürür."""
    if uzaktan and not ayar.yukle().get("uzaktan_kod_calistir", False):
        raise KodHatasi("Uzaktan kod çalıştırma kapalı. Mac'te Ülgen "
                        "penceresinden çalıştırın ya da ayar.json içine "
                        "\"uzaktan_kod_calistir\": true yazın.")
    if dil not in DILLER:
        raise KodHatasi("Desteklenen diller: " + ", ".join(DILLER))
    if len(icerik) > AZAMI_KOD:
        raise KodHatasi("Kod çok uzun.")
    sure = max(1, min(int(sure), AZAMI_SURE))
    if not _KILIT.acquire(blocking=False):
        raise KodHatasi("Başka bir kod çalışıyor; bitmesini bekleyin.")
    try:
        komut0 = DILLER[dil]["komut"]()
        if dil != "python" and not shutil.which(komut0[0]):
            raise KodHatasi("%s bu makinede kurulu değil." % dil)
        dizin = klasor()
        with tempfile.NamedTemporaryFile(
                "w", suffix=DILLER[dil]["uzanti"], dir=dizin, prefix=".calisan-",
                delete=False, encoding="utf-8") as f:
            f.write(icerik)
            gecici = f.name
        veritabani.gunluge_yaz("bilgi", "kod", "çalıştırıldı: %s, %d karakter, "
                               "%s" % (dil, len(icerik),
                                       "uzaktan" if uzaktan else "yerel"))
        basla = time.time()
        zaman_asimi = False
        try:
            surec = subprocess.Popen(
                komut0 + [gecici], cwd=dizin, env=_ortam(),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True)
            try:
                cikti, _ = surec.communicate(timeout=sure)
            except subprocess.TimeoutExpired:
                zaman_asimi = True
                try:
                    os.killpg(surec.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                cikti, _ = surec.communicate()
        finally:
            try:
                os.remove(gecici)
            except OSError:
                pass
        metin = cikti.decode("utf-8", errors="replace")
        if len(metin) > CIKTI_SINIRI:
            metin = metin[:CIKTI_SINIRI] + "\n... (çıktı kısaltıldı)"
        if zaman_asimi:
            metin += "\n[%d sn sınırı aşıldı, süreç durduruldu]" % sure
        return {"cikis": surec.returncode, "cikti": metin,
                "sure_sn": round(time.time() - basla, 2),
                "zaman_asimi": zaman_asimi}
    finally:
        _KILIT.release()
