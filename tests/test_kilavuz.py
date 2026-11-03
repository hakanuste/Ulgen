"""Kılavuz klasöründen Obsidian kasasına artımlı aktarım."""

import json
import os
import tempfile
import time

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import ayar, kilavuz, sunucu
from ulgen.cekirdek import Ulgen


def pdf_yap(yol, sayfalar):
    """Her sayfada bir metin satırı olan, pypdf'in okuyabileceği küçük PDF."""
    nesneler = []
    n = len(sayfalar)
    nesneler.append("<< /Type /Catalog /Pages 2 0 R >>")
    nesneler.append("<< /Type /Pages /Kids [%s] /Count %d >>" % (
        " ".join("%d 0 R" % (4 + 2 * i) for i in range(n)), n))
    nesneler.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, metin in enumerate(sayfalar):
        icerik = "BT /F1 12 Tf 72 720 Td (%s) Tj ET" % metin
        nesneler.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                        "/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (5 + 2 * i))
        nesneler.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(icerik), icerik))
    cikti, konumlar = b"%PDF-1.4\n", []
    for i, o in enumerate(nesneler, 1):
        konumlar.append(len(cikti))
        cikti += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("latin-1")
    xref = len(cikti)
    cikti += ("xref\n0 %d\n0000000000 65535 f \n" % (len(nesneler) + 1)).encode()
    for k in konumlar:
        cikti += ("%010d 00000 n \n" % k).encode()
    cikti += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(nesneler) + 1, xref)).encode()
    with open(yol, "wb") as f:
        f.write(cikti)


class KilavuzTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.kaynak = tempfile.mkdtemp()
        self.kasa = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.kasa, ".obsidian"))

    def test_pdf_parcalanir_dizin_yazilir_ve_artimli(self):
        pdf_yap(os.path.join(self.kaynak, "musso vakum.pdf"),
                ["Sayfa bir vakum hortumu"] * 120)          # 3 parça (50+50+20)
        with open(os.path.join(self.kaynak, "not.txt"), "w") as f:
            f.write("düz metin")
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["hata"]), (2, []))
        klasor = os.path.join(self.kasa, "musso vakum")
        self.assertEqual(sorted(os.listdir(klasor)), [
            "musso vakum - Dizin.md", "musso vakum - Sayfa 1-50.md",
            "musso vakum - Sayfa 101-120.md", "musso vakum - Sayfa 51-100.md"])
        dizin = open(os.path.join(klasor, "musso vakum - Dizin.md"), encoding="utf-8").read()
        self.assertIn("Toplam sayfa: 120", dizin)
        self.assertIn("[[musso vakum - Sayfa 51-100]]", dizin)
        self.assertIn("vakum hortumu", open(os.path.join(
            klasor, "musso vakum - Sayfa 1-50.md"), encoding="utf-8").read())
        self.assertTrue(os.path.isfile(os.path.join(self.kasa, "not.txt")))
        # ikinci çalıştırma: yeni bir şey yok
        self.assertEqual(kilavuz.aktar(self.kaynak, self.kasa)["yeni"], 0)
        # yeni dosya eklenince yalnız o aktarılır
        pdf_yap(os.path.join(self.kaynak, "transfercase.pdf"), ["transfer kutusu"] * 3)
        self.assertEqual(len(kilavuz.bekleyenler(self.kaynak)), 1)
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual(s["yeni"], 1)
        self.assertTrue(os.path.isfile(os.path.join(
            self.kasa, "transfercase", "transfercase - Dizin.md")))

    def test_degisen_dosya_yeniden_aktarilir(self):
        yol = os.path.join(self.kaynak, "a.pdf")
        pdf_yap(yol, ["eski metin"])
        kilavuz.aktar(self.kaynak, self.kasa)
        time.sleep(0.05)
        pdf_yap(yol, ["yeni metin", "ikinci sayfa"])
        os.utime(yol, (time.time() + 5, time.time() + 5))
        self.assertEqual(kilavuz.aktar(self.kaynak, self.kasa)["yeni"], 1)
        icerik = open(os.path.join(self.kasa, "a", "a - Sayfa 1-2.md"), encoding="utf-8").read()
        self.assertIn("yeni metin", icerik)

    def test_eski_aractan_aktarilan_yeniden_yazilmaz(self):
        os.makedirs(os.path.join(self.kasa, "b"))
        with open(os.path.join(self.kasa, "b", "b - Dizin.md"), "w") as f:
            f.write("ESKI ARAC")
        pdf_yap(os.path.join(self.kaynak, "b.pdf"), ["metin"])
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["atlanan"]), (0, 1))
        self.assertEqual(open(os.path.join(self.kasa, "b", "b - Dizin.md")).read(), "ESKI ARAC")

    def test_bozuk_pdf_digerlerini_durdurmaz_ve_klasor_yoksa_hata(self):
        with open(os.path.join(self.kaynak, "bozuk.pdf"), "wb") as f:
            f.write(b"pdf degil")
        pdf_yap(os.path.join(self.kaynak, "iyi.pdf"), ["iyi metin"])
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual(s["yeni"], 1)
        self.assertEqual(len(s["hata"]), 1)
        self.assertIn("Kılavuz klasörü yok", kilavuz.aktar("/yok/klasor", self.kasa)["hata"][0])
        self.assertIn("kasası yok", kilavuz.aktar(self.kaynak, "/yok/kasa")["hata"][0])

    def test_dosya_adi_temizligi_ve_kasa_disina_yazmaz(self):
        self.assertNotIn("/", kilavuz.dosya_adi_temizle("../../etc/passwd"))
        self.assertEqual(kilavuz.dosya_adi_temizle("a:b*c?"), "a b c")

    def test_klasor_bulma_ve_http(self):
        ev = tempfile.mkdtemp()
        os.makedirs(os.path.join(ev, "Documents", "Klavuzlar"))
        eski = os.environ.get("HOME")
        os.environ["HOME"] = ev
        self.addCleanup(lambda: os.environ.__setitem__("HOME", eski))
        self.assertTrue(kilavuz.klasor_bul().endswith("Documents/Klavuzlar"))
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        k, h = istek(p, "/kilavuz/durum")
        self.assertEqual((k, json.loads(h)["klasor_var"]), (200, True))
        self.assertEqual(istek(p, "/kilavuz/ayar", "POST", json.dumps({"klasor": "/yok/yer"}), JSON)[0], 400)
        k, h = istek(p, "/kilavuz/ayar", "POST", json.dumps({"otomatik": False}), JSON)
        self.assertFalse(ayar.yukle()["kilavuz_otomatik"])
        srv.yerel = False
        self.assertEqual(istek(p, "/kilavuz/durum")[0], 403)
        self.assertEqual(istek(p, "/kilavuz/aktar", "POST", json.dumps({}), JSON)[0], 403)


