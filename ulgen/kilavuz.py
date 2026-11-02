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
from datetime import date

from . import ayar, obsidyen

PARCA_BOYU = 50
UZANTILAR = (".pdf", ".md", ".txt")
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


def _metin_aktar(yol, kasa):
    ad = dosya_adi_temizle(os.path.basename(yol))
    shutil.copy2(yol, os.path.join(kasa, ad))


def _eski_aktarim_var(yol, kasa):
    """Eski 'Kılavuz Aktar' aracı bu dosyayı zaten aktardıysa True."""
    ad = dosya_adi_temizle(os.path.splitext(os.path.basename(yol))[0])
    if yol.lower().endswith(".pdf"):
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
                elif yol.lower().endswith(".pdf"):
                    _pdf_aktar(yol, kasa)
                    sonuc["yeni"] += 1
                else:
                    _metin_aktar(yol, kasa)
                    sonuc["yeni"] += 1
                kayit[yol] = {"mtime": mtime, "boyut": boyut}
                _kayit_yaz(kayit)
            except ImportError:
                sonuc["hata"].append("pypdf kurulu değil (pip install pypdf)")
                break
            except Exception as hata:
                sonuc["hata"].append("%s: %s" % (os.path.basename(yol),
                                                 str(hata)[:120]))
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
