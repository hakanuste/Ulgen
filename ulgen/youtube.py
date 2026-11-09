"""YouTube videosunu yorumlama: bağlantı sohbete yapıştırılınca videonun
altyazısı (konuşma metni) çekilir ve iletiye eklenir.

- Önce youtube-transcript-api kütüphanesi denenir (ücretsiz, anahtarsız);
  yoksa ya da çalışmazsa izleme sayfasındaki altyazı listesinden okunur.
- Türkçe altyazı önce, yoksa İngilizce, yoksa ilk bulunan (otomatik dahil).
- Görüntü anlaşılmaz; yalnızca konuşulanlar. Altyazısı olmayan videoda
  bunu açıkça söyler.
- Tam metin Obsidian'a 'Ülgen/YouTube' notu olarak yazılır; sonraki
  sorularda kütüphaneden bulunur.
"""

import html
import json
import re
from urllib.parse import urlparse, parse_qs

from . import obsidyen, obsidyen_yaz

ADRES = re.compile(
    r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com/(?:watch\?[^\s]*v=|shorts/|live/|embed/)"
    r"|youtu\.be/)([A-Za-z0-9_-]{11})[^\s]*")
IZINLI = {"www.youtube.com", "youtube.com", "m.youtube.com"}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DILLER = ("tr", "en")
ILETI_SINIRI = 10000
AZAMI_BAYT = 6_000_000


class YoutubeHatasi(Exception):
    pass


def kimlik_bul(metin):
    m = ADRES.search(metin or "")
    return m.group(1) if m else None


def _indir(adres):
    if urlparse(adres).hostname not in IZINLI:
        raise YoutubeHatasi("Bu adrese bağlanılmaz.")
    import requests
    y = requests.get(adres, headers={"User-Agent": UA, "Accept-Language": "tr,en;q=0.8"},
                     cookies={"CONSENT": "YES+1", "SOCS": "CAI"}, timeout=15)
    y.raise_for_status()
    if len(y.content) > AZAMI_BAYT:
        raise YoutubeHatasi("Yanıt çok büyük.")
    return y.text


