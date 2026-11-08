"""Piyasa verisi: kur, endeks, altın, kripto - ücretsiz ve anahtarsız kaynaklardan.

* Döviz: TCMB günlük kurları (tcmb.gov.tr/kurlar/today.xml) - resmî kaynak.
* Endeks/emtia/kripto: Yahoo Finance'in herkese açık grafik ucu (gecikmeli
  olabilir; resmî borsa verisi değildir).
Siteleri kazımak yerine bu iki sabit adres kullanılır (Cloudflare engeli ve
JavaScript ile çizilen sayfalar yüzünden kazıma güvenilmezdi). Hiçbir ücretli
servis kullanılmaz. Yalnızca bu iki alan adına bağlanılır.
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime

IZINLI = ("www.tcmb.gov.tr", "query1.finance.yahoo.com")
TCMB = "https://www.tcmb.gov.tr/kurlar/today.xml"
YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
         "?range=5d&interval=1d")
UA = "Mozilla/5.0 (Ulgen kisisel asistan)"
AZAMI_BAYT = 1_500_000

DOVIZ = {"dolar": "USD", "usd": "USD", "euro": "EUR", "eur": "EUR",
         "sterlin": "GBP", "gbp": "GBP", "frank": "CHF", "chf": "CHF"}
# (aranan kalıp, Yahoo sembolü, ad, para birimi)
SEMBOLLER = [
    (r"\b(bist ?100|xu100|borsa\w*|endeks\w*)\b", "XU100.IS", "BIST 100", "puan"),
    (r"\b(bitcoin\w*|btc)\b", "BTC-USD", "Bitcoin", "USD"),
    (r"\b(ethereum\w*|eth)\b", "ETH-USD", "Ethereum", "USD"),
    (r"\b(ons)\b", "GC=F", "Ons altın", "USD"),
    (r"\b(gümüş\w*|gumus\w*)\b", "SI=F", "Gümüş (ons)", "USD"),
    (r"\b(brent|petrol\w*)\b", "BZ=F", "Brent petrol", "USD"),
]
GRAM_ALTIN = re.compile(r"\b(gram|altın\w*|altin\w*)\b", re.IGNORECASE)


def _indir(adres):
    from urllib.parse import urlparse
    if urlparse(adres).hostname not in IZINLI:
        raise ValueError("Bu adrese bağlanılmaz.")
    import requests
    y = requests.get(adres, headers={"User-Agent": UA}, timeout=12,
                     allow_redirects=False)
    y.raise_for_status()
    if len(y.content) > AZAMI_BAYT:
        raise ValueError("Yanıt çok büyük.")
    return y.text


def tr_sayi(x, basamak=2):
    s = "{:,.{b}f}".format(x, b=basamak)
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def tcmb_kurlari(indir=None):
    """{"tarih": "08.11.2026", "kurlar": {"USD": (alış, satış), ...}}"""
    kok = ET.fromstring((indir or _indir)(TCMB))
    kurlar = {}
    for c in kok.findall("Currency"):
        kod = c.get("Kod")
        al = c.findtext("ForexBuying") or ""
        sat = c.findtext("ForexSelling") or ""
        if kod and al and sat:
            kurlar[kod] = (float(al), float(sat))
    return {"tarih": kok.get("Tarih", ""), "kurlar": kurlar}


def yahoo(sembol, indir=None):
    """{"fiyat", "onceki", "zaman", "para"} ya da ValueError."""
    import json
    veri = json.loads((indir or _indir)(YAHOO % sembol))
    sonuc = (veri.get("chart", {}).get("result") or [None])[0]
    if not sonuc:
        raise ValueError("Veri bulunamadı: %s" % sembol)
    m = sonuc["meta"]
    fiyat = m.get("regularMarketPrice")
    if fiyat is None:
        raise ValueError("Fiyat yok: %s" % sembol)
    zaman = datetime.fromtimestamp(m.get("regularMarketTime", 0)).strftime(
        "%Y-%m-%d %H:%M")
    return {"fiyat": float(fiyat),
            "onceki": m.get("chartPreviousClose"), "zaman": zaman,
            "para": m.get("currency", "")}


def gecmis(sembol, aralik="1y", indir=None):
    """Günlük kapanışlar: [(tarih 'YYYY-MM-DD', kapanış)], eskiden yeniye."""
    import json
    adres = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
             "?range=%s&interval=1d" % (sembol, aralik))
    veri = json.loads((indir or _indir)(adres))
    sonuc = (veri.get("chart", {}).get("result") or [None])[0]
    if not sonuc:
        raise ValueError("Veri bulunamadı: %s" % sembol)
    zamanlar = sonuc.get("timestamp") or []
    kapanis = ((sonuc.get("indicators", {}).get("quote") or [{}])[0]
               .get("close") or [])
    cift = [(datetime.fromtimestamp(t).strftime("%Y-%m-%d"), float(c))
            for t, c in zip(zamanlar, kapanis) if c is not None]
    if len(cift) < 30:
        raise ValueError("Yeterli geçmiş yok: %s (%d gün)" % (sembol, len(cift)))
    return cift


def _satir(ad, d, birim=""):
    deg = ""
    if d.get("onceki"):
        yuz = 100 * (d["fiyat"] - d["onceki"]) / d["onceki"]
        deg = " (önceki kapanışa göre %+.2f%%)" % yuz
    return "%s: %s %s%s - Yahoo Finance, %s" % (
        ad, tr_sayi(d["fiyat"]), birim or d["para"], deg, d["zaman"])


def sorgula(metin, indir=None):
    """Sorudaki varlıkların güncel değerlerini kaynak ve zamanla döndürür."""
    kucuk = (metin or "").lower()
    satirlar, hatalar = [], []
    istenen = [k for k in DOVIZ if re.search(r"\b%s\w*" % k, kucuk)]
    kurlar = None
    if istenen or "kur" in kucuk:
        try:
            kurlar = tcmb_kurlari(indir)
        except Exception as hata:
            hatalar.append("TCMB kurları alınamadı (%s)" % str(hata)[:80])
    if kurlar:
        kodlar = sorted({DOVIZ[k] for k in istenen}) or ["USD", "EUR"]
        for kod in kodlar:
            if kod in kurlar["kurlar"]:
                al, sat = kurlar["kurlar"][kod]
                satirlar.append("%s/TL: alış %s, satış %s - TCMB günlük "
                                "döviz kuru, %s" % (kod, tr_sayi(al, 4),
                                                    tr_sayi(sat, 4),
                                                    kurlar["tarih"]))
    for kalip, sembol, ad, birim in SEMBOLLER:
        if re.search(kalip, kucuk, re.IGNORECASE):
            try:
                satirlar.append(_satir(ad, yahoo(sembol, indir), birim))
            except Exception as hata:
                hatalar.append("%s alınamadı (%s)" % (ad, str(hata)[:80]))
    if GRAM_ALTIN.search(kucuk) and "gram" in kucuk:
        try:
            ons = yahoo("GC=F", indir)
            usd = (kurlar or tcmb_kurlari(indir))["kurlar"]["USD"][1]
            gram = ons["fiyat"] * usd / 31.1035
            satirlar.append("Gram altın (HESAPLAMA, piyasa fiyatı değildir): "
                            "%s TL = ons %s USD x TCMB USD satış %s / 31,1035"
                            % (tr_sayi(gram), tr_sayi(ons["fiyat"]),
                               tr_sayi(usd, 4)))
        except Exception as hata:
            hatalar.append("Gram altın hesaplanamadı (%s)" % str(hata)[:80])
    if not satirlar and not hatalar:
        return ("Hangi değeri istediğinizi anlayamadım. Örnek: dolar, euro, "
                "bist 100, bitcoin, ons altın, gram altın, brent petrol.")
    metin = "\n".join(satirlar + hatalar)
    return metin + ("\nNot: Yahoo verisi gecikmeli olabilir; resmî borsa "
                    "verisi değildir. Yatırım tavsiyesi değildir.")
