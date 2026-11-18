import json
import os
import unittest
from unittest import mock

from tests.temel import TemizVeri
from ulgen import kilavuz, kitap_bul


def sahte_getir(adres):
    if "tr.wikipedia.org" in adres and "list=search" in adres:
        return {"query": {"search": [{"title": "El-Kanun fi't-Tıb"}]}}
    if "en.wikipedia.org" in adres:
        return {"query": {"search": []}}
    if "langlinks" in adres:
        return {"query": {"pages": {"1": {"langlinks": [{"*": "The Canon of Medicine"}]}}}}
    if "advancedsearch" in adres:
        if "medici" in adres:
            return {"response": {"docs": [
                {"identifier": "canonofmedicine00avic", "title": "The Canon of Medicine",
                 "creator": "Avicenna", "year": "1930", "language": "eng"},
                {"identifier": "kanunlatince", "title": "Canon medicinae",
                 "creator": ["Avicenna"], "date": "1507", "language": "lat"}]}}
        return {"response": {"docs": [
            {"identifier": "kanunodunc", "title": "Tıp Kanunu", "year": "2014"},
            {"identifier": "ilgisiz", "title": "Çöl Korsanı", "subject": ["tarih"]}]}}
    if "archive.org/metadata/canonofmedicine00avic" in adres:
        return {"metadata": {}, "files": [
            {"name": "canon.pdf", "size": "9000000"},
            {"name": "canon_djvu.txt", "size": "1500000"}]}
    if "archive.org/metadata/kanunodunc" in adres:
        return {"metadata": {"access-restricted-item": "true"}, "files": []}
    if "archive.org/metadata/kanunlatince" in adres:
        return {"metadata": {}, "files": [{"name": "kanun.pdf", "size": "20000"}]}
    if "gutendex" in adres:
        return {"results": []}
    raise AssertionError(adres)


class KitapBulTesti(TemizVeri):
    def test_komut_tanima(self):
        self.assertIsNone(kitap_bul.komut("bugün hava nasıl"))
        with mock.patch.object(kitap_bul, "ara", return_value="A") as ara:
            self.assertEqual(kitap_bul.komut("İbn Sina'nın Tıp Kanunu kitabını bul"), "A")
            ara.assert_called_with("İbn Sina'nın Tıp Kanunu", None)
            kitap_bul.komut("kitap ara: Tıp Kanunu")
            ara.assert_called_with("Tıp Kanunu", None)
            kitap_bul.komut("Tıp Kanunu kitabını bul ve yerel klasöre ekle")
            ara.assert_called_with("Tıp Kanunu", None)
        with mock.patch.object(kitap_bul, "indir", return_value="İ") as indir:
            for m, n in (("kitap indir 2", [2]), ("kitap indir 1, 3", [1, 3]),
                         ("2'yi indir", [2]), ("1 ve 3 indir", [1, 3])):
                self.assertEqual(kitap_bul.komut(m), "İ")
                indir.assert_called_with(n)

    def test_arama_listeler_telif_ve_engel_yazar(self):
        y = kitap_bul.ara("Tıp Kanunu", sahte_getir)
        self.assertNotIn("Çöl Korsanı", y)                     # ilgisiz sonuç atılır
        self.assertIn("The Canon of Medicine", y)
        self.assertIn("https://archive.org/details/canonofmedicine00avic", y)
        self.assertIn("ödünç", y)
        self.assertIn("eski baskı (1507)", y)
        self.assertIn("telif durumu belirsiz", y)
        self.assertIn("kitap indir", y)
        with open(kitap_bul._aday_yolu(), encoding="utf-8") as f:
            adaylar = json.load(f)["adaylar"]
        canon = [a for a in adaylar if a["kimlik"] == "canonofmedicine00avic"][0]
        self.assertTrue(canon["dosya"].endswith("canon_djvu.txt"))    # metin önce

    def test_indir_klasore_koyar_ve_aktarir(self):
        kitap_bul.ara("Tıp Kanunu", sahte_getir)
        hedef_klasor = os.path.join(os.path.dirname(kitap_bul._aday_yolu()), "Klavuz")
        indirilen = []

        def indirici(adres, hedef):
            indirilen.append(adres)
            with open(hedef, "w") as f:
                f.write("metin")
        aktar = mock.Mock()
        with mock.patch.object(kilavuz, "klasor_bul", return_value=hedef_klasor):
            y = kitap_bul.indir([1, 2, 99], indirici, aktar)
        self.assertIn("indirildi", y)
        self.assertIn("listede böyle bir numara yok", y)
        aktar.assert_called_once()
        dosyalar = os.listdir(hedef_klasor)
        self.assertTrue(any(d.endswith(".txt") for d in dosyalar))
        self.assertTrue(all(a.startswith("https://archive.org/") for a in indirilen))

    def test_isabet_ve_terimler(self):
        self.assertEqual(kitap_bul.onemli_sozcukler("Türk Tarihi ve mitolojisi kitabı"),
                         ["türk", "tarihi", "mitolojisi"])
        t = kitap_bul._arsiv_terimleri("Türk Tarihi ve mitolojisi")
        self.assertIn("(türk* OR turk*)", t)
        self.assertIn("AND mitoloji*", t)
        iyi = {"baslik": "Türk Mitolojisi", "yazar": "Bahaeddin Ögel",
               "konu": "Türk tarihi"}
        kotu = {"baslik": "Çöl Korsanı", "yazar": "", "konu": "Gizlenen İslam"}
        s = "Türk Tarihi ve mitolojisi"
        self.assertGreaterEqual(kitap_bul.isabet(s, iyi), kitap_bul._esik(s))
        self.assertLess(kitap_bul.isabet(s, kotu), kitap_bul._esik(s))

    def test_yalniz_guvenilir_site(self):
        self.assertTrue(kitap_bul._izinli("https://ia800.us.archive.org/x.txt"))
        self.assertTrue(kitap_bul._izinli("https://www.gutenberg.org/ebooks/1.txt.utf-8"))
        self.assertFalse(kitap_bul._izinli("https://archive.org.kotu.com/x"))
        self.assertFalse(kitap_bul._izinli("http://archive.org/x"))


if __name__ == "__main__":
    unittest.main()
