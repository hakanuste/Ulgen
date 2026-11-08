"""Varlık analizi: fiyat geçmişinden hesaplanan göstergeler + kaynaklı bağlam.

Hesaplamalar kodda yapılır (modelin tahminine bırakılmaz). Çıktı bir
DEĞERLENDİRME'dir: veriler hangi yönü gösteriyor, hangi varsayımla. Kesin
al/sat emri ya da fiyat tahmini vermez; finansal danışmanlık değildir.
"""

import math
import re

from . import obsidyen_yaz, piyasa

KOMUT_DESENI = re.compile(r"^\s*analiz\s*[:\-]\s*(.{2,60})$", re.IGNORECASE)
OZEL = {
    "ons altın": ("GC=F", "Ons altın (USD)"), "ons": ("GC=F", "Ons altın (USD)"),
    "altın": ("GC=F", "Ons altın (USD)"), "gümüş": ("SI=F", "Gümüş (USD)"),
    "brent": ("BZ=F", "Brent petrol (USD)"), "petrol": ("BZ=F", "Brent petrol (USD)"),
    "bitcoin": ("BTC-USD", "Bitcoin (USD)"), "btc": ("BTC-USD", "Bitcoin (USD)"),
    "ethereum": ("ETH-USD", "Ethereum (USD)"),
    "bist 100": ("XU100.IS", "BIST 100"), "bist100": ("XU100.IS", "BIST 100"),
    "borsa": ("XU100.IS", "BIST 100"),
}


def sembol_bul(metin):
    """'THYAO' -> ('THYAO.IS', 'THYAO'); 'ons altın' -> ('GC=F', ...)."""
    k = " ".join((metin or "").lower().split())
    if k in OZEL:
        return OZEL[k]
    kod = re.sub(r"[^A-Za-z]", "", metin or "").upper()
    if 3 <= len(kod) <= 6:
        return kod + ".IS", kod
    raise ValueError("Varlık anlaşılmadı. Örnek: analiz: THYAO, analiz: ons altın")


def sma(kapanis, n):
    return sum(kapanis[-n:]) / n if len(kapanis) >= n else None


def rsi(kapanis, n=14):
    if len(kapanis) <= n:
        return None
    fark = [b - a for a, b in zip(kapanis, kapanis[1:])]
    kazanc = sum(max(f, 0) for f in fark[:n]) / n
    kayip = sum(max(-f, 0) for f in fark[:n]) / n
    for f in fark[n:]:       # Wilder yumuşatması
        kazanc = (kazanc * (n - 1) + max(f, 0)) / n
        kayip = (kayip * (n - 1) + max(-f, 0)) / n
    return 100.0 if kayip == 0 else 100 - 100 / (1 + kazanc / kayip)


def yillik_oynaklik(kapanis):
    if len(kapanis) < 20:
        return None
    g = [math.log(b / a) for a, b in zip(kapanis, kapanis[1:]) if a > 0 and b > 0]
    ort = sum(g) / len(g)
    var = sum((x - ort) ** 2 for x in g) / (len(g) - 1)
    return math.sqrt(var) * math.sqrt(252) * 100


def getiri(kapanis, gun):
    if len(kapanis) <= gun:
        return None
    return 100 * (kapanis[-1] / kapanis[-1 - gun] - 1)


def en_buyuk_dusus(kapanis):
    tepe, en = kapanis[0], 0.0
    for x in kapanis:
        tepe = max(tepe, x)
        en = min(en, 100 * (x / tepe - 1))
    return en


def gostergeler(cift):
    k = [c for _, c in cift]
    return {
        "son": k[-1], "tarih": cift[-1][0],
        "sma20": sma(k, 20), "sma50": sma(k, 50), "sma200": sma(k, 200),
        "rsi": rsi(k), "oynaklik": yillik_oynaklik(k),
        "g1a": getiri(k, 21), "g3a": getiri(k, 63), "g1y": getiri(k, 252),
        "tepe": max(k), "dip": min(k), "dusus": en_buyuk_dusus(k),
    }


def _f(x, b=2):
    return "—" if x is None else piyasa.tr_sayi(x, b)


def _yuzde(x):
    return "—" if x is None else "%+.1f%%" % x


