"""Gelişmiş hafıza: kaynak, güven, eskime, çelişki, düzeltme, projeler, gizlilik."""

import os

from tests.temel import TemizVeri
from ulgen import ayar
from ulgen.hafiza import HafizaYoneticisi, benzerlik


class HafizaTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.h = HafizaYoneticisi(lambda: None)

    def test_kullanici_bilgisi_kaynak_ve_guven(self):
        kimlik = self.h.ekle("bilgi", "Zeytinliğim Koçarlı'da", "kullanici")
        oge = self.h.goster(kimlik)
        self.assertEqual(oge["kaynak"], "kullanici")
        self.assertEqual(oge["guven"], 1.0)

    def test_cikarim_dusuk_guvenli_ve_etiketli(self):
        kimlik = self.h.ekle("bilgi", "Kahveyi sever", "cikarim")
        oge = self.h.goster(kimlik)
        self.assertLess(oge["guven"], 1.0)
        self.assertIn("ÇIKARIM", self.h.etiket(oge))

    def test_ayni_bilgi_tekrar_eklenmez(self):
        self.assertTrue(self.h.ekle("bilgi", "Dans eğitmeniyim", "kullanici"))
        self.assertIsNone(self.h.ekle("bilgi", "Dans eğitmeniyim", "kullanici"))

    def test_kullanici_bilgisi_eskisini_eskitir_silmez(self):
        a = self.h.ekle("bilgi", "Arsa yüzölçümü 1500 metrekare zeytinlik", "kullanici")
        b = self.h.ekle("bilgi", "Arsa yüzölçümü 1509 metrekare zeytinlik", "kullanici")
        self.assertEqual(self.h.goster(a)["durum"], "eskimis")
        self.assertEqual(self.h.goster(a)["yerine"], b)
        self.assertEqual(self.h.goster(b)["durum"], "gecerli")
        self.assertIn(a, self.h.goster(b)["oncekiler"])

    def test_cikarim_kullanici_bilgisinin_yerine_gecmez(self):
        a = self.h.ekle("bilgi", "Arsa yüzölçümü 1509 metrekare zeytinlik", "kullanici")
        b = self.h.ekle("bilgi", "Arsa yüzölçümü 900 metrekare zeytinlik", "cikarim")
        self.assertEqual(self.h.goster(a)["durum"], "gecerli")
        self.assertEqual(self.h.goster(b)["durum"], "celiski")
        self.assertIn(b, [o["id"] for o in self.h.celiskiler()])

    def test_teyit_celiskiyi_cozer(self):
        a = self.h.ekle("bilgi", "Arsa yüzölçümü 1509 metrekare zeytinlik", "kullanici")
        b = self.h.ekle("bilgi", "Arsa yüzölçümü 900 metrekare zeytinlik", "cikarim")
        self.assertTrue(self.h.teyit(b))
        self.assertEqual(self.h.goster(b)["durum"], "gecerli")
        self.assertEqual(self.h.goster(a)["durum"], "eskimis")

    def test_duzeltme_gecmisi_korur(self):
        a = self.h.ekle("bilgi", "Aracım Musso 2000 model", "kullanici")
        b = self.h.duzelt(a, "Aracım Musso 1998 model", "yanlış yıl")
        self.assertEqual(self.h.goster(a)["durum"], "eskimis")
        self.assertEqual(self.h.goster(b)["metin"], "Aracım Musso 1998 model")
        self.assertEqual(self.h.goster(b)["kaynak"], "kullanici")
        self.assertIsNone(self.h.duzelt("999", "olmayan kayıt"))

    def test_proje_takma_adlari(self):
        self.h.proje_ekle("TILSIM", ["tılsım", "tilsim"])
        self.assertEqual(self.h.projeleri_bul("tılsım için karar"), ["TILSIM"])
        self.h.ekle("karar", "Veri tabanı SQLite olacak", "kullanici", "TILSIM")
        self.assertEqual(len(self.h.liste(proje="TILSIM", kategori="karar")), 1)

    def test_duyarli_bilgi_ayri_depoda(self):
        kimlik = self.h.ekle("bilgi", "Tansiyon ilacı kullanıyorum", "kullanici",
                             duyarli=True)
        self.assertTrue(kimlik.startswith("h"))
        self.assertTrue(os.path.exists(ayar.HASSAS_DOSYASI))
        bulut = self.h.metne_cevir(metin_ipucu="tansiyon", duyarli_dahil=False)
        self.assertNotIn("Tansiyon", bulut)
        yerel = self.h.metne_cevir(metin_ipucu="tansiyon", duyarli_dahil=True)
        self.assertIn("Tansiyon", yerel)

    def test_arama_duyarliyi_bulutta_gizler(self):
        self.h.ekle("bilgi", "Tansiyon ilacı kullanıyorum", "kullanici",
                    duyarli=True)
        self.assertEqual(self.h.ara("tansiyon", duyarli_dahil=False), [])
        self.assertTrue(self.h.ara("tansiyon", duyarli_dahil=True))

    def test_disk_sifreli(self):
        self.h.ekle("bilgi", "Gizli deneme cümlesi zeytin", "kullanici")
        with open(ayar.HAFIZA_DOSYASI, "rb") as f:
            ham = f.read()
        self.assertNotIn(b"zeytin", ham)

    def test_unut_siler(self):
        self.h.ekle("bilgi", "Silinecek benzersiz bilgi", "kullanici")
        self.assertEqual(self.h.eslesen_sayisi("benzersiz"), 1)
        self.h.unut("benzersiz")
        self.assertEqual(self.h.eslesen_sayisi("benzersiz"), 0)

    def test_benzerlik(self):
        self.assertGreaterEqual(benzerlik("arsa 1509 metrekare", "arsa 1500 metrekare"), 0.5)
        self.assertLess(benzerlik("zeytin budama", "kamera radar"), 0.2)


class AracKapisiTesti(TemizVeri):
    """Bulut beyin kullanılırken kişisel araçlar çalışmaz."""

    def setUp(self):
        super().setUp()
        from ulgen.cekirdek import Ulgen
        self.u = Ulgen()

    def test_bulutta_kisisel_arac_reddedilir(self):
        self.u.hafiza.ekle("bilgi", "Özel not zeytin", "kullanici")
        self.u.araclar.bulut_modu = True
        sonuc = self.u.araclar.calistir("hafiza_ara", {"sorgu": "zeytin"})
        self.assertIn("bulut", sonuc.lower())
        self.assertNotIn("Özel not", sonuc)

    def test_yerelde_kisisel_arac_calisir(self):
        self.u.hafiza.ekle("bilgi", "Özel not zeytin", "kullanici")
        self.u.araclar.bulut_modu = False
        sonuc = self.u.araclar.calistir("hafiza_ara", {"sorgu": "zeytin"})
        self.assertIn("Özel not", sonuc)
        self.assertTrue(self.u.araclar.kisisel_kullanildi)

    def test_hizli_komutlar(self):
        yanit, _ = self.u.sohbet_isle("karar (TILSIM): Veritabanı SQLite olacak"), None
        self.assertIn("Kaydettim", yanit["yanit"])
        self.assertEqual(len(self.u.hafiza.liste(kategori="karar")), 1)
        self.assertIn("SQLite", self.u.sohbet_isle("tılsım kararları")["yanit"])
