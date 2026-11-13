"""Mali tablo çözücü: eklenen bilanço/gelir tablosundan oranları KODDA hesaplar.

Kaynak: kullanıcının kendi indirip eklediği dosya (Fintables, KAP, İş Yatırım
dışa aktarımı; Excel/CSV/PDF/HTML). Otomatik veri çekmez (bu siteler bot
erişimine kapalı). Kalemler Türkçe adlarıyla tanınır; her satırdaki sayılar
dönem sütunları sayılır (ilk sayı en yeni dönem varsayılır, başlık satırı
varsa ondan okunur). Model yalnızca bu hesaplanmış oranları anlatır.
"""

import re

from . import obsidyen, piyasa

KALEMLER = [   # (anahtar, görünen ad, desen: normal biçimde satır başı)
    ("hasilat", "Hasılat (satışlar)", r"(hasilat|satis gelirleri|net satislar|satislar)\b"),
    ("brut_kar", "Brüt kâr", r"brut kar"),
    ("esas_faaliyet", "Esas faaliyet kârı", r"(esas )?faaliyet kari"),
    ("net_kar", "Dönem net kârı", r"(net )?donem (net )?kari|net kar\b"),
    ("ana_net_kar", "Ana ortaklık payı (net kâr)", r"ana ortaklik paylari"),
    ("donen", "Dönen varlıklar", r"donen varliklar"),
    ("toplam_varlik", "Toplam varlıklar", r"(toplam varliklar|varliklar toplami|toplam aktifler)"),
    ("kisa_yuk", "Kısa vadeli yükümlülükler", r"kisa vadeli yukumlulukler"),
    ("uzun_yuk", "Uzun vadeli yükümlülükler", r"uzun vadeli yukumlulukler"),
    ("ozkaynak", "Özkaynaklar", r"(toplam )?ozkaynaklar\b"),
    ("ana_ozkaynak", "Ana ortaklığa ait özkaynaklar", r"ana ortakliga ait ozkaynaklar"),
    ("nakit", "Nakit ve benzerleri", r"nakit ve nakit benzerleri"),
    ("sermaye", "Ödenmiş sermaye", r"odenmis sermaye"),
]
SAYI = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})+(?:,\d+)?\)?|\(?-?\d+(?:[.,]\d+)?\)?")
DONEM = re.compile(r"\b(20\d{2})\s*[/.\-]\s*(0?3|0?6|0?9|12)\b"
                   r"|\b(0?3|0?6|0?9|12)\s*/\s*(20\d{2})\b")


def sayi_coz(s):
    """'1.234.567,89' / '(1.234)' / '-12345.6' -> float."""
    eksi = s.startswith("(") and s.endswith(")") or s.startswith("-")
    s = s.strip("()-")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if eksi else x


def _satir_coz(satir):
    """'Hasılat\t12.345\t10.000' -> ('hasilat', [12345.0, 10000.0])"""
    parca = re.split(r"\t|;|\s{2,}|\|", satir.strip())
    etiket, degerler = [], []
    for p in parca:
        p = p.strip()
        if not p:
            continue
        if re.fullmatch(SAYI.pattern, p):
            x = sayi_coz(p)
            if x is not None:
                degerler.append(x)
        elif not degerler:
            etiket.append(p)
    if not etiket and not degerler:
        return "", []
    if not etiket:
        return "", degerler
    ad = " ".join(etiket)
    if not degerler:          # boşlukla ayrılmış: sondaki sayıları ayıkla
        sozler = ad.split()
        while sozler and re.fullmatch(SAYI.pattern, sozler[-1]) and \
                sayi_coz(sozler[-1]) is not None:
            degerler.insert(0, sayi_coz(sozler.pop()))
        ad = " ".join(sozler)
    temiz = re.sub(r"^(?:\d+[.)]?\s*|[a-zA-Z]\)\s*|[-•]\s*)+", "", ad.strip())  # "1. a)" vb.
    return obsidyen.normal(temiz).strip(" :.-"), degerler


