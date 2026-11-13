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
    """Göstergeler. Getiri için uzun geçmiş (2 yıl) kullanılır; tepe, dip ve
    en büyük düşüş son 1 yılın (252 işlem günü) içinden hesaplanır."""
    k = [c for _, c in cift]
    yil = k[-252:]
    return {
        "son": k[-1], "tarih": cift[-1][0],
        "sma20": sma(k, 20), "sma50": sma(k, 50), "sma200": sma(k, 200),
        "rsi": rsi(k), "oynaklik": yillik_oynaklik(yil),
        "g1a": getiri(k, 21), "g3a": getiri(k, 63), "g1y": getiri(k, 252),
        "tepe": max(yil), "dip": min(yil), "dusus": en_buyuk_dusus(yil),
    }


def _f(x, b=2):
    return "—" if x is None else piyasa.tr_sayi(x, b)


def _yuzde(x):
    """Türkçe yazım: %+2,3 / %-16,2."""
    return "—" if x is None else "%" + ("+" if x >= 0 else "-") + piyasa.tr_sayi(abs(x), 1)


def _degisim(x):
    """Sade anlatım: '%2,3 yükseldi' / '%16,2 düştü'."""
    if x is None:
        return "bilinmiyor (yeterli geçmiş yok)"
    if abs(x) < 0.05:
        return "neredeyse değişmedi"
    return "%%%s %s" % (piyasa.tr_sayi(abs(x), 1), "yükseldi" if x > 0 else "düştü")


def birim(sembol):
    if sembol.startswith("XU"):
        return "puan"
    if sembol.endswith(".IS") or "TRY" in sembol:
        return "TL"
    return "dolar"


BIRIM_DEN = {"puan": "puandan", "TL": "TL'den", "dolar": "dolardan"}

AYLAR_TR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
            "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def _tarih(t):
    try:
        y, a, g = t.split("-")
        return "%d %s %s" % (int(g), AYLAR_TR[int(a) - 1], y)
    except (ValueError, IndexError):
        return t


def degerlendir(g):
    """Gözlemler: (yön, cümle) listesi; sade Türkçe. Emir değil, durum tespiti."""
    o = []
    s = g["son"]
    if g["sma200"]:
        o.append(("+" if s > g["sma200"] else "-",
                  "Uzun vadeli yön %s. Fiyat, son 200 işlem gününün "
                  "ortalamasının (%s) %s." % (
                      "yukarı" if s > g["sma200"] else "aşağı", _f(g["sma200"]),
                      "üstünde" if s > g["sma200"] else "altında")))
    if g["sma50"] and g["sma20"]:
        iyi = g["sma20"] > g["sma50"]
        o.append(("+" if iyi else "-",
                  "Kısa vadeli yön %s. Son 20 günün ortalaması (%s), son 50 "
                  "günün ortalamasının (%s) %s." % (
                      "güçleniyor" if iyi else "zayıf", _f(g["sma20"]),
                      _f(g["sma50"]), "üstünde" if iyi else "altında")))
    if g["rsi"] is not None:
        r = g["rsi"]
        durum = ("fazla alınmış görünüyor; kısa vadede geri çekilme olasılığı artar"
                 if r >= 70 else
                 "fazla satılmış görünüyor; tepki yükselişi gelebilir ama düşüş "
                 "de sürebilir" if r <= 30 else "alıcı ve satıcı dengede")
        o.append(("!" if r >= 70 or r <= 30 else "=",
                  "Alım-satım dengesi: %s. (RSI %s; 70 üstü fazla alınmış, "
                  "30 altı fazla satılmış demektir)." % (durum, _f(r, 0))))
    if g["oynaklik"] is not None:
        v = g["oynaklik"]
        o.append(("!" if v > 40 else "=",
                  "Dalgalanma %s. Fiyat bir yılda ortalama %%%s oynuyor." % (
                      "yüksek" if v > 40 else "orta" if v > 20 else "düşük",
                      _f(v, 0))))
    return o


