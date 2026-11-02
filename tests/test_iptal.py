"""Çalışan sohbet işinin kullanıcı isteğiyle durdurulması."""

import json
import threading
import time
from unittest import mock

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import iptal, sunucu
from ulgen.cekirdek import Ulgen


class IptalTesti(TemizVeri):

    def test_bayrak_temizlenir_ve_denetlenir(self):
        iptal.ayarla()
        with self.assertRaises(iptal.Iptal):
            iptal.denetle()
        iptal.temizle()
        iptal.denetle()

    def test_eski_iptal_yeni_isi_durdurmaz(self):
        u = Ulgen()
        iptal.ayarla()                      # boşta gelen iptal
        r = u.sohbet_isle("saat kaç")
        self.assertNotIn("İptal", r["yanit"])

    def test_calisan_is_iptal_edilir(self):
        u = Ulgen()
        basladi = threading.Event()

        def yavas(beyin, metin):
            basladi.set()
            for _ in range(100):
                time.sleep(0.02)
                iptal.denetle()
            return "bitti"

        class Beyin:
            yerel = False
            ad = "sahte"
            gecmis_butce = 1

        sonuc = {}
        with mock.patch.object(u.yonlendirici, "kullanilabilirler", return_value=[Beyin()]), \
                mock.patch.object(u, "_beyinle_yanitla", yavas):
            t = threading.Thread(target=lambda: sonuc.update(
                u.sohbet_isle("bana bir şey anlat")))
            t.start()
            self.assertTrue(basladi.wait(3))
            srv = sunucu.yerel_sunucu(u, 0)
            sunucu.arka_planda_calistir(srv)
            self.addCleanup(srv.shutdown)
            kod, _ = istek(srv.server_address[1], "/sohbet/iptal", "POST", json.dumps({}), JSON)
            t.join(5)
        self.assertEqual(kod, 200)
        self.assertEqual(sonuc.get("yanit"), "İptal ettim.")
