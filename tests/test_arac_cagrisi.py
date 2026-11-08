import unittest

from ulgen.cekirdek import arac_cagrisi_ayikla


class AracCagrisi(unittest.TestCase):

    def test_json_biçimi(self):
        self.assertEqual(
            arac_cagrisi_ayikla('{"arac": "kasa_ara", "parametreler": '
                                '{"sorgu": "araç"}}'),
            ("kasa_ara", {"sorgu": "araç"}))

    def test_etiketli_bicim(self):
        metin = ('<dots_function_call>\n<arac>dosya_ara</arac>\n'
                 '<parametreler>{"sorgu": "arac"}</param>\n'
                 '</dots_function_call>')
        self.assertEqual(arac_cagrisi_ayikla(metin),
                         ("dosya_ara", {"sorgu": "arac"}))

    def test_etiketli_bicim_bozuk_parametre(self):
        self.assertEqual(
            arac_cagrisi_ayikla("<arac>hafiza_ara</arac><parametreler>"
                                "{bozuk</parametreler>"),
            ("hafiza_ara", {}))

    def test_cagri_yoksa_none(self):
        self.assertIsNone(arac_cagrisi_ayikla("Merhaba, nasılsınız?"))


if __name__ == "__main__":
    unittest.main()
