import os
import unittest

from .temel import TemizVeri
from ulgen import ayar, obsidyen, uzmanlar


class SahteArastirma:
    def arastir(self, sorgu):
        self.sorgu = sorgu
        return "KAYNAK 1: Örnek (https://ornek.org)\nBiberiye geleneksel..."


class Uzmanlar(TemizVeri):

    def test_yonlendirme(self):
        self.assertEqual(uzmanlar.sec("biberiye neye iyi gelir"), "OTACI")
        self.assertEqual(uzmanlar.sec("Musso şanzıman yağı"), "TULGA")
        self.assertEqual(uzmanlar.sec("kerpiç sıva nasıl yapılır"), "BALBAL")
        self.assertEqual(uzmanlar.sec("lifepo4 akü şarj"), "KÜN")
        self.assertIsNone(uzmanlar.sec("bugün hava nasıl"))

    def test_tum_uzmanlar_ve_liste(self):
        self.assertEqual(len(uzmanlar.UZMANLAR), 12)
        self.assertEqual(uzmanlar.sec("bitcoin ve borsa"), "AKÇA")
        self.assertEqual(uzmanlar.sec("tapu ve imar kanunu"), "YARGU")
        self.assertEqual(uzmanlar.sec("bağlama akort makam"), "KOPUZ")
        self.assertEqual(uzmanlar.sec("halay koreografi figür"), "OYUN")
        self.assertEqual(uzmanlar.sec("yangın alarm çit"), "ALPAGU")
        l = uzmanlar.liste()
        self.assertEqual(len(l["genel"]), 6)
        self.assertEqual(len(l["uzmanlar"]), 12)

    def test_istem_kurallari(self):
        m = uzmanlar.istem("biberiye hangi vitamini içerir")
        self.assertIn("OTACI", m)
        self.assertIn("Do NOT diagnose", m)
        self.assertIn("112", m)
        self.assertEqual(uzmanlar.istem("merhaba"), "")

    def test_bitki_notu_obsidyene_yazar(self):
        kasa = os.path.join(os.path.expanduser("~"), "Obsidyen")
        os.makedirs(os.path.join(kasa, ".obsidian"), exist_ok=True)
        self.addCleanup(__import__("shutil").rmtree, kasa, True)
        a = ayar.yukle()
        a["kasa"] = kasa
        import json
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)
        obsidyen._SON.update(zaman=0.0, sonuc=None)
        ar = SahteArastirma()
        sonuc = uzmanlar.bitki_notu("Biberiye", ar)
        self.assertIn("Biberiye", ar.sorgu)
        self.assertIn("112", sonuc)
        self.assertTrue(os.path.exists(os.path.join(
            kasa, "Ülgen", "Bitkiler", "Biberiye.md")))

    def test_bos_ad(self):
        with self.assertRaises(ValueError):
            uzmanlar.bitki_notu("  ", SahteArastirma())


if __name__ == "__main__":
    unittest.main()
