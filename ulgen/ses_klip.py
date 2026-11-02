"""Sabit cümleler için kendi sesiniz (ElevenLabs), BİR KEZ üretilip yerelde saklanır.

Neden böyle: ElevenLabs bulut hizmetidir. Gizlilik kuralı gereği ilaç, sağlık,
kasa ya da sohbet içeriği ona GİTMEZ; yalnızca aşağıdaki sabit, kişisel
olmayan cümleler gider. Üretilen mp3 dosyaları ~/ÜlgenVeri/ses/ altında kalır,
sonrasında çevrimdışı çalar. Ücretsiz katmanın aylık karakter sınırı sayılır
ve aşılmaz. Değişken yanıtlar Mac'in/tarayıcının yerel sesiyle okunur.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

from . import ag, ayar

CUMLELER = {
    "karsilama": "Merhaba, hoş geldiniz. Size nasıl yardımcı olabilirim?",
    "dinliyorum": "Buyurun, dinliyorum.",
    "efendim": "Efendim?",
    "tamam": "Tamam.",
    "anlamadim": "Bunu anlayamadım, yeniden söyler misiniz?",
    "hatirlatma": "Hatırlatma zamanı.",
    "ilac_zamani": "İlaç zamanı geldi.",
}
ADRES = "https://api.elevenlabs.io/v1/text-to-speech/%s"
AZAMI_BAYT = 4 * 1024 * 1024


class KlipHatasi(Exception):
    pass


def klasor():
    return os.path.join(ayar.KLASOR, "ses")


def yol(ad):
    if ad not in CUMLELER:
        raise KlipHatasi("bilinmeyen cümle")
    return os.path.join(klasor(), ad + ".mp3")


def normal(metin):
    return re.sub(r"\s+", " ", metin).strip().lower()


def hazir_klipler():
    """{normalleştirilmiş cümle: ad} yalnız dosyası üretilmiş olanlar."""
    return {normal(m): a for a, m in CUMLELER.items()
            if os.path.isfile(os.path.join(klasor(), a + ".mp3"))}


def _sayac_dosyasi():
    return os.path.join(ayar.KLASOR, "elevenlabs_sayac.json")


def kullanilan(ay=None):
    ay = ay or time.strftime("%Y-%m")
    try:
        with open(_sayac_dosyasi(), "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        veri = {}
    return int(veri.get(ay, 0)), ay


def _sayac_yaz(ay, adet):
    with open(_sayac_dosyasi(), "w", encoding="utf-8") as f:
        json.dump({ay: adet}, f)


def uret(ad, zorla=False):
    """Tek cümleyi üretir (varsa atlar). Dönen: 'uretildi' | 'var'."""
    hedef = yol(ad)
    if os.path.isfile(hedef) and not zorla:
        return "var"
    a = ayar.yukle()
    anahtar = a.get("elevenlabs_anahtar")
    ses_kimligi = (a.get("elevenlabs_ses_kimligi") or "").strip()
    if not anahtar or not ses_kimligi:
        raise KlipHatasi("ElevenLabs anahtarı ya da ses kimliği yok")
    if not re.fullmatch(r"[A-Za-z0-9]{8,64}", ses_kimligi):
        raise KlipHatasi("ses kimliği geçersiz görünüyor")
    metin = CUMLELER[ad]
    adet, ay = kullanilan()
    sinir = int(a.get("elevenlabs_aylik_sinir", 8000))
    if adet + len(metin) > sinir:
        raise KlipHatasi("aylık karakter sınırına ulaşıldı (%d/%d)" % (
            adet, sinir))
    govde = json.dumps({
        "text": metin,
        "model_id": a.get("elevenlabs_model", "eleven_multilingual_v2"),
        "language_code": "tr"}).encode("utf-8")
    istek = urllib.request.Request(
        ADRES % ses_kimligi + "?output_format=mp3_44100_128", data=govde,
        method="POST")
    istek.add_header("Content-Type", "application/json")
    istek.add_header("xi-api-key", anahtar)
    istek.add_header("Accept", "audio/mpeg")
    try:
        with urllib.request.urlopen(istek, timeout=60,
                                    context=ag.baglam()) as r:
            ses = r.read(AZAMI_BAYT + 1)
    except urllib.error.HTTPError as hata:
        raise KlipHatasi("HTTP %d: %s" % (
            hata.code, hata.read().decode("utf-8", "replace")[:160])) from hata
    except (urllib.error.URLError, OSError) as hata:
        raise KlipHatasi(str(hata)) from hata
    if not ses or len(ses) > AZAMI_BAYT:
        raise KlipHatasi("beklenmeyen ses yanıtı")
    os.makedirs(klasor(), mode=0o700, exist_ok=True)
    gecici = hedef + ".tmp"
    with open(gecici, "wb") as f:
        f.write(ses)
    os.replace(gecici, hedef)
    _sayac_yaz(ay, adet + len(metin))
    return "uretildi"


def hepsini_uret(zorla=False):
    sonuc = {}
    for ad in CUMLELER:
        try:
            sonuc[ad] = uret(ad, zorla)
        except KlipHatasi as hata:
            sonuc[ad] = "HATA: %s" % hata
            if "sınır" in str(hata) or "anahtar" in str(hata):
                break
    return sonuc
