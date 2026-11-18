"""Kitap bulma: Vikipedi, archive.org ve Project Gutenberg'de arar, bağlantıları
gösterir; siz inceledikten sonra "kitap indir 2" deyince indirir, Kılavuz
klasörüne koyar ve Obsidian'a aktarır.

Örnekler:
  kitap ara: Tıp Kanunu            İbn Sina'nın Tıp Kanunu kitabını bul
  kitap indir 2                    kitap indir 1, 3

Hiçbir şey kendiliğinden indirilmez. Yalnızca bu güvenilir sitelerden
indirilir: archive.org, gutenberg.org. Telif durumu her sonuçta yazılır;
telifli olabilecek kitapta karar sizindir. Kişisel veri gönderilmez:
yalnızca kitap adı aranır.
"""

import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlparse

from . import ayar, kilavuz

UA = "Ulgen/2 (kisisel kutuphane yardimcisi; hakanuste/Ulgen)"
ZAMAN = 15
AZAMI_BOYUT = 80 * 1024 * 1024
ADAY_SAYISI = 8
IZINLI = ("archive.org", "gutenberg.org", "gutenberg.pglaf.org")

ARA_DESENI = re.compile(
    r"^\s*(?:kitap\s*(?:ara|bul)\s*[:\-]?\s*(?P<a>.+?)"
    r"|(?P<b>.+?)\s+kitab(?:ını|ini|ı|i|ları|lari|larını)\s+(?:bul|ara)\w*"
    r"(?:\s+ve\s+.*)?)\s*[.!?]*\s*$", re.IGNORECASE | re.DOTALL)
INDIR_DESENI = re.compile(
    r"^\s*(?:kitap\s+indir\s*[:\-]?\s*(?P<a>[\d\s,ve]+)"
    r"|(?P<b>[\d\s,ve]+?)\s*(?:\.|'?\s*(?:yi|yı|yu|yü|i|ı|u|ü))?\s*"
    r"(?:numaral\w*\s*)?(?:kitab\w*\s*)?indir)\s*[.!]*\s*$", re.IGNORECASE)


def _aday_yolu():
    return os.path.join(ayar.KLASOR, "kitap_adaylari.json")


_TUR = threading.local()          # bu aramada ulaşılamayan siteler


def _json(adres, getir=None):
    try:
        if getir:
            return getir(adres)
        import requests
        y = requests.get(adres, headers={"User-Agent": UA}, timeout=ZAMAN)
        y.raise_for_status()
        return y.json()
    except Exception as hata:
        hatalar = getattr(_TUR, "hatalar", None)
        if hatalar is not None:
            hatalar.append("%s: %s" % (urlparse(adres).hostname, str(hata)[:80]))
        raise


# ---------------------------------------------------------------- arama
def vikipedi(sorgu, getir=None):
    """[(başlık, adres)], İngilizce karşılık başlığı ve Vikipedi'de kitap
    maddesi olarak geçen adlar (ör. 'Türk Mitolojisi (kitap)')."""
    sonuc, ingilizce = [], None
    for dil in ("tr", "en"):
        if dil == "en" and sonuc:          # Türkçe bulunduysa İngilizce adı
            break                          # langlinks verir; ilgisiz sonuç gelmez
        try:
            v = _json("https://%s.wikipedia.org/w/api.php?action=query&list=search"
                      "&format=json&srlimit=3&srsearch=%s" % (dil, quote(sorgu)), getir)
        except Exception:
            continue
        for s in v.get("query", {}).get("search", []):
            sonuc.append((s["title"], "https://%s.wikipedia.org/wiki/%s"
                          % (dil, quote(s["title"].replace(" ", "_")))))
            if dil == "en" and ingilizce is None:
                ingilizce = s["title"]
    if sonuc and sonuc[0][1].startswith("https://tr."):
        try:
            v = _json("https://tr.wikipedia.org/w/api.php?action=query&prop=langlinks"
                      "&lllang=en&format=json&titles=%s" % quote(sonuc[0][0]), getir)
            for sayfa in v.get("query", {}).get("pages", {}).values():
                for b in sayfa.get("langlinks", []):
                    ingilizce = b.get("*") or ingilizce
        except Exception:
            pass
    kitaplar = [re.sub(r"\s*\((kitap|book|roman|novel)\)\s*$", "", b, flags=re.I)
                for b, _ in sonuc if re.search(r"\((kitap|book|roman|novel)\)", b, re.I)]
    return sonuc, ingilizce, kitaplar


