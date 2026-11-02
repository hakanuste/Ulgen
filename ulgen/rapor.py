"""Sabah, akşam ve haftalık raporlar (yerel veriden, yapay zekâ OLMADAN).

Rapor metni yalnızca bu Mac'teki verilerden (ilaç dozları, görevler,
randevular, iPhone Sağlık ölçümleri, hava) kurulur; hiçbir bulut hizmetine
gitmez. Ülgen tıbbi öneri vermez, doz değiştirmez: yalnızca olanı yazar.
Saatler ayar.json "rapor_saatleri" ile değişir.
"""

import time
from datetime import datetime, timedelta

from . import ayar, hava, saglik_veri, veritabani

VARSAYILAN = {"sabah": "07:30", "aksam": "21:00", "haftalik": "20:00",
              "haftalik_gun": 6}          # 6 = pazar
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi",
          "Pazar"]
DURUM_YAZI = {"alindi": "alındı", "tamamlandi": "alındı", "almadi": "almadı",
              "atlandi": "atlandı", "bekliyor": "bekliyor",
              "ertelendi": "ertelendi", "yanitsiz": "yanıtsız"}


def saatler():
    s = dict(VARSAYILAN)
    s.update(ayar.yukle().get("rapor_saatleri") or {})
    return s


def _dozlar(bas, son):
    return veritabani.sorgu(
        "SELECT ilac_ad, planli, durum FROM doz WHERE planli >= ? AND "
        "planli < ? ORDER BY planli", (bas, son), True)


def _gorevler():
    return veritabani.sorgu(
        "SELECT tur, baslik, zaman FROM gorev WHERE durum='acik' "
        "ORDER BY COALESCE(zaman,'9999'), id", (), True)


def _saglik_satiri(simdi):
    b = saglik_veri.bugun(simdi)
    if not b["veri_var"]:
        return None
    parca = []
    if b["adim"] is not None:
        parca.append("%s adım" % format(b["adim"], ",").replace(",", "."))
    if b["nabiz"] is not None:
        parca.append("son nabız %d" % b["nabiz"])
    if b["uyku_dk"] is not None:
        parca.append("uyku %s" % saglik_veri.uyku_yazi(b["uyku_dk"]))
    return "Sağlık ölçümleri: " + ", ".join(parca) + "."


def _gun_basligi(simdi):
    return "%d %s %d %s" % (simdi.day, [
        "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
        "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"][simdi.month],
        simdi.year, GUNLER[simdi.weekday()])


def sabah(simdi=None):
    simdi = simdi or datetime.now()
    gun = simdi.strftime("%Y-%m-%d")
    yarin = (simdi + timedelta(days=1)).strftime("%Y-%m-%d")
    satir = ["Günaydın Hakan. %s." % _gun_basligi(simdi)]
    h = hava.getir()
    if h:
        satir.append("Hava: %s %d°C, %s." % (
            h["ad"], h["sicaklik"], h["durum"].lower()))
    dozlar = _dozlar(gun, yarin)
    if dozlar:
        satir.append("Bugünkü ilaç dozları:")
        satir += ["  • %s %s (%s)" % (d["planli"][11:16], d["ilac_ad"],
                                      DURUM_YAZI.get(d["durum"], d["durum"]))
                  for d in dozlar]
    else:
        satir.append("Bugün için planlı ilaç dozu yok.")
    gor = [g for g in _gorevler() if not g["zaman"] or g["zaman"][:10] <= gun]
    if gor:
        satir.append("Bugünün görevleri ve randevuları:")
        for g in gor[:10]:
            saat = " — " + g["zaman"][11:16] if g["zaman"] else ""
            satir.append("  • %s%s" % (g["baslik"], saat))
    else:
        satir.append("Bugün için açık görev ya da randevu yok.")
    sg = _saglik_satiri(simdi)
    if sg:
        satir.append(sg)
    return "\n".join(satir)


def aksam(simdi=None):
    simdi = simdi or datetime.now()
    gun = simdi.strftime("%Y-%m-%d")
    yarin = (simdi + timedelta(days=1)).strftime("%Y-%m-%d")
    ertesi = (simdi + timedelta(days=2)).strftime("%Y-%m-%d")
    satir = ["İyi akşamlar Hakan. Günün özeti (%s):" % _gun_basligi(simdi)]
    dozlar = _dozlar(gun, yarin)
    if dozlar:
        sayim = {}
        for d in dozlar:
            sayim[DURUM_YAZI.get(d["durum"], d["durum"])] = \
                sayim.get(DURUM_YAZI.get(d["durum"], d["durum"]), 0) + 1
        satir.append("İlaç dozları: " + ", ".join(
            "%d %s" % (n, a) for a, n in sorted(sayim.items())) + ".")
        sorunlu = [d for d in dozlar if d["durum"] in ("yanitsiz", "bekliyor",
                                                       "ertelendi")]
        for d in sorunlu:
            satir.append("  ! %s %s hâlâ '%s' — İlaçlar sekmesinden "
                         "düzeltebilirsiniz." % (d["planli"][11:16],
                                                 d["ilac_ad"],
                                                 DURUM_YAZI[d["durum"]]))
    else:
        satir.append("Bugün planlı ilaç dozu yoktu.")
    acik = [g for g in _gorevler() if g["tur"] == "gorev"]
    satir.append("Açık görev: %d." % len(acik) if acik else
                 "Açık görev kalmadı.")
    for g in acik[:5]:
        satir.append("  • " + g["baslik"])
    yarinki = [g for g in _gorevler() if g["zaman"] and
               yarin <= g["zaman"][:10] < ertesi]
    if yarinki:
        satir.append("Yarın:")
        satir += ["  • %s %s" % (g["zaman"][11:16], g["baslik"])
                  for g in yarinki]
    else:
        satir.append("Yarın için kayıtlı randevu/görev yok.")
    sg = _saglik_satiri(simdi)
    if sg:
        satir.append(sg)
    return "\n".join(satir)