def degerlendir(g):
    """Gözlemler: (yön, cümle) listesi. Emir değil, durum tespiti."""
    o = []
    s = g["son"]
    if g["sma200"]:
        o.append(("+" if s > g["sma200"] else "-",
                  "Fiyat 200 günlük ortalamanın %s." % (
                      "üstünde (uzun vadeli eğilim yukarı)" if s > g["sma200"]
                      else "altında (uzun vadeli eğilim aşağı)")))
    if g["sma50"] and g["sma20"]:
        o.append(("+" if g["sma20"] > g["sma50"] else "-",
                  "20 günlük ortalama 50 günlüğün %s (kısa vadeli ivme %s)." % (
                      "üstünde" if g["sma20"] > g["sma50"] else "altında",
                      "olumlu" if g["sma20"] > g["sma50"] else "olumsuz")))
    if g["rsi"] is not None:
        if g["rsi"] >= 70:
            o.append(("!", "RSI %.0f: aşırı alım bölgesi; sert düzeltme riski "
                           "artar." % g["rsi"]))
        elif g["rsi"] <= 30:
            o.append(("!", "RSI %.0f: aşırı satım bölgesi; tepki yükselişi "
                           "olasılığı artar ama düşüş sürebilir." % g["rsi"]))
        else:
            o.append(("=", "RSI %.0f: nötr bölge." % g["rsi"]))
    if g["oynaklik"] is not None:
        o.append(("!" if g["oynaklik"] > 40 else "=",
                  "Yıllık oynaklık %%%.0f: %s." % (
                      g["oynaklik"], "yüksek, fiyat sert dalgalanıyor"
                      if g["oynaklik"] > 40 else "orta/düşük")))
    return o


def senaryolar(g, gun=63):
    """Geçmiş oynaklığa dayalı ±1σ aralığı (tahmin değil, ölçek göstergesi)."""
    if g["oynaklik"] is None:
        return None
    sigma = g["oynaklik"] / 100 * math.sqrt(gun / 252)
    return (g["son"] * (1 - sigma), g["son"] * (1 + sigma))


def rapor(metin, indir=None):
    sembol, ad = sembol_bul(metin)
    cift = piyasa.gecmis(sembol, "1y", indir)
    g = gostergeler(cift)
    satir = ["# Analiz: %s" % ad, "",
             "Veri: Yahoo Finance günlük kapanışlar (gecikmeli olabilir), "
             "son kapanış %s: **%s**" % (g["tarih"], _f(g["son"])), "",
             "## Göstergeler (kodda hesaplandı)",
             "- Getiri: 1 ay %s · 3 ay %s · 1 yıl %s" % (
                 _yuzde(g["g1a"]), _yuzde(g["g3a"]), _yuzde(g["g1y"])),
             "- Ortalamalar: 20g %s · 50g %s · 200g %s" % (
                 _f(g["sma20"]), _f(g["sma50"]), _f(g["sma200"])),
             "- RSI(14): %s · Yıllık oynaklık: %s" % (
                 _f(g["rsi"], 0), _f(g["oynaklik"], 0) + "%"),
             "- Son 1 yıl: tepe %s · dip %s · en büyük düşüş %s" % (
                 _f(g["tepe"]), _f(g["dip"]), _yuzde(g["dusus"])), "",
             "## Değerlendirme (durum tespiti)"]
    for isaret, cumle in degerlendir(g):
        satir.append("- [%s] %s" % (isaret, cumle))
    sn = senaryolar(g)
    if sn:
        satir += ["", "## Ölçek göstergesi",
                  "Geçmiş oynaklığa göre 3 ay içinde yaklaşık %s – %s aralığı "
                  "'olağan' sayılır (±1 standart sapma). Bu bir tahmin değil, "
                  "dalgalanmanın büyüklüğünü gösterir." % (_f(sn[0]), _f(sn[1]))]
    satir += ["", "## Eksik olan (bu rapor bunları KAPSAMAZ)",
              "Mali tablolar, çarpanlar (F/K, PD/DD), KAP bildirimleri ve "
              "haberler. Bunlar için: 'kaynak ekle: AKÇA <sayfa adresi>' ile "
              "İş Yatırım/KAP sayfası ekleyip 'Akça: %s mali durumu' diye "
              "sorun." % ad,
              "", "> Bu bir finansal danışmanlık değildir. Geçmiş veri "
              "geleceği garanti etmez; karar sizindir."]
    return "\n".join(satir)


def komut(metin, indir=None):
    """'analiz: THYAO' -> rapor metni; kural dışı None. Notu Obsidian'a yazar."""
    e = KOMUT_DESENI.match(metin or "")
    if not e:
        return None
    try:
        r = rapor(e.group(1), indir)
    except Exception as hata:
        return "Analiz yapılamadı: %s" % str(hata)[:160]
    try:
        yol = obsidyen_yaz.yaz("Akçe", e.group(1).strip()[:40] + " analiz",
                               obsidyen_yaz.onbilgi(tur="analiz") + r)
        r += "\n\n(Not kaydedildi: %s)" % yol
    except Exception:
        pass
    return r
