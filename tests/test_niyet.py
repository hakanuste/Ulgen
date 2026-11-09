import json
import os
import unittest
from unittest import mock

from ulgen import niyet, uzmanlar
from tests.temel import TemizVeri


def gecmis_sahte(adres):
    if "/search" in adres:
        return json.dumps({"quotes": [{"symbol": "XYZAB.IS", "longname": "Xyz A.Ş."}]})
    gun = 86400
    kap = [100 + i * 0.5 for i in range(260)]
    return json.dumps({"chart": {"result": [{
        "meta": {"regularMarketPrice": kap[-1], "chartPreviousClose": kap[-2],
                 "regularMarketTime": 1762446000, "currency": "TRY"},
        "timestamp": [1730000000 + i * gun for i in range(260)],
        "indicators": {"quote": [{"close": kap}]}}]}})


class Varlik(unittest.TestCase):

    def test_sirket_adindan_kod(self):
        self.assertEqual(niyet.varlik_bul("anadolu efes hissesi ne oldu")[0], "AEFES.IS")
        self.assertEqual(niyet.varlik_bul("thy hissesi nasıl gidiyor")[0], "THYAO.IS")
        self.assertEqual(niyet.varlik_bul("İş Bankası analiz")[0], "ISCTR.IS")
        self.assertEqual(niyet.varlik_bul("vestel beyaz analiz")[0], "VESBE.IS")
        self.assertEqual(niyet.varlik_bul("AEFES kaç TL")[0], "AEFES.IS")

    def test_listede_yoksa_yahoo_aramasi(self):
        self.assertEqual(niyet.varlik_bul("xyz hissesi analiz et", gecmis_sahte)[0],
                         "XYZAB.IS")


class Yonlendirme(TemizVeri):

    def test_efes_analizi_akcaya_gider_ve_rapor_cikar(self):
        ad, yanit = niyet.yonlendir("anadolu efes hissesi ne oldu analiz et",
                                    gecmis_sahte)
        self.assertEqual(ad, "AKÇA")
        self.assertIn("# Analiz: Anadolu Efes (AEFES)", yanit)
        self.assertIn("RSI", yanit)

    def test_fiyat_sorusu(self):
        ad, yanit = niyet.yonlendir("aefes kaç TL", gecmis_sahte)
        self.assertEqual(ad, "AKÇA")
        self.assertIn("Anadolu Efes", yanit)

    def test_niyetsiz_soru_beyne_kalir(self):
        self.assertIsNone(niyet.yonlendir("efes pilsen nasıl yapılır diye merak ettim"))
        self.assertIsNone(niyet.yonlendir("bugün hava nasıl"))

    def test_sohbette_ajan_etiketi(self):
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        with mock.patch.object(niyet, "yonlendir", return_value=("AKÇA", "RAPOR")):
            c = u.sohbet_isle("anadolu efes hissesi ne oldu analiz et")
        self.assertEqual(c["yanit"], "RAPOR")
        self.assertTrue(c["ajan"].startswith("AKÇA – "))


class Kilavuz(unittest.TestCase):

    def test_turkce_soru_ingilizce_terimle_aranir(self):
        q = "mussonun şanzımanında geçme sorunu var hangi parça lazım"
        self.assertEqual(uzmanlar.sec(q), "TULGA")
        g = uzmanlar.terim_genislet(q)
        self.assertTrue(g.startswith("transmission"))
        self.assertIn("shift", g)

    def test_musso_kilavuzu_once(self):
        def ara(m, adet):
            return [("Genel - Sayfa 1-20", "/k/Genel/Genel - Sayfa 1-20.md", "transmission"),
                    ("Not", "/k/notlar/a.md", "shift"),
                    ("Musso - Sayfa 300-320", "/k/Musso/Musso - Sayfa 300-320.md",
                     "shift valve and modulator")]
        m = uzmanlar.kilavuz_alintilari(
            "TULGA", "şanzıman geçmiyor", ara,
            kilavuz_mu=lambda y: os.path.basename(os.path.dirname(y)) != "notlar")
        self.assertTrue(m.startswith("## KILAVUZ ("))
        self.assertIn("): Musso - Sayfa 300-320", m.split("\n")[0])
        self.assertNotIn("## Not\n", m)

    def test_kilavuz_varsa_istemde_ve_arastirma_yok(self):
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        u._ajan = "TULGA"
        with mock.patch.object(uzmanlar, "kilavuz_alintilari",
                               return_value="## Musso\nmodulator"), \
                mock.patch.object(u.arastirma, "arastir") as ar:
            u._kutuphane_yoksa_arastir("musso şanzıman geçme sorunu hangi parça?")
            istem = u.sistem_istemi(mock.Mock(yerel=False, sistem_butce=20000),
                                    "musso şanzıman geçme sorunu hangi parça?")
        ar.assert_not_called()
        self.assertIn("LIBRARY EXCERPTS", istem)
        self.assertIn("modulator", istem)


