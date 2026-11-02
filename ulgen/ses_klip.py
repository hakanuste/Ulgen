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


def _kimlik_ve_ayar():
    a = ayar.yukle()
    anahtar = a.get("elevenlabs_anahtar")
    ses_kimligi = (a.get("elevenlabs_ses_kimligi") or "").strip()
    if not anahtar or not ses_kimligi:
        raise KlipHatasi("ElevenLabs anahtarı ya da ses kimliği yok")
    if not re.fullmatch(r"[A-Za-z0-9]{8,64}", ses_kimligi):
        raise KlipHatasi("ses kimliği geçersiz görünüyor")
    return a, anahtar, ses_kimligi


def _sentezle(metin):
    """ElevenLabs'e TEK metin gönderir, mp3 baytlarını döndürür.
    Aylık karakter sınırı burada denetlenir ve sayılır."""
    a, anahtar, ses_kimligi = _kimlik_ve_ayar()
    adet, ay = kullanilan()
    sinir = int(a.get("elevenlabs_aylik_sinir", 8000))
    if adet + len(metin) > sinir:
        raise KlipHatasi("aylık karakter sınırına ulaşıldı (%d/%d)" % (
            adet, sinir))
    govde = json.dumps({
        "text": metin,
        "model_id": a.get("elevenlabs_model", "eleven_flash_v2_5"),
        "language_code": "tr",
        "voice_settings": {
            "stability": float(a.get("elevenlabs_kararlilik", 0.66)),
            "speed": float(a.get("elevenlabs_hiz", 1.15))}}).encode("utf-8")
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
        ayrinti = hata.read().decode("utf-8", "replace")[:160]
        if hata.code in (402, 403):
            ayrinti += (" — bu ses kitaplık sesi olabilir; API için ücretli "
                        "plan gerekebilir")
        raise KlipHatasi("HTTP %d: %s" % (hata.code, ayrinti)) from hata
    except (urllib.error.URLError, OSError) as hata:
        raise KlipHatasi(str(hata)) from hata
    if not ses or len(ses) > AZAMI_BAYT:
        raise KlipHatasi("beklenmeyen ses yanıtı")
    _sayac_yaz(ay, adet + len(metin))
    return ses


def _yaz(hedef, ses):
    os.makedirs(os.path.dirname(hedef), mode=0o700, exist_ok=True)
    gecici = hedef + ".tmp"
    with open(gecici, "wb") as f:
        f.write(ses)
    os.replace(gecici, hedef)


def uret(ad, zorla=False):
    """Sabit cümleyi üretir (varsa atlar). Dönen: 'uretildi' | 'var'."""
    hedef = yol(ad)
    if os.path.isfile(hedef) and not zorla:
        return "var"
    _yaz(hedef, _sentezle(CUMLELER[ad]))
    return "uretildi"


# ---- Bulut sesi: yanıt metinlerini okutma (varsayılan KAPALI, isteğe bağlı)
HASSAS = re.compile(
    r"\b(ila[çc]|doz|hap|tablet|sa[ğg]l[ıi]k|nab[ıi]?z|tansiyon|uyku|hasta|"
    r"te[şs]his|kasa|parola|[şs]ifre|iban|kimlik|belirte[çc]|anahtar)\w*",
    re.IGNORECASE)
AZAMI_METIN = 700


def bulut_acik_mi():
    return bool(ayar.yukle().get("elevenlabs_bulut_ses", False))


def metni_oku(metin):
    """Yanıt metnini ElevenLabs ile mp3'e çevirir (aynı metin önbellekten).

    Kapalıysa, hassas içerik varsa (ilaç, sağlık, kasa, parola...) ya da çok
    uzunsa KlipHatasi fırlatır; çağıran yerel sese döner."""
    import hashlib
    if not bulut_acik_mi():
        raise KlipHatasi("bulut sesi kapalı")
    metin = re.sub(r"\s+", " ", metin).strip()
    if not metin or len(metin) > AZAMI_METIN:
        raise KlipHatasi("metin boş ya da çok uzun")
    if HASSAS.search(metin):
        raise KlipHatasi("hassas içerik: yerel sesle okunur")
    ayarlar = ayar.yukle()
    imza = "%s|%s|%s|%s" % (ayarlar.get("elevenlabs_ses_kimligi"), metin,
                            ayarlar.get("elevenlabs_hiz", 1.15),
                            ayarlar.get("elevenlabs_kararlilik", 0.66))
    hedef = os.path.join(klasor(), "onbellek", hashlib.sha256(
        imza.encode("utf-8")).hexdigest()[:32] + ".mp3")
    if os.path.isfile(hedef):
        with open(hedef, "rb") as f:
            return f.read()
    ses = _sentezle(metin)
    _yaz(hedef, ses)
    return ses


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


def yukle(ad, ham):
    """Kendi mp3 dosyanızı bir cümle için koyar (ElevenLabs gerekmez)."""
    hedef = yol(ad)
    if not ham or len(ham) > AZAMI_BAYT:
        raise KlipHatasi("dosya boş ya da 4 MB'tan büyük")
    if not (ham[:3] == b"ID3" or (len(ham) > 2 and ham[0] == 0xFF
                                  and ham[1] & 0xE0 == 0xE0)):
        raise KlipHatasi("yalnız mp3 dosyası kabul edilir")
    _yaz(hedef, ham)


def sil(ad):
    try:
        os.remove(yol(ad))
        return True
    except FileNotFoundError:
        return False