def sonuc_cumlesi(g):
    """Tek cümlelik sade sonuç (göstergelerden kuralla)."""
    uzun = g["sma200"] and g["son"] > g["sma200"]
    kisa = g["sma50"] and g["sma20"] and g["sma20"] > g["sma50"]
    if g["sma200"] is None:
        return "Uzun vadeli yönü söylemek için yeterli geçmiş yok."
    if uzun and kisa:
        return "Hem uzun hem kısa vadede yukarı yönlü bir görünüm var."
    if uzun and not kisa:
        return "Uzun vadede yukarı yönlü, ancak son haftalarda ivme kaybediyor."
    if not uzun and kisa:
        return ("Uzun vadede düşüş eğiliminde, ama son haftalarda toparlanma "
                "belirtisi var; dönüş henüz kesinleşmiş değil.")
    return "Hem uzun hem kısa vadede düşüş eğiliminde; belirgin bir dönüş işareti yok."


def senaryolar(g, gun=63):
    """Geçmiş oynaklığa dayalı ±1σ aralığı (tahmin değil, ölçek göstergesi)."""
    if g["oynaklik"] is None:
        return None
    sigma = g["oynaklik"] / 100 * math.sqrt(gun / 252)
    return (g["son"] * (1 - sigma), g["son"] * (1 + sigma))


ISARET = {"+": "Olumlu", "-": "Olumsuz", "=": "Nötr", "!": "Dikkat"}


def rapor_sembol(sembol, ad, indir=None):
    try:
        cift = piyasa.gecmis(sembol, "2y", indir)
    except ValueError:
        cift = piyasa.gecmis(sembol, "1y", indir)
    g = gostergeler(cift)
    bir = birim(sembol)
    satir = ["# %s – sade özet" % ad, "",
             "%s günü %s, %s %s kapandı. %s" % (
                 _tarih(g["tarih"]), ad, _f(g["son"]), BIRIM_DEN[bir],
                 sonuc_cumlesi(g)), "",
             "Son 1 ayda %s, son 3 ayda %s, son 1 yılda %s." % (
                 _degisim(g["g1a"]), _degisim(g["g3a"]), _degisim(g["g1y"])), "",
             "## Ne gösteriyor?"]
    for isaret, cumle in degerlendir(g):
        satir.append("- %s – %s" % (ISARET[isaret], cumle))
    satir += ["- Bilgi – son 1 yılın en yükseği %s, en düşüğü %s %s. En yüksekten "
              "en büyük geri çekilme %%%s oldu." % (
                  _f(g["tepe"]), _f(g["dip"]), bir, _f(abs(g["dusus"]), 1))]
    sn = senaryolar(g)
    if sn:
        satir += ["", "## Olağan dalgalanma aralığı",
                  "Geçmişteki dalgalanmaya bakılırsa önümüzdeki 3 ayda %s ile %s "
                  "%s arası 'olağan' sayılır. Bu bir tahmin değildir; yalnızca "
                  "fiyatın ne kadar oynayabildiğini gösterir." % (
                      _f(sn[0]), _f(sn[1]), bir)]
    satir += ["", "## Bu rapor neyi kapsamaz?",
              "Şirket bilançoları, F/K ve PD/DD gibi oranlar, KAP bildirimleri "
              "ve haberler bu raporda yok. Eklemek için İş Yatırım ya da KAP "
              "sayfasını 'kaynak ekle: AKÇA <adres>' ile ekleyip 'Akça: %s mali "
              "durumu' diye sorun." % ad,
              "", "Kaynak: Yahoo Finance günlük kapanışları (gecikmeli olabilir). "
              "Hesaplar Ülgen'de yapıldı.",
              "", "> Bu bir yatırım tavsiyesi değildir. Geçmiş veri geleceği "
              "garanti etmez; karar sizindir."]
    return "\n".join(satir)


def rapor(metin, indir=None):
    sembol, ad = sembol_bul(metin)
    return rapor_sembol(sembol, ad, indir)


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