# Aramada anlamsız sözcükler (bağlaçlar, "kitabı", iyelik ekleri)
DOLGU = set("""ve ile veya ya da bir bu şu kitap kitabı kitabını kitapları hakkında
için üzerine nin nın nun nün in ın un ün the of and or a an in on to for book books
about""".split())


def onemli_sozcukler(sorgu):
    return [k for k in re.findall(r"\w+", sorgu.lower())
            if len(k) >= 2 and k not in DOLGU][:6]


def _kok(sozcuk):
    """Kaba Türkçe/İngilizce kök: ekleri kesmek için sondan kırp
    ('mitolojisi' -> 'mitoloji', 'tarihi' -> 'tarih')."""
    n = len(sozcuk)
    return sozcuk[:n - 2] if n > 6 else sozcuk[:n - 1] if n > 4 else sozcuk


def isabet(sorgu, aday):
    """Sorudaki önemli sözcüklerin kaçı başlık/yazar/konu içinde (0..1)."""
    from .obsidyen import normal
    sozcukler = onemli_sozcukler(sorgu)
    if not sozcukler:
        return 1.0
    metin = normal(" ".join(str(aday.get(x) or "") for x in ("baslik", "yazar", "konu")))
    parcalar = re.findall(r"\w+", metin)
    tutan = sum(1 for k in sozcukler
                if any(p.startswith(normal(_kok(k))) for p in parcalar))
    return tutan / float(len(sozcukler))


def _esik(sorgu):
    n = len(onemli_sozcukler(sorgu))
    return 1.0 if n <= 2 else 0.6


def _yil(d):
    e = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", str(d.get("year") or d.get("date") or ""))
    return int(e.group(1)) if e else None


def _ilk(x):
    return (x[0] if isinstance(x, list) and x else x) or ""


def _arsiv_sorgu(q, getir):
    alanlar = "".join("&fl%%5B%%5D=%s" % x for x in (
        "identifier", "title", "creator", "year", "date", "language", "licenseurl",
        "subject"))
    adres = ("https://archive.org/advancedsearch.php?q=%s%s&rows=%d&output=json"
             % (quote(q), alanlar, ADAY_SAYISI * 2))
    try:
        return _json(adres, getir).get("response", {}).get("docs", [])
    except Exception:
        return []


def _arsiv_terimleri(sorgu):
    """Her önemli sözcük ZORUNLU (AND); kök + '*' ile ekli biçimler de tutar,
    Türkçe harfsiz yazımlar da ('türk*' OR 'turk*')."""
    from .obsidyen import normal
    terimler = []
    for k in onemli_sozcukler(sorgu):
        kok = re.sub(r"[^\w]", "", _kok(k))
        if not kok:
            continue
        duz = normal(kok)
        terimler.append("(%s* OR %s*)" % (kok, duz) if duz != kok else kok + "*")
    return " AND ".join(terimler)