class KilavuzIcerikTesti(TemizVeri):
    """Uzantısı .pdf ama içeriği Word/zip olan dosyalar."""

    def setUp(self):
        super().setUp()
        self.kaynak = tempfile.mkdtemp()
        self.kasa = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.kasa, ".obsidian"))

    def _docx(self, yol, metin):
        import zipfile
        with zipfile.ZipFile(yol, "w") as z:
            z.writestr("word/document.xml",
                       "<w:document><w:p><w:t>%s</w:t></w:p></w:document>" % metin)

    def test_pdf_adli_docx_okunur(self):
        self._docx(os.path.join(self.kaynak, "motor.pdf"), "Yağ değişimi &amp; filtre")
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["hata"]), (1, []))
        not_ = open(os.path.join(self.kasa, "motor", "motor - Bölüm 1.md"),
                    encoding="utf-8").read()
        self.assertIn("Yağ değişimi & filtre", not_)

    def test_bozuk_dosya_bir_kez_bildirilir_tekrar_denenmez(self):
        import zipfile
        with zipfile.ZipFile(os.path.join(self.kaynak, "resimler.pdf"), "w") as z:
            z.writestr("a.png", "x")
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual(len(s["hata"]), 1)
        self.assertIn("resimler.pdf", s["hata"][0])
        self.assertEqual(kilavuz.bekleyenler(self.kaynak), [])


class KilavuzHtmlTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.kaynak = tempfile.mkdtemp()
        self.kasa = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.kasa, ".obsidian"))

    def test_chatgpt_dokumu_konusma_basina_not(self):
        veri = [{"title": "Zeytin budama", "create_time": 1760000000, "current_node": "c",
                 "mapping": {
                     "a": {"parent": None, "message": None},
                     "b": {"parent": "a", "message": {"author": {"role": "user"},
                                                      "content": {"parts": ["Ne zaman budamalı?"]}}},
                     "c": {"parent": "b", "message": {"author": {"role": "assistant"},
                                                      "content": {"parts": ["Şubat sonu uygundur."]}}}}}]
        html = "<html><script>var jsonData = %s;</script></html>" % json.dumps(veri)
        with open(os.path.join(self.kaynak, "chat.html"), "w", encoding="utf-8") as f:
            f.write(html)
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["hata"]), (1, []))
        klasor = os.path.join(self.kasa, "Yapay Zekâ Konuşmaları", "ChatGPT")
        dosyalar = os.listdir(klasor)
        self.assertEqual(len(dosyalar), 1)
        t = open(os.path.join(klasor, dosyalar[0]), encoding="utf-8").read()
        self.assertIn("## Ben", t)
        self.assertIn("Ne zaman budamalı?", t)
        self.assertIn("Şubat sonu uygundur.", t)

    def test_genel_html_metne_cevrilir_betik_atilir(self):
        html = ("<html><head><title>x</title><style>p{}</style></head><body>"
                "<script>gizli()</script><h2>Başlık</h2><p>Merhaba <b>dünya</b></p>"
                "<ul><li>bir</li><li>iki</li></ul><pre>kod satırı</pre></body></html>")
        with open(os.path.join(self.kaynak, "gemini.html"), "w", encoding="utf-8") as f:
            f.write(html)
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["hata"]), (1, []))
        t = open(os.path.join(self.kasa, "Yapay Zekâ Konuşmaları", "gemini",
                              "gemini - Bölüm 1.md"), encoding="utf-8").read()
        self.assertIn("## Başlık", t)
        self.assertIn("Merhaba dünya", t)
        self.assertIn("- bir", t)
        self.assertIn("kod satırı", t)
        self.assertNotIn("gizli", t)


class KilavuzKmlTesti(TemizVeri):

    KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>Zeytinlik</name>
<description>Deneme <b>parsel</b></description><Polygon><outerBoundaryIs><LinearRing>
<coordinates>%s</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
</Document></kml>"""

    def setUp(self):
        super().setUp()
        self.kaynak = tempfile.mkdtemp()
        self.kasa = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.kasa, ".obsidian"))

    @staticmethod
    def _kare(en=37.85, bo=27.80, kenar=100.0):
        import math
        d_en = kenar / 111195.0
        d_bo = kenar / (111195.0 * math.cos(math.radians(en)))
        n = [(bo, en), (bo + d_bo, en), (bo + d_bo, en + d_en), (bo, en + d_en), (bo, en)]
        return " ".join("%.8f,%.8f,0" % x for x in n)

    def test_alan_olcumu_dogru(self):
        k = kilavuz._koordinatlar(self._kare())
        alan, cevre, merkez = kilavuz.alan_olc(k)
        self.assertAlmostEqual(alan, 10000, delta=60)
        self.assertAlmostEqual(cevre, 400, delta=2)
        self.assertAlmostEqual(merkez[0], 37.85 + 50 / 111195.0, places=4)

    def test_kml_notu_yazilir(self):
        with open(os.path.join(self.kaynak, "arsa.kml"), "w", encoding="utf-8") as f:
            f.write(self.KML % self._kare())
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["hata"]), (1, []))
        t = open(os.path.join(self.kasa, "Arazi", "arsa.md"), encoding="utf-8").read()
        self.assertIn("## Zeytinlik", t)
        self.assertIn("m²", t)
        self.assertIn("tags: [arazi]", t)

    def test_kmz_okunur(self):
        import zipfile
        with zipfile.ZipFile(os.path.join(self.kaynak, "arsa.kmz"), "w") as z:
            z.writestr("doc.kml", self.KML % self._kare())
        s = kilavuz.aktar(self.kaynak, self.kasa)
        self.assertEqual((s["yeni"], s["hata"]), (1, []))
        self.assertTrue(os.path.isfile(os.path.join(self.kasa, "Arazi", "arsa.md")))
