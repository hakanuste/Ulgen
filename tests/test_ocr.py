"""Yerel OCR (gerçek tesseract varsa uçtan uca) ve Kitap Okuyucu."""

import json
import os
import shutil
import unittest

from .temel import TemizVeri
from ulgen import ajan_kayit, ayar, iptal, ocr


def _ocr_var():
    return ocr._bul("tesseract") is not None and "eng" in ocr.diller()


def _tarama_pdf(yol, sayfalar):
    """Yalnız resim içeren (taranmış gibi) PDF üretir."""
    from PIL import Image, ImageDraw, ImageFont
    resimler = []
    try:
        yazi = ImageFont.truetype("DejaVuSans.ttf", 48)
    except OSError:
        yazi = ImageFont.load_default()
    for satirlar in sayfalar:
        r = Image.new("RGB", (1240, 700), "white")
        d = ImageDraw.Draw(r)
        for i, s in enumerate(satirlar):
            d.text((60, 60 + i * 90), s, fill="black", font=yazi)
        resimler.append(r)
    resimler[0].save(yol, save_all=True, append_images=resimler[1:],
                     resolution=150.0)


class OcrTemel(TemizVeri):

    def setUp(self):
        super().setUp()
        self.kasa = os.path.join(os.path.expanduser("~"), "ObsidyenOcr")
        shutil.rmtree(self.kasa, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.kasa, True)
        os.makedirs(os.path.join(self.kasa, ".obsidian"))
        a = ayar.yukle()
        a["kasa"] = self.kasa
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)
        ajan_kayit.sifirla()

    def pdf(self, ad, sayfalar):
        yol = os.path.join(os.path.expanduser("~"), ad)
        self.addCleanup(lambda: os.path.exists(yol) and os.remove(yol))
        _tarama_pdf(yol, sayfalar)
        return yol

    def oku(self, yol):
        with open(os.path.join(self.kasa, yol), encoding="utf-8") as f:
            return f.read()


class SahteOcrTesti(OcrTemel):

    def test_sayfa_sayfa_yazar_ve_kaldigi_yerden_surer(self):
        yol = self.pdf("kitap1.pdf", [["bir"], ["iki"], ["uc"]])
        gelen = []

        def sahte(resim, dil):
            gelen.append(resim)
            return "sayfa metni %d\nsatır- \nsonu" % len(gelen)
        ilk = []
        ozet = ocr.isle(yol, ilk.append, tesseract=sahte)
        self.assertEqual(len(gelen), 3)
        self.assertIn("3 sayfa okundu (3'i OCR", ozet)
        self.assertEqual(len(ilk), 3)
        not_yolu = ozet.split("Not: ")[1].split(" ·")[0]
        ic = self.oku(not_yolu)
        self.assertIn("## Sayfa 1", ic)
        self.assertIn("## Sayfa 3", ic)
        self.assertIn("kaynak: \"kitap1.pdf\"", ic)
        # yeniden: tüm sayfalar kayıtlı, OCR çağrılmaz
        gelen.clear()
        ocr.isle(yol, tesseract=sahte)
        self.assertEqual(gelen, [])

    def test_iptal_sonrasi_devam(self):
        yol = self.pdf("kitap2.pdf", [["a"], ["b"], ["c"]])
        sayac = []

        def sahte(resim, dil):
            sayac.append(1)
            if len(sayac) == 2:
                iptal.ayarla()
            return "metin"
        iptal.temizle()
        with self.assertRaises(iptal.Iptal):
            ocr.isle(yol, tesseract=sahte)
        iptal.temizle()
        self.assertEqual(len(sayac), 2)
        ocr.isle(yol, tesseract=sahte)
        self.assertEqual(len(sayac), 3)      # yalnız 3. sayfa kaldı

    def test_uzun_kitap_bolumlere_ayrilir(self):
        sayfalar = [(i, "x" * 100) for i in range(1, 95)]
        notlar, uyari = ocr.notlari_yaz("Kitap", "k.pdf", sayfalar,
                                        "tur+eng", 94, 0)
        self.assertEqual(len(notlar), 4)        # dizin + 3 bölüm (40+40+14)
        self.assertEqual(uyari, "")
        self.assertIn("[[Kitap - Bölüm 01]]", self.oku(notlar[0]))

    def test_obsidyen_yoksa_yerel_kopya(self):
        shutil.rmtree(self.kasa)
        notlar, uyari = ocr.notlari_yaz("Kitap", "k.pdf", [(1, "metin")],
                                        "eng", 1, 0)
        self.assertIn("yerel klasöre kaydedildi", uyari)
        self.assertTrue(os.path.exists(notlar[0]))

    def test_yol_izinleri(self):
        ev = os.path.expanduser("~")
        with self.assertRaises(ocr.OcrHatasi):
            ocr.izinli_yol("/etc/passwd")
        with self.assertRaises(ocr.OcrHatasi):
            ocr.izinli_yol(os.path.join(ev, ".ssh", "x.pdf"))
        with self.assertRaises(ocr.OcrHatasi):
            ocr.izinli_yol(os.path.join(ayar.KLASOR, "ayar.json"))
        yol = ocr.yukle("a.pdf", __import__("io").BytesIO(b"%PDF-1"), 6)
        self.assertEqual(ocr.izinli_yol("a.pdf"), os.path.realpath(yol))

    def test_yukleme_kurallari(self):
        import io
        with self.assertRaises(ocr.OcrHatasi):
            ocr.yukle("virus.exe", io.BytesIO(b"x"), 1)
        with self.assertRaises(ocr.OcrHatasi):
            ocr.yukle("a.pdf", io.BytesIO(b"x"), 10)      # yarıda kesilir
        self.assertEqual(os.listdir(ocr.gelen_klasoru()), [])
        a = ocr.yukle("b.pdf", io.BytesIO(b"1234"), 4)
        b = ocr.yukle("b.pdf", io.BytesIO(b"1234"), 4)
        self.assertNotEqual(a, b)

    def test_ajan_gelen_klasorunu_isler(self):
        k = ocr.KitapAjani()
        self.assertIn("yeni dosya yok", k.isle(""))
        durum = ocr.durum()
        self.assertIn("kurulum", durum)

    def test_temizle(self):
        self.assertEqual(ocr.temizle("kitap-\nlık  \n\n\n\nson"), "kitaplık\n\nson")