def arsiv(sorgu, getir=None):
    """Önce başlıkta (tüm sözcükler zorunlu), az sonuç çıkarsa konu ve
    açıklamada arar."""
    terim = _arsiv_terimleri(sorgu)
    if not terim:
        return []
    belgeler = _arsiv_sorgu("title:(%s) AND mediatype:texts" % terim, getir)
    if len(belgeler) < 3:
        gorulen = {d.get("identifier") for d in belgeler}
        belgeler += [d for d in _arsiv_sorgu("(%s) AND mediatype:texts" % terim, getir)
                     if d.get("identifier") not in gorulen]
    return [{"kaynak": "archive.org", "kimlik": d["identifier"],
             "baslik": _ilk(d.get("title")) or d["identifier"],
             "yazar": _ilk(d.get("creator")), "yil": _yil(d),
             "dil": _ilk(d.get("language")), "lisans": d.get("licenseurl") or "",
             "konu": " ".join(d["subject"]) if isinstance(d.get("subject"), list)
             else d.get("subject") or "",
             "sayfa": "https://archive.org/details/%s" % d["identifier"]}
            for d in belgeler if d.get("identifier")]


def _arsiv_dosyasi(aday, getir=None):
    """Adayın indirilecek dosyasını seçer: taranmış metin > düz metin > PDF."""
    try:
        m = _json("https://archive.org/metadata/%s" % aday["kimlik"], getir)
    except Exception:
        return aday
    ust = m.get("metadata", {})
    if aday["baslik"] == aday["kimlik"] and ust.get("title"):     # eksik alanlar
        aday["baslik"] = _ilk(ust["title"])
    aday["yazar"] = aday["yazar"] or _ilk(ust.get("creator"))
    aday["yil"] = aday["yil"] or _yil(ust)
    aday["dil"] = aday["dil"] or _ilk(ust.get("language"))
    aday["lisans"] = aday["lisans"] or ust.get("licenseurl") or ""
    if str(ust.get("access-restricted-item", "")).lower() == "true":
        aday["engel"] = "ödünç verilen kitap; indirilemez (yalnızca sitede okunur)"
        return aday
    dosyalar = m.get("files", [])
    for uzanti in ("_djvu.txt", ".txt", ".pdf"):
        for f in dosyalar:
            ad = f.get("name", "")
            if ad.lower().endswith(uzanti) and f.get("private") != "true":
                aday["dosya"] = "https://archive.org/download/%s/%s" % (
                    aday["kimlik"], quote(ad))
                aday["tur"] = "pdf" if uzanti == ".pdf" else "txt"
                aday["boyut"] = int(f.get("size") or 0)
                return aday
    aday["engel"] = "indirilebilir metin ya da PDF yok"
    return aday


def gutenberg(sorgu, getir=None):
    try:
        v = _json("https://gutendex.com/books?search=%s" % quote(sorgu), getir)
    except Exception:
        return []
    sonuc = []
    for k in v.get("results", [])[:4]:
        bicim = k.get("formats", {})
        metin = next((u for t, u in bicim.items()
                      if t.startswith("text/plain") and not u.endswith(".zip")), None)
        yazar = ", ".join(a.get("name", "") for a in k.get("authors", []))
        sonuc.append({"kaynak": "gutenberg.org", "kimlik": "pg%s" % k.get("id"),
                      "baslik": k.get("title", ""), "yazar": yazar, "yil": None,
                      "dil": ",".join(k.get("languages", [])), "lisans": "public domain",
                      "sayfa": "https://www.gutenberg.org/ebooks/%s" % k.get("id"),
                      "dosya": metin, "tur": "txt", "boyut": 0,
                      "engel": None if metin else "düz metin biçimi yok"})
    return sonuc


def telif(aday):
    lisans = (aday.get("lisans") or "").lower()
    if aday["kaynak"] == "gutenberg.org":
        return "telif dışı (Project Gutenberg denetler)"
    if "publicdomain" in lisans or "public domain" in lisans:
        return "yükleyen kişi telif dışı olarak işaretlemiş (doğrulanmamış)"
    if "creativecommons" in lisans:
        return "yükleyen kişi açık lisanslı olarak işaretlemiş (Creative Commons)"
    if aday.get("yil") and aday["yil"] < 1930:
        return "eski baskı (%d), büyük olasılıkla telif dışı" % aday["yil"]
    return "telif durumu belirsiz: telifli olabilir, indirme kararı sizin"


