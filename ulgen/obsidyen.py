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


def _alinti(yol, kelimeler, uzunluk=1400):
    try:
        icerik = _oku(yol)
    except Exception:
        return ""
    kucuk = normal(icerik)
    konumlar = [kucuk.find(k) for k in kelimeler if k in kucuk]
    konum = min(konumlar) if konumlar else 0
    # normal() uzunluğu değiştirmez (harf başına harf), konum eşleşir
    return icerik[max(0, konum - 300): konum + uzunluk - 300].strip()


def ara(metin, adet=3):
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
        sonuc.append((baslik, s["yol"], _alinti(s["yol"], kelimeler)))
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
