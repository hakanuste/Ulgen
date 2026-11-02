import io
import json
import unittest
from unittest import mock

from .temel import TemizVeri
from ulgen import hava


class Hava(TemizVeri):

    def setUp(self):
        super().setUp()
        hava._ONBELLEK.update(zaman=0.0, veri=None)

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