@unittest.skipUnless(_ocr_var(), "tesseract kurulu değil")
class GercekOcrTesti(OcrTemel):

    def test_taranmis_pdf_gercekten_okunur(self):
        yol = self.pdf("tarama.pdf", [["Hello world book"], ["Second page text"]])
        ozet = ocr.isle(yol)
        self.assertIn("2 sayfa okundu (2'i OCR", ozet)
        ic = self.oku(ozet.split("Not: ")[1].split(" ·")[0]).lower()
        self.assertIn("hello world", ic)
        self.assertIn("second page", ic)


class SunucuUcTesti(OcrTemel):

    def setUp(self):
        super().setUp()
        from ulgen import sunucu
        from ulgen.cekirdek import Ulgen
        self.u = Ulgen()
        self.srv = sunucu.yerel_sunucu(self.u, 0)
        sunucu.arka_planda_calistir(self.srv)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_yukle_durum_ve_ajan(self):
        import time
        from .test_sunucu import istek
        d, g = istek(self.port, "/ocr/durum")
        self.assertEqual(d, 200)
        self.assertIn("kurulum", json.loads(g))
        ham = open(self.pdf("yukle.pdf", [["Upload test page"]]), "rb").read()
        d, g = istek(self.port, "/kitap/yukle?ad=Kitabim.pdf", "POST", ham,
                     {"Content-Type": "application/octet-stream"})
        self.assertEqual((d, json.loads(g)["ad"]), (200, "Kitabim.pdf"))
        d, _ = istek(self.port, "/kitap/yukle?ad=zararli.exe", "POST", b"x",
                     {"Content-Type": "application/octet-stream"})
        self.assertEqual(d, 400)
        d, _ = istek(self.port, "/kitap/yukle?ad=a.pdf", "POST", b"x",
                     {"Content-Type": "application/octet-stream"},
                     yetkisiz=True)
        self.assertEqual(d, 401)
        d, g = istek(self.port, "/ajanlar/calistir", "POST",
                     json.dumps({"id": "kitap", "girdi": ""}),
                     {"Content-Type": "application/json"})
        self.assertEqual(d, 202)
        for _ in range(100):
            k = [x for x in ajan_kayit.liste() if x["id"] == "kitap"][0]
            if k["durum"] != "calisiyor" and k["sayac"]:
                break
            time.sleep(0.2)
        self.assertEqual(k["sayac"], 1)
        if _ocr_var():
            self.assertIn("1 sayfa okundu", k["ozet"] + k["hata"])

    def test_uzun_gorev_kabul_edilir(self):
        from .test_sunucu import istek
        verilen = []
        self.u.arastirma.arastir = lambda q: verilen.append(q) or "ok"
        d, _ = istek(self.port, "/ajanlar/calistir", "POST",
                     json.dumps({"id": "arastirma", "girdi": "x" * 5000}),
                     {"Content-Type": "application/json"})
        self.assertEqual(d, 202)
        import time
        for _ in range(50):
            if verilen:
                break
            time.sleep(0.1)
        self.assertEqual(len(verilen[0]), 5000)     # 300'e kesilmedi
