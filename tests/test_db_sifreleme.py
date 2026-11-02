"""Canlı veritabanı şifrelemesi (SQLCipher): diskte düz metin olmamalı."""

import base64
import glob
import hashlib
import os
import sqlite3
import unittest
from unittest import mock

from tests.temel import TemizVeri
from ulgen import ayar, gizli, veritabani, yedek

GIZLI_METIN = "ÇOKGİZLİ-zeytin-tansiyon-ilacı-7391"


def diskteki_tum_baytlar():
    ham = b""
    for yol in glob.glob(ayar.VERI_TABANI + "*"):
        with open(yol, "rb") as f:
            ham += f.read()
    return ham


def ekle(metin=GIZLI_METIN):
    veritabani.sorgu("INSERT INTO sohbet (rol, metin, zaman, duyarli) "
                     "VALUES ('kullanici', ?, 'z', 0)", (metin,))
    veritabani.sorgu("INSERT INTO notlar (metin, zaman) VALUES (?, 'z')",
                     (metin + "-not",))


@unittest.skipUnless(veritabani.sifreleme_var(), "SQLCipher yok")
class SifrelemeTesti(TemizVeri):

    def test_yeni_veritabani_sifreli_ve_duz_metin_yok(self):
        self.assertTrue(veritabani.SIFRELI)
        ekle()
        self.assertEqual(veritabani.dosya_turu(ayar.VERI_TABANI), "sifreli")
        # WAL dosyası dahil diskteki hiçbir bayt düz metin içermez
        ham = diskteki_tum_baytlar()
        self.assertNotIn(GIZLI_METIN.encode(), ham)
        self.assertNotIn(b"SQLite format 3", ham)
        veritabani.kapat()
        self.assertNotIn(GIZLI_METIN.encode(), diskteki_tum_baytlar())

    def test_sifreli_veritabani_yeniden_acilinca_okunur_ve_fts_calisir(self):
        ekle()
        veritabani.kapat()
        veritabani.kur()
        self.assertEqual(veritabani.sohbet_ara("zeytin")[0]["metin"],
                         GIZLI_METIN)

    def test_duz_sqlite_ile_acilamaz(self):
        ekle()
        veritabani.kapat()
        with self.assertRaises(sqlite3.DatabaseError):
            sqlite3.connect(ayar.VERI_TABANI).execute(
                "SELECT * FROM sohbet").fetchall()

    def test_eski_duz_veritabani_dogrulanarak_sifrelenir(self):
        veritabani.kapat()
        for yol in glob.glob(ayar.VERI_TABANI + "*"):
            os.remove(yol)
        with mock.patch.object(veritabani, "_sc", None):    # eski sürüm gibi düz
            veritabani.kur()
            ekle()
            ekle("ikinci-kayit")
            self.assertFalse(veritabani.SIFRELI)
            veritabani.kapat()
        self.assertEqual(veritabani.dosya_turu(ayar.VERI_TABANI), "duz")
        self.assertIn(GIZLI_METIN.encode(), diskteki_tum_baytlar())
        # SQLCipher açılınca otomatik göç
        veritabani.kur()
        self.assertTrue(veritabani.SIFRELI)
        self.assertIn("şifrelendi", veritabani.GOC_NOTU)
        sayi = veritabani.sorgu("SELECT COUNT(*) AS n FROM sohbet", (), True)
        self.assertEqual(sayi[0]["n"], 2)
        self.assertEqual(veritabani.surum(), veritabani.SURUM)
        self.assertEqual(len(veritabani.sohbet_ara("zeytin")), 1)
        veritabani.kapat()
        self.assertNotIn(GIZLI_METIN.encode(), diskteki_tum_baytlar())
        self.assertFalse(os.path.exists(ayar.VERI_TABANI + ".eski"))
        self.assertFalse(os.path.exists(ayar.VERI_TABANI + ".yeni"))

    def test_eski_duz_kopya_yalniz_sifreli_arsivde_ve_geri_cozulur(self):
        veritabani.kapat()
        for yol in glob.glob(ayar.VERI_TABANI + "*"):
            os.remove(yol)
        with mock.patch.object(veritabani, "_sc", None):
            veritabani.kur()
            ekle()
            veritabani.kapat()
        with open(ayar.VERI_TABANI, "rb") as f:
            orijinal = f.read()
        veritabani.kur()
        arsivler = glob.glob(os.path.join(ayar.KLASOR, "yedekler",
                                          "onceki-sifresiz-*"))
        self.assertEqual(len(arsivler), 1)
        with open(arsivler[0], "rb") as f:
            sifreli = f.read()
        self.assertNotIn(GIZLI_METIN.encode(), sifreli)       # arşiv şifreli
        self.assertEqual(
            gizli.aes_coz(gizli.ana_anahtar(), sifreli, b"ULGENDBDUZ1"),
            orijinal)                                          # geri çözülür

    def test_yanlis_anahtar_dosyaya_dokunmaz_parolali_yedekten_donulur(self):
        ekle()
        parolali = os.path.join(ayar.KLASOR, "k.ulgenyedek")
        yedek.al(parolali, "parola-1234")
        yedek.otomatik_al()
        veritabani.kapat()
        with open(ayar.VERI_TABANI, "rb") as f:
            oncesi = hashlib.sha256(f.read()).hexdigest()
        # anahtar kayboldu ve yenisi üretildi
        with open(os.path.join(ayar.KLASOR, "bellek.anahtar"), "w") as f:
            f.write(base64.urlsafe_b64encode(os.urandom(32)).decode())
        with self.assertRaises(veritabani.VeriTabaniHatasi):
            veritabani.kur()
        with open(ayar.VERI_TABANI, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), oncesi)
        self.assertFalse(veritabani.butunluk_denetimi()[0])
        # Açılış kurtarması: otomatik yedek de eski anahtarla şifreliydi,
        # çözülemez; dürüstçe bildirir. Bozuk dosya silinmez, taşınır.
        mesaj = yedek.veritabani_kurtar()
        self.assertIn("sağlam yedek bulunamadı", mesaj)
        bozuk = glob.glob(os.path.join(ayar.KLASOR, "yedekler", "bozuk-*",
                                       "veri.db"))
        self.assertEqual(len(bozuk), 1)
        with open(bozuk[0], "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), oncesi)
        # Anahtardan bağımsız tek yol: parolalı yedek
        veritabani.kapat()
        for yol in glob.glob(ayar.VERI_TABANI + "*"):
            os.remove(yol)
        yedek.geri_yukle(parolali, "parola-1234")
        veritabani.kur()
        self.assertEqual(veritabani.sohbet_ara("zeytin")[0]["metin"],
                         GIZLI_METIN)

    def test_sqlcipher_yokken_sifreli_dosya_acilmaz_ve_degismez(self):
        ekle()
        veritabani.kapat()
        with open(ayar.VERI_TABANI, "rb") as f:
            oncesi = f.read()
        with mock.patch.object(veritabani, "_sc", None):
            with self.assertRaises(veritabani.VeriTabaniHatasi):
                veritabani.kur()
        with open(ayar.VERI_TABANI, "rb") as f:
            self.assertEqual(f.read(), oncesi)

    def test_tasinabilir_yedek_dongusu(self):
        ekle()
        hedef = os.path.join(ayar.KLASOR, "t.ulgenyedek")
        yedek.al(hedef, "parola-1234")
        self.assertNotIn(GIZLI_METIN.encode(),
                         open(hedef, "rb").read())            # yedek şifreli
        veritabani.kapat()
        for yol in glob.glob(ayar.VERI_TABANI + "*"):
            os.remove(yol)
        yedek.geri_yukle(hedef, "parola-1234")
        veritabani.kur()
        self.assertTrue(veritabani.SIFRELI)                   # geri yükleme sonrası yine şifreli
        self.assertEqual(veritabani.sohbet_ara("zeytin")[0]["metin"],
                         GIZLI_METIN)
        veritabani.kapat()
        self.assertNotIn(GIZLI_METIN.encode(), diskteki_tum_baytlar())

    def test_duz_kopya_okunabilir_sqlite(self):
        ekle()
        yol = os.path.join(ayar.KLASOR, "duz.db")
        veritabani.duz_kopya(yol)
        satir = sqlite3.connect(yol).execute(
            "SELECT metin FROM sohbet").fetchone()
        self.assertEqual(satir[0], GIZLI_METIN)

    def test_butunluk_denetimi_baska_dosyada(self):
        ekle()
        yol = os.path.join(ayar.KLASOR, "duz2.db")
        veritabani.duz_kopya(yol)
        self.assertTrue(veritabani.butunluk_denetimi(yol)[0])


class SifresizYedekModTesti(TemizVeri):

    def test_sqlcipher_yoksa_duz_calisir_ve_durum_bildirir(self):
        veritabani.kapat()
        for yol in glob.glob(ayar.VERI_TABANI + "*"):
            os.remove(yol)
        with mock.patch.object(veritabani, "_sc", None):
            veritabani.kur()
            ekle()
            self.assertFalse(veritabani.SIFRELI)
            self.assertEqual(veritabani.sohbet_ara("zeytin")[0]["metin"],
                             GIZLI_METIN)
            veritabani.kapat()
