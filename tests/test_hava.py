import io
import json
import unittest
from unittest import mock

from .temel import TemizVeri
from ulgen import hava


class Hava(TemizVeri):

    def setUp(self):
        super().setUp()
        hava._ONBELLEK.clear()

    def test_getir_onbellek_ve_hata(self):
        yanit = io.BytesIO(json.dumps({"current": {
            "temperature_2m": 18.4, "weather_code": 2}}).encode())
        with mock.patch("urllib.request.urlopen") as u:
            u.return_value.__enter__.return_value = yanit
            v = hava.getir(zorla=True)
        self.assertEqual(v, {"ad": "Aydın", "sicaklik": 18,
                             "durum": "Parçalı bulutlu"})
        with mock.patch("urllib.request.urlopen",
                        side_effect=OSError("ağ yok")) as u:
            self.assertEqual(hava.getir(zorla=True), v)   # eski değer
            u.assert_called_once()

    def test_kapali_ise_istek_yapmaz(self):
        import json as j
        from ulgen import ayar
        a = ayar.yukle()
        a["hava_acik"] = False
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            j.dump(a, f)
        with mock.patch("urllib.request.urlopen") as u:
            self.assertIsNone(hava.getir(zorla=True))
            u.assert_not_called()


if __name__ == "__main__":
    unittest.main()


class HavaKonum(TemizVeri):

    def setUp(self):
        super().setUp()
        hava._ONBELLEK.clear()

    def test_en_yakin_il_cevrimdisi(self):
        self.assertEqual(hava.en_yakin_il(38.43, 27.15), "İzmir")
        self.assertEqual(hava.en_yakin_il(37.84, 27.85), "Aydın")
        self.assertEqual(hava.en_yakin_il(41.02, 29.0), "İstanbul")
        self.assertEqual(len(hava.ILLER), 81)

    def test_koordinatla_istek_ve_son_konum_rapor_icin(self):
        yanit = lambda: io.BytesIO(json.dumps({"current": {
            "temperature_2m": 9.6, "weather_code": 61}}).encode())
        with mock.patch("urllib.request.urlopen") as u:
            u.return_value.__enter__.return_value = yanit()
            v = hava.getir(enlem=39.9334, boylam=32.8597)
            self.assertEqual((v["ad"], v["sicaklik"]), ("Ankara", 10))
            self.assertIn("latitude=39.93", u.call_args.args[0])
            self.assertIn("longitude=32.86", u.call_args.args[0])
        hava.son_konum_yaz(39.9334, 32.8597)       # tarayıcı bildirdi
        hava._ONBELLEK.clear()
        with mock.patch("urllib.request.urlopen") as u:
            u.return_value.__enter__.return_value = yanit()
            v = hava.getir()                        # sunucu raporu: koordinatsız
            self.assertEqual(v["ad"], "Ankara")

    def test_http_gecersiz_koordinat(self):
        from ulgen import sunucu, veritabani
        from ulgen.cekirdek import Ulgen
        from .test_sunucu import istek
        veritabani.kur()
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        for kotu in ("?enlem=abc&boylam=1", "?enlem=95&boylam=1", "?enlem=10"):
            self.assertEqual(istek(p, "/hava" + kotu)[0], 400)
