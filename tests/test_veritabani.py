"""Veritabanı katmanı: göç, işlem, bütünlük, kurtarma, arama."""

import os
import sqlite3

from tests.temel import TemizVeri
from ulgen import ayar, veritabani, yedek


class VeritabaniTesti(TemizVeri):

    def test_surum_guncel(self):
        self.assertEqual(veritabani.surum(), veritabani.SURUM)

    def test_wal_kipi(self):
        kip = veritabani.sorgu("PRAGMA journal_mode", (), True)[0]
        self.assertEqual(list(kip.values())[0].lower(), "wal")

    def test_kur_tekrar_calisinca_veri_kaybolmaz(self):
        veritabani.sorgu("INSERT INTO sohbet (rol, metin, zaman, duyarli) "
                         "VALUES ('kullanici', 'merhaba', 'z', 0)")
        veritabani.kur()
        veritabani.kur()
        satirlar = veritabani.sorgu("SELECT * FROM sohbet", (), True)
        self.assertEqual(len(satirlar), 1)

    def test_eski_v1_veritabani_goc_eder(self):
        veritabani.kapat()
        for ek in ("", "-wal", "-shm"):
            if os.path.exists(ayar.VERI_TABANI + ek):
                os.remove(ayar.VERI_TABANI + ek)
        b = sqlite3.connect(ayar.VERI_TABANI)
        b.execute("CREATE TABLE sohbet (id INTEGER PRIMARY KEY, rol TEXT, "
                  "metin TEXT, zaman TEXT)")
        b.execute("INSERT INTO sohbet (rol, metin, zaman) "
                  "VALUES ('kullanici', 'eski kayit', 'z')")
        b.commit()
        b.close()
        veritabani.kur()
        self.assertEqual(veritabani.surum(), veritabani.SURUM)
        satir = veritabani.sorgu("SELECT * FROM sohbet", (), True)[0]
        self.assertEqual(satir["metin"], "eski kayit")
        self.assertEqual(satir["duyarli"], 0)

    def test_islem_hatada_geri_alinir(self):
        with self.assertRaises(RuntimeError):
            with veritabani.islem():
                veritabani.sorgu(
                    "INSERT INTO sohbet (rol, metin, zaman, duyarli) "
                    "VALUES ('kullanici', 'gecici', 'z', 0)")
                raise RuntimeError("yarida kes")
        self.assertEqual(
            veritabani.sorgu("SELECT COUNT(*) AS n FROM sohbet", (), True)[0]["n"], 0)

    def test_islem_basarida_kalir_ve_ic_ice_calisir(self):
        with veritabani.islem():
            with veritabani.islem():
                veritabani.sorgu(
                    "INSERT INTO sohbet (rol, metin, zaman, duyarli) "
                    "VALUES ('kullanici', 'kalici', 'z', 0)")
        self.assertEqual(
            veritabani.sorgu("SELECT COUNT(*) AS n FROM sohbet", (), True)[0]["n"], 1)

    def test_butunluk_saglam(self):
        self.assertTrue(veritabani.butunluk_denetimi()[0])

    def test_butunluk_bozuk_dosya(self):
        bozuk = os.path.join(ayar.KLASOR, "bozuk.db")
        with open(bozuk, "wb") as f:
            f.write(b"bu bir sqlite dosyasi degil" * 100)
        self.assertFalse(veritabani.butunluk_denetimi(bozuk)[0])

    def test_sohbet_ara(self):
        for metin in ("zeytin budama takvimi", "ilgisiz bir cümle"):
            veritabani.sorgu(
                "INSERT INTO sohbet (rol, metin, zaman, duyarli) "
                "VALUES ('kullanici', ?, 'z', 0)", (metin,))
        sonuc = veritabani.sohbet_ara("zeytin")
        self.assertEqual(len(sonuc), 1)
        self.assertIn("zeytin", sonuc[0]["metin"])

    def test_gunluk_yazilir(self):
        veritabani.gunluge_yaz("bilgi", "test", "deneme")
        self.assertTrue(veritabani.sorgu("SELECT * FROM gunluk", (), True))


class KurtarmaTesti(TemizVeri):

    def test_otomatik_yedek_ve_bozulmada_kurtarma(self):
        veritabani.sorgu("INSERT INTO sohbet (rol, metin, zaman, duyarli) "
                         "VALUES ('kullanici', 'önemli kayıt', 'z', 0)")
        self.assertTrue(yedek.otomatik_al())
        veritabani.kapat()
        for ek in ("", "-wal", "-shm"):
            if os.path.exists(ayar.VERI_TABANI + ek):
                os.remove(ayar.VERI_TABANI + ek)
        with open(ayar.VERI_TABANI, "wb") as f:
            f.write(b"bozuk" * 2000)
        mesaj = yedek.veritabani_kurtar()
        self.assertTrue(mesaj)
        veritabani.kur()
        satirlar = veritabani.sorgu("SELECT metin FROM sohbet", (), True)
        self.assertEqual([s["metin"] for s in satirlar], ["önemli kayıt"])
        # bozuk dosya silinmedi, yedekler klasörüne taşındı
        klasor = os.path.join(ayar.KLASOR, "yedekler")
        self.assertTrue(any(a.startswith("bozuk-") for a in os.listdir(klasor)))
