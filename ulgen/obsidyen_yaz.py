"""Obsidian kasasına güvenli not yazma (araştırma ve OCR çıktıları için).

Kural (kullanıcı onaylı): Ülgen yalnızca kasadaki ``Ülgen/`` alt klasörüne
yazar. Kullanıcının kendi notlarının üzerine ASLA yazılmaz, hiçbir dosya
silinmez. Ülgen'in kendi yazdığı bir not (ilk satırlarında ``ulgen: true``
işareti olan) yeniden çalışmada güncellenebilir; işaretsiz bir dosya varsa
yeni not " (2)" gibi bir son ekle yanına yazılır. Yol kaçışı ve ayar dışı
klasör engellenir. Kasa yoksa hata verilir (çağıran yerel kopyayı korur).
"""

import os
import re
import unicodedata
from datetime import datetime

from . import ayar, obsidyen

ISARET = "ulgen: true"
AZAMI_BAYT = 5_000_000
AD_SINIRI = 110
_YASAK = re.compile(r'[\\/:*?"<>|\x00-\x1f#^\[\]]')


class YazmaHatasi(Exception):
    pass


def guvenli_ad(ad, varsayilan="not"):
    """Dosya/klasör adı: yol ayracı, denetim ve Obsidian'a özgü karakter yok."""
    ad = unicodedata.normalize("NFC", str(ad))
    ad = _YASAK.sub(" ", ad)
    ad = re.sub(r"\s+", " ", ad).strip(" .")
    return (ad[:AD_SINIRI].strip(" .")) or varsayilan


def acik_mi():
    return bool(ayar.yukle().get("obsidyen_yazma", True))


def yazma_koku(kasa=None):
    """<kasa>/<yazma klasörü>; klasör adı tek parça, ayrıştırılmış olmalı."""
    a = ayar.yukle()
    kasa = os.path.realpath(kasa or obsidyen.kasa_yolu())
    if not os.path.isdir(kasa):
        raise YazmaHatasi("Obsidian kasası bulunamadı: %s (ayar.json'da \"kasa\" "
                          "alanına gerçek yolu yazın)" % kasa)
    ad = guvenli_ad(a.get("obsidyen_yazma_klasoru") or "Ülgen", "Ülgen")
    return kasa, os.path.join(kasa, ad)


def _ulgenin_mi(yol):
    try:
        with open(yol, "r", encoding="utf-8", errors="ignore") as f:
            return ISARET in f.read(600)
    except OSError:
        return False


def onbilgi(**alanlar):
    """Obsidian front matter bloğu (ulgen işaretiyle)."""
    satirlar = ["---", ISARET,
                "tarih: %s" % datetime.now().strftime("%Y-%m-%d %H:%M")]
    for k, v in alanlar.items():
        v = " ".join(str(v).split()).replace('"', "'")
        satirlar.append('%s: "%s"' % (guvenli_ad(k, "alan").replace(" ", "_"), v))
    satirlar.append("---")
    return "\n".join(satirlar) + "\n\n"


def yaz(altklasor, ad, icerik, kasa=None):
    """<kasa>/Ülgen/<altklasor>/<ad>.md yazar; kasaya göreli yolu döndürür.

    ``icerik`` front matter ``onbilgi()`` ile başlamalıdır; başlamıyorsa
    eklenir (işaret olmadan Ülgen kendi notunu tanıyamaz)."""
    if not acik_mi():
        raise YazmaHatasi("Obsidian'a yazma ayarlardan kapalı (obsidyen_yazma)")
    metin = str(icerik)
    if len(metin.encode("utf-8")) > AZAMI_BAYT:
        raise YazmaHatasi("Not çok büyük (>%d MB); bölümlere ayırın"
                          % (AZAMI_BAYT // 1_000_000))
    if ISARET not in metin[:600]:
        metin = onbilgi() + metin
    kasa, kok = yazma_koku(kasa)
    parcalar = [guvenli_ad(p, "klasor") for p in
                re.split(r"[\\/]+", str(altklasor or "")) if p.strip(" .")]
    klasor = os.path.join(kok, *parcalar)
    ad = guvenli_ad(ad)
    if ad.lower().endswith(".md"):
        ad = ad[:-3].rstrip(" .") or "not"
    # Gerçek yol ``Ülgen`` kökünün dışına çıkamaz (symlink/.. dahil).
    ust = os.path.realpath(kok)
    os.makedirs(klasor, exist_ok=True)
    if os.path.commonpath([os.path.realpath(klasor), ust]) != ust:
        raise YazmaHatasi("Yazma klasörü dışına çıkılamaz")
    for sira in range(1, 200):
        yol = os.path.join(klasor, ad + (".md" if sira == 1
                                         else " (%d).md" % sira))
        if not os.path.exists(yol) or _ulgenin_mi(yol):
            gecici = yol + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(metin)
            os.replace(gecici, yol)
            return os.path.relpath(yol, kasa)
    raise YazmaHatasi("Aynı adlı çok fazla not var")
