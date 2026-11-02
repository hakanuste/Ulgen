"""Hava durumu (isteğe bağlı, Open-Meteo: ücretsiz, anahtarsız).

Gizlilik: Open-Meteo'ya yalnızca yaklaşık enlem/boylam ve IP adresiniz gider;
başka hiçbir kişisel veri gitmez. ``hava_acik: false`` ile kapatılır.
Sonuç 30 dakika önbelleğe alınır.
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import ag, ayar

ONBELLEK_SN = 1800
_KILIT = threading.Lock()
_ONBELLEK = {}      # anahtar -> (zaman, veri); anahtar: "varsayilan" ya da "enlem,boylam"
SON_KONUM_OMRU = 7 * 86400
ILLER = (
    ("Adana", 37.00, 35.32),
    ("Adıyaman", 37.76, 38.28),
    ("Afyonkarahisar", 38.76, 30.54),
    ("Ağrı", 39.72, 43.05),
    ("Aksaray", 38.37, 34.03),
    ("Amasya", 40.65, 35.83),
    ("Ankara", 39.93, 32.86),
    ("Antalya", 36.90, 30.70),
    ("Ardahan", 41.11, 42.70),
    ("Artvin", 41.18, 41.82),
    ("Aydın", 37.85, 27.84),
    ("Balıkesir", 39.65, 27.89),
    ("Bartın", 41.64, 32.34),
    ("Batman", 37.88, 41.13),
    ("Bayburt", 40.26, 40.23),
    ("Bilecik", 40.14, 29.98),
    ("Bingöl", 38.88, 40.50),
    ("Bitlis", 38.40, 42.11),
    ("Bolu", 40.74, 31.61),
    ("Burdur", 37.72, 30.29),
    ("Bursa", 40.19, 29.06),
    ("Çanakkale", 40.15, 26.41),
    ("Çankırı", 40.60, 33.62),
    ("Çorum", 40.55, 34.95),
    ("Denizli", 37.78, 29.09),
    ("Diyarbakır", 37.91, 40.24),
    ("Düzce", 40.84, 31.16),
    ("Edirne", 41.68, 26.56),
    ("Elazığ", 38.67, 39.22),
    ("Erzincan", 39.75, 39.49),
    ("Erzurum", 39.90, 41.27),
    ("Eskişehir", 39.78, 30.52),
    ("Gaziantep", 37.07, 37.38),
    ("Giresun", 40.91, 38.39),
    ("Gümüşhane", 40.46, 39.48),
    ("Hakkâri", 37.58, 43.74),
    ("Hatay", 36.40, 36.35),
    ("Iğdır", 39.92, 44.05),
    ("Isparta", 37.76, 30.55),
    ("İstanbul", 41.01, 28.98),
    ("İzmir", 38.42, 27.14),
    ("Kahramanmaraş", 37.58, 36.94),
    ("Karabük", 41.20, 32.62),
    ("Karaman", 37.18, 33.23),
    ("Kars", 40.60, 43.10),
    ("Kastamonu", 41.38, 33.78),
    ("Kayseri", 38.73, 35.49),
    ("Kilis", 36.72, 37.12),
    ("Kırıkkale", 39.85, 33.51),
    ("Kırklareli", 41.74, 27.23),
    ("Kırşehir", 39.15, 34.17),
    ("Kocaeli", 40.77, 29.94),
    ("Konya", 37.87, 32.48),
    ("Kütahya", 39.42, 29.98),
    ("Malatya", 38.35, 38.31),
    ("Manisa", 38.61, 27.43),
    ("Mardin", 37.31, 40.74),
    ("Mersin", 36.80, 34.64),
    ("Muğla", 37.22, 28.36),
    ("Muş", 38.74, 41.51),
    ("Nevşehir", 38.63, 34.71),
    ("Niğde", 37.97, 34.68),
    ("Ordu", 40.98, 37.88),
    ("Osmaniye", 37.07, 36.25),
    ("Rize", 41.02, 40.52),
    ("Sakarya", 40.76, 30.40),
    ("Samsun", 41.29, 36.33),
    ("Siirt", 37.93, 41.94),
    ("Sinop", 42.03, 35.15),
    ("Sivas", 39.75, 37.02),
    ("Şanlıurfa", 37.16, 38.79),
    ("Şırnak", 37.52, 42.46),
    ("Tekirdağ", 40.98, 27.51),
    ("Tokat", 40.31, 36.55),
    ("Trabzon", 41.00, 39.72),
    ("Tunceli", 39.11, 39.55),
    ("Uşak", 38.68, 29.41),
    ("Van", 38.49, 43.38),
    ("Yalova", 40.65, 29.27),
    ("Yozgat", 39.82, 34.81),
    ("Zonguldak", 41.45, 31.80),
)

KODLAR = {0: "Açık", 1: "Çoğunlukla açık", 2: "Parçalı bulutlu",
          3: "Bulutlu", 45: "Sisli", 48: "Kırağılı sis", 51: "Çiseleme",
          53: "Çiseleme", 55: "Yoğun çiseleme", 61: "Hafif yağmurlu",
          63: "Yağmurlu", 65: "Şiddetli yağmur", 71: "Hafif karlı",
          73: "Karlı", 75: "Yoğun kar", 80: "Sağanak", 81: "Sağanak",
          82: "Şiddetli sağanak", 95: "Gök gürültülü fırtına",
          96: "Dolulu fırtına", 99: "Dolulu fırtına"}


def konum():
    a = ayar.yukle()
    k = a.get("hava_konum") or {}
    return (str(k.get("ad", "Aydın")), float(k.get("enlem", 37.85)),
            float(k.get("boylam", 27.84)))


def en_yakin_il(enlem, boylam):
    """Çevrimdışı: koordinata en yakın il merkezinin adı (ağa gitmez)."""
    import math
    kos = math.cos(math.radians(enlem))
    return min(ILLER, key=lambda i: (i[1] - enlem) ** 2
               + ((i[2] - boylam) * kos) ** 2)[0]


def _son_konum_dosyasi():
    import os
    return os.path.join(ayar.KLASOR, "son_konum.json")


def son_konum_yaz(enlem, boylam):
    """Tarayıcının bildirdiği konumu (≈1 km'ye yuvarlı) yerelde saklar;
    sabah/akşam raporları sunucu tarafında bunu kullanır."""
    import os
    ayar.klasor_hazirla()
    yol = _son_konum_dosyasi()
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"enlem": round(enlem, 2), "boylam": round(boylam, 2),
                   "zaman": time.time()}, f)
    os.chmod(yol, 0o600)


def _son_konum():
    try:
        with open(_son_konum_dosyasi(), "r", encoding="utf-8") as f:
            k = json.load(f)
        if time.time() - float(k["zaman"]) < SON_KONUM_OMRU:
            return float(k["enlem"]), float(k["boylam"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def getir(zorla=False, enlem=None, boylam=None):
    """{"ad","sicaklik","durum"} | None (kapalı/ulaşılamaz).

    Konum önceliği: verilen koordinat > son bildirilen cihaz konumu >
    ayar.json "hava_konum"."""
    if ayar.yukle().get("hava_acik", True) is False:
        return None
    if enlem is None:
        son = _son_konum()
        if son:
            enlem, boylam = son
    if enlem is not None:
        enlem, boylam = round(float(enlem), 2), round(float(boylam), 2)
        ad = en_yakin_il(enlem, boylam)
        anahtar = "%s,%s" % (enlem, boylam)
    else:
        ad, enlem, boylam = konum()
        anahtar = "varsayilan"
    with _KILIT:
        onb = _ONBELLEK.get(anahtar)
        if not zorla and onb and time.time() - onb[0] < ONBELLEK_SN:
            return onb[1]
    adres = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": enlem, "longitude": boylam, "timezone": "auto",
         "current": "temperature_2m,weather_code"})
    try:
        with urllib.request.urlopen(adres, timeout=6, context=ag.baglam()) as r:
            j = json.loads(r.read(20000).decode("utf-8"))
        o = j["current"]
        veri = {"ad": ad, "sicaklik": round(float(o["temperature_2m"])),
                "durum": KODLAR.get(int(o["weather_code"]), "—")}
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return onb[1] if onb else None   # eski değer varsa o, yoksa None
    with _KILIT:
        _ONBELLEK[anahtar] = (time.time(), veri)
    return veri
