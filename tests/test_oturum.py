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


class GirisKendiliginden(TemizVeri):

    def test_finans_sitesi_akcaya_eklenir_ve_pencere_acilir(self):
        from unittest import mock
        from ulgen import uzmanlar
        with mock.patch.object(oturum, "hazir_mi", return_value=True), \
                mock.patch("ulgen.ajanlar.adres_guvenli_mi", return_value=True), \
                mock.patch.object(oturum.subprocess, "Popen") as ac:
            ac.return_value.poll.return_value = None       # pencere açık kaldı
            y = oturum.giris_baslat("fintables.com")
        self.assertIn("Eklendi: fintables.com artık AKÇA", y)
        self.assertIn("tarayıcı penceresi açılıyor", y)
        self.assertIn("fintables.com", uzmanlar.kullanici_kaynaklari("AKÇA"))
        ac.assert_called_once()

    def test_finans_disi_site_sorulur(self):
        from unittest import mock
        with mock.patch.object(oturum, "hazir_mi", return_value=True), \
                mock.patch("ulgen.ajanlar.adres_guvenli_mi", return_value=True), \
                mock.patch.object(oturum.subprocess, "Popen") as ac:
            y = oturum.giris_baslat("ornekforum.com")
        self.assertIn("hangi uzmana", y)
        ac.assert_not_called()

    def test_yardim_ve_yanlis_yonlendirme_yok(self):
        from ulgen import uzmanlar
        self.assertIn("kaynak ekle: AKÇA fintables.com",
                      uzmanlar.komut("kaynak ekle nerden yapılıyor"))
        self.assertIsNone(uzmanlar.sec("kaynak ekle nerden yapılıyor"))
        self.assertEqual(uzmanlar.sec("taş evin yapısı"), "BALBAL")

    def test_pencere_acilamazsa_neden_soylenir(self):
        from unittest import mock
        surec = mock.Mock()
        surec.poll.return_value = 1

        def baslat(*a, **k):
            k["stdout"].write("ModuleNotFoundError: No module named 'playwright'\n")
            k["stdout"].flush()
            self.assertTrue(k["cwd"])
            return surec
        with mock.patch.object(oturum, "hazir_mi", return_value=True), \
                mock.patch("ulgen.ajanlar.adres_guvenli_mi", return_value=True), \
                mock.patch.object(oturum.subprocess, "Popen", side_effect=baslat):
            y = oturum.giris_baslat("fintables.com")
        self.assertIn("Giriş penceresi açılamadı", y)
        self.assertIn("pip install playwright", y)


class MacOS12(unittest.TestCase):

    def test_sistem_node_kullanilir(self):
        import os
        with mock.patch.object(oturum, "_mac_surumu", return_value=12), \
                mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(oturum.os.path, "isfile",
                                  side_effect=lambda y: y == "/usr/local/bin/node"):
            os.environ.pop("PLAYWRIGHT_NODEJS_PATH", None)
            oturum.ortam_hazirla()
            self.assertEqual(os.environ["PLAYWRIGHT_NODEJS_PATH"], "/usr/local/bin/node")
            self.assertFalse(oturum.node_eksik_mi())

    def test_node_yoksa_ipucu(self):
        import os
        with mock.patch.object(oturum, "_mac_surumu", return_value=12), \
                mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PLAYWRIGHT_NODEJS_PATH", None)
            self.assertTrue(oturum.node_eksik_mi())
            with mock.patch.object(oturum, "hazir_mi", return_value=True):
                self.assertIn("Node.js 22", oturum.giris_baslat("fintables.com"))

    def test_libcpp_hatasi_taninir(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".log") as f:
            f.write("dyld: Symbol not found: (__ZNSt3__122__libcpp_verbose_abortEPKcz)\n"
                    "Exception: Connection closed while reading from the driver\n")
        self.assertIn("Node.js 22", oturum._hata_ozeti(f.name))

    def test_chrome_varsa_kullanilir(self):
        with mock.patch.object(oturum.sys, "platform", "darwin"), \
                mock.patch.object(oturum.os.path, "isfile", return_value=True):
            self.assertEqual(oturum.tarayici_secenegi(), {"channel": "chrome"})
