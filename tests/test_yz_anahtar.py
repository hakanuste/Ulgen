import json
from unittest import mock

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import gizli, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class AnahtarKutusu(TemizVeri):

    def _sunucu(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        return srv, srv.server_address[1]

    def test_yaz_dogrula_ve_sizinti_yok(self):
        srv, p = self._sunucu()
        g = lambda d: json.dumps(d)
        k, h = istek(p, "/yz/anahtar", "POST",
                     g({"saglayici": "nvidia", "anahtar": "nvapi-GIZLI-12345"}), JSON)
        self.assertEqual(k, 200)
        self.assertNotIn(b"GIZLI", h)
        self.assertEqual(gizli.sir_oku("nvidia"), "nvapi-GIZLI-12345")
        gunluk = veritabani.sorgu("SELECT * FROM gunluk", (), True)
        self.assertNotIn("GIZLI", json.dumps([dict(x) for x in gunluk], default=str))
        for kotu in ({"saglayici": "x", "anahtar": "abcdefgh12"},
                     {"saglayici": "nvidia", "anahtar": "kisa"},
                     {"saglayici": "nvidia", "anahtar": "bosluk var burada"},
                     {"saglayici": "nvidia", "anahtar": 5}):
            self.assertEqual(istek(p, "/yz/anahtar", "POST", g(kotu), JSON)[0], 400)
        self.assertEqual(istek(p, "/yz/anahtar", "POST", g(
            {"saglayici": "nvidia", "anahtar": "abcdefgh12"}), JSON,
            yetkisiz=True)[0], 401)

    def test_uzaktan_reddedilir_ve_dene(self):
        srv, p = self._sunucu()
        body = json.dumps({"saglayici": "gemini", "anahtar": "abcdefgh1234"})
        srv.yerel = False
        self.assertEqual(istek(p, "/yz/anahtar", "POST", body, JSON)[0], 403)
        srv.yerel = True
        with mock.patch("ulgen.tani.dene", return_value=0):
            k, h = istek(p, "/yz/dene", "POST", json.dumps({"saglayici": "gemini"}), JSON)
        self.assertEqual((k, json.loads(h)["calisti"]), (200, True))