def haftalik(simdi=None):
    simdi = simdi or datetime.now()
    bas = (simdi - timedelta(days=6)).strftime("%Y-%m-%d")
    son = (simdi + timedelta(days=1)).strftime("%Y-%m-%d")
    satir = ["Haftalık rapor (%s – %s)." % (bas, simdi.strftime("%Y-%m-%d"))]
    dozlar = [d for d in _dozlar(bas, son)
              if d["planli"] <= simdi.strftime("%Y-%m-%d %H:%M")]
    if dozlar:
        sayim = {}
        for d in dozlar:
            a = DURUM_YAZI.get(d["durum"], d["durum"])
            sayim[a] = sayim.get(a, 0) + 1
        alinan = sayim.get("alındı", 0)
        satir.append("İlaç: %d dozun %d'i alındı (%%%d). Ayrıntı: %s." % (
            len(dozlar), alinan, round(100 * alinan / len(dozlar)),
            ", ".join("%d %s" % (n, a) for a, n in sorted(sayim.items()))))
        for ilac in sorted({d["ilac_ad"] for d in dozlar}):
            alt = [d for d in dozlar if d["ilac_ad"] == ilac]
            satir.append("  • %s: %d/%d alındı" % (
                ilac, sum(1 for d in alt if d["durum"] in
                          ("alindi", "tamamlandi")), len(alt)))
    else:
        satir.append("Son 7 günde ilaç kaydı yok.")
    g = saglik_veri.gunluk(7, simdi)
    adimlar = [x["adim"] for x in g if x["adim"] is not None]
    nabizlar = [x["nabiz"] for x in g if x["nabiz"] is not None]
    uykular = [x["uyku"] for x in g if x["uyku"] is not None]
    if adimlar or nabizlar or uykular:
        parca = []
        if adimlar:
            parca.append("günlük ort. %d adım" % round(sum(adimlar)
                                                       / len(adimlar)))
        if nabizlar:
            parca.append("ort. nabız %d" % round(sum(nabizlar)
                                                 / len(nabizlar)))
        if uykular:
            parca.append("ort. uyku %s" % saglik_veri.uyku_yazi(
                round(sum(uykular) / len(uykular))))
        satir.append("Sağlık: " + ", ".join(parca) + ".")
    else:
        satir.append("Sağlık ölçümü kaydı yok.")
    acik = _gorevler()
    satir.append("Açık kayıt: %d görev/randevu/rutin." % len(acik))
    return "\n".join(satir)


URETICILER = {"sabah": sabah, "aksam": aksam, "haftalik": haftalik}


class Raporlar:
    """Zamanı gelen raporu bir kez üretir, saklar ve bildirir."""

    def __init__(self, bildir):
        self._bildir = bildir

    @staticmethod
    def _anahtar(tur, simdi):
        if tur == "haftalik":
            y, h, _ = simdi.isocalendar()
            return "%d-H%02d" % (y, h)
        return simdi.strftime("%Y-%m-%d")

    def uret(self, tur, simdi=None, bildir=True):
        simdi = simdi or datetime.now()
        metin = URETICILER[tur](simdi)
        anahtar = self._anahtar(tur, simdi)
        veritabani.sorgu(
            "INSERT OR REPLACE INTO rapor (tur, anahtar, zaman, metin) "
            "VALUES (?, ?, ?, ?)", (tur, anahtar, time.time(), metin))
        if bildir:
            self._bildir("%s raporu:\n%s" % (
                {"sabah": "Sabah", "aksam": "Akşam",
                 "haftalik": "Haftalık"}[tur], metin))
        return metin

    def adim(self, simdi):
        if ayar.yukle().get("rapor_acik", True) is False:
            return
        s = saatler()
        hedefler = (("sabah", s["sabah"], None),
                    ("aksam", s["aksam"], None),
                    ("haftalik", s["haftalik"], int(s["haftalik_gun"])))
        for tur, saat, gun in hedefler:
            if gun is not None and simdi.weekday() != gun:
                continue
            if simdi.strftime("%H:%M") < saat:
                continue
            var = veritabani.sorgu(
                "SELECT 1 FROM rapor WHERE tur=? AND anahtar=?",
                (tur, self._anahtar(tur, simdi)), True)
            if not var:
                self.uret(tur, simdi)

    @staticmethod
    def son(adet=10):
        return veritabani.sorgu(
            "SELECT tur, anahtar, zaman, metin FROM rapor ORDER BY zaman "
            "DESC LIMIT ?", (adet,), True)
