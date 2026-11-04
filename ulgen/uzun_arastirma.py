"""Uzun araştırma görevi: uzunluğu ne olursa olsun madde madde yürütür.

Görev metni (sınır 60 000 karakter) maddelere ayrılır; her madde için ayrı
aramalar yapılır, sayfalar okunur, bulgular kaynak bağlantılarıyla Obsidian'da
``Ülgen/Araştırmalar/<görev>/`` altında bir not olur; en sonda bir dizin notu
yazılır. Her madde bitince denetim noktası kaydedilir: iş yarıda kalırsa
(kapanma, iptal, ağ kopması) aynı görev yeniden verildiğinde kalan maddelerden
sürer. Obsidian yoksa notlar ``~/ÜlgenVeri/notlar/`` altına yazılır.

Dürüst sınırlar:
  * Yalnız web araması ve açık sayfalar kullanılır; telifli kitapların TAM metni
    indirilmez. PDF bağlantıları notta listelenir; kitabı kendiniz indirip
    Kitap Okuyucu'ya verebilirsiniz.
  * Özetleme yerel beyinle yapılır (yoksa çıkarımsal özet); sayısal bulgular
    kaynaktan doğrulanmalıdır.
  * Arama motoru sık sorguda kısıtlayabilir; bu yüzden istekler arasında
    beklenir ve başarısız olanlar notta belirtilir.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime

from . import ajan_kayit, ayar, iptal, obsidyen_yaz

AZAMI_GOREV = 60000
AZAMI_MADDE = 120
SORGU_ARASI_SN = 2.0
SAYFA_SAYISI = 4
SAYFA_UZUNLUK = 2500
DEFTER = "arastirmalar"
_GIRIS = re.compile(r"^\s*(?:\d+[.)]|[-•*])\s+")
_OGE = re.compile(r"([^,;()\n]{2,80}?)\s*\(([^)]{2,200})\)")
_ONEK = re.compile(r"^\s*(?:\d+[.)]\s*)?[^:\n]{0,60}:\s*")


def _kimlik(gorev):
    return hashlib.sha1(gorev.strip().encode("utf-8")).hexdigest()[:12]


def _defter_yolu(kimlik):
    k = os.path.join(ayar.KLASOR, DEFTER)
    os.makedirs(k, exist_ok=True)
    return os.path.join(k, kimlik + ".json")


def maddelere_ayir(gorev):
    """Görev → [{"ad", "sorgular"}]. Kural tabanlı ve öngörülebilir:

    1. "Ad (eser, eser)" kalıbı en az 3 kez geçiyorsa her ad bir maddedir
       (örn. ozan listesi); sorgular adın kendisi ve eserleridir.
    2. Değilse numaralı/madde işaretli satırlar birer maddedir.
    3. O da yoksa görevin kendisi tek maddedir.
    """
    gorev = str(gorev).strip()[:AZAMI_GOREV]
    ogeler = []
    for satir in gorev.splitlines():
        govde = _ONEK.sub("", satir, count=1) if ":" in satir[:70] else satir
        for m in _OGE.finditer(govde):
            ad = m.group(1).strip(" -•*0123456789.)")
            eserler = [e.strip() for e in m.group(2).split(",") if e.strip()]
            var = {x["ad"].lower() for x in ogeler}
            if 1 < len(ad) <= 60 and ad.lower() not in var:
                ogeler.append({"ad": ad, "sorgular": (
                    ["%s eserleri dili" % ad]
                    + ["%s %s" % (ad, e) for e in eserler[:4]])})
    if len(ogeler) >= 3:
        return ogeler[:AZAMI_MADDE]
    satirlar = [_GIRIS.sub("", x).strip() for x in gorev.splitlines()
                if _GIRIS.match(x) and len(x.strip()) > 15]
    if len(satirlar) >= 2:
        return [{"ad": s[:70], "sorgular": [s[:300]]}
                for s in satirlar[:AZAMI_MADDE]]
    return [{"ad": gorev[:70] or "görev", "sorgular": [gorev[:300]]}]


def _baslik(gorev):
    ilk = re.sub(r"\s+", " ", gorev.strip().splitlines()[0] if gorev.strip()
                 else "araştırma")[:60]
    return "%s %s" % (datetime.now().strftime("%Y-%m-%d"), ilk)


def _madde_notu(madde, bulgular, hatalar, gorev_adi):
    s = [obsidyen_yaz.onbilgi(tur="arastirma", gorev=gorev_adi,
                              madde=madde["ad"]),
         "# %s\n" % madde["ad"]]
    pdfler = []
    for sorgu, kaynaklar in bulgular:
        s.append("## %s\n" % sorgu)
        for k in kaynaklar:
            s.append("### %s\n%s\n\n%s\n" % (
                (k["baslik"] or k["adres"])[:140], k["adres"], k["metin"]))
            if k["adres"].lower().split("?")[0].endswith(".pdf"):
                pdfler.append(k["adres"])
    if pdfler:
        s.append("## PDF bağlantıları (kendiniz indirip Kitap Okuyucu'ya verin)\n")
        s += ["- %s" % u for u in dict.fromkeys(pdfler)]
        s.append("")
    if hatalar:
        s.append("## Alınamayanlar\n")
        s += ["- %s" % h for h in hatalar]
        s.append("")
    s.append("> Bu not web aramasından otomatik derlendi; sayılar ve "
             "alıntılar kaynağından doğrulanmalıdır.")
    return "\n".join(s) + "\n"


def _yaz(alt, ad, icerik):
    """Obsidian'a, olmazsa yerel klasöre yazar. (yol, uyarı)"""
    try:
        return obsidyen_yaz.yaz(alt, ad, icerik), ""
    except obsidyen_yaz.YazmaHatasi as hata:
        k = os.path.join(ayar.KLASOR, "notlar", *[
            obsidyen_yaz.guvenli_ad(p) for p in alt.split("/")])
        os.makedirs(k, exist_ok=True)
        yol = os.path.join(k, obsidyen_yaz.guvenli_ad(ad) + ".md")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
        return yol, ("Obsidian'a yazılamadı (%s); notlar ~/ÜlgenVeri/notlar/ "
                     "altında" % hata)