def _sure(sn):
    sn = int(sn)
    return "%d:%02d:%02d" % (sn // 3600, sn % 3600 // 60, sn % 60) if sn >= 3600 \
        else "%d:%02d" % (sn // 60, sn % 60)


def _birlestir(parcalar):
    """[(saniye, metin)] -> yaklaşık 30 sn'de bir zaman imli metin."""
    satirlar, son = [], -999
    for t, m in parcalar:
        m = " ".join(html.unescape(m).split())
        if not m:
            continue
        if t - son >= 30:
            satirlar.append("\n[%s] " % _sure(t))
            son = t
        satirlar.append(m + " ")
    return "".join(satirlar).strip()


def _kutuphane(vid):
    """youtube-transcript-api (0.6 ve 1.x sürümleri)."""
    from youtube_transcript_api import YouTubeTranscriptApi as Api
    if hasattr(Api, "get_transcript"):                  # 0.6.x
        liste = Api.list_transcripts(vid)
        try:
            t = liste.find_transcript(list(DILLER))
        except Exception:
            t = next(iter(liste))
        return [(p["start"], p["text"]) for p in t.fetch()], t.language_code
    api = Api()                                         # 1.x
    liste = api.list(vid)
    try:
        t = liste.find_transcript(list(DILLER))
    except Exception:
        t = next(iter(liste))
    return [(p.start, p.text) for p in t.fetch()], t.language_code


def _oyuncu_verisi(sayfa):
    i = sayfa.find("ytInitialPlayerResponse")
    if i < 0:
        return {}
    k = sayfa.find("{", i)
    try:
        veri, _ = json.JSONDecoder().raw_decode(sayfa[k:])
        return veri
    except ValueError:
        return {}


def _sayfadan(vid, indir):
    sayfa = indir("https://www.youtube.com/watch?v=%s&hl=tr" % vid)
    veri = _oyuncu_verisi(sayfa)
    detay = veri.get("videoDetails") or {}
    bilgi = {"baslik": detay.get("title") or "", "kanal": detay.get("author") or "",
             "sure": int(detay.get("lengthSeconds") or 0),
             "aciklama": (detay.get("shortDescription") or "")[:1500]}
    izler = (((veri.get("captions") or {}).get("playerCaptionsTracklistRenderer") or {})
             .get("captionTracks") or [])
    if not izler:
        return bilgi, [], None

    def sira(iz):
        dil = iz.get("languageCode", "")
        return (DILLER.index(dil) if dil in DILLER else 9, iz.get("kind") == "asr")
    iz = sorted(izler, key=sira)[0]
    ham = indir(iz["baseUrl"] + "&fmt=json3")
    parcalar = []
    for o in json.loads(ham).get("events") or []:
        metin = "".join(s.get("utf8", "") for s in o.get("segs") or [])
        if metin.strip():
            parcalar.append((o.get("tStartMs", 0) / 1000.0, metin))
    return bilgi, parcalar, iz.get("languageCode")


def getir(vid, indir=None):
    """{'kimlik','baslik','kanal','sure','aciklama','dil','metin'}"""
    indir = indir or _indir
    bilgi, parcalar, dil = {}, [], None
    try:
        bilgi, parcalar, dil = _sayfadan(vid, indir)
    except Exception:
        pass
    if not parcalar and indir is _indir:
        try:
            parcalar, dil = _kutuphane(vid)
        except Exception:
            pass
    bilgi.update({"kimlik": vid, "dil": dil, "metin": _birlestir(parcalar)})
    return bilgi


def _secilmis(metin, soru, sinir):
    """Uzun döküm: soruya göre en ilgili parçalar; soru yoksa başı, ortası,
    sonu eşit aralıklı parçalar."""
    if len(metin) <= sinir:
        return metin
    kelimeler = obsidyen.kokler(obsidyen.KELIME.findall(obsidyen.normal(soru)))
    genel = re.compile(r"^(yorumla|ozetle|ozet|anlat|incele|izle|bak|ne diyor|"
                       r"degerlendir)\w*$")
    if [k for k in kelimeler if not genel.match(k)]:
        return obsidyen.parcali_alinti(metin, obsidyen.KELIME.findall(
            obsidyen.normal(soru)), sinir)
    parca = 900
    adet = max(1, sinir // parca)
    adim = max(1, len(metin) // adet)
    return "\n…\n".join(metin[i:i + parca] for i in range(0, len(metin), adim))[:sinir]


def _notla(b):
    try:
        govde = "# %s\n\nKanal: %s · Süre: %s · https://youtu.be/%s\n\n%s\n\n## Döküm\n\n%s\n" % (
            b.get("baslik") or b["kimlik"], b.get("kanal", ""), _sure(b.get("sure", 0)),
            b["kimlik"], b.get("aciklama", ""), b["metin"])
        return obsidyen_yaz.yaz("YouTube", (b.get("baslik") or b["kimlik"])[:60],
                                obsidyen_yaz.onbilgi(tur="youtube") + govde)
    except Exception:
        return None


def iletiye_ekle(metin, indir=None):
    """İletide YouTube bağlantısı varsa dökümü ekler; yoksa metni aynen döndürür."""
    vid = kimlik_bul(metin)
    if not vid:
        return metin
    soru = ADRES.sub(" ", metin).strip()
    b = getir(vid, indir)
    baslik = b.get("baslik") or vid
    if not b["metin"]:
        return ("%s\n\n[YOUTUBE VİDEO: %s · %s]\nBu videonun altyazısı (konuşma "
                "metni) alınamadı; altyazısı olmayabilir ya da YouTube erişimi "
                "engelledi. Video açıklaması: %s\nKullanıcıya bunu açıkça söyle; "
                "videonun içeriğini tahmin etme." % (
                    soru or "Bu videoyu yorumla.", baslik, b.get("kanal", ""),
                    b.get("aciklama") or "(yok)"))
    yol = _notla(b)
    dokum = _secilmis(b["metin"], soru, ILETI_SINIRI)
    return ("%s\n\n[YOUTUBE VİDEO: %s · kanal: %s · süre: %s · altyazı dili: %s%s]\n"
            "Not: yalnızca konuşulanlar var, görüntü yok. Yanıtta yeri geçen "
            "zaman imlerini [dk:sn] belirt.\n%s" % (
                soru or "Bu videoyu yorumla: ana fikirler, önemli noktalar ve değerlendirme.",
                baslik, b.get("kanal", ""), _sure(b.get("sure", 0)), b.get("dil") or "?",
                (" · tam döküm Obsidian'da: %s" % yol) if yol else "",
                dokum))