def ara(sorgu, getir=None):
    """Arar, adayları kaydeder ve gösterilecek metni döndürür."""
    sorgu = re.sub(r"\s+", " ", sorgu).strip(" '\"")[:150]
    _TUR.hatalar = []
    viki, ingilizce, kitap_adlari = vikipedi(sorgu, getir)
    sorgular = []
    for s in [sorgu] + kitap_adlari + ([ingilizce] if ingilizce else []):
        if s and s.lower() not in [x.lower() for x in sorgular]:
            sorgular.append(s)
    adaylar, gorulen = [], set()
    for s in sorgular:
        for a in arsiv(s, getir) + gutenberg(s, getir):
            a["isabet"] = isabet(s, a)
            if a["kimlik"] not in gorulen and a["isabet"] >= _esik(s):
                gorulen.add(a["kimlik"])
                adaylar.append(a)
    adaylar.sort(key=lambda a: -a["isabet"])       # en isabetli önce
    adaylar = adaylar[:10]
    arsivdekiler = [a for a in adaylar if a["kaynak"] == "archive.org"]
    with ThreadPoolExecutor(4) as havuz:
        list(havuz.map(lambda a: _arsiv_dosyasi(a, getir), arsivdekiler))
    try:
        with open(_aday_yolu(), "w", encoding="utf-8") as f:
            json.dump({"sorgu": sorgu, "adaylar": adaylar}, f, ensure_ascii=False)
    except OSError:
        pass
    metin = _goster(sorgu, viki, ingilizce, adaylar)
    if not adaylar and _TUR.hatalar:
        liste = "\n".join("- " + h for h in sorted(set(_TUR.hatalar))[:4])
        metin += ("\n\nAncak bazı sitelere ulaşılamadı (internet bağlantısını "
                  "denetleyin):\n" + liste)
    _TUR.hatalar = None
    return metin


