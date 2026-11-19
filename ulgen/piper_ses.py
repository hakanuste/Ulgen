"""Ülgen'in kendi sesi: Piper ile internetsiz Türkçe konuşma.

Ses dosyaları (<ad>.onnx ve <ad>.onnx.json) ~/ÜlgenVeri/sesler/ içinde
durur. Hazır Türkçe ses ("tr_TR-dfki-medium", ~63 MB) bir kez indirilir;
sonrası tamamen internetsizdir. Kendi sesinizle eğittiğiniz model de aynı
klasöre konunca listede görünür (docs/SESIM.md).

Piper kurulu değilse modül hata vermez; ``hazir_mi`` False döner ve arayüz
"Kur" düğmesini gösterir (pip ile, arka planda, bir kez).
"""

import glob
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import wave

from . import ayar

HAZIR_SESLER = {
    "tr_TR-dfki-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
                         "tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx",
}
AZAMI_METIN = 2000
_YUKLU = {}                 # ad -> PiperVoice (bellekte bir kez yüklenir)
_KILIT = threading.Lock()
_DURUM = {"kurulum": "", "indirme": ""}


class PiperHatasi(Exception):
    pass


def klasor():
    yol = os.path.join(ayar.KLASOR, "sesler")
    os.makedirs(yol, exist_ok=True)
    return yol


def _ortam():
    """Ayrı Piper ortamı: Ülgen'in Python'u hangi sürüm olursa olsun, Piper'ın
    kurulabildiği bir Python ile (3.9-3.12) ~/ÜlgenVeri/piper_ortam."""
    return os.path.join(ayar.KLASOR, "piper_ortam")


def _ortam_python():
    yol = os.path.join(_ortam(), "bin", "python")
    return yol if os.path.exists(yol) else ""


def _ic_piper():
    """Piper Ülgen'in kendi Python'unda kurulu mu (Linux, Raspberry Pi, yeni Mac)."""
    try:
        import piper  # noqa: F401
        return True
    except Exception:
        return False


def piper_var_mi():
    return _ic_piper() or bool(_ortam_python())


