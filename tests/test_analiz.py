import json
import unittest

from .temel import TemizVeri
from ulgen import analiz, ayar, uzmanlar


def seri(n=260, adim=0.5, taban=100.0):
    return [("2026-01-%02d" % (1 + i % 28), taban + adim * i)
            for i in range(n)]


def sahte_indir(adres):
    cift = seri()
    return json.dumps({"chart": {"result": [{
        "timestamp": [1700000000 + 86400 * i for i in range(len(cift))],
        "indicators": {"quote": [{"close": [c for _, c in cift]}]},
        "meta": {}}]}})


class Analiz(TemizVeri):

    def test_gostergeler_yukselen_seri(self):
        g = analiz.gostergeler(seri())
        self.assertGreater(g["sma20"], g["sma50"])
        self.assertGreater(g["sma50"], g["sma200"])
        self.assertGreater(g["rsi"], 90)           # hep yükseliş
        self.assertAlmostEqual(g["dusus"], 0.0)
        self.assertGreater(g["g1y"], 0)

    def test_rsi_dusen_ve_sma(self):
        d = [100 - i * 0.3 for i in range(60)]
        self.assertLess(analiz.rsi(d), 5)
        self.assertEqual(analiz.sma([1, 2, 3, 4], 2), 3.5)
        self.assertIsNone(analiz.sma([1], 5))

    def test_sembol_bul(self):
        self.assertEqual(analiz.sembol_bul("THYAO")[0], "THYAO.IS")
        self.assertEqual(analiz.sembol_bul("ons altın")[0], "GC=F")
        with self.assertRaises(ValueError):
            analiz.sembol_bul("12")

    def test_rapor_emir_icermez(self):
        r = analiz.rapor("THYAO", sahte_indir)
        self.assertIn("Göstergeler", r)
        self.assertIn("finansal danışmanlık değildir", r)
        for yasak in ("AL ", "SAT ", "alın", "satın"):
            self.assertNotIn(yasak, r)

    def test_komut_hata_ve_eslesmeme(self):
        self.assertIsNone(analiz.komut("merhaba"))
        self.assertIn("anlaşılmadı", analiz.komut("analiz: 12"))


class KaynakKomutlari(TemizVeri):

    def setUp(self):
        super().setUp()
        from unittest import mock
        yama = mock.patch("ulgen.ajanlar.adres_guvenli_mi",
                          lambda a: "127.0.0.1" not in a)
        yama.start()
        self.addCleanup(yama.stop)

    def test_ekle_listele_sil(self):
        y = uzmanlar.komut("kaynak ekle: akça https://www.isyatirim.com.tr/x")
        self.assertIn("Eklendi", y)
        self.assertIn("isyatirim.com.tr", uzmanlar.guvenilir_kaynaklar("AKÇA"))
        self.assertIn("isyatirim", uzmanlar.komut("kaynaklar: AKÇA"))
        self.assertIn("zaten", uzmanlar.komut(
            "kaynak ekle: AKÇA https://www.isyatirim.com.tr/x"))
        self.assertIn("Çıkarıldı", uzmanlar.komut(
            "kaynak sil: AKÇA isyatirim.com.tr"))
        self.assertNotIn("isyatirim.com.tr",
                         uzmanlar.guvenilir_kaynaklar("AKÇA"))

    def test_gecersiz(self):
        self.assertIn("Biçim", uzmanlar.komut("kaynak ekle: AKÇA"))
        self.assertIn("güvenlik", uzmanlar.komut(
            "kaynak ekle: AKÇA http://127.0.0.1/x"))
        self.assertIsNone(uzmanlar.komut("merhaba"))
        self.assertIn("tanınmadı", uzmanlar.komut("kaynaklar: YOK"))
        ayar.yukle()


if __name__ == "__main__":
    unittest.main()
