"""Hangi uzmana sorulduğunu anlar; uzman kendi işini doğrudan yapar.

Örnek: "anadolu efes hissesi ne oldu analiz et" -> AKÇA, şirket adından
AEFES.IS sembolünü bulur ve kodda hesaplanan analiz raporunu çalıştırır
(modelin tahminine bırakılmaz). "aefes kaç TL" -> AKÇA anlık fiyat.
Uzmanın doğrudan bir aracı yoksa None döner; soru uzman kipiyle beyne gider.
"""

import json
import re
from urllib.parse import quote

from . import ajan_kayit, analiz, obsidyen, obsidyen_yaz, piyasa, uzmanlar

ANALIZ = re.compile(
    r"\b(analiz\w*|ne oldu|ne durumda|nasıl gid\w*|nasil gid\w*|durumu\w*|"
    r"yorumla\w*|incele\w*|değerlendir\w*|degerlendir\w*|teknik)\b",
    re.IGNORECASE)
FIYAT = re.compile(r"\b(kaç|kac|fiyat\w*|ne kadar|kaçtan|kactan)\b", re.IGNORECASE)
HISSE = re.compile(r"\b(hisse\w*|borsa\w*|bist\w*|şirket\w*|sirket\w*|"
                   r"senet\w*|pay\w*)\b", re.IGNORECASE)

# Bilinen BIST şirketleri: ad/takma ad -> işlem kodu. Listede olmayanlar
# Yahoo Finance aramasıyla bulunur (aynı izinli sunucu).
SIRKETLER = {
    "AEFES": ["anadolu efes", "efes"], "AGHOL": ["anadolu grubu", "ag anadolu"],
    "AKBNK": ["akbank"], "AKSA": ["aksa akrilik"], "AKSEN": ["aksa enerji"],
    "ALARK": ["alarko"], "ARCLK": ["arçelik", "arcelik"], "ASELS": ["aselsan"],
    "ASTOR": ["astor"], "BIMAS": ["bim", "bim mağazalar", "bim magazalar"],
    "BRSAN": ["borusan boru", "borusan mannesmann"], "BRYAT": ["borusan yatırım"],
    "CCOLA": ["coca cola içecek", "coca-cola içecek", "coca cola"],
    "CIMSA": ["çimsa", "cimsa"], "DOAS": ["doğuş otomotiv", "dogus otomotiv"],
    "DOHOL": ["doğan holding", "dogan holding"], "EKGYO": ["emlak konut"],
    "ENKAI": ["enka", "enka inşaat"], "ENJSA": ["enerjisa"],
    "EREGL": ["ereğli demir çelik", "erdemir", "ereğli", "eregli"],
    "FROTO": ["ford otosan", "ford"], "GARAN": ["garanti", "garanti bbva"],
    "GUBRF": ["gübre fabrikaları", "gubretas", "gübretaş"],
    "HALKB": ["halkbank", "halk bankası"], "HEKTS": ["hektaş", "hektas"],
    "ISCTR": ["iş bankası", "is bankasi", "işbank"], "ISMEN": ["iş yatırım"],
    "KCHOL": ["koç holding", "koc holding"], "KONTR": ["kontrolmatik"],
    "KRDMD": ["kardemir"], "KORDS": ["kordsa"], "KARSN": ["karsan"],
    "MGROS": ["migros"], "MAVI": ["mavi giyim"], "MPARK": ["mlp sağlık", "medical park"],
    "OTKAR": ["otokar"], "OYAKC": ["oyak çimento"], "ODAS": ["odaş", "odas"],
    "PETKM": ["petkim"], "PGSUS": ["pegasus"], "SAHOL": ["sabancı holding", "sabancı"],
    "SASA": ["sasa polyester", "sasa"], "SISE": ["şişecam", "sisecam"],
    "SKBNK": ["şekerbank"], "SOKM": ["şok marketler", "şok market"],
    "TAVHL": ["tav havalimanları", "tav"], "TCELL": ["turkcell"],
    "THYAO": ["türk hava yolları", "turk hava yollari", "thy"],
    "TKFEN": ["tekfen"], "TOASO": ["tofaş", "tofas"], "TSKB": ["tskb"],
    "TTKOM": ["türk telekom", "turk telekom"], "TTRAK": ["türk traktör"],
    "TUPRS": ["tüpraş", "tupras"], "TURSG": ["türkiye sigorta"],
    "ULKER": ["ülker", "ulker"], "VAKBN": ["vakıfbank", "vakifbank"],
    "VESTL": ["vestel"], "VESBE": ["vestel beyaz"], "YKBNK": ["yapı kredi", "yapi kredi"],
    "ZOREN": ["zorlu enerji"], "LOGO": ["logo yazılım"], "DEVA": ["deva holding"],
    "ECILC": ["eczacıbaşı ilaç"], "SELEC": ["selçuk ecza"], "TABGD": ["tab gıda"],
    "ANSGR": ["anadolu sigorta"], "ANHYT": ["anadolu hayat"],
    "GLYHO": ["global yatırım holding"], "ALBRK": ["albaraka"],
}
# Gündelik sözcükle karışan kodlar yalnızca BÜYÜK harfle yazılınca tanınır.
SOZCUK_KODLAR = {"SISE", "SASA", "MAVI", "LOGO", "DEVA", "AKSA", "ODAS", "TAVHL"}
DOLGU = re.compile(
    r"\b(hisse\w*|borsa\w*|analiz\w*|et|eder misin|yap|ne|oldu|durum\w*|nasıl|"
    r"nasil|gid\w*|kaç|kac|fiyat\w*|ne kadar|yorumla\w*|incele\w*|bugün|bugun|"
    r"son|şu an|su an|bana|lütfen|lutfen|akça|akca|değerlendir\w*|teknik)\b",
    re.IGNORECASE)
