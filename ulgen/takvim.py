"""iPhone takvim dışa aktarımı: Mac kapalıyken de çalan alarmlar.

Neden: Mac uyurken/kapalıyken hiçbir Ülgen kodu çalışmaz, Safari de yerel
bildirim planlayamaz. iPhone'un KENDİ takvimi ise ağsız ve Mac'siz alarm
çalar. Bu modül, ilaç planlarını, randevuları, saatli görevleri ve rutinleri
bir .ics dosyasına çevirir (sohbetten kurulan hatırlatıcılar dahil); iPhone'a bir kez aktarılır.

Sınırlar (dürüst):
  * Alarm yalnızca ÇALAR; "aldım" yanıtı Ülgen'e dönmez. Yanıt Ülgen'e
    ulaşılabildiğinde arayüzden verilir (kapalıyken kaçan doz "yanıtsız"
    görünür, 'düzelt' ile işaretlenir).
  * Ülgen'de "aldım" dediğinizde iPhone alarmları iptal olmaz (tekrarlar çalar).
  * Tekrar alarmı için her saat birkaç ayrı olay üretilir (Apple Takvim olay
    başına en çok iki uyarı gösterir); her biri tek uyarılıdır.
  * Plan değişince dosyayı yeniden aktarın; UID sabit olduğundan çift kayıt
    oluşmaz ama silinen planın eski olayı iPhone'da kalır (elle silinir).
  * Saatler "Europe/Istanbul" diliminde AÇIKÇA yazılır (sabit +03:00,
    VTIMEZONE ile). Eskiden "yüzen" saat yazılıyordu; iPhone'da Takvim >
    Saat Dilimi Geçersiz Kılma ya da cihaz dilimi farklıysa alarm bir saat
    kayabiliyordu. Ayar ``takvim_saat_dilimi`` (boş = eski yüzen davranış).
  * Varsayılan başlıklar GENELDİR ("Ülgen: ilaç zamanı"): takvim iCloud'a
    senkronlanırsa ilaç adı bulutta görünmesin diye. ``takvim_ayrintili``
    ile ad yazılabilir.
"""

import re
import secrets
import time
from datetime import datetime, timedelta

from . import ayar, veritabani

GUN_KODU = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
_TOKENLER = {}               # tek kullanımlık indirme anahtarları
OMUR_SN = 120


# ----------------------------------------------------------- indirme anahtarı
def anahtar_uret():
    simdi = time.time()
    for k in [k for k, v in _TOKENLER.items() if v < simdi]:
        del _TOKENLER[k]
    anahtar = secrets.token_urlsafe(24)
    _TOKENLER[anahtar] = simdi + OMUR_SN
    return anahtar


def anahtar_tuket(anahtar):
    """Geçerliyse True; her anahtar TEK kez kullanılır."""
    bitis = _TOKENLER.pop(anahtar or "", 0)
    return bitis > time.time()


