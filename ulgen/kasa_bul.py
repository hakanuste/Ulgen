"""'Obsidian'da bul' komutu: notları Mac'te arar, sonucu doğrudan gösterir.

Model kullanılmaz ve hiçbir içerik buluta gitmez. Örnekler:
  obsidyende taş ev ölçüleri bul      obsidyende ara: taş ev
  kasada musso şanzıman ara           obsidyende bu sohbeti bul
'bu sohbet / bunu / şunu' denirse bir önceki sorunun konusu aranır.
"""

import os
import re

from . import obsidyen

DESEN = re.compile(
    r"^\s*(?:obsid[iy]\w*|kasa\w*)\s*(?:'?d[ae]n?)?\s*(?:(?:ara|bul|getir)\s*:\s*(?P<a>.+)"
    r"|(?P<b>.*?)\s*(?:bul|ara|getir)\w*\s*[.!?]*)\s*$", re.IGNORECASE)
GOSTERGE = re.compile(r"^(bu|şu|o)?\s*(sohbet\w*|konu\w*|not\w*|dosya\w*|bunu|şunu|onu)?$",
                      re.IGNORECASE)


def esles(metin):
    """Komutsa aranacak metni (boş olabilir) döndürür; değilse None."""
    e = DESEN.match(metin or "")
    if not e:
        return None
    return (e.group("a") or e.group("b") or "").strip()


def _tarih(yol):
    from .uzmanlar import tarih_bul
    return tarih_bul(yol)


def bul(sorgu, onceki_soru="", adet=5):
    if not sorgu or GOSTERGE.match(sorgu):
        sorgu = onceki_soru or ""
    if not sorgu.strip():
        return "Neyi arayayım? Örnek: 'obsidyende ara: taş ev ölçüleri'"
    if not obsidyen.hazir_mi():
        return "Obsidian kasası bağlı değil ya da henüz taranmadı (Ayarlar > Obsidian)."
    bulgular = obsidyen.ara(sorgu, adet, 700)
    if not bulgular:
        return "Obsidian'da '%s' için bir not bulamadım." % sorgu[:80]
    kasa = obsidyen.kasa_yolu() or ""
    satirlar = ["# Obsidian'da bulunanlar: %s" % sorgu[:80], ""]
    for i, (baslik, yol, alinti) in enumerate(bulgular, 1):
        goreli = (os.path.relpath(yol, kasa) if kasa and yol.startswith(kasa)
                  else os.path.basename(yol))
        satirlar.append("## %d. %s (%s)" % (i, baslik, _tarih(yol)))
        satirlar.append("Yer: %s" % goreli)
        satirlar.append((alinti or "").strip()[:700])
        satirlar.append("")
    satirlar.append("> Bu sonuçlar yalnızca Mac'te arandı; hiçbir şey buluta gönderilmedi.")
    return "\n".join(satirlar)
