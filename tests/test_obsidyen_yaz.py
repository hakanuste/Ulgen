"""Obsidian'a güvenli yazma: yalnız Ülgen/ klasörü, üzerine yazma yok."""

import json
import os
import shutil

from .temel import TemizVeri
from ulgen import ayar, obsidyen_yaz


class YazTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.kasa = os.path.join(os.path.expanduser("~"), "ObsidyenYaz")
        shutil.rmtree(self.kasa, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.kasa, True)
        os.makedirs(os.path.join(self.kasa, ".obsidian"))
        self.ayarla(kasa=self.kasa)

    def ayarla(self, **alan):
        a = ayar.yukle()
        a.update(alan)
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)

    def test_yazar_ve_onbilgi_ekler(self):
        g = obsidyen_yaz.yaz("Kitaplar", "Orhun Yazıtları", "metin")
        self.assertEqual(g, os.path.join("Ülgen", "Kitaplar", "Orhun Yazıtları.md"))
        with open(os.path.join(self.kasa, g), encoding="utf-8") as f:
            ic = f.read()
        self.assertIn("ulgen: true", ic[:200])
        self.assertTrue(ic.rstrip().endswith("metin"))

    def test_kullanicinin_notuna_dokunmaz(self):
        os.makedirs(os.path.join(self.kasa, "Ülgen"))
        kendi = os.path.join(self.kasa, "Ülgen", "Not.md")
        with open(kendi, "w", encoding="utf-8") as f:
            f.write("benim notum")
        g = obsidyen_yaz.yaz("", "Not", "yeni")
        self.assertEqual(os.path.basename(g), "Not (2).md")
        with open(kendi, encoding="utf-8") as f:
            self.assertEqual(f.read(), "benim notum")

    def test_kendi_notunu_gunceller(self):
        a = obsidyen_yaz.yaz("A", "N", "bir")
        b = obsidyen_yaz.yaz("A", "N", "iki")
        self.assertEqual(a, b)
        with open(os.path.join(self.kasa, b), encoding="utf-8") as f:
            self.assertIn("iki", f.read())

    def test_yol_kacisi_engellenir(self):
        g = obsidyen_yaz.yaz("../../Disari", "../../etc/passwd", "x")
        self.assertTrue(g.startswith("Ülgen" + os.sep))
        self.assertNotIn("..", g)
        self.assertFalse(os.path.exists(os.path.join(self.kasa, "..", "Disari")))

    def test_symlink_kacisi_engellenir(self):
        dis = os.path.join(os.path.expanduser("~"), "ObsidyenDis")
        os.makedirs(dis, exist_ok=True)
        self.addCleanup(shutil.rmtree, dis, True)
        os.makedirs(os.path.join(self.kasa, "Ülgen"))
        os.symlink(dis, os.path.join(self.kasa, "Ülgen", "Kacis"))
        with self.assertRaises(obsidyen_yaz.YazmaHatasi):
            obsidyen_yaz.yaz("Kacis", "n", "x")
        self.assertEqual(os.listdir(dis), [])

    def test_kapali_ve_kasa_yok(self):
        self.ayarla(obsidyen_yazma=False)
        with self.assertRaises(obsidyen_yaz.YazmaHatasi):
            obsidyen_yaz.yaz("A", "n", "x")
        self.ayarla(obsidyen_yazma=True, kasa=os.path.join(self.kasa, "yok"))
        with self.assertRaises(obsidyen_yaz.YazmaHatasi):
            obsidyen_yaz.yaz("A", "n", "x")

    def test_buyuk_not_reddedilir_ve_ad_temizlenir(self):
        with self.assertRaises(obsidyen_yaz.YazmaHatasi):
            obsidyen_yaz.yaz("A", "n", "x" * (obsidyen_yaz.AZAMI_BAYT + 1))
        self.assertEqual(obsidyen_yaz.guvenli_ad('a/b:c*d?e#f[g]'), "a b c d e f g")
        self.assertEqual(obsidyen_yaz.guvenli_ad("..."), "not")
