import unittest

from .temel import TemizVeri
from ulgen import ajan_gorevi


class SahteUlgen:
    def __init__(self):
        self.bildirimler, self.kayit = [], []

        class A:
            def arastir(_, g):
                return "BULGU: " + g
        self.arastirma = A()

    def _kaydet(self, rol, metin, duyarli=False):
        self.kayit.append((rol, metin))

    def sohbet_isle(self, metin, ajan_gorevi=False):
        assert ajan_gorevi                       # görev sohbet kilidini tutmaz
        return {"yanit": "UZMAN YANITI: " + metin}

    def bildir(self, metin, eylem=None):
        self.bildirimler.append((metin, eylem))


class AjanGorevi(TemizVeri):

    def test_dogrula(self):
        self.assertEqual(ajan_gorevi.dogrula("arastirma", " konu ")[0], "arastirma")
        self.assertEqual(ajan_gorevi.dogrula("akça", "x"), ("AKÇA", "x"))
        self.assertEqual(ajan_gorevi.dogrula("yok", "x"), ("Bilinmeyen ajan", ""))
        self.assertEqual(ajan_gorevi.dogrula("OTACI", "  ")[1], "")

    def test_arastirma_sonucu_sohbette_yayinlanir(self):
        u = SahteUlgen()
        ajan_gorevi.calistir(u, "arastirma", "borsa")
        metin, eylem = u.bildirimler[0]
        self.assertIn("BULGU: borsa", metin)
        self.assertEqual(eylem["tur"], "ajan_sonuc")
        self.assertEqual([r for r, _ in u.kayit], ["kullanici", "asistan"])

    def test_uzman_gorevi_uzman_adiyla_sorulur(self):
        u = SahteUlgen()
        ajan_gorevi.calistir(u, "OTACI", "biberiye")
        self.assertIn("UZMAN YANITI: OTACI: biberiye", u.bildirimler[0][0])

    def test_hata_bildirilir(self):
        u = SahteUlgen()
        u.arastirma.arastir = lambda g: (_ for _ in ()).throw(OSError("ağ"))
        ajan_gorevi.calistir(u, "arastirma", "x")
        self.assertIn("tamamlanamadı", u.bildirimler[0][0])


if __name__ == "__main__":
    unittest.main()


class SunucuUcu(TemizVeri):

    def setUp(self):
        super().setUp()
        from ulgen import sunucu
        from ulgen.cekirdek import Ulgen
        self.u = Ulgen()
        self.srv = sunucu.yerel_sunucu(self.u, 0)
        sunucu.arka_planda_calistir(self.srv)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_gorev_kabul_ve_sonuc_bildirimi(self):
        import json
        import time
        from .test_sunucu import istek
        self.u.arastirma.arastir = lambda q: "SONUÇ " + q
        d, g = istek(self.port, "/ajanlar/gorev", "POST",
                     json.dumps({"ajan": "arastirma", "gorev": "zeytin"}),
                     {"Content-Type": "application/json"})
        self.assertEqual(d, 202)
        for _ in range(50):
            son = [b for b in self.u.bildirimler(0)
                   if (b["eylem"] or {}).get("tur") == "ajan_sonuc"]
            if son:
                break
            time.sleep(0.1)
        self.assertIn("SONUÇ zeytin", son[0]["metin"])
        d, _ = istek(self.port, "/ajanlar/gorev", "POST",
                     json.dumps({"ajan": "yok", "gorev": "x"}),
                     {"Content-Type": "application/json"})
        self.assertEqual(d, 400)
        d, _ = istek(self.port, "/ajanlar/gorev", "POST",
                     json.dumps({"ajan": "arastirma", "gorev": "x"}),
                     {"Content-Type": "application/json"}, yetkisiz=True)
        self.assertEqual(d, 401)


class Eszamanli(TemizVeri):
    """Bir ajan çalışırken diğer ajanlar ve sohbet beklemez."""

    def test_iki_uzman_ve_sohbet_ayni_anda(self):
        import threading
        import time
        from unittest import mock
        from ulgen import ajan_gorevi
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        gorulen = {}

        def yavas(metin):
            # her tur kendi uzmanını görmeli (durum iş parçacığına özel)
            gorulen[threading.current_thread().name] = u._ajan
            time.sleep(0.6)
            return ("tamam", "yanıt: " + metin[:12], "sahte")
        with mock.patch.object(u, "_beyinle_dene", side_effect=yavas), \
                mock.patch.object(u, "bildir"):
            bas = time.time()
            t1 = ajan_gorevi.arka_planda(u, "OTACI", "biberiye neye iyi gelir")
            t2 = ajan_gorevi.arka_planda(u, "BALBAL", "kerpiç duvar nasıl örülür")
            time.sleep(0.05)
            y = u.sohbet_isle("merhaba, nasılsın bugün")
            t1.join(3)
            t2.join(3)
            sure = time.time() - bas
        self.assertLess(sure, 1.5)                 # sırayla olsaydı ≥ 1,8 sn
        self.assertTrue(y["yanit"])
        self.assertIn("OTACI", gorulen.values())
        self.assertIn("BALBAL", gorulen.values())
