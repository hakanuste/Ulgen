"""Görevler, randevular ve rutinler (kalıcı, yeniden başlatmada sürer).

  * görev   : isteğe bağlı zamanı olan yapılacak iş; "görev tamam #N" ile biter.
  * randevu : tarih+saat; ``randevu_oncesi_dk`` (varsayılan 60) önce ve
              zamanında olmak üzere iki kez bildirilir.
  * rutin   : her gün / belirli günler HH:MM; her oluşta bir kez bildirilir.
Kritik (ilaç) takibi ayrıdır: bkz. ilac.py.
"""

import re
from datetime import datetime, timedelta

from . import ayar, veritabani
from .ilac import _norm

# Görev/randevu/rutinde saat YALNIZCA iki nokta ile yazılır (14:30); nokta
# tarih içindir (25.11). "10.01" bir tarihtir, saat değil.
SAAT_K = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")

BICIM = "%Y-%m-%d %H:%M"
GUNLER = ("pazartesi", "sali", "carsamba", "persembe", "cuma", "cumartesi",
          "pazar")
GUN_YAZI = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")


def gun_adi_bul(metin):
    """Metindeki ilk gün adını bulur: (indeks, başlangıç, bitiş) | None.
    'pazartesi', 'pazar' ile; 'cumartesi', 'cuma' ile karışmaz."""
    for e in re.finditer(r"\w+", metin):
        kelime = _norm(e.group(0))
        en_uzun = None
        for i, ad in enumerate(GUNLER):
            if kelime.startswith(ad) and (
                    en_uzun is None or len(ad) > len(GUNLER[en_uzun])):
                en_uzun = i
        if en_uzun is not None:
            return en_uzun, e.start(), e.end()
    return None


def zaman_ayikla(metin, su_an):
    """(datetime | None, kalan_metin). Bugün/yarın, gg.aa(.yyyy), gün adı,
    SS:DD tanınır. Saat yoksa ve tarih varsa 09:00 alınır."""
    kalan = metin
    k = _norm(metin)
    gun = None
    e = re.search(r"\b(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?(?!\d|:)", metin)
    if e:
        try:
            yil = int(e.group(3)) if e.group(3) else su_an.year
            gun = datetime(yil, int(e.group(2)), int(e.group(1)))
            if not e.group(3) and gun.date() < su_an.date():
                gun = gun.replace(year=yil + 1)
            kalan = kalan.replace(e.group(0), " ", 1)
        except ValueError:
            gun = None
    if gun is None:
        if re.search(r"\byarin\b", k):
            gun = datetime.combine(su_an.date() + timedelta(days=1),
                                   datetime.min.time())
            kalan = re.sub(r"yar[ıi]n", " ", kalan, flags=re.I)
        elif re.search(r"\bbugun\b", k):
            gun = datetime.combine(su_an.date(), datetime.min.time())
            kalan = re.sub(r"bug[üu]n", " ", kalan, flags=re.I)
        else:
            bulunan = gun_adi_bul(kalan)
            if bulunan:
                i, bas, son = bulunan
                fark = (i - su_an.weekday()) % 7 or 7
                gun = datetime.combine(su_an.date() + timedelta(days=fark),
                                       datetime.min.time())
                kalan = kalan[:bas] + " " + kalan[son:]
    s = SAAT_K.search(kalan)
    if s:
        sa, dk = int(s.group(1)), int(s.group(2))
        kalan = kalan[:s.start()] + " " + kalan[s.end():]
        if gun is None:
            gun = datetime.combine(su_an.date(), datetime.min.time())
            if gun.replace(hour=sa, minute=dk) <= su_an:
                gun += timedelta(days=1)
        return gun.replace(hour=sa, minute=dk), _temizle(kalan)
    if gun is not None:
        return gun.replace(hour=9), _temizle(kalan)
    return None, _temizle(kalan)


def _temizle(m):
    return re.sub(r"\s+", " ", m).strip(" ,.:;-") or ""


