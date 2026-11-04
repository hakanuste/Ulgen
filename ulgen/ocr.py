"""Yerel OCR: taranmış kitap sayfaları (PDF/resim) → metin → Obsidian notu.

Her şey Mac'te yerelde yapılır (tesseract); sayfalar ve metin buluta GİTMEZ.
Sayfa sayfa çalışır ve her sayfayı ``~/ÜlgenVeri/ocr/<kimlik>/`` altına
kaydeder; iş yarıda kalırsa (kapanma, iptal) aynı dosya yeniden verildiğinde
kaldığı sayfadan sürer. Kaynak PDF'ye dokunulmaz.

Gerekenler (Mac): ``brew install tesseract tesseract-lang poppler``
(poppler yoksa PDF'in içindeki gömülü sayfa resimleri kullanılır; bu çoğu
tarama PDF'inde yeter ama her biçimde çalışmaz).

Dürüst sınırlar: OCR doğruluğu tarama kalitesine bağlıdır; eski harfli
(Osmanlıca) metinler tanınmaz; çok sütunlu sayfalar karışabilir.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading

from . import ajan_kayit, ayar, iptal, obsidyen_yaz

DESTEK = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
AZAMI_DOSYA = 600_000_000
PARCA_SAYFA = 40            # bir Obsidian notunda en çok sayfa
PARCA_KARAKTER = 300_000    # Obsidian dizini 1 MB'tan büyük .md'yi atlar
YETERLI_METIN = 60          # bir PDF sayfasında gömülü metin sayılması için
SAYFA_ZAMAN_ASIMI = 300
KURULUM = "brew install tesseract tesseract-lang poppler"
_KILIT = threading.Lock()


class OcrHatasi(Exception):
    pass


def calisma_klasoru():
    return os.path.join(ayar.KLASOR, "ocr")


def gelen_klasoru():
    yol = os.path.join(ayar.KLASOR, "gelen")
    os.makedirs(yol, exist_ok=True)
    return yol


def _bul(ad):
    yol = shutil.which(ad)
    if yol:
        return yol
    for ust in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):
        aday = os.path.join(ust, ad)
        if os.path.exists(aday) and os.access(aday, os.X_OK):
            return aday
    return None


def diller():
    t = _bul("tesseract")
    if not t:
        return []
    try:
        c = subprocess.run([t, "--list-langs"], capture_output=True,
                           text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    return [x.strip() for x in (c.stdout + c.stderr).splitlines()[1:]
            if x.strip() and " " not in x.strip()]


def durum():
    """Ayarlar/Tanı için: araçlar var mı, hangi diller kurulu."""
    t, p = _bul("tesseract"), _bul("pdftoppm")
    d = diller()
    eksik = []
    if not t:
        eksik.append("tesseract")
    elif "tur" not in d:
        eksik.append("tesseract-lang (Türkçe)")
    if not p:
        eksik.append("poppler (isteğe bağlı)")
    return {"tesseract": bool(t), "poppler": bool(p), "diller": d,
            "eksik": eksik, "kurulum": KURULUM,
            "tamam": bool(t) and "tur" in d}


def _dil():
    istenen = [x for x in str(ayar.yukle().get("ocr_dil", "tur+eng")).split("+")
               if x.strip()]
    kurulu = diller()
    secilen = [x for x in istenen if x in kurulu]
    if not secilen:
        secilen = [x for x in ("eng",) if x in kurulu]
    if not secilen:
        raise OcrHatasi("tesseract kurulu değil ya da dil verisi yok. Mac'te "
                        "Terminal'e şunu yazın: %s" % KURULUM)
    return "+".join(secilen)


def _sayfa_sayisi(yol):
    if yol.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return len(PdfReader(yol).pages)
    return 1


def temizle(metin):
    """Satır sonu tirelerini birleştirir, boşlukları toparlar."""
    metin = metin.replace("\r", "")
    metin = re.sub(r"(\w)-\n([a-zçğıöşü])", r"\1\2", metin)
    metin = re.sub(r"[ \t]+\n", "\n", metin)
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    return metin.strip()


def _gomulu_metin(okuyucu, no):
    try:
        return (okuyucu.pages[no - 1].extract_text() or "").strip()
    except Exception:
        return ""


def _sayfa_resmi(yol, no, dpi, gecici):
    """Sayfa resmini ``gecici`` klasöre yazar, dosya yolunu döndürür."""
    if not yol.lower().endswith(".pdf"):
        return yol
    pdftoppm = _bul("pdftoppm")
    if pdftoppm:
        onek = os.path.join(gecici, "s")
        c = subprocess.run(
            [pdftoppm, "-r", str(int(dpi)), "-f", str(no), "-l", str(no),
             "-gray", "-png", yol, onek],
            capture_output=True, timeout=SAYFA_ZAMAN_ASIMI)
        dosyalar = sorted(x for x in os.listdir(gecici) if x.startswith("s-"))
        if c.returncode == 0 and dosyalar:
            return os.path.join(gecici, dosyalar[0])
    try:
        from pypdf import PdfReader
        resimler = list(PdfReader(yol).pages[no - 1].images)
    except Exception:
        resimler = []
    if resimler:
        r = max(resimler, key=lambda x: len(x.data))
        uzanti = os.path.splitext(r.name)[1].lower() or ".png"
        hedef = os.path.join(gecici, "gomulu" + uzanti)
        with open(hedef, "wb") as f:
            f.write(r.data)
        return hedef
    raise OcrHatasi("Sayfa %d resme çevrilemedi. poppler kurun: %s"
                    % (no, KURULUM))


def _tesseract(resim, dil):
    t = _bul("tesseract")
    if not t:
        raise OcrHatasi("tesseract kurulu değil. %s" % KURULUM)
    try:
        c = subprocess.run([t, resim, "stdout", "-l", dil, "--psm", "3"],
                           capture_output=True, timeout=SAYFA_ZAMAN_ASIMI)
    except subprocess.TimeoutExpired:
        raise OcrHatasi("Bir sayfa %d sn içinde okunamadı" % SAYFA_ZAMAN_ASIMI)
    if c.returncode != 0:
        raise OcrHatasi("tesseract hata verdi: %s"
                        % c.stderr.decode("utf-8", "ignore")[-160:])
    return c.stdout.decode("utf-8", "ignore")


def _kimlik(yol):
    st = os.stat(yol)
    h = hashlib.sha1(("%s|%d|%d" % (os.path.basename(yol), st.st_size,
                                    int(st.st_mtime))).encode("utf-8"))
    return h.hexdigest()[:12]


def _not_adi(yol):
    ad = os.path.splitext(os.path.basename(yol))[0]
    return obsidyen_yaz.guvenli_ad(ad, "kitap")


def _parcala(sayfalar):
    """[(no, metin)] → her biri ≤ PARCA_SAYFA sayfa ve ≤ PARCA_KARAKTER."""
    parcalar, simdiki, boyut = [], [], 0
    for no, metin in sayfalar:
        if simdiki and (len(simdiki) >= PARCA_SAYFA
                        or boyut + len(metin) > PARCA_KARAKTER):
            parcalar.append(simdiki)
            simdiki, boyut = [], 0
        simdiki.append((no, metin))
        boyut += len(metin)
    if simdiki:
        parcalar.append(simdiki)
    return parcalar


def _yerel_kopya(altklasor, ad, icerik):
    kok = os.path.join(ayar.KLASOR, "notlar", obsidyen_yaz.guvenli_ad(altklasor))
    os.makedirs(kok, exist_ok=True)
    yol = os.path.join(kok, obsidyen_yaz.guvenli_ad(ad) + ".md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    return yol


def notlari_yaz(ad, kaynak_ad, sayfalar, dil, ocr_sayfa, bos):
    """Sayfa metinlerini Obsidian'a (olmazsa yerel klasöre) yazar.
    (yazılan yollar, uyarı) döndürür."""
    uyari = ""
    parcalar = _parcala(sayfalar)
    notlar = []

    def yaz(alt, nad, icerik):
        nonlocal uyari
        try:
            return obsidyen_yaz.yaz(alt, nad, icerik)
        except obsidyen_yaz.YazmaHatasi as hata:
            uyari = ("Obsidian'a yazılamadı (%s); yerel klasöre kaydedildi: "
                     "~/ÜlgenVeri/notlar/" % hata)
            return _yerel_kopya(alt, nad, icerik)
    ortak = dict(kaynak=kaynak_ad, sayfa=len(sayfalar), ocr_sayfa=ocr_sayfa,
                 ocr_dil=dil, bos_sayfa=bos)
    if len(parcalar) <= 1:
        govde = "\n\n".join("## Sayfa %d\n\n%s" % (n, m) for n, m in sayfalar)
        notlar.append(yaz("Kitaplar", ad, obsidyen_yaz.onbilgi(
            tur="kitap", **ortak) + "# %s\n\n%s\n" % (ad, govde)))
        return notlar, uyari
    baglar = []
    for i, p in enumerate(parcalar, 1):
        nad = "%s - Bölüm %02d" % (ad, i)
        govde = "\n\n".join("## Sayfa %d\n\n%s" % (n, m) for n, m in p)
        notlar.append(yaz("Kitaplar/" + ad, nad, obsidyen_yaz.onbilgi(
            tur="kitap-bolum", kaynak=kaynak_ad, sayfa_araligi="%d-%d" % (
                p[0][0], p[-1][0])) + "# %s (Bölüm %d)\n\n%s\n" % (ad, i, govde)))
        baglar.append("- [[%s]] (sayfa %d–%d)" % (
            os.path.basename(notlar[-1])[:-3], p[0][0], p[-1][0]))
    notlar.insert(0, yaz("Kitaplar", ad, obsidyen_yaz.onbilgi(
        tur="kitap", **ortak) + "# %s\n\n%s\n" % (ad, "\n".join(baglar))))
    return notlar, uyari


def isle(yol, ilerleme=None, tesseract=None):
    """Tek dosyayı okur ve Obsidian'a yazar. Özet metni döndürür.

    ``tesseract``: sınama için ``(resim, dil) -> metin`` yerine geçer."""
    yol = os.path.realpath(yol)
    if not os.path.isfile(yol) or not yol.lower().endswith(DESTEK):
        raise OcrHatasi("Desteklenen dosya değil (PDF, PNG, JPG, TIFF): %s"
                        % os.path.basename(yol))
    if os.path.getsize(yol) > AZAMI_DOSYA:
        raise OcrHatasi("Dosya 600 MB'tan büyük")
    oku = tesseract or _tesseract
    dil = "tur+eng" if tesseract else _dil()
    dpi = int(ayar.yukle().get("ocr_dpi", 250) or 250)
    ad = _not_adi(yol)
    toplam = _sayfa_sayisi(yol)
    pdf = yol.lower().endswith(".pdf")
    klasor = os.path.join(calisma_klasoru(), _kimlik(yol))
    os.makedirs(klasor, exist_ok=True)
    okuyucu = None
    if pdf:
        from pypdf import PdfReader
        okuyucu = PdfReader(yol)
    ocr_sayfa = bos = 0
    sayfalar = []
    for no in range(1, toplam + 1):
        iptal.denetle()
        dosya = os.path.join(klasor, "s%05d.txt" % no)
        if os.path.exists(dosya):                  # kaldığı yerden sürer
            with open(dosya, "r", encoding="utf-8") as f:
                metin = f.read()
        else:
            metin = _gomulu_metin(okuyucu, no) if okuyucu else ""
            if len(metin) < YETERLI_METIN:
                with tempfile.TemporaryDirectory() as gecici:
                    resim = _sayfa_resmi(yol, no, dpi, gecici)
                    metin = oku(resim, dil)
                ocr_sayfa += 1
            metin = temizle(metin)
            with open(dosya, "w", encoding="utf-8") as f:
                f.write(metin)
        if not metin.strip():
            bos += 1
        sayfalar.append((no, metin or "_(boş sayfa)_"))
        if ilerleme:
            ilerleme("%s: sayfa %d/%d okundu" % (ad, no, toplam))
    notlar, uyari = notlari_yaz(ad, os.path.basename(yol), sayfalar, dil,
                                ocr_sayfa, bos)
    with open(os.path.join(klasor, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"bitti": True, "notlar": notlar, "sayfa": toplam}, f)
    return ("%s: %d sayfa okundu (%d'i OCR, %d boş). Not: %s%s"
            % (ad, toplam, ocr_sayfa, bos, notlar[0],
               (" · " + uyari) if uyari else ""))


def _islendi_mi(yol):
    try:
        with open(os.path.join(calisma_klasoru(), _kimlik(yol), "meta.json"),
                  "r", encoding="utf-8") as f:
            return bool(json.load(f).get("bitti"))
    except (OSError, ValueError):
        return False


def izinli_yol(girdi):
    """Ad ya da yol → gerçek dosya. Yalnız gelen klasörü veya ev klasörü
    (gizli klasörler ve ÜlgenVeri hariç)."""
    girdi = str(girdi).strip()
    gelen = gelen_klasoru()
    aday = girdi if os.path.isabs(os.path.expanduser(girdi)) else \
        os.path.join(gelen, girdi)
    aday = os.path.realpath(os.path.expanduser(aday))
    ev = os.path.realpath(ayar.EV)
    veri = os.path.realpath(ayar.KLASOR)
    if os.path.commonpath([aday, ev]) != ev:
        raise OcrHatasi("Yalnız ev klasörünüzdeki dosyalar okunur")
    if os.path.commonpath([aday, veri]) == veri and \
            os.path.commonpath([aday, os.path.realpath(gelen)]) != \
            os.path.realpath(gelen):
        raise OcrHatasi("ÜlgenVeri içinden yalnız 'gelen' klasörü okunur")
    if any(p.startswith(".") for p in os.path.relpath(aday, ev).split(os.sep)):
        raise OcrHatasi("Gizli klasörlerdeki dosyalar okunmaz")
    return aday


class KitapAjani:
    """Taranmış kitap sayfalarını yerelde okuyup Obsidian'a yazar."""

    def isle(self, girdi=""):
        """Girdi: dosya adı ya da yolu; boşsa 'gelen' klasöründeki yeni
        dosyalar. Özet metni döndürür."""
        def ilerleme(m):
            ajan_kayit.ilerleme("kitap", m)
        girdi = str(girdi or "").strip()
        if girdi:
            return isle(izinli_yol(girdi), ilerleme)
        bekleyen = [os.path.join(gelen_klasoru(), x)
                    for x in sorted(os.listdir(gelen_klasoru()))
                    if x.lower().endswith(DESTEK)
                    and not _islendi_mi(os.path.join(gelen_klasoru(), x))]
        if not bekleyen:
            return ("'gelen' klasöründe işlenecek yeni dosya yok. Arayüzden "
                    "PDF yükleyin ya da ~/ÜlgenVeri/gelen içine koyun.")
        sonuclar = []
        for y in bekleyen:
            try:
                sonuclar.append(isle(y, ilerleme))
            except OcrHatasi as hata:
                sonuclar.append("%s: %s" % (os.path.basename(y), hata))
        return "\n".join(sonuclar)


