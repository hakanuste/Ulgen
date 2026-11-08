import json
import unittest

from ulgen import piyasa

TCMB_XML = """<?xml version="1.0"?>
<Tarih_Date Tarih="06.11.2026" Date="11/06/2026">
<Currency Kod="USD" CurrencyCode="USD"><Isim>ABD DOLARI</Isim>
<ForexBuying>42.1000</ForexBuying><ForexSelling>42.1500</ForexSelling>
</Currency>
<Currency Kod="EUR" CurrencyCode="EUR"><Isim>EURO</Isim>
<ForexBuying>46.0000</ForexBuying><ForexSelling>46.0500</ForexSelling>
</Currency></Tarih_Date>"""


def sahte(adres):
    if "tcmb" in adres:
        return TCMB_XML
    sembol = adres.split("/chart/")[1].split("?")[0]
    fiyat = {"XU100.IS": 10500.5, "GC=F": 4000.0}.get(sembol, 1.0)
    return json.dumps({"chart": {"result": [{"meta": {
        "regularMarketPrice": fiyat, "chartPreviousClose": fiyat / 1.01,
        "regularMarketTime": 1762446000, "currency": "USD"}}]}})


class Piyasa(unittest.TestCase):

    def test_kur(self):
        m = piyasa.sorgula("bugün dolar kaç TL", sahte)
        self.assertIn("USD/TL", m)
        self.assertIn("42,1500", m)
        self.assertIn("06.11.2026", m)
        self.assertNotIn("EUR/TL", m)

    def test_borsa(self):
        m = piyasa.sorgula("türkiye'deki borsa", sahte)
        self.assertIn("BIST 100", m)
        self.assertIn("10.500,50", m)
        self.assertIn("Yahoo Finance", m)

    def test_gram_altin_hesap_etiketli(self):
        m = piyasa.sorgula("gram altın", sahte)
        self.assertIn("HESAPLAMA", m)

    def test_hata_acikca_soylenir(self):
        def bozuk(adres):
            raise OSError("ağ yok")
        m = piyasa.sorgula("bitcoin", bozuk)
        self.assertIn("alınamadı", m)

    def test_yalniz_izinli_adres(self):
        with self.assertRaises(ValueError):
            piyasa._indir("https://ornek.com/x")

    def test_tr_sayi(self):
        self.assertEqual(piyasa.tr_sayi(1234567.891), "1.234.567,89")


if __name__ == "__main__":
    unittest.main()
