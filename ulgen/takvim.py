"""iPhone takvim dışa aktarımı: Mac kapalıyken de çalan alarmlar.

Neden: Mac uyurken/kapalıyken hiçbir Ülgen kodu çalışmaz, Safari de yerel
bildirim planlayamaz. iPhone'un KENDİ takvimi ise ağsız ve Mac'siz alarm
çalar. Bu modül, ilaç planlarını, randevuları, saatli görevleri ve rutinleri
bir .ics dosyasına çevirir; iPhone'a bir kez aktarılır.

Sınırlar (dürüst):
  * Alarm yalnızca ÇALAR; "aldım" yanıtı Ülgen'e dönmez. Yanıt Ülgen'e
    ulaşılabildiğinde arayüzden verilir (kapalıyken kaçan doz "yanıtsız"
    görünür, 'düzelt' ile işaretlenir).
  * Ülgen'de "aldım" dediğinizde iPhone alarmları iptal olmaz (tekrarlar çalar).
  * Tekrar alarmı için her saat birkaç ayrı olay üretilir (Apple Takvim olay
    başına en çok iki uyarı gösterir); her biri tek uyarılıdır.
  * Plan değişince dosyayı yeniden aktarın; UID sabit olduğundan çift kayıt
    oluşmaz ama silinen planın eski olayı iPhone'da kalır (elle silinir).
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
    return dt.strftime("%Y%m%dT%H%M%S")      # yüzen (cihaz saat dilimi)


def _olay(uid, baslik, bas, sure_dk=5, rrule="", alarmlar=(0,), simdi=None,
          aciklama=""):
    s = ["BEGIN:VEVENT", "UID:" + uid,
         "DTSTAMP:" + (simdi or datetime.utcnow()).strftime("%Y%m%dT%H%M%SZ"),
         "DTSTART:" + _zaman(bas),
         "DTEND:" + _zaman(bas + timedelta(minutes=sure_dk)),
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
                "X-WR-CALNAME:Ülgen", "X-WR-TIMEZONE:Europe/Istanbul"]
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
                                  "Ülgen'de 'aldım' yazın."))
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
                              gun0.replace(hour=sa, minute=dk), 15, rr, (0,))
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
                              alarm)
    satirlar.append("END:VCALENDAR")
    return "\r\n".join(_katla(s) for s in satirlar) + "\r\n"
