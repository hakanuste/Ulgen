"""Sohbete dosya ve resim ekleme.

Dosya ~/ÜlgenVeri/ekler altına kaydedilir, içindeki yazı çıkarılır ve iletiyle
birlikte Ülgen'e verilir:
- metin, Markdown, CSV, JSON: doğrudan okunur;
- HTML: etiketler atılarak okunur metne çevrilir (harf harf değil);
- Word (.docx): paragraflar okunur;
- PDF: yazı katmanı okunur (taranmışsa Kitaplık'taki OCR önerilir);
- resim: içindeki yazı tesseract ile okunur (Mac'te kuruluysa). Resmin
  kendisini görerek tanıma yoktur.
Hiçbir şey dışarı gönderilmez; içerik duyarlıysa yanıt yerel beyinde kalır.
"""

import json
import os
import re
import time
import zipfile

from . import ayar, obsidyen_yaz

METIN = (".txt", ".md", ".csv", ".json", ".log")
HTML = (".html", ".htm")
RESIM = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
DESTEK = METIN + HTML + RESIM + (".pdf", ".docx")
AZAMI = 25 * 1024 * 1024
ILETI_SINIRI = 12000          # iletiye eklenecek en çok karakter (tüm ekler)


class EkHatasi(Exception):
    pass


def klasor():
    yol = os.path.join(ayar.KLASOR, "ekler")
    os.makedirs(yol, exist_ok=True)
    return yol


def kaydet(ad, kaynak, uzunluk):
    """Gövdeyi parça parça yazar; kimliği (dosya adı) döndürür."""
    govde, uzanti = os.path.splitext(os.path.basename(ad or ""))
    uzanti = uzanti.lower()
    if uzanti not in DESTEK:
        raise EkHatasi("Bu dosya türü eklenemez. Desteklenenler: "
                       + ", ".join(DESTEK))
    if uzunluk <= 0 or uzunluk > AZAMI:
        raise EkHatasi("Dosya boş ya da 25 MB'tan büyük")
    kimlik = "%s_%s%s" % (time.strftime("%Y%m%d-%H%M%S"),
                          obsidyen_yaz.guvenli_ad(govde, "dosya")[:60], uzanti)
    yol = os.path.join(klasor(), kimlik)
    kalan = uzunluk
    try:
        with open(yol, "wb") as f:
            while kalan > 0:
                parca = kaynak.read(min(1_048_576, kalan))
                if not parca:
                    raise EkHatasi("Yükleme yarıda kesildi")
                f.write(parca)
                kalan -= len(parca)
    except BaseException:
        try:
            os.remove(yol)
        except OSError:
            pass
        raise
    return kimlik


def yol_bul(kimlik):
    ad = os.path.basename(str(kimlik or ""))
    yol = os.path.join(klasor(), ad)
    if not ad or not os.path.isfile(yol):
        raise EkHatasi("Ek bulunamadı: %s" % ad)
    return yol


def _docx(yol):
    with zipfile.ZipFile(yol) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    metin = re.sub(r"<[^>]+>", "", xml)
    for kod, kar in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                     ("&apos;", "'"), ("&amp;", "&")):
        metin = metin.replace(kod, kar)
    return metin


def _html(yol):
    from .kilavuz import _HtmlMetin
    with open(yol, "r", encoding="utf-8", errors="replace") as f:
        ayrac = _HtmlMetin()
        ayrac.feed(f.read())
    return ayrac.metin()


def _pdf(yol, sayfa=60):
    from pypdf import PdfReader
    okuyucu = PdfReader(yol)
    return "\n".join((s.extract_text() or "") for s in okuyucu.pages[:sayfa])


def _resim(yol):
    from . import ocr
    return ocr._tesseract(yol, ocr._dil())


def metin_cikar(yol):
    """(metin, not) — not, kullanıcıya gösterilecek kısa açıklama."""
    uz = os.path.splitext(yol)[1].lower()
    try:
        if uz in METIN:
            with open(yol, "r", encoding="utf-8", errors="replace") as f:
                metin = f.read()
            if uz == ".json":
                try:
                    metin = json.dumps(json.loads(metin), ensure_ascii=False, indent=1)
                except ValueError:
                    pass
            return metin, ""
        if uz in HTML:
            return _html(yol), "HTML sayfası okunur metne çevrildi."
        if uz == ".docx":
            return _docx(yol), ""
        if uz == ".pdf":
            metin = _pdf(yol)
            if len(metin.strip()) < 50:
                return "", ("PDF'te yazı katmanı yok (taranmış). Kitaplık'tan "
                            "OCR ile okutabilirsiniz.")
            return metin, ""
        if uz in RESIM:
            try:
                metin = _resim(yol)
            except Exception as hata:
                return "", ("Resim kaydedildi ama içindeki yazı okunamadı: %s"
                            % str(hata)[:160])
            if len(metin.strip()) < 3:
                return "", ("Resimde okunacak yazı bulunamadı. Ülgen resmin "
                            "kendisini göremez; yalnızca içindeki yazıyı okur.")
            return metin, "Resimdeki yazı okundu (resmin kendisi görülmez)."
    except Exception as hata:
        return "", "Dosya okunamadı: %s" % str(hata)[:160]
    return "", "Bu dosya türünden yazı çıkarılamadı."


def ozet(kimlik):
    """Yükleme sonrası arayüze dönen bilgi."""
    yol = yol_bul(kimlik)
    metin, aciklama = metin_cikar(yol)
    return {"kimlik": kimlik, "ad": kimlik.split("_", 1)[-1],
            "karakter": len(metin.strip()), "not": aciklama}


def iletiye_ekle(metin, kimlikler):
    """Kullanıcının iletisine eklerin yazısını ekler (toplam sınırlı)."""
    kimlikler = [k for k in (kimlikler or []) if k][:5]
    if not kimlikler:
        return metin
    pay = ILETI_SINIRI // len(kimlikler)
    parcalar = [metin.strip() or "Ekteki dosyayı inceleyin."]
    for k in kimlikler:
        try:
            yol = yol_bul(k)
        except EkHatasi as hata:
            parcalar.append("[EK: %s]\n(%s)" % (k, hata))
            continue
        icerik, aciklama = metin_cikar(yol)
        icerik = icerik.strip()
        kesildi = len(icerik) > pay
        parcalar.append("[EKLİ DOSYA: %s]%s\n%s%s" % (
            k.split("_", 1)[-1], (" (" + aciklama + ")") if aciklama else "",
            icerik[:pay] or "(yazı yok)",
            "\n[… dosyanın kalanı sığmadı; %d karakterin %d'i verildi]"
            % (len(icerik), pay) if kesildi else ""))
    return "\n\n".join(parcalar)