def coz(metin):
    """-> {'donemler': [...], 'kalem': {anahtar: [değerler]}}"""
    donemler, kalem = [], {}
    son_net_kar_sira = None
    for sira, satir in enumerate((metin or "").splitlines()):
        if not donemler:
            bulunan = DONEM.findall(satir)
            if len(bulunan) >= 2:
                donemler = ["%s/%s" % ((a or d), int(b or c)) for a, b, c, d in bulunan]
                continue
        etiket, degerler = _satir_coz(satir)
        if not etiket or not degerler or len(etiket) > 80:
            continue
        # KAP tablolarındaki "Dipnot" sütunu (küçük tam sayı) dönem değeri sayılmasın
        if len(degerler) >= 2 and float(degerler[0]).is_integer() and \
                0 < abs(degerler[0]) < 100 and (
                    (donemler and len(degerler) == len(donemler) + 1)
                    or (not donemler and all(abs(x) >= 1000 for x in degerler[1:]))):
            degerler = degerler[1:]
        for anahtar, _, desen in KALEMLER:
            if anahtar in kalem and anahtar != "ana_net_kar":
                continue
            if not re.match(desen, etiket):
                continue
            if anahtar == "ana_net_kar":
                # yalnızca net kârın hemen altındaki ana ortaklık payı
                if anahtar in kalem or son_net_kar_sira is None or sira - son_net_kar_sira > 4:
                    continue
            if anahtar == "net_kar":
                son_net_kar_sira = sira
            kalem[anahtar] = degerler
            break
    return {"donemler": donemler, "kalem": kalem}


def tablo_mu(metin):
    return len(coz(metin)["kalem"]) >= 3


def _oran(a, b):
    if a is None or not b:
        return None
    return 100.0 * a / b


def _ilk(k, ad, i=0):
    d = k.get(ad) or []
    return d[i] if len(d) > i else None


def _tr(x, b=1):
    return "—" if x is None else piyasa.tr_sayi(x, b)


def ozet(metin):
    """Kodda hesaplanan oranlar (en yeni dönem = ilk sütun)."""
    c = coz(metin)
    k, d = c["kalem"], c["donemler"]
    if len(k) < 3:
        return ""
    donem = d[0] if d else "en yeni dönem (ilk sütun)"
    onceki = d[1] if len(d) > 1 else "önceki sütun"
    net = _ilk(k, "ana_net_kar") if "ana_net_kar" in k else _ilk(k, "net_kar")
    oz = _ilk(k, "ana_ozkaynak") or _ilk(k, "ozkaynak")
    borc = None
    if _ilk(k, "kisa_yuk") is not None or _ilk(k, "uzun_yuk") is not None:
        borc = (_ilk(k, "kisa_yuk") or 0) + (_ilk(k, "uzun_yuk") or 0)
    satir = ["[KODDA HESAPLANAN MALİ ORANLAR – dönem: %s]" % donem]
    for anahtar, ad, _ in KALEMLER:
        if anahtar in k:
            v = k[anahtar]
            degisim = ""
            if len(v) > 1 and v[1]:
                degisim = " (önceki döneme, %s, göre %%%s)" % (
                    onceki, _tr(100 * (v[0] / v[1] - 1)))
            satir.append("- %s: %s%s" % (ad, _tr(v[0], 0), degisim))
    oranlar = [
        ("Brüt kâr marjı", _oran(_ilk(k, "brut_kar"), _ilk(k, "hasilat"))),
        ("Esas faaliyet kâr marjı", _oran(_ilk(k, "esas_faaliyet"), _ilk(k, "hasilat"))),
        ("Net kâr marjı", _oran(net, _ilk(k, "hasilat"))),
        ("Özkaynak kârlılığı (dönem, yıllığa çevrilmemiş)", _oran(net, oz)),
        ("Borç / özkaynak", _oran(borc, oz)),
        ("Cari oran (dönen varlık / kısa vadeli borç)",
         _oran(_ilk(k, "donen"), _ilk(k, "kisa_yuk"))),
    ]
    satir.append("Oranlar:")
    for ad, x in oranlar:
        if x is not None:
            kat = "Cari" in ad or "Borç" in ad
            satir.append("- %s: %s" % (ad, _tr(x / 100, 2) + " kat" if kat else "%" + _tr(x)))
    satir.append("Not: Tutarlar dosyadaki birimle (çoğunlukla TL ya da bin TL). Ara "
                 "dönem oranları yıllık değildir. F/K ve PD/DD için güncel fiyat ve pay "
                 "sayısı gerekir; dosyada yoksa hesaplanmaz. Kaynak: eklediğiniz dosya.")
    return "\n".join(satir)


def yapistirmaya_ekle(metin):
    """Sohbete yapıştırılmış (Fintables/KAP'tan kopyalanmış) mali tablo:
    oranlar kodda hesaplanıp iletinin başına eklenir; ileti AKÇA'ya gider."""
    if (not metin or metin.count("\n") < 3 or "[KODDA HESAPLANAN MALİ ORANLAR" in metin
            or "[EKLİ DOSYA:" in metin or not tablo_mu(metin)):
        return metin
    satirlar = metin.splitlines()
    soru = satirlar[0] if not _satir_coz(satirlar[0])[1] and len(satirlar[0]) < 200 else ""
    return "%s\n\n%s\n\n[EKLİ DOSYA: yapıştırılan tablo]\n%s" % (
        soru or "Bu mali tabloyu yorumla.", ozet(metin), metin)
