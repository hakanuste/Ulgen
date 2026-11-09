import shutil
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

    def test_ek_almis_sozcuk_koku_bulur(self):
        self.yaz("Arac.md", "# Araç\nDaewoo Musso 3.2, 1998 model.")
        obsidyen.tara(zorla=True)
        sonuc = obsidyen.ara("benim aracım nedir")
        self.assertEqual(sonuc[0][0], "Arac")

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


class TamOkuma(unittest.TestCase):

    def test_notun_sonundaki_bilgi_alinir(self):
        from ulgen import obsidyen
        icerik = ("# Taş ev\n\n" + "\n\n".join(
            "Eski taslak paragrafı %d, ölçüler henüz belli değil. %s" % (i, "x" * 300)
            for i in range(30)) + "\n\nSon karar: taş ev ölçüleri 9x12 metre.")
        m = obsidyen.parcali_alinti(icerik, ["tas", "ev", "olculeri"])
        self.assertIn("9x12", m)
        self.assertIn("parça)", m)

    def test_eslesme_yoksa_bas(self):
        from ulgen import obsidyen
        self.assertTrue(obsidyen.parcali_alinti("kısa not", ["zzz"]).startswith("kısa"))


class EsAnlamVeSon(unittest.TestCase):
    """Örnek: Eylül'de konuşulan taş ev tablosu 'ölçü' yerine 'boyut/kot'
    sözcükleriyle yazılmış ve sohbetin sonunda; LaTeX ve kutu çizgileri var."""

    ICERIK = ("Taş ev planı: $6,5\\text{ m} \\times 6,5\\text{ m}$ ilk taslak.\n\n"
              "25 Eylül 2026\n\n" + "\n\n".join(
                  "Sera bitkileri, kekik ve biberiye yerleşimi %d. %s" % (i, "y" * 400)
                  for i in range(40)) +
              "\n\n26 Eylül 2026\n\n╔════╗\n║ MİMARİ YAPI BOYUT VE KOT ÇERÇEVESİ ║\n"
              "║ 1. ANA TAŞ EV ║\n║ • Taban Oturumu : 7,0 m × 7,0 m ║\n"
              "║ • Dış Duvar Kalınlığı : 40 cm ║\n║ • Toplam Mahya Kotu : 6,5 m ║\n╚════╝")

    def test_son_olculer_sondaki_tablodan(self):
        from ulgen import obsidyen as o
        m = o.parcali_alinti(self.ICERIK, o.KELIME.findall(o.normal(
            "taş evin son ölçüleri nedir")), 1500)
        self.assertIn("7,0 m × 7,0 m", m)
        self.assertIn("26 eylul 2026", m)
        self.assertNotIn("═", m)

    def test_latex_temizlenir_ve_kisa_kok(self):
        from ulgen import obsidyen as o
        self.assertIn("6,5 m × 6,5 m", o.gorunum_temizle("$6,5\\text{ m} \\times 6,5\\text{ m}$"))
        self.assertEqual(o.kok_bul("evin"), "ev")
        self.assertTrue(o.eslesir("ev", "tas evin olculeri"))
        self.assertFalse(o.eslesir("ev", "evet dedi"))
        self.assertIn("boyut", o.kokler(["olculeri"]))
