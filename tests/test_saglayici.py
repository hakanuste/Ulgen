"""Sağlayıcı yöneticisi: kota, geçiş, ücretsiz güvencesi, kalıcı kuyruk."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from tests.temel import TemizVeri
from ulgen import ayar, beyin, kota, kuyruk, veritabani
from ulgen.beyin import BeyinHatasi, OpenAIUyumluBeyin


class Sahte:
    """Yerel sahte sağlayıcı sunucusu; yol önekine göre davranış ayarlanır."""

    def __init__(self):
        self.mod = {}        # önek -> "ok" | "429" | "usage_yok" | "hata"
        self.sayac = {}      # önek -> gelen istek sayısı
        sahte = self

        class Istek(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _yaz(self, kod, veri, ek=None):
                govde = json.dumps(veri).encode()
                self.send_response(kod)
                self.send_header("Content-Type", "application/json")
                for k, v in (ek or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(govde)))
                self.end_headers()
                self.wfile.write(govde)

            def do_GET(self):
                self._yaz(200, {"data": [], "models": []})

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                self.rfile.read(n)
                onek = self.path.split("/")[1]
                sahte.sayac[onek] = sahte.sayac.get(onek, 0) + 1
                mod = sahte.mod.get(onek, "ok")
                if mod == "429":
                    return self._yaz(429, {"error": "kota"},
                                     {"Retry-After": "120"})
                if mod == "hata":
                    return self._yaz(500, {"error": "bozuk"})
                if onek == "gemini":
                    veri = {"candidates": [{"content": {"parts": [
                        {"text": "gemini yanıtı"}]}}]}
                    if mod != "usage_yok":
                        veri["usageMetadata"] = {"promptTokenCount": 11,
                                                 "candidatesTokenCount": 7}
                    return self._yaz(200, veri)
                veri = {"choices": [{"message": {"content": onek + " yanıtı"}}]}
                if mod != "usage_yok":
                    veri["usage"] = {"prompt_tokens": 20,
                                     "completion_tokens": 5}
                self._yaz(200, veri, {
                    "x-ratelimit-remaining-requests": "999",
                    "x-ratelimit-remaining-tokens": "5000"})

        self.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Istek)
        self.port = self.sunucu.server_address[1]
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()

    def kapat(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()


class SaglayiciTabani(TemizVeri):

    @classmethod
    def setUpClass(cls):
        cls.sahte = Sahte()
        taban = "http://127.0.0.1:%d" % cls.sahte.port
        cls.yamalar = [
            mock.patch.dict(OpenAIUyumluBeyin.TABANLAR, {
                "groq": taban + "/groq", "mistral": taban + "/mistral",
                "nvidia": taban + "/nvidia",
                "openrouter": taban + "/openrouter"}),
            mock.patch.object(beyin, "GEMINI_TABAN", taban + "/gemini"),
        ]
        for y in cls.yamalar:
            y.start()

    @classmethod
    def tearDownClass(cls):
        for y in cls.yamalar:
            y.stop()
        cls.sahte.kapat()

    def setUp(self):
        super().setUp()
        self.sahte.mod.clear()
        self.sahte.sayac.clear()
        self.ayar_yaz()

    def ayar_yaz(self, **ek):
        a = {"beyin": "bulut", "gemini_anahtar": "g", "groq_anahtar": "k",
             "mistral_anahtar": "m", "openrouter_anahtar": "o",
             "yerel_tur": "llamacpp",
             "llamacpp_adres": "http://127.0.0.1:1"}
        a.update(ek)
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)

    def ulgen(self):
        from ulgen.cekirdek import Ulgen
        return Ulgen()


class KotaTesti(SaglayiciTabani):

    def test_gercek_usage_gercek_diye_isaretlenir(self):
        u = self.ulgen()
        u.sohbet_isle("merhaba nasılsın")
        s = veritabani.sorgu("SELECT * FROM kota_olay", (), True)
        self.assertEqual(s[0]["saglayici"], "gemini")
        self.assertEqual((s[0]["giris_token"], s[0]["cikis_token"],
                          s[0]["gercek"]), (11, 7, 1))

    def test_usage_yoksa_tahmini(self):
        self.sahte.mod["gemini"] = "usage_yok"
        self.ulgen().sohbet_isle("merhaba nasılsın")
        s = veritabani.sorgu("SELECT * FROM kota_olay", (), True)
        self.assertEqual(s[0]["gercek"], 0)
        self.assertGreater(s[0]["giris_token"], 0)

    def test_rapor_gercek_ve_tahmini_ayri(self):
        self.ayar_yaz(bulut_sirasi=["groq"])
        self.ulgen().sohbet_isle("merhaba nasılsın")
        metin = kota.metin()
        self.assertIn("Tahmini (kendi sayacım)", metin)
        self.assertIn("GERÇEK", metin)
        self.assertIn("kalan_istek=999", metin)
        self.assertIn("maliyet 0", metin)

    def test_dakikalik_sinir_engeller(self):
        self.ayar_yaz(kota_sinirlari={"gemini": {"rpm": 2}})
        for _ in range(2):
            kota.kaydet("gemini", "m", 1, 1, True, "ok", 5)
        engelli, neden, _ = kota.engel("gemini")
        self.assertTrue(engelli)
        self.assertIn("dakikalık", neden)

    def test_gunluk_sinir_ve_yenilenme(self):
        self.ayar_yaz(kota_sinirlari={"groq": {"rpd": 1}})
        kota.kaydet("groq", "m", 1, 1, True, "ok", 5)
        engelli, _, bekle = kota.engel("groq")
        self.assertTrue(engelli)
        self.assertLessEqual(bekle, 86400)

    def test_gemini_gunu_pasifik_gece_yarisi(self):
        # 2026-11-02 12:00 UTC = 04:00 Pasifik -> gün başı 2026-11-02 08:00 UTC
        simdi = 1793620800.0
        bas = kota.gun_basi("gemini", simdi)
        self.assertEqual(time.gmtime(bas).tm_hour, 8)
        self.assertEqual(time.gmtime(kota.gun_basi("groq", simdi)).tm_hour, 0)

    def test_yerel_beyin_hic_engellenmez(self):
        self.assertFalse(kota.engel("ollama")[0])


class GecisTesti(SaglayiciTabani):

    def test_nvidia_saglayicisi_gemini_dolunca_devreye_girer(self):
        self.ayar_yaz(nvidia_anahtar="nvapi-x",
                      bulut_sirasi=["gemini", "nvidia", "groq"])
        self.sahte.mod["gemini"] = "429"
        r = self.ulgen().sohbet_isle("merhaba nasılsın")
        self.assertIn("nvidia yanıtı", r["yanit"])
        self.assertEqual(kota.SINIRLAR["nvidia"]["rpm"], 40)
        self.assertIn("NVIDIA", kota.metin())

    def test_429_olunca_siradaki_ucretsiz_saglayiciya_gecer(self):
        self.sahte.mod["gemini"] = "429"
        r = self.ulgen().sohbet_isle("merhaba nasılsın")
        self.assertIn("groq yanıtı", r["yanit"])
        self.assertTrue(kota.engel("gemini")[0])
        # engelliyken Gemini'ye yeniden istek gitmez
        onceki = self.sahte.sayac["gemini"]
        self.ulgen().sohbet_isle("bir şey daha")
        self.assertEqual(self.sahte.sayac["gemini"], onceki)

    def test_gercek_baslik_saklanir(self):
        self.ayar_yaz(bulut_sirasi=["groq"])
        self.ulgen().sohbet_isle("merhaba nasılsın")
        t = [x for x in kota.tablo() if x["saglayici"] == "groq"][0]
        self.assertEqual(t["gercek"]["kalan_istek"], "999")

    def test_sunucu_hatasi_siradakine_gecer_kota_saymaz(self):
        self.sahte.mod["gemini"] = "hata"
        r = self.ulgen().sohbet_isle("merhaba nasılsın")
        self.assertIn("groq yanıtı", r["yanit"])
        self.assertFalse(kota.engel("gemini")[0])


class UcretsizGuvenceTesti(SaglayiciTabani):

    def test_openrouter_ucretli_model_agdan_once_reddedilir(self):
        b = OpenAIUyumluBeyin("openrouter", "o", "anthropic/claude-sonnet")
        self.assertFalse(b.kullanilabilir_mi())
        with self.assertRaises(BeyinHatasi):
            b.yanitla("s", [{"role": "user", "content": "x"}])
        self.assertNotIn("openrouter", self.sahte.sayac)

    def test_openrouter_free_kabul(self):
        for m in ("meta/model:free", "openrouter/free"):
            self.assertTrue(kota.ucretsiz_mi("openrouter", m))

    def test_ucretli_gecis_ayari_yoktur_ve_etkisizdir(self):
        self.ayar_yaz(bulut_sirasi=["openrouter"],
                      openrouter_model="pahali/model",
                      ucretli_gecis=True, ucretli_izin=True)
        r = self.ulgen().sohbet_isle("merhaba nasılsın")
        self.assertNotIn("openrouter yanıtı", r["yanit"])
        self.assertNotIn("openrouter", self.sahte.sayac)
        self.assertTrue(kota.UCRETLI_YASAK)
        self.assertEqual(kota.MALIYET, 0.0)


class KuyrukTesti(SaglayiciTabani):

    def hepsini_doldur(self):
        for ad in ("gemini", "groq", "mistral", "openrouter"):
            kota.engel_koy(ad, 3600, "deneme: kota doldu")

    def test_kota_dolunca_kuyruga_alir_hatirlatici_calisir(self):
        self.hepsini_doldur()
        u = self.ulgen()
        r = u.sohbet_isle("bana zeytin hakkında bir şiir yaz")
        self.assertIn("kuyruğa aldım", r["yanit"])
        self.assertIn("Ücretli servise geçmem", r["yanit"])
        self.assertEqual(len(kuyruk.bekleyenler()), 1)
        self.assertEqual(sum(self.sahte.sayac.values()), 0)
        # AI yokken yerel işler sürer
        h = u.sohbet_isle("23:59 ilaç al diye hatırlat")
        self.assertNotIn("kuyruğa", h["yanit"])

    def test_yeniden_baslatmada_kuyruk_korunur_ve_islenir(self):
        self.hepsini_doldur()
        u1 = self.ulgen()
        u1.sohbet_isle("zeytin ağacı ne zaman budanır")
        veritabani.sorgu("UPDATE kuyruk SET durum='isleniyor'")  # yarıda kesilmiş
        veritabani.kapat()
        u2 = self.ulgen()               # açılışta kurtar()
        self.assertEqual(kuyruk.bekleyenler()[0]["durum"], "bekliyor")
        veritabani.sorgu("UPDATE kota_durum SET engel_son=0")  # kota yenilendi
        self.assertTrue(u2.kuyruk_isle())
        self.assertEqual(kuyruk.bekleyenler(), [])
        self.assertIn("yanıtlandı", u2.bildirimler()[-1]["metin"])
        son = veritabani.sorgu(
            "SELECT rol FROM sohbet ORDER BY id DESC LIMIT 2", (), True)
        self.assertEqual({s["rol"] for s in son}, {"kullanici", "asistan"})

    def test_kisisel_mesaj_buluta_gitmez_kuyruga_girer(self):
        u = self.ulgen()
        r = u.sohbet_isle("tansiyon ilacımı hangi saatte almalıyım")
        self.assertIn("YEREL", r["yanit"])
        self.assertEqual(sum(self.sahte.sayac.values()), 0)
        self.assertEqual(len(kuyruk.bekleyenler()), 1)
        self.assertEqual(kuyruk.bekleyenler()[0]["duyarli"], 1)
        # bulut açık olsa da kuyruk işleyicisi kişisel isteği buluta vermez
        self.assertFalse(u.kuyruk_isle())
        self.assertEqual(sum(self.sahte.sayac.values()), 0)

    def test_kisisel_mesaj_yerel_beyin_acilinca_yanitlanir(self):
        yerel = Sahte()
        try:
            u = self.ulgen()
            u.sohbet_isle("tansiyon ilacımı hangi saatte almalıyım")
            self.assertEqual(len(kuyruk.bekleyenler()), 1)
            # yerel beyin açıldı (sahte llama.cpp); bulut yine kullanılmaz
            self.ayar_yaz(beyin="otomatik", yerel_tur="llamacpp",
                          llamacpp_adres="http://127.0.0.1:%d" % yerel.port)
            u.yonlendirici.sifirla()
            self.assertTrue(u.kuyruk_isle())
            self.assertEqual(sum(self.sahte.sayac.values()), 0)
            self.assertEqual(yerel.sayac.get("v1"), 1)
            self.assertEqual(kuyruk.bekleyenler(), [])
        finally:
            yerel.kapat()

    def test_yerel_acikken_kisisel_mesaj_dogrudan_yerelde_yanitlanir(self):
        yerel = Sahte()
        try:
            self.ayar_yaz(beyin="otomatik", yerel_tur="llamacpp",
                          llamacpp_adres="http://127.0.0.1:%d" % yerel.port)
            r = self.ulgen().sohbet_isle("tansiyon ilacımı ne zaman almalıyım")
            self.assertIn("v1 yanıtı", r["yanit"])
            self.assertEqual(sum(self.sahte.sayac.values()), 0)
            self.assertEqual(kuyruk.bekleyenler(), [])
        finally:
            yerel.kapat()

    def test_suresi_dolan_istek_bildirilir_silinmez(self):
        self.hepsini_doldur()
        u = self.ulgen()
        u.sohbet_isle("uzun süre bekleyecek soru")
        veritabani.sorgu("UPDATE kuyruk SET olusturma=?", (time.time() - 90000,))
        u.kuyruk_isle()
        satir = veritabani.sorgu("SELECT * FROM kuyruk", (), True)[0]
        self.assertEqual(satir["durum"], "suresi_doldu")
        self.assertIn("süresi doldu", u.bildirimler()[-1]["metin"])

    def test_kuyruk_iptal_komutu(self):
        self.hepsini_doldur()
        u = self.ulgen()
        u.sohbet_isle("bekleyen soru")
        kimlik = kuyruk.bekleyenler()[0]["id"]
        self.assertIn("İptal", u.sohbet_isle("kuyruk iptal %d" % kimlik)["yanit"])
        self.assertEqual(kuyruk.bekleyenler(), [])

    def test_kuyruk_dolunca_reddeder(self):
        for i in range(kuyruk.AZAMI_BEKLEYEN):
            kuyruk.ekle("x%d" % i)
        self.assertIsNone(kuyruk.ekle("fazla"))


class YerelUlasimTesti(TemizVeri):
    def test_kapali_yerel_sunucu_hazir_gorunmez(self):
        from ulgen import kota
        kota._ULASIM.clear()
        from unittest import mock
        with mock.patch("ulgen.beyin.OllamaBeyin.kullanilabilir_mi",
                        return_value=False):
            self.assertFalse(kota.yerel_ulasilir_mi("ollama"))
        kota._ULASIM.clear()
        with mock.patch("ulgen.beyin.OllamaBeyin.kullanilabilir_mi",
                        return_value=True):
            self.assertTrue(kota.yerel_ulasilir_mi("ollama"))
        kota._ULASIM.clear()