def yukle(ad, kaynak, uzunluk):
    """Yüklenen dosyayı (``kaynak.read``) 'gelen' klasörüne parça parça yazar;
    yolunu döndürür. Yarım kalırsa dosya silinir."""
    govde, uzanti = os.path.splitext(ad)
    ad = obsidyen_yaz.guvenli_ad(govde, "dosya") + uzanti.lower()
    if not ad.lower().endswith(DESTEK):
        raise OcrHatasi("Yalnız PDF, PNG, JPG, TIFF yüklenir")
    if uzunluk <= 0 or uzunluk > AZAMI_DOSYA:
        raise OcrHatasi("Dosya boş ya da 600 MB'tan büyük")
    klasor = gelen_klasoru()
    yol = os.path.join(klasor, ad)
    sira = 1
    while os.path.exists(yol):
        sira += 1
        yol = os.path.join(klasor, "%s (%d)%s" % (
            os.path.splitext(ad)[0], sira, os.path.splitext(ad)[1]))
    kalan = uzunluk
    try:
        with open(yol, "wb") as f:
            while kalan > 0:
                parca = kaynak.read(min(1_048_576, kalan))
                if not parca:
                    raise OcrHatasi("Yükleme yarıda kesildi")
                f.write(parca)
                kalan -= len(parca)
    except BaseException:
        try:
            os.remove(yol)
        except OSError:
            pass
        raise
    return yol