def _boyut_yazi(b):
    if not b:
        return ""
    return " (%.1f MB)" % (b / 1048576.0) if b >= 1048576 else " (%d KB)" % max(1, b // 1024)


def _goster(sorgu, viki, ingilizce, adaylar):
    s = ["# Kitap araması: %s" % sorgu, ""]
    if viki:
        s.append("**Vikipedi (konu hakkında):**")
        s += ["- [%s](%s)" % (b, u) for b, u in viki[:3]]
        s.append("")
    if ingilizce:
        s += ["İngilizce adıyla da arandı: *%s*" % ingilizce, ""]
    if not adaylar:
        s.append("archive.org ve Project Gutenberg'de adı bu sözcüklerin hepsini "
                 "içeren bir kitap çıkmadı. Kitabın tam adıyla, yazarıyla ya da "
                 "İngilizce adıyla yeniden deneyin (örn. 'kitap ara: Bahaeddin "
                 "Ögel Türk Mitolojisi').")
        return "\n".join(s)
    s.append("**Bulunan kitaplar:**")
    for i, a in enumerate(adaylar, 1):
        bilgi = ", ".join(str(x) for x in (a.get("yazar"), a.get("yil"), a.get("dil")) if x)
        s.append("%d. **%s**%s" % (i, a["baslik"][:140], " — " + bilgi if bilgi else ""))
        s.append("   Sayfa: [%s](%s)" % (a["kaynak"], a["sayfa"]))
        if a.get("engel"):
            s.append("   İndirilemez: %s" % a["engel"])
        elif a.get("dosya"):
            tur = "metin" if a.get("tur") == "txt" else "PDF"
            s.append("   Dosya: %s%s" % (tur, _boyut_yazi(a.get("boyut"))))
        s.append("   Telif: %s" % telif(a))
    s += ["", "Bağlantıları açıp inceleyin. Uygun olanı indirmek için yazın: "
          "**kitap indir 2** (birden çok: **kitap indir 1, 3**). İndirilen kitap "
          "Kılavuz klasörüne konur ve Obsidian'a aktarılır; uzmanlar oradan okur."]
    return "\n".join(s)


# ---------------------------------------------------------------- indirme
def _izinli(adres):
    ana = (urlparse(adres or "").hostname or "").lower()
    return adres.startswith("https://") and any(
        ana == h or ana.endswith("." + h) for h in IZINLI)


def _dosya_adi(a):
    uzanti = ".pdf" if a.get("tur") == "pdf" else ".txt"
    ad = kilavuz.dosya_adi_temizle("%s - %s" % (a["baslik"][:100], a["kimlik"][:40]))
    return ad + uzanti


def _indir_dosya(adres, hedef, indirici=None):
    if indirici:
        return indirici(adres, hedef)
    import requests
    with requests.get(adres, headers={"User-Agent": UA}, timeout=60, stream=True) as y:
        y.raise_for_status()
        if not _izinli(y.url):
            raise ValueError("izin verilmeyen siteye yönlendirdi: %s" % y.url)
        toplam = 0
        gecici = hedef + ".indiriliyor"
        with open(gecici, "wb") as f:
            for parca in y.iter_content(65536):
                toplam += len(parca)
                if toplam > AZAMI_BOYUT:
                    f.close()
                    os.remove(gecici)
                    raise ValueError("dosya %d MB sınırını aşıyor" % (AZAMI_BOYUT >> 20))
                f.write(parca)
        os.replace(gecici, hedef)


def indir(numaralar, indirici=None, aktar=None):
    try:
        with open(_aday_yolu(), encoding="utf-8") as f:
            adaylar = json.load(f).get("adaylar", [])
    except (OSError, ValueError):
        return "Önce bir kitap arayın. Örnek: 'kitap ara: Tıp Kanunu'"
    klasor = kilavuz.klasor_bul()
    os.makedirs(klasor, exist_ok=True)
    satirlar, yeni = [], 0
    for n in numaralar:
        if not 1 <= n <= len(adaylar):
            satirlar.append("%d: listede böyle bir numara yok." % n)
            continue
        a = adaylar[n - 1]
        if a.get("engel") or not a.get("dosya"):
            satirlar.append("%d. %s: indirilemez (%s)." % (n, a["baslik"][:80],
                                                           a.get("engel") or "dosya yok"))
            continue
        if not _izinli(a["dosya"]):
            satirlar.append("%d: güvenilir site dışında; indirilmedi." % n)
            continue
        hedef = os.path.join(klasor, _dosya_adi(a))
        if os.path.exists(hedef):
            satirlar.append("%d. %s: zaten indirilmiş." % (n, a["baslik"][:80]))
            continue
        try:
            _indir_dosya(a["dosya"], hedef, indirici)
        except Exception as hata:
            satirlar.append("%d. %s: indirilemedi (%s)."
                            % (n, a["baslik"][:80], str(hata)[:120]))
            continue
        yeni += 1
        satirlar.append("%d. %s: indirildi → %s" % (n, a["baslik"][:80], hedef))
    if yeni:
        (aktar or kilavuz.arka_planda_aktar)()
        satirlar.append("")
        satirlar.append("Obsidian'a aktarım başladı; büyük kitaplar birkaç dakika "
                        "sürebilir. Sonra uzmanlara sorabilirsiniz.")
    return "\n".join(satirlar)


# ---------------------------------------------------------------- komut
def komut(metin, getir=None):
    """Kitap komutuysa yanıt metni, değilse None."""
    e = INDIR_DESENI.match(metin or "")
    if e:
        sayilar = [int(x) for x in re.findall(r"\d+", e.group("a") or e.group("b") or "")]
        if sayilar:
            return indir(sayilar)
    e = ARA_DESENI.match(metin or "")
    if e:
        sorgu = (e.group("a") or e.group("b") or "").strip()
        if len(sorgu) >= 2:
            return ara(sorgu, getir)
    return None
