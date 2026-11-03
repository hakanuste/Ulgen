"""Kılavuz klasöründeki PDF/metin dosyalarını Obsidian kasasına not olarak aktarır.

Artımlıdır: yalnız yeni ya da değişen dosyalar işlenir (kayıt ÜlgenVeri
klasöründe). Büyük PDF'ler 50 sayfalık Markdown notlara bölünür ve her PDF için
bir "Dizin" notu yazılır. Kasa dışına YAZILMAZ; yazılan yerler yalnız
``<kasa>/<PDF adı>/`` klasörleri ve kopyalanan .md/.txt dosyalarıdır.
Taranmış (görüntü) PDF'lerde metin çıkmaz; dizin notunda uyarı yazılır."""

import json
import os
import re
import shutil
import threading
import time
import math
import xml.etree.ElementTree as ET
from datetime import date, datetime
from html.parser import HTMLParser

from . import ayar, obsidyen

PARCA_BOYU = 50
UZANTILAR = (".pdf", ".docx", ".html", ".htm", ".kml", ".kmz", ".md", ".txt")
DOCX_PARCA = 40000      # karakter
_KILIT = threading.Lock()
_DURUM = {"calisiyor": False, "dosya": "", "bitti": 0, "toplam": 0,
          "son": None, "hata": []}


def _normal(ad):
    return obsidyen.normal(ad)


def klasor_bul():
    """ayar 'kilavuz_klasoru' doluysa o; değilse Belgeler/Masaüstü/ev içinde
    adında 'klavuz' ya da 'kilavuz' geçen ilk klasör."""
    ayarli = ayar.yukle().get("kilavuz_klasoru")
    if ayarli:
        return ayar.yol_ac(ayarli)
    ev = os.path.expanduser("~")
    for ust in (os.path.join(ev, "Documents"), os.path.join(ev, "Desktop"), ev):
        try:
            adlar = sorted(os.listdir(ust))
        except OSError:
            continue
        for ad in adlar:
            n = _normal(ad)
            yol = os.path.join(ust, ad)
            if os.path.isdir(yol) and ("klavuz" in n or "kilavuz" in n):
                return yol
    return os.path.join(ev, "Documents", "Klavuzlar")


def _kayit_yolu():
    return os.path.join(ayar.KLASOR, "kilavuz_aktarim.json")