YAHOO_ARA = ("https://query1.finance.yahoo.com/v1/finance/search?q=%s"
             "&quotesCount=6&newsCount=0")


def _baslik(ad):
    return " ".join(("İ" + w[1:]) if w[:1] == "i" else w[:1].upper() + w[1:]
                    for w in ad.split())


def _adlar():
    cift = [(obsidyen.normal(a), kod) for kod, adlar in SIRKETLER.items()
            for a in adlar]
    return sorted(cift, key=lambda x: -len(x[0]))     # en uzun ad önce


def sirket_bul(metin):
    """Metindeki BIST şirketi: (kod, ad) ya da None."""
    k = obsidyen.normal(metin or "")
    for ad, kod in _adlar():
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(ad), k):
            return kod, _baslik(SIRKETLER[kod][0])
    for kelime in re.findall(r"\b[A-ZÇĞİÖŞÜ]{4,6}\b", metin or ""):
        if kelime in SIRKETLER:
            return kelime, _baslik(SIRKETLER[kelime][0])
    for kelime in re.findall(r"\w+", k):    # küçük yazılmış kod: "aefes"
        kod = kelime.upper()
        if kod in SIRKETLER and kod not in SOZCUK_KODLAR:
            return kod, _baslik(SIRKETLER[kod][0])
    return None


def yahoo_ara(metin, indir=None):
    """Listede olmayan şirket: Yahoo aramasıyla BIST (.IS) sembolü."""
    sorgu = " ".join(DOLGU.sub(" ", metin or "").split())[:60]
    if len(sorgu) < 3:
        return None
    veri = json.loads((indir or piyasa._indir)(YAHOO_ARA % quote(sorgu)))
    for q in veri.get("quotes") or []:
        s = str(q.get("symbol", ""))
        if s.endswith(".IS"):
            return s, q.get("longname") or q.get("shortname") or s[:-3]
    return None


def varlik_bul(metin, indir=None):
    """(Yahoo sembolü, görünen ad) ya da None."""
    k = obsidyen.normal(metin or "")
    for ad in sorted(analiz.OZEL, key=len, reverse=True):
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(obsidyen.normal(ad)), k):
            return analiz.OZEL[ad]
    s = sirket_bul(metin)
    if s:
        return s[0] + ".IS", "%s (%s)" % (s[1], s[0])
    if HISSE.search(metin or ""):
        try:
            b = yahoo_ara(metin, indir)
        except Exception:
            b = None
        if b:
            return b[0], "%s (%s)" % (b[1], b[0][:-3])
    return None


def _notla(ad, r):
    try:
        yol = obsidyen_yaz.yaz("Akçe", ad[:40] + " analiz",
                               obsidyen_yaz.onbilgi(tur="analiz") + r)
        return r + "\n\n(Not kaydedildi: %s)" % yol
    except Exception:
        return r


def akca(metin, indir=None):
    analiz_mi, fiyat_mi = ANALIZ.search(metin), FIYAT.search(metin)
    if not (analiz_mi or fiyat_mi):
        return None
    v = varlik_bul(metin, indir)
    if not v and fiyat_mi:                # kur/altın/endeks: TCMB ve piyasa
        r = piyasa.sorgula(metin, indir)
        if not r.startswith("Hangi değeri"):
            return r
    if not v:
        if HISSE.search(metin):
            return ("Hangi hisseyi kastettiğinizi bulamadım. Şirket adını ya da "
                    "işlem kodunu yazar mısınız? (örn. AEFES, THYAO)")
        return None
    sembol, ad = v
    if analiz_mi:
        try:
            r = analiz.rapor_sembol(sembol, ad, indir)
        except Exception as hata:
            return "%s için analiz yapılamadı: %s" % (ad, str(hata)[:160])
        return _notla(ad, r)
    try:
        return piyasa._satir(ad, piyasa.yahoo(sembol, indir), "") + (
            "\nNot: Yahoo verisi gecikmeli olabilir; resmî borsa verisi değildir.")
    except Exception as hata:
        return "%s fiyatı alınamadı: %s" % (ad, str(hata)[:160])


ISLER = {"AKÇA": akca}


def yonlendir(metin, indir=None):
    """-> (uzman adı, yanıt) | None. Uzman seçilir; doğrudan aracı varsa çalışır."""
    ad = uzmanlar.sec(metin)
    if not ad and (sirket_bul(metin) and (ANALIZ.search(metin) or FIYAT.search(metin))):
        ad = "AKÇA"
    is_ = ISLER.get(ad)
    if not is_ or not (ANALIZ.search(metin) or FIYAT.search(metin)):
        return None
    is_ = ajan_kayit.sar(uzmanlar.kimlik(ad), is_)   # uzmanın kartına düşsün
    yanit = is_(re.sub(r"^\s*%s\s*[:,\-]\s*" % re.escape(ad), "", metin,
                       flags=re.IGNORECASE), indir)
    return (ad, yanit) if yanit else None
