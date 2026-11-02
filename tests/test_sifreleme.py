import base64
import io
import json
import os
import sqlite3
import tarfile
import unittest

from .temel import TemizVeri
from ulgen import ayar, gizli, veritabani, yedek
from ulgen.cekirdek import Ulgen
from ulgen.hafiza import HafizaYoneticisi


class Sifreleme(TemizVeri):

    def test_gidis_donus(self):
        d = gizli.sifrele("merhaba Ülgen".encode())
        self.assertTrue(d.startswith(gizli.ONEK2))
        self.assertNotIn(b"merhaba", d)
        self.assertEqual(gizli.coz(d), "merhaba Ülgen".encode())

    def test_rastgele_nonce(self):
        self.assertNotEqual(gizli.sifrele(b"x"), gizli.sifrele(b"x"))

    def test_kurcalama_yakalanir(self):
        d = bytearray(gizli.sifrele(b"gizli veri"))
        d[-3] ^= 1
        with self.assertRaises(gizli.AnahtarYok):
            gizli.coz(bytes(d))

    def test_yanlis_anahtar(self):
        d = gizli.sifrele(b"gizli veri")
        os.remove(os.path.join(ayar.KLASOR, "bellek.anahtar"))
        with self.assertRaises(gizli.AnahtarYok):
            gizli.coz(d)

    def test_anahtar_uzunlugu_ve_izin(self):
        self.assertEqual(len(gizli.ana_anahtar()), 32)
        yol = os.path.join(ayar.KLASOR, "bellek.anahtar")
        self.assertEqual(oct(os.stat(yol).st_mode & 0o777), "0o600")

    def test_eski_fernet_okunur(self):
        from cryptography.fernet import Fernet
        k = base64.urlsafe_b64encode(gizli.ana_anahtar())
        self.assertEqual(gizli.coz(gizli.ONEK + Fernet(k).encrypt(b"eski")),
                         b"eski")

    def test_sirlar(self):
        gizli.sir_yaz("gemini", "AIza-deneme")
        gizli._SIR_ONBELLEK.clear()
        self.assertEqual(gizli.sir_oku("gemini"), "AIza-deneme")
        self.assertEqual(ayar.yukle()["gemini_anahtar"], "AIza-deneme")
        with open(os.path.join(ayar.KLASOR, "sirlar.bin"), "rb") as f:
            self.assertNotIn(b"AIza", f.read())


class HafizaSifreli(TemizVeri):

    def test_diskte_sifreli(self):
        h = HafizaYoneticisi(lambda: None)
        h.ekle("bilgi", "çok gizli bir bilgi")
        with open(ayar.HAFIZA_DOSYASI, "rb") as f:
            ham = f.read()
        self.assertTrue(ham.startswith(gizli.ONEK2))
        self.assertNotIn("gizli".encode(), ham)
        self.assertIn("çok gizli", h.metne_cevir())

    def test_duz_yazi_dosya_sifrelenir(self):
        with open(ayar.HAFIZA_DOSYASI, "w") as f:
            json.dump({"surum": 1, "saglik": {}, "ogeler": [
                {"kategori": "bilgi", "metin": "eski kayit", "tarih": "x",
                 "kaynak": "t"}]}, f)
        h = HafizaYoneticisi(lambda: None)
        self.assertIn("eski kayit", h.metne_cevir())
        with open(ayar.HAFIZA_DOSYASI, "rb") as f:
            self.assertTrue(f.read().startswith(gizli.ONEK2))

    def test_anahtar_kaybinda_veri_ezilmez(self):
        h = HafizaYoneticisi(lambda: None)
        h.ekle("bilgi", "önemli kayıt")
        os.remove(os.path.join(ayar.KLASOR, "bellek.anahtar"))
        h.ekle("bilgi", "yeni kayıt")   # eskisi .bozuk olarak saklanmalı
        self.assertTrue(os.path.exists(ayar.HAFIZA_DOSYASI + ".bozuk"))


