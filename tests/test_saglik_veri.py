import json
import unittest
from datetime import datetime

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import saglik_veri, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class SaglikVeri(TemizVeri):

    def setUp(self):
        super().setUp()
        veritabani.kur()

    def test_ekle_dogrula_ve_ozet(self):
        simdi = datetime(2026, 11, 2, 19, 0)
        e, a = saglik_veri.ekle([
            {"tur": "adim", "deger": 4000, "zaman": "2026-11-02T12:00:00"},
            {"tur": "adim", "deger": 4320, "zaman": "2026-11-02T18:00:00"},
            {"tur": "nabiz", "deger": 78, "zaman": "2026-11-02T18:30:00"},
            {"tur": "uyku", "deger": 432, "zaman": "2026-11-02T06:30:00"},
            {"tur": "nabiz", "deger": 999, "zaman": "2026-11-02T18:31:00"},
            {"tur": "bilinmez", "deger": 1, "zaman": "2026-11-02T18:31:00"},
            {"tur": "adim", "deger": "x", "zaman": "2026-11-02T18:31:00"},
        ])
        self.assertEqual((e, a), (4, 3))
        b = saglik_veri.bugun(simdi)
        self.assertEqual((b["adim"], b["nabiz"], b["uyku_dk"]),
                         (4320, 78, 432))
        self.assertEqual(saglik_veri.uyku_yazi(432), "7s 12dk")
        # aynı tür+zaman tekrar gelirse güncellenir, çoğalmaz
        saglik_veri.ekle([{"tur": "adim", "deger": 4500,
                           "zaman": "2026-11-02T18:00:00"}])
        self.assertEqual(saglik_veri.bugun(simdi)["adim"], 4500)

    def test_http_yetki_ve_sinir(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        govde = json.dumps({"olcumler": [
            {"tur": "adim", "deger": 10, "zaman": "2026-11-02T10:00:00"}]})
        self.assertEqual(istek(port, "/saglik/veri", "POST", govde, JSON,
                               yetkisiz=True)[0], 401)
        kod, ham = istek(port, "/saglik/veri", "POST", govde, JSON)
        self.assertEqual((kod, json.loads(ham)["eklenen"]), (200, 1))
        kod, ham = istek(port, "/saglik/veri", "POST", json.dumps(
            {"olcumler": [{}] * 501}), JSON)
        self.assertEqual(kod, 400)


if __name__ == "__main__":
    unittest.main()
