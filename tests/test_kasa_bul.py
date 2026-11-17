import os
import unittest
from unittest import mock

from ulgen import kasa_bul, metin_temizle
from tests.temel import TemizVeri


class Esles(unittest.TestCase):

    def test_bicimler(self):
        self.assertEqual(kasa_bul.esles("obsidyende taş ev ölçüleri bul"), "taş ev ölçüleri")
        self.assertEqual(kasa_bul.esles("Obsidyende ara: Musso şanzıman"), "Musso şanzıman")
        self.assertEqual(kasa_bul.esles("kasada kerpiç sıva ara"), "kerpiç sıva")
        self.assertEqual(kasa_bul.esles("obsidyende bu sohbeti bul"), "bu sohbeti")
        self.assertIsNone(kasa_bul.esles("obsidyen nedir?"))
        self.assertIsNone(kasa_bul.esles("taş ev ölçüleri ne?"))


class Bul(TemizVeri):

    def test_onceki_konu_ve_sonuc(self):
        with mock.patch.object(kasa_bul.obsidyen, "hazir_mi", return_value=True), \
                mock.patch.object(kasa_bul.obsidyen, "kasa_yolu", return_value="/k"), \
                mock.patch.object(kasa_bul.obsidyen, "ara", return_value=[
                    ("Taş ev sera", "/k/Yapay Zekâ Konuşmaları/2026-09-26 Taş ev.md",
                     "Taban 6,5 m × 6,5 m")]) as ara:
            y = kasa_bul.bul("bu sohbeti", "taş evin son ölçüleri nedir")
        ara.assert_called_once()
        self.assertEqual(ara.call_args[0][0], "taş evin son ölçüleri nedir")
        self.assertIn("## 1. Taş ev sera (2026-09-26)", y)
        self.assertIn("Yer: " + os.path.join("Yapay Zekâ Konuşmaları", "2026-09-26 Taş ev.md"), y)
        self.assertIn("buluta gönderilmedi", y)

    def test_sohbette_modelsiz(self):
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        u._kaydet("kullanici", "taş evin son ölçüleri nedir")
        u._kaydet("asistan", "...")
        with mock.patch.object(kasa_bul, "bul", return_value="SONUÇ") as bul, \
                mock.patch.object(u, "_beyinle_dene") as beyin:
            c = u.sohbet_isle("obsidyende bu sohbeti bul")
        beyin.assert_not_called()
        self.assertEqual(c["yanit"], "SONUÇ")
        self.assertEqual(bul.call_args[0][1], "taş evin son ölçüleri nedir")


class Sahne(unittest.TestCase):

    def test_sahne_anlatimi_atilir(self):
        y = metin_temizle.yabanci_harfleri_at(
            "*(Ülgen derin ve sakin bir nefes alır, ses tonu yumuşar.)*\nHakan, ölçüler şöyle.")
        self.assertEqual(y, "Hakan, ölçüler şöyle.")