def _kayit_oku():
    try:
        with open(_kayit_yolu(), "r", encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def _kayit_yaz(veri):
    ayar.klasor_hazirla()
    gecici = _kayit_yolu() + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.chmod(gecici, 0o600)
    os.replace(gecici, _kayit_yolu())


def dosya_adi_temizle(ad):
    ad = re.sub(r'[\\/:*?"<>|#^\[\]]+', " ", ad)
    return re.sub(r"\s+", " ", ad).strip(" .") or "isimsiz"


def _dosyalar(kaynak):
    for kok, klasorler, adlar in os.walk(kaynak):
        klasorler[:] = [k for k in klasorler if not k.startswith(".")]
        for ad in sorted(adlar):
            if ad.lower().endswith(UZANTILAR) and not ad.startswith("."):
                yol = os.path.join(kok, ad)
                try:
                    st = os.stat(yol)
                except OSError:
                    continue
                yield yol, st.st_mtime, st.st_size


def bekleyenler(kaynak=None):
    """Aktarılmamış ya da değişmiş dosyalar [(yol, mtime, boyut)]."""
    kaynak = kaynak or klasor_bul()
    if not os.path.isdir(kaynak):
        return []
    kayit = _kayit_oku()
    return [(y, m, b) for y, m, b in _dosyalar(kaynak)
            if kayit.get(y, {}).get("mtime") != m
            or kayit.get(y, {}).get("boyut") != b]


def _pdf_aktar(yol, kasa):
    """Bir PDF'i parçalara bölüp yazar; (sayfa, parça, boş) döndürür."""
    from pypdf import PdfReader
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    hedef = os.path.join(kasa, ad)
    dizin_yolu = os.path.join(hedef, ad + " - Dizin.md")
    okuyucu = PdfReader(yol)
    toplam = len(okuyucu.pages)
    os.makedirs(hedef, exist_ok=True)
    parcalar, bos = [], 0
    for bas in range(0, toplam, PARCA_BOYU):
        son = min(bas + PARCA_BOYU, toplam)
        parca_ad = "%s - Sayfa %d-%d" % (ad, bas + 1, son)
        satirlar = ["---", "kaynak: %s" % os.path.basename(yol),
                    "sayfalar: %d-%d" % (bas + 1, son),
                    "aktarim: %s" % date.today().isoformat(),
                    "tags: [kılavuz]", "---", "", "# " + parca_ad, "",
                    "[[%s - Dizin]]" % ad, ""]
        for i in range(bas, son):
            try:
                metin = (okuyucu.pages[i].extract_text() or "").strip()
            except Exception:
                metin = ""
            if not metin:
                bos += 1
            satirlar += ["## Sayfa %d" % (i + 1), "",
                         metin or "*(bu sayfada metin yok)*", ""]
        gecici = os.path.join(hedef, parca_ad + ".md.tmp")
        with open(gecici, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar))
        os.replace(gecici, os.path.join(hedef, parca_ad + ".md"))
        parcalar.append((parca_ad, bas + 1, son))
    dizin = ["---", "kaynak: %s" % os.path.basename(yol),
             "sayfa_sayisi: %d" % toplam,
             "aktarim: %s" % date.today().isoformat(), "tags: [dizin]", "---",
             "", "# %s — Dizin" % ad, "",
             "Toplam sayfa: %d. Metni olmayan sayfa: %d." % (toplam, bos), ""]
    if toplam and bos > toplam * 0.5:
        dizin += ["> Uyarı: Sayfaların büyük bölümünde metin çıkmadı. Dosya "
                  "taranmış bir görüntü olabilir; OCR gerekir.", ""]
    dizin += ["- [[%s]] (sayfa %d-%d)" % p for p in parcalar]
    with open(dizin_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(dizin) + "\n")
    return toplam, len(parcalar), bos


def _tur(yol):
    """Dosyanın gerçek türü (içeriğe göre): pdf | docx | zip | metin | bilinmiyor."""
    low = yol.lower()
    if low.endswith((".md", ".txt")):
        return "metin"
    if low.endswith((".kml", ".kmz")):
        return "kml"
    if low.endswith((".html", ".htm")):
        return "html"
    try:
        with open(yol, "rb") as f:
            bas = f.read(8)
    except OSError:
        return "bilinmiyor"
    if bas.startswith(b"%PDF"):
        return "pdf"
    if bas.startswith(b"PK"):
        import zipfile
        try:
            with zipfile.ZipFile(yol) as z:
                return "docx" if "word/document.xml" in z.namelist() else "zip"
        except (zipfile.BadZipFile, OSError):
            return "zip"
    return "pdf" if low.endswith(".pdf") else "bilinmiyor"


