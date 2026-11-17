import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from ulgen import ayar, beyin
from tests.temel import TemizVeri


class Sunucu(BaseHTTPRequestHandler):
    n_ctx = 2048
    sinir_karakter = 10 ** 9
    istekler = []

    def _yaz(self, kod, veri):
        v = json.dumps(veri).encode()
        self.send_response(kod)
        self.send_header("Content-Length", str(len(v)))
        self.end_headers()
        self.wfile.write(v)

    def do_GET(self):
        if self.path == "/props":
            return self._yaz(200, {"default_generation_settings": {"n_ctx": self.n_ctx}})
        return self._yaz(200, {"data": [{"id": "m"}]})

    def do_POST(self):
        g = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        boy = sum(len(m["content"]) for m in g["messages"])
        Sunucu.istekler.append((boy, len(g["messages"]), g["max_tokens"]))
        if boy > self.sinir_karakter:
            return self._yaz(500, {"error": {"code": 500, "type": "server_error",
                                             "message": "Context size has been exceeded."}})
        return self._yaz(200, {"choices": [{"message": {"content": "tamam"}}]})

    def log_message(self, *a):
        pass


class BaglamSiniri(TemizVeri):

    def setUp(self):
        super().setUp()
        Sunucu.istekler = []
        beyin._CTX_ONBELLEK.clear()
        self.srv = HTTPServer(("127.0.0.1", 0), Sunucu)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        self.adres = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def test_butce_sunucunun_baglamina_gore(self):
        b = beyin.LlamaCppBeyin(self.adres)
        self.assertLess(b.sistem_butce + b.gecmis_butce + b.cikti, 2048)
        self.assertEqual(b.cikti, 512)

    def test_tasarsa_kisa_istemle_yeniden_dener(self):
        from ulgen.cekirdek import Ulgen
        ayar.guncelle("llamacpp_adres", self.adres)
        ayar.guncelle("beyin", "yerel")
        ayar.guncelle("kapali_beyinler", ["ollama"])
        u = Ulgen()
        for i in range(6):
            u._kaydet("kullanici", "eski soru %d " % i + "x" * 600)
            u._kaydet("asistan", "eski yanıt %d " % i + "y" * 600)
        Sunucu.sinir_karakter = 10 ** 9
        u.sohbet_isle("şanzıman nedir?")
        ana = [x for x in Sunucu.istekler if x[2] == 512]    # özetleme isteği değil
        ilk = ana[-1][0]
        Sunucu.istekler = []
        Sunucu.sinir_karakter = ilk - 1          # ilk boyda istek taşsın
        Sunucu.kayit_boy = []
        c = u.sohbet_isle("şanzıman nedir?")
        self.assertEqual(c["yanit"], "tamam")
        ana = [x for x in Sunucu.istekler if x[2] == 512]
        self.assertEqual(len(ana), 2)
        self.assertLess(ana[1][0], ana[0][0])
        self.assertEqual(ana[1][1], 2)               # sistem + yalnız son soru

    def test_dar_baglamda_istem_kisa(self):
        from types import SimpleNamespace as N
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        genis = u.sistem_istemi(N(yerel=True, sistem_butce=3000), "merhaba")
        dar = u.sistem_istemi(N(yerel=True, sistem_butce=650), "merhaba")
        self.assertLess(len(dar), len(genis) * 0.75)
        self.assertLess(len(dar), 650 * 3.2 * 2.2)


class AnythingLLMKisa(TemizVeri):

    def test_anythingllm_kisa_istem_ve_bos_500_yeniden(self):
        from ulgen import ozel_saglayici as oz
        from ulgen.beyin import KotaliBeyin, OzelBeyin
        t = {"ad": "ozel_anythingllm", "baslik": "AnythingLLM",
             "taban": "http://127.0.0.1:3001/api/v1/openai", "model": "assistant-chats"}
        b = KotaliBeyin(OzelBeyin(t, "anahtar-12345678"), "ozel_anythingllm")
        self.assertTrue(b.kisa)
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        istem = u.sistem_istemi(b, "Daewoo Musso şanzımanı nedir?")
        self.assertLess(len(istem), 3500)
        self.assertNotIn("hatirlatici_kur", istem)    # araç listesi yok
        self.assertIsNotNone(oz)

    def test_dogrulama_hata_iletisini_denetlemez(self):
        from ulgen import dogrulama
        y = ("Beyin yanıt veremedi:\nAnythingLLM (yerel): HTTP 500:\nClaude (bulut): "
             "HTTP 400: credit balance is too low to access the Anthropic API")
        from unittest import mock
        with mock.patch.object(dogrulama, "acik_mi", return_value=True):
            self.assertFalse(dogrulama.uygun_mu("Musso şanzımanı nedir?", y))
            self.assertTrue(dogrulama.uygun_mu(
                "Musso şanzımanı nedir?", "Daewoo Musso 3.2 Mercedes 722 ailesi bir "
                "otomatik şanzıman kullanır; 1998 modellerde dört ileri vites vardır. "
                "Arazi şanzımanı BorgWarner yapımı, yarı zamanlı dört çekerdir."))