def tekrar_ayikla(metin):
    """'her gün', 'her pazartesi ve cuma', 'hafta içi' -> ('0,1,..', kalan)."""
    k = _norm(metin)
    if re.search(r"hafta ici", k):
        return "0,1,2,3,4", re.sub(r"(her )?hafta i[çc]i( her g[üu]n)?", " ",
                                   metin, flags=re.I)
    if re.search(r"hafta sonu", k):
        return "5,6", re.sub(r"(her )?hafta sonu", " ", metin, flags=re.I)
    if re.search(r"\bher ?gun\b|\bgunluk\b", k):
        return "0,1,2,3,4,5,6", re.sub(r"her ?g[üu]n|g[üu]nl[üu]k", " ", metin,
                                       flags=re.I)
    secilen, kalan = [], metin
    if re.search(r"\bher\b", k):
        while True:
            bulunan = gun_adi_bul(kalan)
            if not bulunan:
                break
            i, bas, son = bulunan
            if str(i) not in secilen:
                secilen.append(str(i))
            kalan = kalan[:bas] + " " + kalan[son:]
        kalan = re.sub(r"\bher\b|\bve\b", " ", kalan, flags=re.I)
    if secilen:
        return ",".join(sorted(secilen)), kalan
    return "", metin


class Gorevler:

    def __init__(self, bildir):
        self._bildir = bildir

    # ------------------------------------------------------------ ekleme
    def gorev_ekle(self, metin, su_an=None):
        su_an = su_an or datetime.now()
        zaman, baslik = zaman_ayikla(metin, su_an)
        if not baslik:
            return "Görevin adı boş olamaz. Örnek: görev ekle: faturayı öde yarın 10:00"
        kimlik = veritabani.sorgu(
            "INSERT INTO gorev (tur, baslik, zaman, olusturma) "
            "VALUES ('gorev', ?, ?, ?)",
            (baslik, zaman.strftime(BICIM) if zaman else None,
             su_an.timestamp()))
        return "Görev #%d eklendi: %s%s." % (
            kimlik, baslik, zaman.strftime(" (%d.%m %H:%M)") if zaman else "")

    def randevu_ekle(self, metin, su_an=None):
        su_an = su_an or datetime.now()
        zaman, baslik = zaman_ayikla(metin, su_an)
        if zaman is None or not baslik:
            return ("Tarih ve saat gerekli. Örnek: randevu ekle: 25.11 14:30 "
                    "diş hekimi")
        if zaman <= su_an:
            return "Bu zaman geçmişte görünüyor."
        kimlik = veritabani.sorgu(
            "INSERT INTO gorev (tur, baslik, zaman, onceden_dk, olusturma) "
            "VALUES ('randevu', ?, ?, ?, ?)",
            (baslik, zaman.strftime(BICIM),
             int(ayar.yukle().get("randevu_oncesi_dk", 60)),
             su_an.timestamp()))
        return "Randevu #%d eklendi: %s, %s." % (
            kimlik, baslik, zaman.strftime("%d.%m.%Y %H:%M"))

    def rutin_ekle(self, metin, su_an=None):
        su_an = su_an or datetime.now()
        gunler, kalan = tekrar_ayikla(metin)
        if not gunler:
            return ("Hangi günler? Örnek: rutin ekle: her gün 07:00 yürüyüş; "
                    "her pazartesi ve cuma 18:00 dans çalışması")
        zaman, baslik = zaman_ayikla(kalan, su_an)
        if zaman is None or not SAAT_K.search(kalan) or not baslik:
            return "Saat ve ad gerekli. Örnek: rutin ekle: her gün 07:00 yürüyüş"
        kimlik = veritabani.sorgu(
            "INSERT INTO gorev (tur, baslik, zaman, tekrar, olusturma) "
            "VALUES ('rutin', ?, ?, ?, ?)",
            (baslik, zaman.strftime("%H:%M"), gunler, su_an.timestamp()))
        return "Rutin #%d eklendi: %s, %s %s." % (
            kimlik, baslik, self._gun_yazi(gunler), zaman.strftime("%H:%M"))

    @staticmethod
    def _gun_yazi(gunler):
        if gunler == "0,1,2,3,4,5,6":
            return "her gün"
        if gunler == "0,1,2,3,4":
            return "hafta içi"
        if gunler == "5,6":
            return "hafta sonu"
        return "/".join(GUN_YAZI[int(g)] for g in gunler.split(","))

    # ------------------------------------------------------- tamam / iptal
    def bitir(self, kimlik, durum="tamam"):
        adet = veritabani.sorgu(
            "UPDATE gorev SET durum=? WHERE id=? AND durum='acik' AND "
            "tur IN ('gorev','randevu','rutin')", (durum, int(kimlik)),
            sayi=True)
        if not adet:
            return "#%s numaralı açık kayıt yok." % kimlik
        return "#%s %s olarak işaretlendi." % (
            kimlik, "tamamlandı" if durum == "tamam" else "iptal edildi")

    # ------------------------------------------------- düzenle / sil
    @staticmethod
    def _acik(kimlik):
        try:
            kimlik = int(kimlik)
        except (TypeError, ValueError):
            return None
        satir = veritabani.sorgu(
            "SELECT * FROM gorev WHERE id=? AND durum='acik' AND "
            "tur IN ('gorev','randevu','rutin')", (kimlik,), True)
        return satir[0] if satir else None

    def liste_json(self):
        """Arayüz için tüm açık kayıtlar (tür sırasıyla)."""
        return veritabani.sorgu(
            "SELECT id, tur, baslik, zaman, tekrar, onceden_dk FROM gorev "
            "WHERE durum='acik' ORDER BY COALESCE(zaman,'9999'), id", (), True)

    def duzenle(self, kimlik, baslik, zaman="", tekrar="", su_an=None):
        """Açık bir görev/randevu/rutini düzeltir.

        zaman: görev için '' (zamansız) ya da 'YYYY-MM-DD HH:MM'; randevu için
        'YYYY-MM-DD HH:MM'; rutin için 'HH:MM'. tekrar yalnız rutin içindir
        ('0,1,..' hafta günleri, 0=pazartesi)."""
        su_an = su_an or datetime.now()
        g = self._acik(kimlik)
        if g is None:
            return "#%s numaralı açık kayıt yok." % kimlik
        baslik = " ".join(str(baslik or "").split())
        if not baslik or len(baslik) > 200:
            return "Ad boş olamaz (en çok 200 karakter)."
        zaman = str(zaman or "").strip().replace("T", " ")
        yeni_zaman, yeni_tekrar = g["zaman"], g["tekrar"]
        if g["tur"] == "rutin":
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", zaman):
                return "Rutin saati SS:DD biçiminde olmalı (örn. 07:30)."
            gunler = sorted({x for x in str(tekrar).split(",") if x != ""})
            if not gunler or any(x not in "0123456" or len(x) != 1
                                 for x in gunler):
                return "En az bir gün seçin (0=pazartesi … 6=pazar)."
            yeni_zaman, yeni_tekrar = zaman, ",".join(gunler)
        else:
            if zaman == "" and g["tur"] == "gorev":
                yeni_zaman = None
            else:
                try:
                    z = datetime.strptime(zaman, BICIM)
                except ValueError:
                    return "Zaman YYYY-AA-GG SS:DD biçiminde olmalı."
                if g["tur"] == "randevu" and z <= su_an:
                    return "Bu zaman geçmişte görünüyor."
                yeni_zaman = z.strftime(BICIM)
        veritabani.sorgu(
            "UPDATE gorev SET baslik=?, zaman=?, tekrar=?, asama=?, "
            "son_bildirim=? WHERE id=?",
            (baslik, yeni_zaman, yeni_tekrar,
             0 if yeni_zaman != g["zaman"] else g["asama"],
             "" if (yeni_zaman != g["zaman"]
                    or yeni_tekrar != g["tekrar"]) else g["son_bildirim"],
             g["id"]))
        return "Düzelttim: #%d %s." % (g["id"], baslik)

    def sil(self, kimlik):
        """Kaydı kalıcı siler (arayüz onay ister)."""
        g = self._acik(kimlik)
        if g is None:
            return "#%s numaralı açık kayıt yok." % kimlik
        veritabani.sorgu("DELETE FROM gorev WHERE id=?", (g["id"],))
        return "Sildim: #%d %s." % (g["id"], g["baslik"])

    def duzenle_metin(self, kimlik, metin, su_an=None):
        """Sohbetten: 'görev düzelt #3: yeni ad yarın 10:00' gibi."""
        su_an = su_an or datetime.now()
        g = self._acik(kimlik)
        if g is None:
            return "#%s numaralı açık kayıt yok." % kimlik
        if g["tur"] == "rutin":
            gunler, kalan = tekrar_ayikla(metin)
            zaman, baslik = zaman_ayikla(kalan, su_an)
            if not gunler or zaman is None or not SAAT_K.search(kalan):
                return "Örnek: rutin düzelt #%s: her gün 07:00 yürüyüş" % kimlik
            return self.duzenle(kimlik, baslik, zaman.strftime("%H:%M"),
                                gunler, su_an)
        zaman, baslik = zaman_ayikla(metin, su_an)
        return self.duzenle(kimlik, baslik,
                            zaman.strftime(BICIM) if zaman else "", "", su_an)

    # ------------------------------------------------------------ listeler
    def listele(self, tur, su_an=None):
        su_an = su_an or datetime.now()
        satirlar = veritabani.sorgu(
            "SELECT * FROM gorev WHERE tur=? AND durum='acik' "
            "ORDER BY COALESCE(zaman,'9999'), id", (tur,), True)
        if not satirlar:
            return {"gorev": "Açık görev yok.", "randevu": "Randevu yok.",
                    "rutin": "Rutin yok."}[tur]
        cikti = []
        for g in satirlar:
            if tur == "rutin":
                cikti.append("#%d %s — %s %s" % (
                    g["id"], g["baslik"], self._gun_yazi(g["tekrar"]),
                    g["zaman"]))
                continue
            z = datetime.strptime(g["zaman"], BICIM) if g["zaman"] else None
            gec = " (GECİKMİŞ)" if z and z < su_an and tur == "gorev" else ""
            cikti.append("#%d %s%s%s" % (
                g["id"], g["baslik"],
                z.strftime(" — %d.%m %H:%M") if z else "", gec))
        return "\n".join(cikti)

    # --------------------------------------------------------------- adım
    def adim(self, su_an):
        simdi = su_an.strftime(BICIM)
        for g in veritabani.sorgu(
                "SELECT * FROM gorev WHERE durum='acik'", (), True):
            if g["tur"] == "rutin":
                self._rutin_adim(g, su_an)
            elif g["tur"] == "randevu" and g["zaman"]:
                z = datetime.strptime(g["zaman"], BICIM)
                if g["asama"] == 0 and g["onceden_dk"] and \
                        su_an >= z - timedelta(minutes=g["onceden_dk"]):
                    self._asama(g, 1)
                    if su_an < z:
                        self._bildir("Randevu yaklaşıyor (%d dk sonra): %s, "
                                     "%s." % (max(1, int((z - su_an)
                                                         .total_seconds() // 60)),
                                              g["baslik"], g["zaman"][11:]),
                                     {"tur": "randevu", "id": g["id"]})
                if g["asama"] < 2 and su_an >= z:
                    self._asama(g, 2)
                    self._bildir("Randevu zamanı: %s (%s)."
                                 % (g["baslik"], g["zaman"][11:]),
                                 {"tur": "randevu", "id": g["id"]})
                if su_an > z + timedelta(hours=6):
                    self.bitir(g["id"], "tamam")
            elif g["tur"] == "gorev" and g["zaman"] and g["asama"] == 0 \
                    and g["zaman"] <= simdi:
                self._asama(g, 2)
                self._bildir("Görev zamanı: %s [#%d]. Bitince 'görev tamam %d'."
                             % (g["baslik"], g["id"], g["id"]),
                             {"tur": "gorev", "id": g["id"]})

    @staticmethod
    def _asama(g, deger):
        veritabani.sorgu("UPDATE gorev SET asama=? WHERE id=?",
                         (deger, g["id"]))
        g["asama"] = deger

    def _rutin_adim(self, g, su_an):
        if str(su_an.weekday()) not in g["tekrar"].split(","):
            return
        sa, dk = (int(x) for x in g["zaman"].split(":"))
        olus = su_an.replace(hour=sa, minute=dk, second=0, microsecond=0)
        if su_an < olus or g["son_bildirim"] >= olus.strftime(BICIM):
            return
        veritabani.sorgu("UPDATE gorev SET son_bildirim=? WHERE id=?",
                         (olus.strftime(BICIM), g["id"]))
        if su_an - olus > timedelta(hours=2):
            return          # çok geç kalmış rutin: sessizce atlanır (kritik değil)
        self._bildir("Rutin zamanı: %s (%s)." % (g["baslik"], g["zaman"]),
                     {"tur": "rutin", "id": g["id"]})
