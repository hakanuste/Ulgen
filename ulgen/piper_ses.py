"""Ülgen'in kendi sesi: Piper ile internetsiz Türkçe konuşma.

Ses dosyaları (<ad>.onnx ve <ad>.onnx.json) ~/ÜlgenVeri/sesler/ içinde
durur. Hazır Türkçe ses ("tr_TR-dfki-medium", ~63 MB) bir kez indirilir;
sonrası tamamen internetsizdir. Kendi sesinizle eğittiğiniz model de aynı
klasöre konunca listede görünür (docs/SESIM.md).

Piper kurulu değilse modül hata vermez; ``hazir_mi`` False döner ve arayüz
"Kur" düğmesini gösterir (pip ile, arka planda, bir kez).
"""

import io
import os
import re
import subprocess
import sys
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


def piper_var_mi():
    try:
        import piper  # noqa: F401
        return True
    except Exception:
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
    """piper-tts'i Ülgen'in kendi Python ortamına kurar (bir kez, internetle)."""
    if _DURUM["kurulum"] == "sürüyor":
        return
    _DURUM["kurulum"] = "sürüyor"

    def is_():
        try:
            s = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "piper-tts"],
                               capture_output=True, text=True, timeout=1200)
            _DURUM["kurulum"] = "tamam" if s.returncode == 0 else \
                "hata: " + (s.stderr or s.stdout).strip().splitlines()[-1][:200]
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
    from piper import SynthesisConfig
    hiz = float(hiz or ayar.yukle().get("piper_hiz", 1.0) or 1.0)
    ses = _ses_yukle(ad)
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        ses.synthesize_wav(metin, w, syn_config=SynthesisConfig(length_scale=1.0 / hiz))
    return tampon.getvalue()
