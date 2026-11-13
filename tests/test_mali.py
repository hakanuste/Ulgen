import io
import unittest
import zipfile

from ulgen import ekler, mali
from tests.temel import TemizVeri

TABLO = """Kalem\t2025/9\t2024/9
Hasılat\t1.234.567\t1.000.000
Satışların Maliyeti\t(900.000)\t(750.000)
BRÜT KAR (ZARAR)\t334.567\t250.000
Esas Faaliyet Karı (Zararı)\t150.000\t120.000
DÖNEM KARI (ZARARI)\t100.000\t80.000
Ana Ortaklık Payları\t98.000\t79.000
Dönen Varlıklar\t500.000\t400.000
TOPLAM VARLIKLAR\t3.000.000\t2.500.000
Kısa Vadeli Yükümlülükler\t400.000\t350.000
Uzun Vadeli Yükümlülükler\t1.100.000\t1.000.000
Ana Ortaklığa Ait Özkaynaklar\t1.450.000\t1.100.000
"""


def xlsx(satirlar):
    """Asgari .xlsx (paylaşılan dizgeler + sayılar)."""
    ortak, xml_satir = [], []
    for r, satir in enumerate(satirlar, 1):
        hucre = []
        for deger in satir:
            if isinstance(deger, str):
                ortak.append(deger)
                hucre.append('<c t="s"><v>%d</v></c>' % (len(ortak) - 1))
            else:
                hucre.append('<c><v>%s</v></c>' % deger)
        xml_satir.append('<row r="%d">%s</row>' % (r, "".join(hucre)))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook %s><sheets><sheet name="Bilanço" '
                   'sheetId="1"/></sheets></workbook>' % ns)
        z.writestr("xl/sharedStrings.xml", "<sst %s>%s</sst>" % (
            ns, "".join("<si><t>%s</t></si>" % s for s in ortak)))
        z.writestr("xl/worksheets/sheet1.xml", "<worksheet %s><sheetData>%s"
                   "</sheetData></worksheet>" % (ns, "".join(xml_satir)))
    return b.getvalue()


class Mali(unittest.TestCase):

    def test_kalemler_ve_donemler(self):
        c = mali.coz(TABLO)
        self.assertEqual(c["donemler"], ["2025/9", "2024/9"])
        self.assertEqual(c["kalem"]["hasilat"], [1234567.0, 1000000.0])
        self.assertEqual(c["kalem"]["ana_net_kar"][0], 98000.0)
        self.assertNotIn("ozkaynak", c["kalem"])          # yalnız ana ortaklık

    def test_oranlar_kodda(self):
        o = mali.ozet(TABLO)
        self.assertIn("Net kâr marjı: %7,9", o)             # 98.000 / 1.234.567
        self.assertIn("Brüt kâr marjı: %27,1", o)
        self.assertIn("Borç / özkaynak: 1,03 kat", o)
        self.assertIn("Cari oran (dönen varlık / kısa vadeli borç): 1,25 kat", o)
        self.assertIn("önceki döneme, 2024/9, göre %23,5", o)

    def test_parantez_eksi_ve_sayi(self):
        self.assertEqual(mali.sayi_coz("(1.234)"), -1234.0)
        self.assertEqual(mali.sayi_coz("1.234.567,89"), 1234567.89)
        self.assertEqual(mali.sayi_coz("1234567.5"), 1234567.5)

    def test_kucuk_harf_ve_numarali_kalem(self):
        c = mali.coz("satış gelirleri\t500\t400\n1. a) Brüt kar\t100\t90\n"
                     "dönem net karı  50  40")
        self.assertEqual(c["kalem"]["hasilat"], [500.0, 400.0])
        self.assertEqual(c["kalem"]["brut_kar"], [100.0, 90.0])
        self.assertEqual(c["kalem"]["net_kar"], [50.0, 40.0])

    def test_kap_dipnot_sutunu_atlanir(self):
        c = mali.coz("Dipnot 2025/9 2024/9\nHasılat 5 1.234.567 1.000.000\n"
                     "Brüt Kar 334.567 250.000")
        self.assertEqual(c["kalem"]["hasilat"], [1234567.0, 1000000.0])

    def test_tablo_olmayan_metin(self):
        self.assertFalse(mali.tablo_mu("Bugün hava güzel. Hasılat kelimesi geçti."))


class EkExcel(TemizVeri):

    def test_xlsx_okunur_ve_oranlar_iletide(self):
        satirlar = [["Kalem", "2025/12", "2024/12"],
                    ["Hasılat", 2000, 1600], ["Brüt Kar", 500, 400],
                    ["Dönem Karı", 200, 120], ["Özkaynaklar", 1000, 800],
                    ["Kısa Vadeli Yükümlülükler", 300, 250]]
        veri = xlsx(satirlar)
        k = ekler.kaydet("bilanco.xlsx", io.BytesIO(veri), len(veri))
        metin, _ = ekler.metin_cikar(ekler.yol_bul(k))
        self.assertIn("## Sayfa: Bilanço", metin)
        self.assertIn("Hasılat\t2000\t1600", metin)
        m = ekler.iletiye_ekle("Bunu yorumla", [k])
        self.assertIn("[KODDA HESAPLANAN MALİ ORANLAR – dönem: 2025/12]", m)
        self.assertIn("Net kâr marjı: %10,0", m)

    def test_ekli_mali_ileti_akcaya_gider(self):
        from unittest import mock
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        m = "Yorumla\n\n" + mali.ozet(TABLO) + "\n\n[EKLİ DOSYA: b.xlsx]\n" + TABLO
        with mock.patch.object(u, "_beyinle_dene", return_value=("tamam", "Y", "sahte")):
            c = u.sohbet_isle(m)
        self.assertTrue(c["ajan"].startswith("AKÇA"))
