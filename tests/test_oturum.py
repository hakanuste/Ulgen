import http.server
import tempfile
import threading
import unittest
from unittest import mock

from .temel import TemizVeri
from ulgen import oturum, uzmanlar


class Sunucu(http.server.BaseHTTPRequestHandler):

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/giris":
            self.send_response(200)
            self.send_header("Set-Cookie", "oturum=tamam; Path=/")
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<title>Giriş</title>Girildi".encode())
            return
        cerez = self.headers.get("Cookie", "")
        govde = ("<title>Gizli</title><p>Portföy: 3 hisse</p>"
                 if "oturum=tamam" in cerez else
                 "<title>Engel</title><p>Lütfen giriş yapın</p>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(govde.encode())


@unittest.skipUnless(oturum.hazir_mi(), "playwright kurulu değil")
class GercekTarayici(TemizVeri):

    def test_cerez_profilde_kalir_ve_okunur(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Sunucu)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        taban = "http://127.0.0.1:%d" % srv.server_address[1]
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(oturum, "PROFIL", d):
                onceki = oturum.oku(taban + "/gizli")
                self.assertIn("Lütfen giriş yapın", onceki)
                oturum.oku(taban + "/giris")        # çerez profile yazılır
                sonra = oturum.oku(taban + "/gizli")
                self.assertIn("Portföy: 3 hisse", sonra)


class Denetimler(TemizVeri):

    def test_eklenmemis_site_okunmaz(self):
        with mock.patch("ulgen.ajanlar.adres_guvenli_mi", lambda a: True), \
                mock.patch.object(oturum, "hazir_mi", lambda: True):
            self.assertIn("eklenmemiş", oturum.oturumlu_oku("ornek.com/x"))

    def test_giris_yapilmadan(self):
        with mock.patch("ulgen.ajanlar.adres_guvenli_mi", lambda a: True), \
                mock.patch.object(oturum, "hazir_mi", lambda: True), \
                mock.patch.object(oturum, "profil_var_mi", lambda: False):
            uzmanlar.komut("kaynak ekle: AKÇA ornek.com")
            self.assertIn("giris:", oturum.oturumlu_oku("ornek.com/x"))

    def test_bilesen_yoksa_ipucu(self):
        with mock.patch.object(oturum, "hazir_mi", lambda: False):
            self.assertIn("playwright", oturum.oturumlu_oku("ornek.com"))

    def test_komut_ayristirma_ve_guvensiz_adres(self):
        self.assertIsNone(oturum.komut("merhaba"))
        with mock.patch.object(oturum, "hazir_mi", lambda: True):
            self.assertIn("güvenlik", oturum.komut("giris: http://127.0.0.1/x"))

    def test_alan_eslesme_alt_alan(self):
        with mock.patch("ulgen.ajanlar.adres_guvenli_mi", lambda a: True):
            uzmanlar.komut("kaynak ekle: AKÇA fintables.com")
        self.assertTrue(oturum.alan_izinli_mi("https://app.fintables.com/x"))
        self.assertFalse(oturum.alan_izinli_mi("https://evilfintables.com"))


if __name__ == "__main__":
    unittest.main()
