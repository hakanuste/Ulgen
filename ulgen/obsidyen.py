"""Obsidian kasası dizini (bu modül YALNIZ OKUR; yazma ``obsidyen_yaz``da).

Kasadaki .md ve .pdf dosyaları kendi yerinde kalır; Ülgen yalnızca şifreli
veritabanında bir arama dizini tutar (FTS5). Tarama artımlıdır: yalnız
değişen dosyalar yeniden okunur. Kasaya hiçbir şey yazılmaz/silinmez.
Dizin her zaman kasadan yeniden üretilebilir (silinse bir şey kaybolmaz).
Araştırma/OCR notları yalnız ``Ülgen/`` alt klasörüne ``obsidyen_yaz`` ile yazılır.
"""

import os
import re
import threading
import time

from . import ayar, veritabani

AZ_BEKLE_SN = 300
MD_SINIR = 1000000
PDF_SINIR = 25000000
PDF_SAYFA = 300
_CEVIRI = str.maketrans("ıİIğĞüÜşŞöÖçÇâÂîÎûÛ", "iiigguussoocc" "aaiiuu")
_KILIT = threading.Lock()
_SON = {"zaman": 0.0, "sonuc": None}
KELIME = re.compile(r"\w{2,}", re.UNICODE)


def normal(metin):
    return metin.translate(_CEVIRI).lower()


def _adaylar():
    """Ayar boşsa bakılacak yerler: içinde .obsidian klasörü olan klasör."""
    ev = os.path.expanduser("~")
    sabit = [os.path.join(ev, "Documents", "Obsidyen"),
             os.path.join(ev, "Documents", "Obsidian"),
             os.path.join(ev, "Obsidyen"), os.path.join(ev, "Obsidian")]
    for ust in (os.path.join(ev, "Documents"), ev,
                os.path.join(ev, "Library", "Mobile Documents",
                             "iCloud~md~obsidian", "Documents")):
        try:
            for ad in sorted(os.listdir(ust)):
                yol = os.path.join(ust, ad)
                if os.path.isdir(os.path.join(yol, ".obsidian")):
                    sabit.append(yol)
        except OSError:
            continue
    return sabit


def kasa_yolu():
    """ayar.json "kasa" doluysa o; değilse bulunan ilk Obsidian kasası."""
    ayarli = ayar.yukle().get("kasa")
    if ayarli:
        return ayar.yol_ac(ayarli)
    adaylar = _adaylar()
    for yol in adaylar:          # önce gerçekten Obsidian kasası olanlar
        if os.path.isdir(os.path.join(yol, ".obsidian")):
            return yol
    for yol in adaylar:
        if os.path.isdir(yol):
            return yol
    return ayar.yol_ac("~/Documents/Obsidyen")


def erisim_durumu(kasa=None):
    """(tamam_mi, ileti, md_sayisi): klasör var mı, okunabiliyor mu."""
    kasa = kasa or kasa_yolu()
    if not os.path.isdir(kasa):
        return False, ("Kasa klasörü yok: %s. ayar.json içinde \"kasa\" "
                       "alanına gerçek yolu yazın." % kasa), 0
    try:
        adet = sum(1 for k, _, a in os.walk(kasa, onerror=_hata_ver)
                   for x in a if x.lower().endswith(".md"))
    except PermissionError:
        return False, ("macOS bu klasöre erişimi engelliyor. Sistem Ayarları "
                       "> Gizlilik ve Güvenlik > Tam Disk Erişimi'ne "
                       "~/Ülgen/ortam/bin/python ekleyin, Ülgen'i yeniden "
                       "başlatın."), 0
    except OSError as hata:
        return False, "Kasa okunamadı: %s" % hata, 0
    return True, "Kasa okunuyor: %d not dosyası." % adet, adet


def _hata_ver(hata):
    raise hata


def hazir_mi():
    return bool(veritabani.sorgu(
        "SELECT 1 FROM sqlite_master WHERE name='not_fts'", (), True))