def calistir(gorev, ajan, ilerleme=None, bekle=time.sleep):
    """Görevi yürütür; özet metni döndürür. ``ajan`` = ArastirmaAjani
    (ara, sayfa_metni). Aynı görev yeniden verilirse kaldığı yerden sürer."""
    gorev = str(gorev).strip()
    if not gorev:
        raise ValueError("Görev boş")
    kimlik = _kimlik(gorev)
    yol = _defter_yolu(kimlik)
    try:
        with open(yol, "r", encoding="utf-8") as f:
            defter = json.load(f)
    except (OSError, ValueError):
        defter = {}
    if not defter.get("maddeler"):
        defter = {"kimlik": kimlik, "baslik": _baslik(gorev),
                  "maddeler": maddelere_ayir(gorev), "notlar": {}, "hata": {}}
    alt = "Araştırmalar/" + obsidyen_yaz.guvenli_ad(defter["baslik"])
    uyari = ""
    toplam = len(defter["maddeler"])
    for sira, madde in enumerate(defter["maddeler"], 1):
        if madde["ad"] in defter["notlar"]:
            continue                                  # önceki çalışmada bitti
        iptal.denetle()
        if ilerleme:
            ilerleme("Araştırma %d/%d: %s" % (sira, toplam, madde["ad"]))
        bulgular, hatalar = [], []
        for sorgu in madde["sorgular"]:
            iptal.denetle()
            sonuc, deneme = [], 0
            while deneme < 3 and not sonuc:
                deneme += 1
                try:
                    sonuc = ajan.ara(sorgu, adet=6)
                except Exception as hata:
                    hatalar.append("%s: arama yapılamadı (%s)" % (
                        sorgu[:60], str(hata)[:80]))
                    bekle(SORGU_ARASI_SN * 3 * deneme)
            kaynaklar, okunan = [], 0
            for s in sonuc:
                metin = s.get("ozet", "")
                if okunan < SAYFA_SAYISI and not s["adres"].lower().split(
                        "?")[0].endswith(".pdf"):
                    try:
                        metin = ajan.sayfa_metni(s["adres"], SAYFA_UZUNLUK)
                        okunan += 1
                    except Exception:
                        pass
                kaynaklar.append({"baslik": s.get("baslik", ""),
                                  "adres": s.get("adres", ""),
                                  "metin": metin})
            if kaynaklar:
                bulgular.append((sorgu, kaynaklar))
            bekle(SORGU_ARASI_SN)
        yolu, u = _yaz(alt, madde["ad"],
                       _madde_notu(madde, bulgular, hatalar, defter["baslik"]))
        uyari = uyari or u
        defter["notlar"][madde["ad"]] = yolu
        if hatalar:
            defter["hata"][madde["ad"]] = len(hatalar)
        with open(yol, "w", encoding="utf-8") as f:     # denetim noktası
            json.dump(defter, f, ensure_ascii=False)
    dizin = [obsidyen_yaz.onbilgi(tur="arastirma-dizin"),
             "# %s\n" % defter["baslik"], "## Görev\n", gorev[:4000], "",
             "## Maddeler\n"]
    for m in defter["maddeler"]:
        dizin.append("- [[%s]]%s" % (
            obsidyen_yaz.guvenli_ad(m["ad"]),
            "  (bazı aramalar alınamadı)" if defter["hata"].get(m["ad"]) else ""))
    dyol, u = _yaz(alt, "00 Dizin", "\n".join(dizin) + "\n")
    uyari = uyari or u
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(dict(defter, bitti=True), f, ensure_ascii=False)
    eksik = sum(1 for m in defter["maddeler"] if defter["hata"].get(m["ad"]))
    return ("%d madde araştırıldı%s. Dizin: %s%s"
            % (toplam, (" (%d maddede bazı aramalar alınamadı)" % eksik)
               if eksik else "", dyol, (" · " + uyari) if uyari else ""))


def ilerleme_yaz(metin):
    ajan_kayit.ilerleme("arastirma", metin)
