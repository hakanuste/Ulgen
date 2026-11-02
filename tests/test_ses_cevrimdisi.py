import json
import unittest
from unittest import mock

from .temel import TemizVeri
from .test_sunucu import istek
from ulgen import ses, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class CevrimdisiSes(TemizVeri):

    def test_kurulu_degilse_durum_ve_503(self):
        veritabani.kur()
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        A = {"Content-Type": "audio/mp4"}
        with mock.patch.object(ses.CevrimdisiTanima, "hazir_mi",
                               return_value=False), \
                mock.patch.object(ses.CevrimdisiTanima, "eksikler",
                                  return_value=["ffmpeg"]):
            k, h = istek(p, "/ses/durum")
            self.assertEqual(k, 200)
            self.assertFalse(json.loads(h)["cevrimdisi"])
            self.assertEqual(istek(p, "/ses/yaz", "POST", b"xxxx", A)[0], 503)
        with mock.patch.object(ses.CevrimdisiTanima, "yaz",
                               return_value="merhaba ülgen"):
            k, h = istek(p, "/ses/yaz", "POST", b"xxxx", A)
            self.assertEqual((k, json.loads(h)["metin"]),
                             (200, "merhaba ülgen"))
        self.assertEqual(istek(p, "/ses/yaz", "POST", b"xxxx",
                               {"Content-Type": "text/plain"})[0], 415)
        with mock.patch.object(ses.CevrimdisiTanima, "AZAMI_BAYT", 10):
            self.assertEqual(istek(p, "/ses/yaz", "POST", b"x" * 20, A)[0],
                             413)
        self.assertEqual(istek(p, "/ses/yaz", "POST", b"xxxx", A,
                               yetkisiz=True)[0], 401)

    def test_yaz_bos_ve_buyuk_reddedilir(self):
        with self.assertRaises(ValueError):
            ses.CevrimdisiTanima.yaz(b"")
        with self.assertRaises(ValueError):
            ses.CevrimdisiTanima.yaz(b"x" * (ses.CevrimdisiTanima.AZAMI_BAYT + 1))


if __name__ == "__main__":
    unittest.main()
