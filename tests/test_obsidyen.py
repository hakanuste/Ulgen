import os
import time
import unittest

from .temel import TemizVeri
from ulgen import ayar, obsidyen, veritabani


class Obsidyen(TemizVeri):

    def setUp(self):
        super().setUp()
        veritabani.kur()
        self.kasa = os.path.join(os.path.expanduser("~"), "Obsidyen")
        import shutil
        shutil.rmtree(self.kasa, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.kasa, True)
        os.makedirs(os.path.join(self.kasa, ".obsidian"))
        os.makedirs(os.path.join(self.kasa, "Bahçe"))
        import json
        a = ayar.yukle()
        a["kasa"] = self.kasa
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)
        obsidyen._SON.update(zaman=0.0, sonuc=None)

    def yaz(self, ad, icerik):
        yol = os.path.join(self.kasa, ad)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(icerik)
        return yol

    def test_tara_ara_ve_turkce_harfler(self):
        self.yaz("Bahçe/Zeytin.md", "# Zeytin budaması\nKışın ılık günde "
                 "budama yapılır. Biyokömür için dallar ayrılır.")
        self.yaz("Diger.md", "alakasız bir not")
        self.yaz(".obsidian/ayar.md", "zeytin gizli sistem dosyası")
        s = obsidyen.tara(zorla=True)
        self.assertEqual((s["yeni"], s["toplam"]), (2, 2))
        sonuc = obsidyen.ara("ZEYTİN budama nasıl")      # İ / ı eşleşir
        self.assertEqual(sonuc[0][0], "Zeytin")
        self.assertIn("Biyokömür", sonuc[0][2])
        self.assertEqual(obsidyen.ara("kantaron"), [])

    def test_artimli_degisen_ve_silinen(self):
        yol = self.yaz("a.md", "ilk içerik elma")
        obsidyen.tara(zorla=True)
        self.assertEqual(obsidyen.tara(zorla=True)["yeni"], 0)
        time.sleep(0.02)
        self.yaz("a.md", "yeni içerik armut ve daha uzun")
        self.assertEqual(obsidyen.tara(zorla=True)["guncel"], 1)
        self.assertTrue(obsidyen.ara("armut"))
        self.assertFalse(obsidyen.ara("elma"))
        os.remove(yol)
        self.assertEqual(obsidyen.tara(zorla=True)["silinen"], 1)
        self.assertFalse(obsidyen.ara("armut"))

    def test_kasaya_yazmaz_ve_pdf_okur(self):
        yol = self.yaz("b.md", "dokunulmamalı")
        once = os.stat(yol).st_mtime_ns
        obsidyen.tara(zorla=True)
        self.assertEqual(os.stat(yol).st_mtime_ns, once)
        self.assertEqual(sorted(os.listdir(self.kasa)),
                         [".obsidian", "Bahçe", "b.md"])
        try:
            from pypdf import PdfWriter
        except ImportError:
            self.skipTest("pypdf yok")
        w = PdfWriter()
        w.add_blank_page(200, 200)
        with open(os.path.join(self.kasa, "bos.pdf"), "wb") as f:
            w.write(f)
        self.assertEqual(obsidyen.tara(zorla=True)["hata"], 0)

    def test_kasa_yoksa_cokmez(self):
        import shutil
        shutil.rmtree(self.kasa)
        self.assertIn("yok", str(obsidyen.tara(zorla=True)["hata"]))
        self.assertEqual(obsidyen.ara("herhangi"), [])


if __name__ == "__main__":
    unittest.main()


class KasaBulmaTesti(TemizVeri):

    def test_ayarsiz_obsidian_kasasini_bulur(self):
        ev = os.path.expanduser("~")
        for temiz in ("Documents", "Obsidyen", "Obsidian"):
            shutil.rmtree(os.path.join(ev, temiz), ignore_errors=True)
        yol = os.path.join(ev, "Documents", "Notlarim")
        os.makedirs(os.path.join(yol, ".obsidian"))
        open(os.path.join(yol, "a.md"), "w").write("merhaba")
        self.assertEqual(obsidyen.kasa_yolu(), yol)
        tamam, ileti, adet = obsidyen.erisim_durumu()
        self.assertEqual((tamam, adet), (True, 1))

    def test_yok_ve_izin_hatasi_acik_yazilir(self):
        tamam, ileti, _ = obsidyen.erisim_durumu("/yok/boyle/klasor")
        self.assertFalse(tamam)
        self.assertIn("yok", ileti)
        yol = os.path.join(os.path.expanduser("~"), "Izinsiz")
        os.makedirs(yol)
        from unittest import mock
        with mock.patch("os.walk", side_effect=PermissionError):
            tamam, ileti, _ = obsidyen.erisim_durumu(yol)
        self.assertFalse(tamam)
        self.assertIn("Tam Disk Erişimi", ileti)
