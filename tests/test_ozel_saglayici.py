import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from ulgen import ayar, beyin, gizli, ozel_saglayici as oz
from tests.temel import TemizVeri


class SahteServis(BaseHTTPRequestHandler):
    def do_POST(self):
        govde = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SahteServis.son = (self.path, self.headers.get("Authorization"), govde["model"])
        veri = json.dumps({"choices": [{"message": {"content": "merhaba"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def log_message(self, *a):
        pass


class Ozel(TemizVeri):

    def test_dogrulama(self):
        for kotu in ({"baslik": "", "taban": "https://a.com/v1", "model": "m"},
                     {"baslik": "X", "taban": "http://dis.com/v1", "model": "m"},
                     {"baslik": "X", "taban": "ftp://a.com", "model": "m"},
                     {"baslik": "X", "taban": "https://u:p@a.com/v1", "model": "m"},
                     {"baslik": "X", "taban": "https://a.com/v1", "model": "a b"}):
            with self.assertRaises(oz.SaglayiciHatasi):
                oz.dogrula(kotu)
        t = oz.dogrula({"baslik": "DeepSeek Çin", "model": "deepseek-chat",
                        "taban": "https://api.deepseek.com/v1/chat/completions"})
        self.assertEqual((t["ad"], t["taban"]),
                         ("ozel_deepseek_cin", "https://api.deepseek.com/v1"))

    def test_ekle_anahtar_zincire_ve_ucretli_kullanilmaz(self):
        with self.assertRaises(oz.SaglayiciHatasi):          # bulutta anahtar şart
            oz.ekle({"baslik": "Deep", "taban": "https://api.deepseek.com/v1",
                     "model": "deepseek-chat"})
        oz.ekle({"baslik": "Deep", "taban": "https://api.deepseek.com/v1",
                 "model": "deepseek-chat", "anahtar": "sk-12345678abcd"})
        with open(ayar.AYAR_DOSYASI, encoding="utf-8") as f:
            self.assertNotIn("sk-12345678abcd", f.read())
        self.assertEqual(gizli.sir_oku("ozel_deep"), "sk-12345678abcd")
        y = beyin.BeyinYonlendirici(ayar.yukle)
        self.assertNotIn("ozel_deep", [b.saglayici for b in y._bulut(ayar.yukle())])
        oz.ekle({"baslik": "Deep", "taban": "https://api.deepseek.com/v1",
                 "model": "deepseek-chat", "ucretsiz": True})   # anahtar korunur
        self.assertIn("ozel_deep", [b.saglayici for b in y._bulut(ayar.yukle())])
        self.assertEqual(len(oz.liste()), 1)
        oz.sil("ozel_deep")
        self.assertEqual(oz.liste(), [])
        self.assertEqual(gizli.sir_oku("ozel_deep"), "")

    def test_yerel_sunucu_yerel_beyin_ve_dene(self):
        srv = HTTPServer(("127.0.0.1", 0), SahteServis)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        taban = "http://127.0.0.1:%d/v1" % srv.server_address[1]
        oz.ekle({"baslik": "LM Studio", "taban": taban, "model": "qwen"})
        y = beyin.BeyinYonlendirici(ayar.yukle)
        yereller = y._yerel(ayar.yukle())
        b = [x for x in yereller if x.saglayici == "ozel_lm_studio"][0]
        self.assertTrue(b.yerel)
        c = oz.dene("ozel_lm_studio")
        self.assertTrue(c["calisti"], c)
        self.assertEqual(SahteServis.son, ("/v1/chat/completions", None, "qwen"))

    def test_sunucu_ucu(self):
        from ulgen import sunucu
        from ulgen.cekirdek import Ulgen
        from tests.test_sunucu import istek
        u = Ulgen()
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        j = {"Content-Type": "application/json"}
        d, g = istek(port, "/yz/ozel", "POST", json.dumps(
            {"islem": "ekle", "baslik": "Claude", "taban": "https://api.anthropic.com/v1",
             "model": "claude-sonnet-5-5", "anahtar": "sk-ant-12345678"}).encode(), j)
        self.assertEqual(d, 200, g)
        d, g = istek(port, "/yz/ozel", "POST", b'{"islem": "liste"}', j)
        liste = json.loads(g)["liste"]
        self.assertEqual(liste[0]["son4"], "5678")
        self.assertNotIn("sk-ant", g.decode())
        d, g = istek(port, "/yz/saglayici", "POST",
                     json.dumps({"saglayici": "ozel_claude", "acik": False}).encode(), j)
        self.assertEqual(d, 200, g)
        d, _ = istek(port, "/yz/ozel", "POST", b'{"islem": "sil", "ad": "ozel_claude"}', j)
        self.assertEqual(d, 400)                     # onay gerekli


if __name__ == "__main__":
    unittest.main()
