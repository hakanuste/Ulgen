import unittest
from unittest import mock

from tests.temel import TemizVeri


class Yogunluk(TemizVeri):
    def _ulgen(self):
        from ulgen import cekirdek
        u = cekirdek.Ulgen()
        return cekirdek, u

    def test_503_yeniden_denenir_sonra_basarir(self):
        cekirdek, u = self._ulgen()
        from ulgen.beyin import BeyinHatasi
        beyin = mock.Mock(yerel=False, ad="gemini")
        cagri = {"n": 0}

        def yanitla(b, m):
            cagri["n"] += 1
            if cagri["n"] < 3:
                raise BeyinHatasi('HTTP 503: {"status": "UNAVAILABLE"}')
            return "tamam"
        with mock.patch.object(u, "_beyinle_yanitla", side_effect=yanitla), \
                mock.patch.object(cekirdek.iptal, "bekle") as bekle:
            self.assertEqual(u._yogunlukta_yinele(beyin, "x"), "tamam")
        self.assertEqual(cagri["n"], 3)
        self.assertEqual(bekle.call_count, 2)

    def test_baska_hata_hemen_yukselir(self):
        cekirdek, u = self._ulgen()
        from ulgen.beyin import BeyinHatasi
        beyin = mock.Mock(yerel=False, ad="gemini")
        with mock.patch.object(u, "_beyinle_yanitla",
                               side_effect=BeyinHatasi("HTTP 400: kötü")), \
                mock.patch.object(cekirdek.iptal, "bekle") as bekle:
            with self.assertRaises(BeyinHatasi):
                u._yogunlukta_yinele(beyin, "x")
        bekle.assert_not_called()

    def test_hata_ozeti_anlasilir(self):
        from ulgen import cekirdek
        from ulgen.beyin import BeyinHatasi
        m = cekirdek._hata_ozeti("Gemini", BeyinHatasi(
            'HTTP 503: {"message": "high demand"}'))
        self.assertIn("çok yoğun", m)
        self.assertNotIn("{", m)


if __name__ == "__main__":
    unittest.main()