# ---------------------------------------------------------------- .ics yazımı
def _kac(m):
    return (m.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\n", "\\n"))


def _katla(satir):
    """RFC 5545: 75 sekizliden uzun satırları katlar (UTF-8 sınırına dikkat)."""
    cikti, parca, uzunluk = [], "", 0
    for ch in satir:
        b = len(ch.encode("utf-8"))
        if uzunluk + b > (75 if not cikti else 74):
            cikti.append(parca)
            parca, uzunluk = "", 0
        parca += ch
        uzunluk += b
    cikti.append(parca)
    return "\r\n ".join(cikti)


def _zaman(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


VARSAYILAN_DILIM = "Europe/Istanbul"


def _dilim_adi():
    """Ayardaki saat dilimi; boşsa 'yüzen' (cihazın saat dilimi) kullanılır."""
    return str(ayar.yukle().get("takvim_saat_dilimi", VARSAYILAN_DILIM) or "")


def _sabit_ofset(ad, su_an):
    """Yaz saati uygulamayan bir dilimin '+0300' gibi ofseti; yoksa None."""
    try:
        from zoneinfo import ZoneInfo
        z = ZoneInfo(ad)
        a = datetime(su_an.year, 1, 1, tzinfo=z).utcoffset()
        b = datetime(su_an.year, 7, 1, tzinfo=z).utcoffset()
    except Exception:
        return None
    if a is None or a != b:
        return None
    dk = int(a.total_seconds() // 60)
    isaret = "+" if dk >= 0 else "-"
    return "%s%02d%02d" % (isaret, abs(dk) // 60, abs(dk) % 60)


def _vtimezone(ad, su_an):
    """Sabit ofsetli dilim için VTIMEZONE (cihazın yaz saati kuralına
    bağımlı kalmasın diye); yaz saatli dilimlerde boş döner."""
    ofset = _sabit_ofset(ad, su_an)
    if not ofset:
        return []
    return ["BEGIN:VTIMEZONE", "TZID:" + ad, "BEGIN:STANDARD",
            "DTSTART:20160101T000000", "TZOFFSETFROM:" + ofset,
            "TZOFFSETTO:" + ofset, "TZNAME:" + ofset[:3], "END:STANDARD",
            "END:VTIMEZONE"]


def _olay(uid, baslik, bas, sure_dk=5, rrule="", alarmlar=(0,), simdi=None,
          aciklama="", dilim=""):
    tz = ";TZID=" + dilim if dilim else ""
    s = ["BEGIN:VEVENT", "UID:" + uid,
         "DTSTAMP:" + (simdi or datetime.utcnow()).strftime("%Y%m%dT%H%M%SZ"),
         "DTSTART%s:%s" % (tz, _zaman(bas)),
         "DTEND%s:%s" % (tz, _zaman(bas + timedelta(minutes=sure_dk))),
         "SUMMARY:" + _kac(baslik)]
    if rrule:
        s.append("RRULE:" + rrule)
    if aciklama:
        s.append("DESCRIPTION:" + _kac(aciklama))
    for dk in alarmlar:
        s += ["BEGIN:VALARM", "ACTION:DISPLAY",
              "DESCRIPTION:" + _kac(baslik),
              "TRIGGER:-PT%dM" % dk if dk > 0 else "TRIGGER:PT0S",
              "END:VALARM"]
    s.append("END:VEVENT")
    return s


def olustur(su_an=None):
    """Tüm aktif planlardan .ics metni üretir."""
    su_an = su_an or datetime.now()
    a = ayar.yukle()
    ayrintili = bool(a.get("takvim_ayrintili", False))
    tekrar_n = max(1, min(int(a.get("takvim_tekrar_sayisi", 6)), 12))
    aralik = max(1, int(a.get("ilac_tekrar_dk", 5)))
    satirlar = ["BEGIN:VCALENDAR", "VERSION:2.0",
                "PRODID:-//Ulgen//Takvim 1.0//TR", "CALSCALE:GREGORIAN",
                "X-WR-CALNAME:Ülgen"]
    dilim = _dilim_adi()
    if dilim:
        satirlar.append("X-WR-TIMEZONE:" + dilim)
        satirlar += _vtimezone(dilim, su_an)
    gun0 = datetime.combine(su_an.date(), datetime.min.time())
    # ---- ilaç planları: saat başına tekrar_n ayrı olay (5 dk arayla)
    for p in veritabani.sorgu(
            "SELECT p.id, p.saat, p.gunler, i.ad, i.doz_notu FROM ilac_plan p "
            "JOIN ilac i ON i.id=p.ilac_id WHERE p.aktif=1 AND i.aktif=1",
            (), True):
        sa, dk = (int(x) for x in p["saat"].split(":"))
        gunler = sorted(int(g) for g in p["gunler"].split(","))
        rr = ("FREQ=DAILY" if len(gunler) == 7 else
              "FREQ=WEEKLY;BYDAY=" + ",".join(GUN_KODU[g] for g in gunler))
        notu = " (%s)" % p["doz_notu"] if p["doz_notu"] else ""
        baslik = ("İlaç: %s%s" % (p["ad"], notu) if ayrintili
                  else "Ülgen: ilaç zamanı")
        for k in range(tekrar_n):
            bas = gun0.replace(hour=sa, minute=dk) + timedelta(
                minutes=k * aralik)
            satirlar += _olay("ilac-%d-%d@ulgen" % (p["id"], k),
                              baslik if k == 0 else baslik + " (tekrar)",
                              bas, 5, rr, (0,), aciklama=(
                                  "Ülgen kapalıyken de çalar. Aldıysanız "
                                  "Ülgen'de 'aldım' yazın."), dilim=dilim)
    # ---- randevular, saatli görevler, rutinler
    for g in veritabani.sorgu(
            "SELECT * FROM gorev WHERE durum='acik'", (), True):
        if g["tur"] == "rutin":
            sa, dk = (int(x) for x in g["zaman"].split(":"))
            gunler = sorted(int(x) for x in g["tekrar"].split(","))
            rr = ("FREQ=DAILY" if len(gunler) == 7 else
                  "FREQ=WEEKLY;BYDAY=" + ",".join(GUN_KODU[x] for x in gunler))
            satirlar += _olay("rutin-%d@ulgen" % g["id"], g["baslik"] if
                              ayrintili else "Ülgen: rutin",
                              gun0.replace(hour=sa, minute=dk), 15, rr, (0,),
                              dilim=dilim)
        elif g["zaman"]:
            z = datetime.strptime(g["zaman"], "%Y-%m-%d %H:%M")
            if z < su_an:
                continue
            onceden = g["onceden_dk"] if g["tur"] == "randevu" else 0
            alarm = (onceden, 0) if onceden else (0,)
            ad = {"randevu": "Randevu", "gorev": "Görev"}[g["tur"]]
            satirlar += _olay("%s-%d@ulgen" % (g["tur"], g["id"]),
                              ("%s: %s" % (ad, g["baslik"])) if ayrintili
                              else "Ülgen: " + ad.lower(),
                              z, 30 if g["tur"] == "randevu" else 15, "",
                              alarm, dilim=dilim)
    # ---- sohbetten kurulan hatırlatıcılar (zamanı gelmemiş, onaysız)
    for h in veritabani.sorgu(
            "SELECT id, zaman, mesaj, kalici FROM hatirlaticilar WHERE "
            "onaylandi=0 AND bildirildi=0", (), True):
        z = datetime.strptime(h["zaman"], "%Y-%m-%d %H:%M")
        if z < su_an:
            continue
        baslik = ("Hatırlatma: %s" % h["mesaj"] if ayrintili
                  else "Ülgen: hatırlatma")
        for k in range(tekrar_n if h["kalici"] else 1):
            satirlar += _olay("hat-%d-%d@ulgen" % (h["id"], k),
                              baslik if k == 0 else baslik + " (tekrar)",
                              z + timedelta(minutes=k * aralik), 5, "",
                              (0,), dilim=dilim)
    satirlar.append("END:VCALENDAR")
    return "\r\n".join(_katla(s) for s in satirlar) + "\r\n"