class Yedek(TemizVeri):

    PAROLA = "dogru-parola-123"

    def hazirla(self):
        self.ulgen = Ulgen()
        self.ulgen.sohbet_isle("not al: yedek denemesi")
        self.ulgen.hafiza.ekle("bilgi", "yedeklenecek bilgi")
        gizli.sir_yaz("gemini", "GIZLI-API-ANAHTARI")
        a = json.load(open(ayar.AYAR_DOSYASI))
        a["gemini_anahtar"] = "AYARDAKI-ANAHTAR"
        json.dump(a, open(ayar.AYAR_DOSYASI, "w"))
        return os.path.join(ayar.EV, "deneme.ulgenyedek")

    def test_alma_ve_geri_yukleme(self):
        hedef = self.hazirla()
        yedek.al(hedef, self.PAROLA)
        ham = open(hedef, "rb").read()
        for yasak in (b"yedek denemesi", b"yedeklenecek", b"SQLite",
                      b"GIZLI-API", b"AYARDAKI"):
            self.assertNotIn(yasak, ham)
        # veriyi boz, sonra geri yükle
        veritabani.sorgu("DELETE FROM notlar")
        self.ulgen.hafiza.unut("yedeklenecek")
        onceki = yedek.geri_yukle(hedef, self.PAROLA)
        self.assertTrue(os.path.isdir(onceki))
        notlar = veritabani.sorgu("SELECT metin FROM notlar", (), True)
        self.assertEqual([n["metin"] for n in notlar], ["yedek denemesi"])
        self.assertEqual(Ulgen().hafiza.eslesen_sayisi("yedeklenecek"), 1)
        # bozulmuş önceki durum silinmedi, taşındı
        self.assertTrue(os.listdir(onceki))
        # API anahtarı yedeğe girmedi
        self.assertNotIn("AYARDAKI", open(ayar.AYAR_DOSYASI).read())

    def test_yanlis_parola(self):
        hedef = self.hazirla()
        yedek.al(hedef, self.PAROLA)
        with self.assertRaises(yedek.YedekHatasi):
            yedek.geri_yukle(hedef, "yanlis-parola-1")

    def test_kisa_parola(self):
        with self.assertRaises(yedek.YedekHatasi):
            yedek.al(os.path.join(ayar.EV, "k.yedek"), "kisa")

    def test_kurcalanmis_yedek(self):
        hedef = self.hazirla()
        yedek.al(hedef, self.PAROLA)
        ham = bytearray(open(hedef, "rb").read())
        ham[200] ^= 1
        open(hedef, "wb").write(bytes(ham))
        with self.assertRaises(yedek.YedekHatasi):
            yedek.dogrula(hedef, self.PAROLA)

    def test_bozuk_yedek_geri_yuklenmez_mevcut_veri_korunur(self):
        hedef = self.hazirla()
        yedek.al(hedef, self.PAROLA)
        ham = bytearray(open(hedef, "rb").read())
        ham[-1] ^= 1
        open(hedef, "wb").write(bytes(ham))
        with self.assertRaises(yedek.YedekHatasi):
            yedek.geri_yukle(hedef, self.PAROLA)
        self.assertEqual(len(veritabani.sorgu(
            "SELECT 1 FROM notlar", (), True)), 1)

    def test_yol_gecisi_saldirisi(self):
        self.hazirla()
        tampon = io.BytesIO()
        with tarfile.open(fileobj=tampon, mode="w:gz") as t:
            veri = b"kotu"
            bilgi = tarfile.TarInfo("../../kotu.txt")
            bilgi.size = len(veri)
            t.addfile(bilgi, io.BytesIO(veri))
        tuz = os.urandom(16)
        sifreli = gizli.aes_sifrele(yedek._anahtar(self.PAROLA, tuz),
                                    tampon.getvalue(), yedek.BASLIK)
        hedef = os.path.join(ayar.EV, "kotu.yedek")
        open(hedef, "wb").write(yedek.BASLIK + tuz + sifreli)
        with self.assertRaises(yedek.YedekHatasi):
            yedek.geri_yukle(hedef, self.PAROLA)
        self.assertFalse(os.path.exists(os.path.join(ayar.EV, "kotu.txt")))

    def test_yedek_bozuk_veritabani_yakalar(self):
        self.hazirla()
        import tempfile
        gecici = tempfile.mkdtemp()
        db = os.path.join(gecici, "veri.db")
        with open(db, "wb") as f:
            f.write(b"SQLite format 3\x00" + os.urandom(2000))
        tampon = io.BytesIO()
        with tarfile.open(fileobj=tampon, mode="w:gz") as t:
            t.add(db, arcname="veri.db")
        tuz = os.urandom(16)
        sifreli = gizli.aes_sifrele(yedek._anahtar(self.PAROLA, tuz),
                                    tampon.getvalue(), yedek.BASLIK)
        hedef = os.path.join(ayar.EV, "bozukdb.yedek")
        open(hedef, "wb").write(yedek.BASLIK + tuz + sifreli)
        with self.assertRaises((yedek.YedekHatasi, sqlite3.DatabaseError)):
            yedek.geri_yukle(hedef, self.PAROLA)
        self.assertEqual(len(veritabani.sorgu(
            "SELECT 1 FROM notlar", (), True)), 1)


if __name__ == "__main__":
    unittest.main()