def _oku(yol):
    if yol.lower().endswith(".pdf"):
        from pypdf import PdfReader
        okuyucu = PdfReader(yol)
        return "\n".join((s.extract_text() or "")
                         for s in okuyucu.pages[:PDF_SAYFA])
    with open(yol, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _dosyalar(kasa):
    for kok, klasorler, adlar in os.walk(kasa):    # erişim kontrolü tara()'da
        klasorler[:] = [k for k in klasorler if not k.startswith(".")]
        for ad in adlar:
            kucuk = ad.lower()
            if kucuk.endswith((".md", ".pdf")):
                yol = os.path.join(kok, ad)
                try:
                    st = os.stat(yol)
                except OSError:
                    continue
                sinir = PDF_SINIR if kucuk.endswith(".pdf") else MD_SINIR
                if st.st_size <= sinir:
                    yield yol, st.st_mtime, st.st_size


def tara(zorla=False):
    """Artımlı tarama. {"yeni", "guncel", "silinen", "toplam", "hata"}."""
    if not hazir_mi():
        return {"hata": "dizin tablosu yok"}
    with _KILIT:
        simdi = time.time()
        if not zorla and simdi - _SON["zaman"] < AZ_BEKLE_SN \
                and _SON["sonuc"]:
            return _SON["sonuc"]
        kasa = kasa_yolu()
        sonuc = {"yeni": 0, "guncel": 0, "silinen": 0, "toplam": 0,
                 "hata": 0, "kasa": kasa}
        tamam, ileti, _ = erisim_durumu(kasa)
        if not tamam:
            sonuc["hata"] = ileti
            _SON.update(zaman=simdi, sonuc=sonuc)
            return sonuc
        var = {s["yol"]: s for s in veritabani.sorgu(
            "SELECT yol, mtime, boyut FROM not_dizin", (), True)}
        gorulen = set()
        for yol, mtime, boyut in _dosyalar(kasa):
            gorulen.add(yol)
            eski = var.get(yol)
            if eski and eski["mtime"] == mtime and eski["boyut"] == boyut:
                continue
            try:
                icerik = _oku(yol)
            except Exception:            # bozuk PDF/okunamayan dosya
                sonuc["hata"] += 1
                continue
            baslik = os.path.splitext(os.path.basename(yol))[0]
            with veritabani.islem():
                veritabani.sorgu("DELETE FROM not_fts WHERE yol=?", (yol,))
                veritabani.sorgu(
                    "INSERT INTO not_fts (yol, baslik, icerik) VALUES "
                    "(?, ?, ?)", (yol, normal(baslik), normal(icerik)))
                veritabani.sorgu(
                    "INSERT OR REPLACE INTO not_dizin (yol, mtime, boyut) "
                    "VALUES (?, ?, ?)", (yol, mtime, boyut))
            sonuc["guncel" if eski else "yeni"] += 1
        for yol in set(var) - gorulen:
            with veritabani.islem():
                veritabani.sorgu("DELETE FROM not_fts WHERE yol=?", (yol,))
                veritabani.sorgu("DELETE FROM not_dizin WHERE yol=?", (yol,))
            sonuc["silinen"] += 1
        sonuc["toplam"] = len(gorulen)
        _SON.update(zaman=time.time(), sonuc=sonuc)
        return sonuc


def arka_planda_tara():
    t = threading.Thread(target=lambda: _guvenli(), daemon=True)
    t.start()
    return t


def _guvenli():
    try:
        tara()
    except Exception:
        pass


DUZELTME = re.compile(
    r"\b(yanlış\w*|yanlis\w*|hatalı\w*|hatali\w*|doğrusu\w*|dogrusu\w*|"
    r"düzelt\w*|duzelt\w*|öyle değil|oyle degil|o değil|hayır|hayir|"
    r"aslında|aslinda)\b", re.IGNORECASE)
TUR = re.compile(r"^## (Ben|Yapay zekâ)\s*$", re.MULTILINE)
PARCA_BOYU = 900         # not/sohbet parçası (karakter); küçük parça = ince seçim
DOLGU = {"var", "hangi", "nedir", "nasil", "neden", "icin", "gibi", "olan",
         "bir", "bu", "ve", "ile", "mi", "mu", "ne"}


def turlar(icerik):
    """ChatGPT aktarımındaki '## Ben' / '## Yapay zekâ' turları: [(rol, metin)]."""
    bol = TUR.split(icerik)
    return [(bol[i], bol[i + 1].strip()) for i in range(1, len(bol) - 1, 2)]


def not_parcalari(icerik, boy=PARCA_BOYU):
    """Notu baştan sona parçalara böler: [(etiket, metin)].

    Rolleri belli sohbette (ChatGPT aktarımı) parça sınırı tur sınırıdır; her
    tur 'KULLANICI (Hakan)' / 'YAPAY ZEKÂ', düzeltmeler 'DÜZELTME' diye
    işaretlenir. Diğer notlar (kılavuz sayfaları, kendi notlarınız, rolsüz
    sohbetler) paragraf sınırından bölünür."""
    tlar = turlar(icerik)
    parcalar, simdiki, ilk = [], [], None
    if tlar:
        for i, (rol, govde) in enumerate(tlar):
            etiket = "KULLANICI (Hakan)" if rol == "Ben" else "YAPAY ZEKÂ"
            if rol == "Ben" and i and DUZELTME.search(govde):
                etiket += " - DÜZELTME"
            satir = "[%d. tur, %s] %s" % (i + 1, etiket, govde[:boy])
            if simdiki and sum(map(len, simdiki)) + len(satir) > boy:
                parcalar.append(("tur %d-%d" % (ilk, i), "\n".join(simdiki)))
                simdiki = []
            if not simdiki:
                ilk = i + 1
            simdiki.append(satir)
        if simdiki:
            parcalar.append(("tur %d-%d" % (ilk, len(tlar)), "\n".join(simdiki)))
        return parcalar
    govde = re.sub(r"^---.*?---\s*", "", icerik, flags=re.S)
    for paragraf in re.split(r"\n\s*\n", govde):
        paragraf = paragraf.strip()
        if not paragraf:
            continue
        if len(paragraf) > boy and simdiki:     # önce birikeni kapat
            parcalar.append(("bölüm %d" % (len(parcalar) + 1), "\n\n".join(simdiki)))
            simdiki = []
        while len(paragraf) > boy:              # çok uzun paragraf da bölünür
            kes = paragraf.rfind("\n", boy // 2, boy)
            kes = kes if kes > 0 else boy
            parcalar.append(("bölüm %d" % (len(parcalar) + 1), paragraf[:kes]))
            paragraf = paragraf[kes:].lstrip("\n")
        if simdiki and sum(map(len, simdiki)) + len(paragraf) > boy:
            parcalar.append(("bölüm %d" % (len(parcalar) + 1), "\n\n".join(simdiki)))
            simdiki = []
        simdiki.append(paragraf)
    if simdiki:
        parcalar.append(("bölüm %d" % (len(parcalar) + 1), "\n\n".join(simdiki)))
    return parcalar


# Aynı şeyi anlatan farklı sözcükler (normal biçimde, kök olarak).
ESANLAM = {
    "olcu": ["boyut", "ebat", "kot", "taban", "genislik", "derinlik",
             "yukseklik", "kalinlik", "uzunluk", "alan"],
    "boyut": ["olcu", "ebat", "kot"], "ebat": ["olcu", "boyut"],
    "fiyat": ["ucret", "tutar", "maliyet"], "maliyet": ["fiyat", "tutar"],
    "plan": ["proje", "cizim", "tasarim"], "tasarim": ["plan", "proje", "cizim"],
    "ariza": ["sorun", "problem"], "sorun": ["ariza", "problem"],
}
EKLER = ("lerinin", "larinin", "lerini", "larini", "leri", "lari", "ler", "lar",
         "inin", "unun", "nin", "nun", "sinin", "sunun", "si", "su", "in", "un",
         "den", "dan", "ten", "tan", "de", "da", "te", "ta", "e", "a", "i", "u")
SON = re.compile(r"\b(son|en son|guncel|nihai|kesin|simdiki|en yeni)\b")
OLCU_SORU = re.compile(r"\b(olcu\w*|boyut\w*|ebat\w*|kot\w*|kac\w*|metre\w*)\b")
OLCU_DEGER = re.compile(r"\d+(?:[.,]\d+)?\s*(?:m²|m2|m³|cm|mm|m|metre|°)(?!\w)")


def kok_bul(k):
    """'evin' -> 'ev', 'olculeri' -> 'olcu' (kaba ek atma; kök ≥ 2 harf)."""
    for ek in EKLER:
        if k.endswith(ek) and len(k) - len(ek) >= 2:
            return k[:-len(ek)]
    return k


def kokler(kelimeler, esanlam=True):
    """Aranacak sözcük kökleri; istenirse eş anlamlılar da eklenir."""
    sonuc = []
    for k in kelimeler:
        k = normal(k)
        if len(k) < 2 or k in DOLGU or k in AYLAR or SON.fullmatch(k):
            continue
        kok = kok_bul(k)
        adaylar = [kok]
        if esanlam:
            for anahtar, liste in ESANLAM.items():
                if kok.startswith(anahtar):
                    adaylar += liste
        for x in adaylar:
            if x not in sonuc:
                sonuc.append(x)
    return sonuc[:20]


def eslesir(kok, n):
    """Kısa kök (≤3 harf, örn. 'ev', 'tas') sözcük başında aranır ve ardından
    yalnızca ek gelebilir: 'ev' 'evet'i, 'tas' 'tasarım'ı tutmaz."""
    if len(kok) > 3:
        return kok in n
    return re.search(r"\b%s(?:%s)?\b" % (re.escape(kok), "|".join(EKLER)), n) is not None


AYLAR = {"ocak": ("oca", "jan"), "subat": ("sub", "feb"), "mart": ("mar",),
         "nisan": ("nis", "apr"), "mayis": ("may",), "haziran": ("haz", "jun"),
         "temmuz": ("tem", "jul"), "agustos": ("agu", "aug"), "eylul": ("eyl", "sep"),
         "ekim": ("eki", "oct"), "kasim": ("kas", "nov"), "aralik": ("ara", "dec")}
TARIH = re.compile(r"\b(\d{1,2}) (%s)\w* (\d{4})\b" % "|".join(AYLAR))


def ay_ipucu(metin):
    """Soruda geçen ay adı (normal biçim) ya da None: 'eylül sonu' -> 'eylul'."""
    n = normal(metin or "")
    for ad in AYLAR:
        if re.search(r"\b%s" % ad, n):
            return ad
    return None


KUTU = re.compile("[\u2500-\u257f]+")


def gorunum_temizle(metin):
    """Kutu çizgileri (╔═║─) ve LaTeX artıkları ($6,5\\text{ m}$) yer kaplar,
    aramayı bozar ve sesle okunur: sade metne çevrilir."""
    t = KUTU.sub(" ", metin)
    t = re.sub(r"\\(?:text|mathbf|mathrm)\{([^{}]*)\}", r"\1", t)
    t = t.replace("\\times", "×").replace("\\(", "").replace("\\)", "")
    t = re.sub(r"\$([^$\n]{1,80})\$", r"\1", t)
    t = t.replace("\\ ", " ").replace("\\", "")
    return re.sub(r"[ \t]{2,}", " ", t)


def _parca_tarihleri(parcalar):
    """Her parçanın tarihi: içinde ya da öncesinde geçen son '25 Eylül 2026'
    (Gemini aktarımlarında tarih turların arasında yazar)."""
    sonuc, son = [], ""
    for _, govde in parcalar:
        bulunan = TARIH.findall(normal(govde))
        if bulunan:
            g, ay, yil = bulunan[-1]
            son = "%s %s %s" % (g, ay, yil)
        sonuc.append(son)
    return sonuc


def parcali_alinti(icerik, kelimeler, sinir=2500):
    """Notun TAMAMI parçalara bölünür ve her parça puanlanır:
    - sorudaki sözcük (kökü) 2, eş anlamlısı 1 puan ('ölçü' -> boyut, kot…);
    - ölçü soruluyorsa ölçü değerleri (6,5 m, 40 cm, 84,5 m²) yoğun parça öne;
    - 'son/güncel' soruluyorsa notun sonuna doğru olan parça öne;
    - soruda ay geçiyorsa (eylül) o ayın tarihli parçası öne;
    - düzeltmenizi içeren parça öne; eşitlikte sonraki parça önce.
    Seçilenler notun kendi sırasıyla, yer ve tarih bilgisiyle verilir."""
    soru = normal(" ".join(kelimeler))
    ay = ay_ipucu(soru)
    son_mu = bool(SON.search(soru))
    olcu_mu = bool(OLCU_SORU.search(soru))
    asil = kokler(kelimeler, esanlam=False)
    kok = kokler(kelimeler)
    # pay küçükse parçalar da küçülür (tek parçaya sığmayan seçimi yapabilsin)
    parcalar = not_parcalari(gorunum_temizle(icerik),
                             min(PARCA_BOYU, max(200, sinir // 2)))
    if not parcalar:
        return ""
    tarihler = _parca_tarihleri(parcalar)
    rollu = bool(TUR.search(icerik))
    adet = len(parcalar)
    puanli = []
    for sira, (_, govde) in enumerate(parcalar):
        n = normal(govde)
        puan = sum(2 if k in asil else 1 for k in kok if eslesir(k, n))
        if not puan:
            continue
        if olcu_mu:
            puan += min(6, len(OLCU_DEGER.findall(n)) // 2)
        if ay and ay in tarihler[sira]:
            puan += 2
        if "DÜZELTME]" in govde or (not rollu and DUZELTME.search(govde)):
            puan += 2
        if son_mu and adet > 1:          # "son ölçüler": ilgili olanlardan sonraki
            puan *= 1 + sira / (adet - 1)
        puanli.append((puan, sira))
    if not puanli:
        return parcalar[0][1][:sinir]
    if adet == 1:
        return parcalar[0][1][:sinir]
    puanlar = dict((sira, puan) for puan, sira in puanli)
    en_iyi = max(puanlar.values())
    secilen, toplam = [], 0
    for puan, sira in sorted(puanli, reverse=True):
        if puan < en_iyi * 0.4 and secilen:     # zayıf parça dolgu olmasın
            break
        # bir tablo/liste iki parçaya bölünmüşse başı ve devamı da alınsın
        for i in (sira, sira - 1, sira + 1):
            if i in secilen or i < 0 or i >= adet:
                continue
            if i != sira and puanlar.get(i, 0) < en_iyi * 0.4:
                continue
            uzunluk = len(parcalar[i][1])
            if toplam + uzunluk > sinir and secilen:
                continue
            secilen.append(i)
            toplam += uzunluk
    return "\n…\n".join(
        "(%s / %d parça%s) %s" % (parcalar[i][0], adet,
                                  ", " + tarihler[i] if tarihler[i] else "",
                                  parcalar[i][1])
        for i in sorted(secilen))


def _alinti(yol, kelimeler, uzunluk=2500):
    """Notun ilk eşleşen yeri DEĞİL, tamamı taranıp en ilgili parçaları."""
    try:
        icerik = _oku(yol)
    except Exception:
        return ""
    return parcali_alinti(icerik, kelimeler, uzunluk)


def ara(metin, adet=3, alinti_boyu=2500):
    """[(baslik, yol, alinti)]; en iyi eşleşmeler önce (bm25)."""
    if not hazir_mi():
        return []
    kelimeler = [k for k in KELIME.findall(normal(metin))][:12]
    if not kelimeler:
        return []
    tara()                                   # artımlı, 5 dakikada bir
    # Türkçe ekler: "aracim" kök "arac"ı da bulsun
    aranacak = list(kelimeler)
    for k in kelimeler:
        if len(k) >= 5 and k[:max(4, len(k) - 3)] not in aranacak:
            aranacak.append(k[:max(4, len(k) - 3)])
    for k in kokler(kelimeler):           # 'evin' -> 'ev'; ölçü -> boyut, kot…
        if len(k) >= 2 and k not in aranacak:
            aranacak.append(k)
    ifade = " OR ".join('"%s"*' % k.replace('"', "") for k in aranacak)
    try:
        satirlar = veritabani.sorgu(
            "SELECT yol FROM not_fts WHERE not_fts MATCH ? "
            "ORDER BY bm25(not_fts, 0, 5.0, 1.0) LIMIT ?",
            (ifade, adet), True)
    except Exception:
        return []
    sonuc = []
    for s in satirlar:
        baslik = os.path.splitext(os.path.basename(s["yol"]))[0]
        sonuc.append((baslik, s["yol"], _alinti(s["yol"], kelimeler, alinti_boyu)))
    return sonuc


def durum():
    """Panel için: kasa yolu, erişim iletisi, dizinlenen not sayısı."""
    kasa = kasa_yolu()
    tamam, ileti, adet = erisim_durumu(kasa)
    dizinli = 0
    if hazir_mi():
        dizinli = veritabani.sorgu(
            "SELECT COUNT(*) AS c FROM not_dizin", (), True)[0]["c"]
    return {"kasa": kasa, "erisim": tamam, "ileti": ileti,
            "dosya": adet, "dizinli": dizinli, "hazir": hazir_mi()}
