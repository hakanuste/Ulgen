import re
import unittest

from .temel import TemizVeri
from .test_sunucu import istek
from ulgen import arayuz, sunucu
from ulgen.cekirdek import Ulgen


class SayfaCSP(TemizVeri):

    def test_sayfada_gomulu_betik_ve_olay_yok(self):
        self.assertNotRegex(arayuz.SAYFA, r"<script(?![^>]*\bsrc=)")
        self.assertNotRegex(arayuz.SAYFA, r"\son(click|keydown|change|load|"
                                          r"error|input)\s*=")
        self.assertNotIn("javascript:", arayuz.SAYFA)
        self.assertNotRegex(arayuz.BETIK, r"\beval\(|new Function\(")
        self.assertNotRegex(arayuz.BETIK, r"\son(click|keydown)=\"")

    def test_baslik_ve_betik_dosyasi(self):
        u = Ulgen()
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", "/")
        r = c.getresponse()
        r.read()
        csp = r.getheader("Content-Security-Policy")
        self.assertIn("script-src 'self';", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertNotRegex(csp, r"script-src[^;]*unsafe-inline")
        self.assertIn("object-src 'none'", csp)
        self.assertEqual(r.getheader("Cache-Control"), "no-store")
        self.assertIn("publickey-credentials-get",
                      r.getheader("Permissions-Policy"))
        c.close()
        kod, ham = istek(port, "/varlik/uygulama.js", yetkisiz=True)
        self.assertEqual(kod, 200)
        self.assertIn(b"data-on", ham)


if __name__ == "__main__":
    unittest.main()
