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

from . import ayar

ONBELLEK_SN = 1800
_KILIT = threading.Lock()
_ONBELLEK = {"zaman": 0.0, "veri": None}

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


def getir(zorla=False):
    """{"ad","sicaklik","durum"} | None (kapalı/ulaşılamaz)."""
    if ayar.yukle().get("hava_acik", True) is False:
        return None
    with _KILIT:
        if not zorla and time.time() - _ONBELLEK["zaman"] < ONBELLEK_SN \
                and _ONBELLEK["veri"]:
            return _ONBELLEK["veri"]
    ad, enlem, boylam = konum()
    adres = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": enlem, "longitude": boylam, "timezone": "auto",
         "current": "temperature_2m,weather_code"})
    try:
        with urllib.request.urlopen(adres, timeout=6) as r:
            j = json.loads(r.read(20000).decode("utf-8"))
        o = j["current"]
        veri = {"ad": ad, "sicaklik": round(float(o["temperature_2m"])),
                "durum": KODLAR.get(int(o["weather_code"]), "—")}
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return _ONBELLEK["veri"]       # eski değer varsa o, yoksa None
    with _KILIT:
        _ONBELLEK.update(zaman=time.time(), veri=veri)
    return veri
