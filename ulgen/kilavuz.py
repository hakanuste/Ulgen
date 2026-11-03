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
from datetime import date, datetime
from html.parser import HTMLParser

from . import ayar, obsidyen

PARCA_BOYU = 50
UZANTILAR = (".pdf", ".docx", ".html", ".htm", ".md", ".txt")
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


def _metin_aktar(yol, kasa):
    ad = dosya_adi_temizle(os.path.basename(yol))
    shutil.copy2(yol, os.path.join(kasa, ad))


def _eski_aktarim_var(yol, kasa):
    """Eski 'Kılavuz Aktar' aracı bu dosyayı zaten aktardıysa True."""
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    if yol.lower().endswith((".html", ".htm")):
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