def _docx_aktar(yol, kasa):
    """Word dosyasını Markdown notlarına yazar; (parça sayısı,) döndürür."""
    import zipfile
    with zipfile.ZipFile(yol) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    metin = re.sub(r"<[^>]+>", "", xml)
    for kod, kar in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"),
                     ("&amp;", "&")):
        metin = metin.replace(kod, kar)
    metin = re.sub(r"\n{3,}", "\n\n", metin).strip()
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    hedef = os.path.join(kasa, ad)
    os.makedirs(hedef, exist_ok=True)
    parcalar = [metin[i:i + DOCX_PARCA] for i in range(0, len(metin), DOCX_PARCA)] or [""]
    adlar = []
    for n, govde in enumerate(parcalar, 1):
        parca_ad = "%s - Bölüm %d" % (ad, n)
        icerik = ["---", "kaynak: %s" % os.path.basename(yol),
                  "aktarim: %s" % date.today().isoformat(), "tags: [kılavuz]", "---", "",
                  "# " + parca_ad, "", "[[%s - Dizin]]" % ad, "",
                  govde or "*(belgede metin yok)*", ""]
        gecici = os.path.join(hedef, parca_ad + ".md.tmp")
        with open(gecici, "w", encoding="utf-8") as f:
            f.write("\n".join(icerik))
        os.replace(gecici, os.path.join(hedef, parca_ad + ".md"))
        adlar.append(parca_ad)
    dizin = ["---", "kaynak: %s" % os.path.basename(yol), "tags: [dizin]", "---", "",
             "# %s — Dizin" % ad, ""] + ["- [[%s]]" % x for x in adlar]
    with open(os.path.join(hedef, ad + " - Dizin.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(dizin) + "\n")
    return len(adlar)


class _HtmlMetin(HTMLParser):
    """HTML'i okunur Markdown metnine çevirir (betik/stil atılır)."""
    BLOK = {"p", "div", "section", "article", "tr", "table", "ul", "ol", "blockquote", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cikti, self._atla, self._kod = [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "noscript", "svg"):
            self._atla += 1
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.cikti.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.cikti.append("\n- ")
        elif tag == "pre":
            self._kod += 1
            self.cikti.append("\n\n```\n")
        elif tag in self.BLOK:
            self.cikti.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "noscript", "svg"):
            self._atla = max(0, self._atla - 1)
        elif tag == "pre":
            self._kod = max(0, self._kod - 1)
            self.cikti.append("\n```\n\n")
        elif tag in self.BLOK or tag in ("h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self.cikti.append("\n")

    def handle_data(self, veri):
        if self._atla:
            return
        self.cikti.append(veri if self._kod else re.sub(r"\s+", " ", veri))

    def metin(self):
        t = "".join(self.cikti)
        t = re.sub(r"[ \t]+\n", "\n", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def _chatgpt_konusmalar(ham):
    """chat.html içindeki 'var jsonData = [...]' konuşma listesini verir; yoksa None."""
    i = ham.find("var jsonData")
    if i < 0:
        return None
    k = ham.find("[", i)
    if k < 0:
        return None
    try:
        veri, _ = json.JSONDecoder().raw_decode(ham[k:])
    except ValueError:
        return None
    return veri if isinstance(veri, list) else None


def _chatgpt_mesajlar(konusma):
    """Konuşmanın mesajlarını (rol, metin) sırasıyla verir."""
    harita = konusma.get("mapping") or {}
    kimlik, zincir = konusma.get("current_node"), []
    while kimlik and kimlik in harita and len(zincir) < 5000:
        zincir.append(harita[kimlik])
        kimlik = harita[kimlik].get("parent")
    sonuc = []
    for d in reversed(zincir):
        m = d.get("message") or {}
        rol = (m.get("author") or {}).get("role")
        parcalar = (m.get("content") or {}).get("parts") or []
        metin = "\n".join(x for x in parcalar if isinstance(x, str)).strip()
        if rol in ("user", "assistant") and metin:
            sonuc.append(("Ben" if rol == "user" else "Yapay zekâ", metin))
    return sonuc


def _konusma_yaz(klasor, ad, kaynak, zaman, mesajlar):
    os.makedirs(klasor, exist_ok=True)
    govde = ["---", "kaynak: %s" % kaynak, "tarih: %s" % zaman, "tags: [konuşma]", "---", "",
             "# " + ad, ""]
    for rol, metin in mesajlar:
        govde += ["## " + rol, "", metin, ""]
    yol = os.path.join(klasor, dosya_adi_temizle("%s %s" % (zaman, ad))[:120] + ".md")
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write("\n".join(govde))
    os.replace(gecici, yol)


def _html_aktar(yol, kasa):
    """HTML'i notlara çevirir; ChatGPT dışa aktarımıysa konuşma başına bir not yazar."""
    with open(yol, "r", encoding="utf-8", errors="replace") as f:
        ham = f.read()
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    konusmalar = _chatgpt_konusmalar(ham)
    if konusmalar:
        klasor = os.path.join(kasa, "Yapay Zekâ Konuşmaları", "ChatGPT")
        n = 0
        for k in konusmalar:
            if not isinstance(k, dict):
                continue
            mesajlar = _chatgpt_mesajlar(k)
            if not mesajlar:
                continue
            try:
                zaman = datetime.fromtimestamp(
                    float(k.get("create_time") or 0)).strftime("%Y-%m-%d")
            except (ValueError, OSError, OverflowError):
                zaman = "tarihsiz"
            _konusma_yaz(klasor, str(k.get("title") or "Başlıksız"), "ChatGPT", zaman, mesajlar)
            n += 1
        return n
    ayrac = _HtmlMetin()
    ayrac.feed(ham)
    metin = ayrac.metin()
    hedef = os.path.join(kasa, "Yapay Zekâ Konuşmaları", ad)
    os.makedirs(hedef, exist_ok=True)
    parcalar = [metin[i:i + DOCX_PARCA] for i in range(0, len(metin), DOCX_PARCA)] or [""]
    adlar = []
    for n, govde in enumerate(parcalar, 1):
        parca_ad = "%s - Bölüm %d" % (ad, n)
        icerik = ["---", "kaynak: %s" % os.path.basename(yol),
                  "aktarim: %s" % date.today().isoformat(), "tags: [konuşma]", "---", "",
                  "# " + parca_ad, "", govde or "*(metin yok)*", ""]
        gecici = os.path.join(hedef, parca_ad + ".md.tmp")
        with open(gecici, "w", encoding="utf-8") as f:
            f.write("\n".join(icerik))
        os.replace(gecici, os.path.join(hedef, parca_ad + ".md"))
        adlar.append(parca_ad)
    return len(adlar)


YARICAP = 6371008.8      # m


def _ad_alani_temiz(etiket):
    return etiket.rsplit("}", 1)[-1]


def _koordinatlar(metin):
    """'boylam,enlem,yükseklik ...' dizgisini [(enlem, boylam)] yapar."""
    sonuc = []
    for parca in (metin or "").split():
        sayilar = parca.split(",")
        try:
            sonuc.append((float(sayilar[1]), float(sayilar[0])))
        except (ValueError, IndexError):
            continue
    return sonuc


def _duzlem(noktalar):
    """Küçük bir bölge için (enlem, boylam) -> yerel metre (x, y)."""
    en0 = sum(n[0] for n in noktalar) / len(noktalar)
    bo0 = sum(n[1] for n in noktalar) / len(noktalar)
    k = math.cos(math.radians(en0))
    return en0, bo0, [(math.radians(bo - bo0) * YARICAP * k,
                       math.radians(en - en0) * YARICAP) for en, bo in noktalar]


def alan_olc(noktalar):
    """Çokgenin (alan m², çevre m, merkez (enlem, boylam)); en az 3 nokta gerekir."""
    if len(noktalar) > 1 and noktalar[0] == noktalar[-1]:
        noktalar = noktalar[:-1]
    if len(noktalar) < 3:
        return None
    en0, bo0, xy = _duzlem(noktalar)
    a2 = cx = cy = 0.0
    cevre = 0.0
    for i, (x1, y1) in enumerate(xy):
        x2, y2 = xy[(i + 1) % len(xy)]
        c = x1 * y2 - x2 * y1
        a2 += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
        cevre += math.hypot(x2 - x1, y2 - y1)
    if abs(a2) < 1e-9:
        return None
    cx, cy = cx / (3 * a2), cy / (3 * a2)
    k = math.cos(math.radians(en0))
    merkez = (en0 + math.degrees(cy / YARICAP),
              bo0 + math.degrees(cx / (YARICAP * k)))
    return abs(a2) / 2.0, cevre, merkez


def kml_oku(yol):
    """KML/KMZ dosyasından [{ad, aciklama, cokgenler:[[(en,bo)...]], noktalar:[(en,bo)]}]."""
    if yol.lower().endswith(".kmz"):
        import zipfile
        with zipfile.ZipFile(yol) as z:
            ad = next((x for x in z.namelist() if x.lower().endswith(".kml")), None)
            if not ad:
                raise ValueError("KMZ içinde KML yok")
            ham = z.read(ad)
    else:
        with open(yol, "rb") as f:
            ham = f.read()
    kok = ET.fromstring(ham)
    sonuc = []
    for pm in kok.iter():
        if _ad_alani_temiz(pm.tag) != "Placemark":
            continue
        kayit = {"ad": "", "aciklama": "", "cokgenler": [], "noktalar": []}
        for e in pm.iter():
            t = _ad_alani_temiz(e.tag)
            if t == "name" and not kayit["ad"]:
                kayit["ad"] = (e.text or "").strip()
            elif t == "description" and not kayit["aciklama"]:
                kayit["aciklama"] = re.sub(r"<[^>]+>", " ", e.text or "").strip()
            elif t == "Polygon":
                for r in e.iter():
                    if _ad_alani_temiz(r.tag) == "coordinates":
                        kayit["cokgenler"].append(_koordinatlar(r.text))
                        break          # yalnız dış sınır
            elif t == "Point":
                for r in e.iter():
                    if _ad_alani_temiz(r.tag) == "coordinates":
                        kayit["noktalar"] += _koordinatlar(r.text)
        if kayit["cokgenler"] or kayit["noktalar"]:
            sonuc.append(kayit)
    return sonuc


def _kml_aktar(yol, kasa):
    """KML/KMZ'deki arazileri alan/çevre/merkez ile tek bir Obsidian notuna yazar."""
    yerler = kml_oku(yol)
    if not yerler:
        raise ValueError("KML içinde çokgen ya da nokta bulunamadı")
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    hedef = os.path.join(kasa, "Arazi")
    os.makedirs(hedef, exist_ok=True)
    satirlar = ["---", "kaynak: %s" % os.path.basename(yol),
                "aktarim: %s" % date.today().isoformat(), "tags: [arazi]", "---", "",
                "# " + ad, ""]
    for i, y in enumerate(yerler, 1):
        satirlar += ["## %s" % (y["ad"] or "Alan %d" % i), ""]
        if y["aciklama"]:
            satirlar += [y["aciklama"][:500], ""]
        for cokgen in y["cokgenler"]:
            sonuc = alan_olc(cokgen)
            if not sonuc:
                continue
            alan, cevre, (en, bo) = sonuc
            satirlar += ["- Alan: **%s m²** (%s dönüm)" % (
                             format(round(alan), ",").replace(",", "."),
                             ("%.2f" % (alan / 1000)).replace(".", ",")),
                         "- Çevre: %s m" % format(round(cevre), ",").replace(",", "."),
                         "- Merkez: %.6f, %.6f" % (en, bo),
                         "- Harita: https://www.google.com/maps?q=%.6f,%.6f" % (en, bo),
                         "- Köşe sayısı: %d" % (
                             len(cokgen) - (1 if cokgen[0] == cokgen[-1] else 0)), "",
                         "Köşeler (enlem, boylam):", ""]
            satirlar += ["%d. %.6f, %.6f" % (k, a, b)
                         for k, (a, b) in enumerate(cokgen, 1)]
            satirlar.append("")
        for en, bo in y["noktalar"]:
            satirlar += ["- Nokta: %.6f, %.6f  (https://www.google.com/maps?q=%.6f,%.6f)" % (
                en, bo, en, bo), ""]
    gecici = os.path.join(hedef, ad + ".md.tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar))
    os.replace(gecici, os.path.join(hedef, ad + ".md"))
    return len(yerler)


def _metin_aktar(yol, kasa):
    ad = dosya_adi_temizle(os.path.basename(yol))
    shutil.copy2(yol, os.path.join(kasa, ad))


def _eski_aktarim_var(yol, kasa):
    """Eski 'Kılavuz Aktar' aracı bu dosyayı zaten aktardıysa True."""
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    if yol.lower().endswith((".html", ".htm", ".kml", ".kmz")):
        return False
    if yol.lower().endswith((".pdf", ".docx")):
        return os.path.isfile(os.path.join(kasa, ad, ad + " - Dizin.md"))
    return os.path.isfile(os.path.join(kasa, dosya_adi_temizle(
        os.path.basename(yol))))


def aktar(kaynak=None, kasa=None):
    """Bekleyen dosyaları aktarır (eşzamanlı). Sonuç sözlüğü döndürür."""
    kaynak = kaynak or klasor_bul()
    kasa = kasa or obsidyen.kasa_yolu()
    sonuc = {"yeni": 0, "atlanan": 0, "hata": [], "kaynak": kaynak,
             "kasa": kasa}
    if not os.path.isdir(kaynak):
        sonuc["hata"].append("Kılavuz klasörü yok: %s" % kaynak)
        return sonuc
    if not os.path.isdir(kasa):
        sonuc["hata"].append("Obsidian kasası yok: %s" % kasa)
        return sonuc
    bekle = bekleyenler(kaynak)
    with _KILIT:
        _DURUM.update(calisiyor=True, bitti=0, toplam=len(bekle), hata=[])
        kayit = _kayit_oku()
        for yol, mtime, boyut in bekle:
            _DURUM["dosya"] = os.path.basename(yol)
            try:
                if _eski_aktarim_var(yol, kasa) and yol not in kayit:
                    sonuc["atlanan"] += 1          # eski araç yapmış: yeniden yazma
                else:
                    tur = _tur(yol)
                    if tur == "pdf":
                        _pdf_aktar(yol, kasa)
                    elif tur == "docx":
                        _docx_aktar(yol, kasa)
                    elif tur == "html":
                        _html_aktar(yol, kasa)
                    elif tur == "kml":
                        _kml_aktar(yol, kasa)
                    elif tur == "metin":
                        _metin_aktar(yol, kasa)
                    else:
                        raise ValueError("desteklenmeyen içerik (%s); uzantısı '%s' ama "
                                         "gerçek PDF/Word değil" % (
                                             tur, os.path.splitext(yol)[1]))
                    sonuc["yeni"] += 1
                kayit[yol] = {"mtime": mtime, "boyut": boyut}
                _kayit_yaz(kayit)
            except ImportError:
                sonuc["hata"].append("pypdf kurulu değil (pip install pypdf)")
                break
            except Exception as hata:
                sonuc["hata"].append("%s: %s" % (os.path.basename(yol),
                                                 str(hata)[:120]))
                # Aynı bozuk dosya her turda yeniden denenmesin: dosya değişene dek atlanır.
                kayit[yol] = {"mtime": mtime, "boyut": boyut, "hata": str(hata)[:120]}
                _kayit_yaz(kayit)
            _DURUM["bitti"] += 1
        _DURUM.update(calisiyor=False, dosya="", son=time.time(),
                      hata=sonuc["hata"])
    return sonuc


def arka_planda_aktar():
    """Çalışmıyorsa arka planda başlatır; başlatıldıysa True."""
    if _DURUM["calisiyor"] or _KILIT.locked():
        return False
    threading.Thread(target=lambda: _guvenli(), daemon=True).start()
    return True


def _guvenli():
    try:
        aktar()
    except Exception as hata:
        _DURUM.update(calisiyor=False, hata=[str(hata)[:120]])


def otomatik_dongu(durdur, aralik=600):
    """Ayar açıksa yeni kılavuzları aralıklarla kendiliğinden aktarır."""
    while not durdur.wait(aralik):
        try:
            if ayar.yukle().get("kilavuz_otomatik", True) and bekleyenler():
                arka_planda_aktar()
        except Exception:
            pass


def durum():
    kaynak = klasor_bul()
    var = os.path.isdir(kaynak)
    bekle = bekleyenler(kaynak) if var else []
    return {"kaynak": kaynak, "klasor_var": var, "kasa": obsidyen.kasa_yolu(),
            "bekleyen": len(bekle), "calisiyor": _DURUM["calisiyor"],
            "dosya": _DURUM["dosya"], "bitti": _DURUM["bitti"],
            "toplam": _DURUM["toplam"], "hata": _DURUM["hata"],
            "otomatik": bool(ayar.yukle().get("kilavuz_otomatik", True))}