def _surum(python):
    try:
        c = subprocess.run([python, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=20)
        a, b = c.stdout.strip().split(".")
        return int(a), int(b)
    except Exception:
        return None


def uygun_python():
    """Piper ve onnxruntime'ın Mac tekerleği olan bir Python (3.9-3.12) bulur.
    macOS 12'de Command Line Tools ile gelen /usr/bin/python3 (3.9) de olur."""
    adaylar = [sys.executable]
    for ad in ("python3.12", "python3.11", "python3.10", "python3.9", "python3"):
        y = shutil.which(ad)
        if y:
            adaylar.append(y)
    adaylar += sorted(glob.glob(
        "/Library/Frameworks/Python.framework/Versions/3.1[0-2]/bin/python3"), reverse=True)
    adaylar += ["/opt/homebrew/bin/python3.12", "/usr/local/bin/python3.12",
                "/usr/local/bin/python3.11", "/usr/bin/python3"]
    gorulen = set()
    for y in adaylar:
        if not y or y in gorulen or not os.path.exists(y):
            continue
        gorulen.add(y)
        s = _surum(y)
        if s and (3, 9) <= s <= (3, 12):
            return y
    return ""


def _mac_eski():
    """macOS 13'ten eski mi? (onnxruntime 1.20+ yalnız macOS 13+ için)"""
    if sys.platform != "darwin":
        return False
    try:
        return int(platform.mac_ver()[0].split(".")[0]) < 13
    except (ValueError, IndexError):
        return False


def sesler():
    """Klasördeki kullanılabilir sesler (adı, .onnx ve .onnx.json ikisi de var)."""
    try:
        adlar = os.listdir(klasor())
    except OSError:
        return []
    return sorted(a[:-5] for a in adlar
                  if a.endswith(".onnx") and (a + ".json") in adlar)


def secili():
    a = ayar.yukle()
    liste = sesler()
    ad = a.get("piper_ses") or ""
    if ad in liste:
        return ad
    # kendi sesiniz (hazır olmayan) varsa o, yoksa ilk ses
    kendi = [s for s in liste if s not in HAZIR_SESLER]
    return (kendi or liste or [""])[0]


def hazir_mi():
    return piper_var_mi() and bool(secili())


def durum():
    a = ayar.yukle()
    return {"piper": piper_var_mi(), "sesler": sesler(), "secili": secili(),
            "acik": bool(a.get("piper_acik")) and hazir_mi(),
            "hiz": float(a.get("piper_hiz", 1.0) or 1.0),
            "hazir_sesler": list(HAZIR_SESLER),
            "kurulum": _DURUM["kurulum"], "indirme": _DURUM["indirme"]}


def ayarla(acik=None, ses=None, hiz=None):
    if ses is not None:
        if ses not in sesler():
            raise PiperHatasi("Böyle bir ses yok.")
        ayar.guncelle("piper_ses", ses)
    if hiz is not None:
        hiz = float(hiz)
        if not 0.6 <= hiz <= 1.6:
            raise PiperHatasi("Hız 0,6 ile 1,6 arasında olmalı.")
        ayar.guncelle("piper_hiz", hiz)
    if acik is not None:
        if acik and not hazir_mi():
            raise PiperHatasi("Önce Piper'ı kurun ve bir ses indirin.")
        ayar.guncelle("piper_acik", bool(acik))
    return durum()


# ------------------------------------------------------------ kurulum, indirme
def kur_arka_planda():
    """Piper'ı ayrı bir Python ortamına kurar (bir kez, internetle).

    Ülgen'in kendi Python'una kurmak yerine ayrı ortam: Ülgen 3.13 gibi
    onnxruntime tekerleği olmayan bir sürümde çalışsa da Piper kurulur;
    macOS 12'de onnxruntime 1.19'a (macOS 11+ ile uyumlu son sürüm) sabitlenir."""
    if _DURUM["kurulum"] == "sürüyor":
        return
    _DURUM["kurulum"] = "sürüyor"

    def is_():
        try:
            py = uygun_python()
            if not py:
                _DURUM["kurulum"] = ("hata: Piper için Python 3.9-3.12 bulunamadı. Terminal'de "
                                     "'xcode-select --install' çalıştırın (Apple'ın Python 3.9'u "
                                     "gelir) ya da python.org'dan Python 3.12 kurun.")
                return
            if os.path.isdir(_ortam()) and not _ortam_python():
                shutil.rmtree(_ortam(), ignore_errors=True)
            if not _ortam_python():
                subprocess.run([py, "-m", "venv", _ortam()], check=True,
                               capture_output=True, text=True, timeout=300)
            pip = [_ortam_python(), "-m", "pip", "install", "-q"]
            subprocess.run(pip + ["-U", "pip"], capture_output=True, text=True, timeout=600)
            paketler = ["piper-tts"] + (["onnxruntime<1.20"] if _mac_eski() else [])
            s = subprocess.run(pip + paketler, capture_output=True, text=True, timeout=1800)
            if s.returncode != 0:
                son = (s.stderr or s.stdout).strip().splitlines()
                _DURUM["kurulum"] = "hata: " + (son[-1] if son else "pip")[:200]
                return
            d = subprocess.run([_ortam_python(), "-c", "import piper"],
                               capture_output=True, text=True, timeout=120)
            _DURUM["kurulum"] = "tamam" if d.returncode == 0 else \
                "hata: piper yüklenemedi: " + (d.stderr.strip().splitlines() or ["?"])[-1][:200]
        except Exception as hata:
            _DURUM["kurulum"] = "hata: %s" % str(hata)[:200]
    threading.Thread(target=is_, daemon=True).start()


def indir_arka_planda(ad="tr_TR-dfki-medium"):
    """Hazır sesi (onnx + json) indirir; yarım dosya bırakmaz."""
    if ad not in HAZIR_SESLER:
        raise PiperHatasi("Bilinmeyen hazır ses.")
    if _DURUM["indirme"].startswith("sürüyor"):
        return

    def is_():
        import requests
        try:
            for uzanti in (".onnx.json", ".onnx"):
                adres = HAZIR_SESLER[ad][:-5] + uzanti
                hedef = os.path.join(klasor(), ad + uzanti)
                gecici = hedef + ".iniyor"
                with requests.get(adres, stream=True, timeout=60) as y:
                    y.raise_for_status()
                    toplam = int(y.headers.get("Content-Length") or 0)
                    inen = 0
                    with open(gecici, "wb") as f:
                        for parca in y.iter_content(1 << 16):
                            f.write(parca)
                            inen += len(parca)
                            if toplam:
                                _DURUM["indirme"] = "sürüyor %%%d" % (inen * 100 // toplam)
                os.replace(gecici, hedef)
            _DURUM["indirme"] = "tamam"
        except Exception as hata:
            _DURUM["indirme"] = "hata: %s" % str(hata)[:200]
    _DURUM["indirme"] = "sürüyor %0"
    threading.Thread(target=is_, daemon=True).start()


# ------------------------------------------------------------ konuşma
def _ses_yukle(ad):
    with _KILIT:
        if ad not in _YUKLU:
            from piper import PiperVoice
            yol = os.path.join(klasor(), ad + ".onnx")
            _YUKLU.clear()                       # bellekte tek ses dursun
            _YUKLU[ad] = PiperVoice.load(yol)
        return _YUKLU[ad]


def temizle(metin):
    """Okunacak metin: biçim imleri ve bağlantılar atılır."""
    metin = re.sub(r"https?://\S+", " ", str(metin or ""))
    metin = re.sub(r"[*_`#>|\[\]{}]+", " ", metin)
    return re.sub(r"\s+", " ", metin).strip()[:AZAMI_METIN]


def sentezle(metin, ad=None, hiz=None):
    """Metni WAV baytlarına çevirir (internetsiz)."""
    if not piper_var_mi():
        raise PiperHatasi("Piper kurulu değil.")
    ad = ad or secili()
    if not ad:
        raise PiperHatasi("Ses dosyası yok; önce bir ses indirin.")
    metin = temizle(metin)
    if not metin:
        raise PiperHatasi("Okunacak metin yok.")
    hiz = float(hiz or ayar.yukle().get("piper_hiz", 1.0) or 1.0)
    if _ic_piper():
        from piper import SynthesisConfig
        ses = _ses_yukle(ad)
        tampon = io.BytesIO()
        with wave.open(tampon, "wb") as w:
            ses.synthesize_wav(metin, w, syn_config=SynthesisConfig(length_scale=1.0 / hiz))
        return tampon.getvalue()
    return _isci.sentezle(os.path.join(klasor(), ad + ".onnx"), metin, 1.0 / hiz)


# Ayrı ortamda sürekli açık bekleyen Piper işçisi: ses bir kez yüklenir,
# her istek JSON satırıyla gelir, WAV geçici dosyaya yazılır.
_ISCI_KODU = r"""
import json, sys, wave
from piper import PiperVoice, SynthesisConfig
yuklu = {}
for satir in sys.stdin:
    try:
        i = json.loads(satir)
        if i["model"] not in yuklu:
            yuklu.clear()
            yuklu[i["model"]] = PiperVoice.load(i["model"])
        with wave.open(i["cikti"], "wb") as w:
            yuklu[i["model"]].synthesize_wav(
                i["metin"], w, syn_config=SynthesisConfig(length_scale=i["olcek"]))
        print(json.dumps({"tamam": True}), flush=True)
    except Exception as h:
        print(json.dumps({"hata": str(h)[:300]}), flush=True)
"""


class _Isci:
    def __init__(self):
        self._p = None
        self._kilit = threading.Lock()

    def _baslat(self):
        if self._p and self._p.poll() is None:
            return
        self._p = subprocess.Popen([_ortam_python(), "-u", "-c", _ISCI_KODU],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, encoding="utf-8")

    def sentezle(self, model, metin, olcek):
        with self._kilit:
            self._baslat()
            fd, cikti = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                self._p.stdin.write(json.dumps({"model": model, "metin": metin,
                                                "olcek": olcek, "cikti": cikti}) + "\n")
                self._p.stdin.flush()
                yanit = self._p.stdout.readline()
                if not yanit:
                    self._p = None
                    raise PiperHatasi("Piper işçisi kapandı.")
                y = json.loads(yanit)
                if y.get("hata"):
                    raise PiperHatasi(y["hata"])
                with open(cikti, "rb") as f:
                    return f.read()
            finally:
                try:
                    os.remove(cikti)
                except OSError:
                    pass


_isci = _Isci()
