import io
import json
import os
import unittest
from unittest import mock

from ulgen import ekler, metin_temizle
from tests.temel import TemizVeri


def yukle(ad, veri):
    return ekler.kaydet(ad, io.BytesIO(veri), len(veri))


class Ekler(TemizVeri):

    def test_metin_ve_html_okunur(self):
        k = yukle("not.txt", "taş ev 9x12".encode())
        self.assertEqual(ekler.ozet(k)["karakter"], 11)
        h = yukle("sayfa.html", b"<html><head><style>p{}</style></head><body>"
                  b"<h1>Ba\xc5\x9fl\xc4\xb1k</h1><p>Bir <b>iki</b> \xc3\xbc\xc3\xa7</p>"
                  b"<script>x()</script></body></html>")
        metin, _ = ekler.metin_cikar(ekler.yol_bul(h))
        self.assertIn("# Başlık", metin)
        self.assertIn("Bir iki üç", metin)        # harf harf değil, sözcük olarak
        self.assertNotIn("x()", metin)

    def test_docx(self):
        b = io.BytesIO()
        import zipfile
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("word/document.xml",
                       "<w:document><w:p><w:t>Birinci</w:t></w:p>"
                       "<w:p><w:t>İkinci &amp; son</w:t></w:p></w:document>")
        k = yukle("rapor.docx", b.getvalue())
        metin, _ = ekler.metin_cikar(ekler.yol_bul(k))
        self.assertIn("İkinci & son", metin)

    def test_tur_ve_boyut_denetimi(self):
        with self.assertRaises(ekler.EkHatasi):
            yukle("zararli.exe", b"x")
        with self.assertRaises(ekler.EkHatasi):
            yukle("bos.txt", b"")
        with self.assertRaises(ekler.EkHatasi):
            ekler.yol_bul("../../etc/passwd")

    def test_resim_yazisi_yoksa_aciklama(self):
        k = yukle("foto.png", b"\x89PNG....")
        with mock.patch.object(ekler, "_resim", return_value=""):
            metin, aciklama = ekler.metin_cikar(ekler.yol_bul(k))
        self.assertEqual(metin, "")
        self.assertIn("resmin kendisini göremez", aciklama)

    def test_iletiye_ekle(self):
        k = yukle("not.md", ("a" * 20000).encode())
        m = ekler.iletiye_ekle("Bunu özetle", [k])
        self.assertTrue(m.startswith("Bunu özetle"))
        self.assertIn("[EKLİ DOSYA: not.md]", m)
        self.assertIn("kalanı sığmadı", m)
        self.assertLess(len(m), ekler.ILETI_SINIRI + 500)


class Sunucu(TemizVeri):

    def test_yukle_ve_sohbette_kullan(self):
        from ulgen import sunucu
        from ulgen.cekirdek import Ulgen
        from tests.test_sunucu import istek
        u = Ulgen()
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        d, g = istek(port, "/ek/yukle?ad=liste.txt", "POST", "kiler 3x4".encode(),
                     {"Content-Type": "application/octet-stream"})
        self.assertEqual(d, 200)
        kimlik = json.loads(g)["kimlik"]
        gelen = []
        with mock.patch.object(u, "sohbet_isle",
                               side_effect=lambda m: gelen.append(m) or
                               {"yanit": "tamam", "beyin": "sahte"}):
            d, g = istek(port, "/sohbet", "POST",
                         json.dumps({"metin": "ölçü ne?", "ekler": [kimlik]}).encode(),
                         {"Content-Type": "application/json"})
        self.assertEqual(d, 200)
        self.assertIn("kiler 3x4", gelen[0])
        d, _ = istek(port, "/ek/yukle?ad=a.exe", "POST", b"x",
                     {"Content-Type": "application/octet-stream"})
        self.assertEqual(d, 400)


class Temizleme(unittest.TestCase):

    def test_yabanci_harfler_atilir(self):
        m = metin_temizle.yabanci_harfleri_at("Biberiye 你好 A vitamini içerir�. Тест")
        self.assertEqual(m, "Biberiye A vitamini içerir. Тест")


class Latex(unittest.TestCase):

    def test_latex_duz_metne(self):
        m = metin_temizle.yabanci_harfleri_at(
            r"$6,5 \times 6,5\text{ m}$ taban, $40\text{ cm}$ duvar, \(84,5\text{ m}^2\)")
        self.assertEqual(m, "6,5 × 6,5 m taban, 40 cm duvar, 84,5 m²")


class Yuzde(unittest.TestCase):

    def test_yuzde_turkce_yazim(self):
        y = metin_temizle.yabanci_harfleri_at
        self.assertEqual(y("Getiri 13.3% oldu"), "Getiri %13,3 oldu")
        self.assertEqual(y("-2.3 % düştü"), "%-2,3 düştü")
        self.assertEqual(y("%25 zaten"), "%25 zaten")
        self.assertEqual(y("v1.5%x"), "v1.5%x")


class SesliSayi(unittest.TestCase):
    """Arayüzdeki sesliMetin/sayiYazi işlevleri node ile denenir (varsa)."""

    def test_sayilar_sozcukle_okunur(self):
        import shutil
        import subprocess
        import tempfile
        if not shutil.which("node"):
            self.skipTest("node yok")
        from ulgen import arayuz
        js = arayuz.BETIK
        i = js.index("function sayiYazi")
        j = js.index("\n}\n", js.index("function sesliMetin")) + 3
        kod = js[i:j] + ('\nconsole.log(sesliMetin("BIST 100, 11.842,82 puandan; '
                         '13.3% arttı; %-2,3"));')
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(kod)
        cikti = subprocess.run(["node", f.name], capture_output=True, text=True).stdout
        self.assertIn("BIST yüz, on bir bin sekiz yüz kırk iki virgül seksen iki", cikti)
        self.assertIn("yüzde on üç virgül üç", cikti)
        self.assertIn("yüzde eksi iki virgül üç", cikti)
