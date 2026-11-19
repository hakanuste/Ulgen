"""Hazır bulut beyinleri (Gemini, NVIDIA, Groq, Mistral, OpenRouter) için
yerinde düzenleme: servisteki modellerden seçme ve "Öne al".

Yalnızca ücretsiz modeller kabul edilir (OpenRouter'da ':free'); sohbet
dışı modeller (gömme, yeniden sıralama, belge ayrıştırma, ses...) listede
gösterilmez. Anahtar burada okunur ama hiçbir yanıta yazılmaz.
"""

import re

from . import ayar, kota
from .beyin import BeyinHatasi, GeminiBeyin, OpenAIUyumluBeyin

MODEL_ALANI = {"gemini": "gemini_model", "nvidia": "nvidia_model",
               "groq": "groq_model", "mistral": "mistral_model",
               "openrouter": "openrouter_model"}
# Sohbet etmeyen modeller listede gösterilmez
SOHBET_DISI = ("embed", "rerank", "parse", "guard", "safety", "reward", "clip",
               "retriev", "audio", "speech", "tts", "asr", "whisper", "diffusion",
               "imagen", "veo", "-tts", "moderation", "ocr", "aqa")


class HazirHatasi(Exception):
    pass


def _denetle(ad):
    if ad not in MODEL_ALANI:
        raise HazirHatasi("Bilinmeyen sağlayıcı.")


def _beyin(ad):
    a = ayar.yukle()
    anahtar = a.get(ad + "_anahtar")
    if not anahtar:
        raise HazirHatasi("Önce bu sağlayıcının anahtarını ekleyin.")
    if ad == "gemini":
        return GeminiBeyin(anahtar, a.get("gemini_model"))
    return OpenAIUyumluBeyin(ad, anahtar, a.get(MODEL_ALANI[ad]))


def durum():
    """Her hazır sağlayıcının şu anki modeli ve öne alınmış mı."""
    a = ayar.yukle()
    one = list(a.get("one_alinanlar") or [])
    return {ad: {"model": a.get(alan) or "", "one": ad in one}
            for ad, alan in MODEL_ALANI.items()}


def modeller(ad):
    """Servisin bu anahtarla sunduğu, ücretsiz ve sohbet eden modeller."""
    _denetle(ad)
    try:
        hepsi = _beyin(ad).modelleri_listele()
    except BeyinHatasi as hata:
        raise HazirHatasi("Model listesi alınamadı: %s" % str(hata)[:160])
    return [m for m in hepsi
            if kota.ucretsiz_mi(ad, m)
            and not any(e in m.lower() for e in SOHBET_DISI)]


def model_degistir(ad, model):
    _denetle(ad)
    model = str(model or "").strip()
    if not re.fullmatch(r"[\w.:/@+-]{1,120}", model):
        raise HazirHatasi("Model adını servisin yazdığı gibi girin.")
    if not kota.ucretsiz_mi(ad, model):
        raise HazirHatasi("'%s' ücretsiz değil; ücretli modeller kapalıdır." % model)
    ayar.guncelle(MODEL_ALANI[ad], model)
    return model


def one_al(ad, one=True):
    """Sağlayıcıyı beyin sırasında en başa alır (one=False: normal sırası)."""
    _denetle(ad)
    liste = [x for x in (ayar.yukle().get("one_alinanlar") or []) if x != ad]
    if one:
        liste.append(ad)
    ayar.guncelle("one_alinanlar", liste)
    return liste
