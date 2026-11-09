import unittest
from unittest import mock

from ulgen import ajan_kayit, kutuphane_once as ko, uzmanlar
from tests.temel import TemizVeri


class SoruTuru(unittest.TestCase):

    def test_bilgi_sorusu(self):
        self.assertTrue(ko.bilgi_sorusu_mu("Göktürk alfabesi kaç harftir?"))
        self.assertTrue(ko.bilgi_sorusu_mu("biberiye neye iyi gelir"))
        self.assertTrue(ko.bilgi_sorusu_mu("Kerpiç duvar nasıl sıvanır"))

    def test_kisisel_ve_kisa_disarida(self):
        self.assertFalse(ko.bilgi_sorusu_mu("selam"))
        self.assertFalse(ko.bilgi_sorusu_mu("bugün benim görevlerim neler?"))
        self.assertFalse(ko.bilgi_sorusu_mu("ilacımı aldım mı?"))
        self.assertFalse(ko.bilgi_sorusu_mu("şunu yaz: merhaba dünya"))


class Kutuphane(unittest.TestCase):

    def test_notta_varsa_arastirma_yok(self):
        def ara(m, adet):
            return [("Kerpiç sıva", "a.md", "kerpiç duvar sıvanır saman kil")]
        self.assertTrue(ko.kutuphanede_var_mi("Kerpiç duvar nasıl sıvanır", ara))
        with mock.patch.object(ko, "acik_mi", return_value=True):
            self.assertFalse(ko.gerekli_mi("Kerpiç duvar nasıl sıvanır", ara))

    def test_ilgisiz_not_yetmez(self):
        def ara(m, adet):
            return [("Musso bakım", "b.md", "duvar boyası alındı")]
        with mock.patch.object(ko, "acik_mi", return_value=True):
            self.assertTrue(ko.gerekli_mi("Göktürk alfabesi kaç harftir?", ara))

    def test_kapaliysa_aramaz(self):
        with mock.patch.object(ko, "acik_mi", return_value=False):
            self.assertFalse(ko.gerekli_mi("Göktürk alfabesi kaç harftir?",
                                           lambda m, a: []))


class Devir(TemizVeri):

    def test_alanli_gorev_uzmana_devredilir(self):
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        cagri = []
        with mock.patch.object(uzmanlar, "devral",
                               side_effect=lambda ad, s, a, g: cagri.append(ad)
                               or "BULGU"):
            ham = mock.Mock(return_value="GENEL")
            sonuc = u._devredici(ham)("biberiye hangi vitaminleri içerir")
        self.assertEqual(cagri, ["OTACI"])
        self.assertIn("OTACI uzmanına", sonuc)
        self.assertIn("BULGU", sonuc)
        ham.assert_not_called()

    def test_alansiz_gorev_genelde_kalir(self):
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        ham = mock.Mock(return_value="GENEL")
        self.assertEqual(u._devredici(ham)("xqzw lorem ipsum"), "GENEL")

    def test_devral_bulgu_yoksa_genel_arama_etiketli(self):
        with mock.patch.object(uzmanlar, "guvenilir_ara",
                               return_value="Güvenilir kaynak listesinde (x) "
                                            "bu konuda bir şey bulamadım."):
            m = uzmanlar.devral("BALBAL", "kerpiç", None, lambda s: "GENEL BULGU")
        self.assertIn("doğrulanmamış", m)
        self.assertIn("GENEL BULGU", m)

    def test_uzmanlar_ayri_ajan_olarak_listelenir(self):
        ajan_kayit.sifirla()
        liste = {x["id"]: x for x in ajan_kayit.liste()}
        self.assertEqual(liste["uzman:AKÇA"]["tur"], "uzman")

    def test_sohbette_kutuphane_yoksa_arastirir(self):
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        with mock.patch.object(ko, "gerekli_mi", return_value=True), \
                mock.patch.object(u.arastirma, "arastir",
                                  return_value="KAYNAK 1: tdk.gov.tr"), \
                mock.patch.object(u, "_beyinle_dene",
                                  side_effect=lambda m: ("tamam", u.sistem_istemi(
                                      mock.Mock(yerel=True, sistem_butce=20000), m),
                                      "sahte")):
            y = u.sohbet_isle("Göktürk alfabesi kaç harftir?")["yanit"]
        self.assertIn("FRESH WEB RESEARCH", y)
        self.assertIn("tdk.gov.tr", y)
