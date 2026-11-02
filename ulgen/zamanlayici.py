"""Gelişmiş zamanlayıcı ve hatırlatıcılar.

Normal hatırlatıcılar zamanı gelince bir kez uyarır. "Kalıcı" hatırlatıcılar
(ilaç, hap, tansiyon gibi) ise kullanıcı 'tamam' diyerek ONAY verene kadar
her 5 dakikada bir yeniden uyarır (en çok 24 kez, yani 2 saat).
"""

import re
import threading
import time
from datetime import datetime, timedelta

from . import veritabani
from .rapor import Raporlar
from .gorev import Gorevler
from .ilac import Ilac

BICIM = "%Y-%m-%d %H:%M"

KALICI_DESENI = re.compile(
    r"\b(ilaç|ilac|hap|insülin|insulin|tansiyon|kritik|"
    r"onaylayana|onay verene)\w*", re.IGNORECASE)

# Mesajdan ayıklanacak dolgu sözcükleri
DOLGU = re.compile(
    r"\b(hatırlat\w*|hatirlat\w*|yarın|yarin|bugün|bugun|saat|bana|"
    r"lütfen|lutfen|kur|ekle|dakika|sonra|diye|de|da)\b", re.IGNORECASE)


class Zamanlayici:
    """Hatırlatıcıları kurar, listeler ve zamanı gelince bildirir."""

    TEKRAR_ARALIGI = 300   # saniye (5 dakika)
    AZAMI_TEKRAR = 24

    def __init__(self, bildir):
        # bildir(metin): uyarıyı kullanıcıya ileten işlev
        self._bildir = bildir
        self._durdur = threading.Event()
        self.ilac = Ilac(bildir)
        self.gorev = Gorevler(bildir)
        self.rapor = Raporlar(bildir)

    # ------------------------------------------------------------ kurma
    def hatirlatici_kur(self, metin, kalici=None, su_an=None):
        """Doğal Türkçe cümleden hatırlatıcı kurar ve onay metni döndürür.

        Örnekler: "14:30 su iç diye hatırlat",
                  "20 dakika sonra çayı demle diye hatırlat",
                  "yarın 09:00 ilaç al diye hatırlat" (kalıcı olur).
        """
        su_an = su_an or datetime.now()
        dakika = re.search(r"(\d+)\s*dakika\s*sonra", metin, re.IGNORECASE)
        saat = re.search(r"(\d{1,2})[:.](\d{2})", metin)
        if dakika:
            zaman = su_an + timedelta(minutes=int(dakika.group(1)))
            temiz = re.sub(r"\d+\s*dakika\s*sonra", " ", metin,
                           flags=re.IGNORECASE)
        elif saat:
            sa, dk = int(saat.group(1)), int(saat.group(2))
            if sa > 23 or dk > 59:
                return "Saat geçersiz görünüyor. Örnek: 14:30."
            gun = su_an.date()
            yarin = re.search(r"yar[ıi]n", metin, re.IGNORECASE) is not None
            if yarin:
                gun += timedelta(days=1)
            zaman = datetime.combine(gun, datetime.min.time()).replace(
                hour=sa, minute=dk)
            if not yarin and zaman <= su_an:
                zaman += timedelta(days=1)
            temiz = metin[:saat.start()] + " " + metin[saat.end():]
        else:
            return ("Ne zaman hatırlatayım? Örnek: 14:30 su iç diye "
                    "hatırlat, ya da 20 dakika sonra çayı demle diye "
                    "hatırlat.")
        mesaj = DOLGU.sub(" ", temiz)
        mesaj = re.sub(r"\s+", " ", mesaj).strip(" ,.:;-") or "Hatırlatma"
        if kalici is None:
            kalici = bool(KALICI_DESENI.search(metin))
        veritabani.sorgu(
            "INSERT INTO hatirlaticilar (zaman, mesaj, kalici) "
            "VALUES (?, ?, ?)", (zaman.strftime(BICIM), mesaj, int(kalici)))
        sonuc = "Tamam, %s için hatırlatıcı kurdum: %s." % (
            zaman.strftime("%d.%m %H:%M"), mesaj)
        if kalici:
            sonuc += (" Bu önemli bir hatırlatma; onay verene ('tamam' "
                      "deyene) kadar 5 dakikada bir uyaracağım.")
        return sonuc

    # ---------------------------------------------------------- listeleme
    def bekleyenler(self):
        """Bekleyen hatırlatıcıları sözlük listesi olarak döndürür."""
        return veritabani.sorgu(
            "SELECT zaman, mesaj, kalici FROM hatirlaticilar "
            "WHERE onaylandi = 0 AND (bildirildi = 0 OR kalici = 1) "
            "ORDER BY zaman LIMIT 20", (), True)

    def listele(self):
        satirlar = self.bekleyenler()
        if not satirlar:
            return "Bekleyen hatırlatıcınız yok."
        parcalar = ["%s, %s" % (
            datetime.strptime(s["zaman"], BICIM).strftime("%d.%m %H:%M"),
            s["mesaj"]) for s in satirlar]
        return "Bekleyen hatırlatıcılarınız: " + "; ".join(parcalar) + "."

    # -------------------------------------------------------------- onay
    def onay_bekleyenler(self):
        """Uyarılmış ama onaylanmamış kalıcı hatırlatıcılar."""
        return veritabani.sorgu(
            "SELECT id, zaman, mesaj FROM hatirlaticilar WHERE kalici = 1 "
            "AND bildirildi = 1 AND onaylandi = 0 ORDER BY id", (), True)

    def onay_bekleyen_var_mi(self):
        return bool(self.onay_bekleyenler())

    def onayla(self, kimlik=None):
        """TEK bir kalıcı hatırlatıcıyı onaylar.

        ``kimlik`` yoksa ve tam bir tane bekliyorsa onu; birden çok varsa
        hiçbirini onaylamaz, hangisi olduğunu sorar ('tamam #N')."""
        bekleyen = self.onay_bekleyenler()
        if not bekleyen:
            return "Onay bekleyen bir hatırlatma yok."
        if kimlik is None:
            if len(bekleyen) > 1:
                return ("%d hatırlatma onay bekliyor: %s. Hangisi? "
                        "'tamam #%d' gibi yazın." % (
                            len(bekleyen), "; ".join(
                                "#%d %s" % (h["id"], h["mesaj"])
                                for h in bekleyen), bekleyen[0]["id"]))
            kimlik = bekleyen[0]["id"]
        adet = veritabani.sorgu(
            "UPDATE hatirlaticilar SET onaylandi = 1 WHERE id = ? AND "
            "kalici = 1 AND bildirildi = 1 AND onaylandi = 0",
            (int(kimlik),), sayi=True)
        if adet:
            return "Onayınız alındı (#%s). Yalnızca onu durdurdum." % kimlik
        return "#%s numaralı onay bekleyen hatırlatma yok." % kimlik

    # -------------------------------------------------------- arka plan
    def adim(self, su_an):
        """Zamanı gelen hatırlatıcıları bildirir; bildirilenleri döndürür."""
        for motor in (self.ilac, self.gorev, self.rapor):
            try:
                motor.adim(su_an)
            except Exception as hata:   # biri bozulsa diğerleri çalışsın
                veritabani.gunluge_yaz("hata", "zamanlayici", str(hata)[:200])
        zaman_metni = su_an.strftime(BICIM)
        satirlar = veritabani.sorgu(
            "SELECT id, zaman, mesaj, kalici, tekrar FROM hatirlaticilar "
            "WHERE onaylandi = 0 AND zaman <= ? "
            "AND (kalici = 1 OR bildirildi = 0)", (zaman_metni,), True)
        bildirilenler = []
        for satir in satirlar:
            if satir["kalici"]:
                tekrar = satir["tekrar"] + 1
                if tekrar > self.AZAMI_TEKRAR:
                    veritabani.sorgu(
                        "UPDATE hatirlaticilar SET onaylandi = 2 "
                        "WHERE id = ?", (satir["id"],))
                    continue
                sonraki = (su_an + timedelta(seconds=self.TEKRAR_ARALIGI))
                veritabani.sorgu(
                    "UPDATE hatirlaticilar SET tekrar = ?, bildirildi = 1, "
                    "zaman = ? WHERE id = ?",
                    (tekrar, sonraki.strftime(BICIM), satir["id"]))
                if tekrar == 1:
                    metin = ("Hatırlatma zamanı: %s [#%d]. Onay verene kadar "
                             "beş dakikada bir uyaracağım. 'Tamam #%d' deyin."
                             % (satir["mesaj"], satir["id"], satir["id"]))
                else:
                    metin = ("Tekrar hatırlatıyorum: %s [#%d]. Onay için "
                             "'tamam #%d' deyin."
                             % (satir["mesaj"], satir["id"], satir["id"]))
            else:
                veritabani.sorgu(
                    "UPDATE hatirlaticilar SET bildirildi = 1 WHERE id = ?",
                    (satir["id"],))
                metin = "Hatırlatma zamanı: %s." % satir["mesaj"]
            self._bildir(metin)
            bildirilenler.append(metin)
        return bildirilenler

    def dongu(self):
        """Her 15 saniyede bir zamanı gelenleri kontrol eder (iş parçacığı)."""
        while not self._durdur.is_set():
            try:
                self.adim(datetime.now())
            except Exception as hata:  # arka plan döngüsü asla ölmemeli
                print("Zamanlayıcı hatası:", hata, flush=True)
            time.sleep(15)

    def durdur(self):
        self._durdur.set()