class TulgaBicim(unittest.TestCase):

    def test_talimat_bicim_ve_uydurmama(self):
        t = uzmanlar.UZMANLAR["TULGA"]["talimat"]
        self.assertIn("FAULT ANSWER FORMAT", t)
        self.assertIn("never invent", t)
        self.assertIn("not a diesel", t)

    def test_devral_sanziman_sorgusu_ingilizce(self):
        alinan = []
        with mock.patch.object(uzmanlar, "guvenilir_ara",
                               side_effect=lambda s, a, r: alinan.append(s) or "KAYNAK"):
            uzmanlar.devral("TULGA", "musso şanzıman vitese geçmiyor", None,
                            lambda s: "")
        self.assertTrue(alinan[0].startswith("Mercedes 722 transmission"))


class EskiSohbet(unittest.TestCase):

    def test_sohbetteki_burc_bilgisi_gelir(self):
        yol = "/k/Yapay Zekâ Konuşmaları/Gemini/2026-10-01 Musso vites.md"

        def ara(m, adet):
            return [(os.path.basename(yol)[:-3], yol,
                     "Musso 722.3 vites kolu mekanizmasında iki burç var: "
                     "A1159920310"),
                    ("Banka", "/k/Yapay Zekâ Konuşmaları/x/banka.md",
                     "kredi kartı numaram 4111 1111 1111 1111 şifre 1234")]
        m = uzmanlar.kilavuz_alintilari(
            "TULGA", "mussonun şanzımanında geçme sorunu var hangi parça lazım",
            ara, kilavuz_mu=lambda y: False)
        self.assertIn("## ESKİ SOHBET (2026-10-01): 2026-10-01 Musso vites", m)
        self.assertIn("A1159920310", m)
        self.assertNotIn("kredi kartı", m)

    def test_her_uzman_kendi_alanindaki_sohbeti_alir(self):
        def ara(m, adet):
            return [("Biberiye", "/k/Yapay Zekâ Konuşmaları/a/biberiye.md",
                     "biberiye bitkisi çayı A vitamini içerir"),
                    ("Musso", "/k/Yapay Zekâ Konuşmaları/a/musso.md",
                     "musso şanzıman burcu")]
        m = uzmanlar.kilavuz_alintilari("OTACI", "biberiye neye iyi gelir", ara,
                                        kilavuz_mu=lambda y: False)
        self.assertIn("biberiye", m)
        self.assertNotIn("şanzıman", m)

    def test_tas_ev_olculeri_en_yeni_once(self):
        k = "/k/Yapay Zekâ Konuşmaları/a/"

        def ara(m, adet):
            return [("2026-03-02 Taş ev", k + "2026-03-02 Taş ev.md", "taş ev 8x10 m"),
                    ("2026-09-15 Taş ev", k + "2026-09-15 Taş ev.md", "taş ev 9x12 m"),
                    ("2026-06-01 Taş ev", k + "2026-06-01 Taş ev.md", "taş ev 9x11 m")]
        q = "taş evin son ölçüleri tarihsel sıralamaya göre kaçtır"
        self.assertEqual(uzmanlar.sec(q), "BALBAL")
        m = uzmanlar.kilavuz_alintilari("BALBAL", q, ara, kilavuz_mu=lambda y: False)
        sira = [m.index(x) for x in ("9x12", "9x11", "8x10")]
        self.assertEqual(sira, sorted(sira))
        self.assertIn("newest one is the user's current decision", uzmanlar.KILAVUZ_ISTEMI)
