import http.client
import json
import os
import ssl
import time
import unittest

from .temel import TemizVeri
from ulgen import cihazlar, sunucu, tls
from ulgen.cekirdek import Ulgen


def istek(port, yol, yontem="GET", govde=None, basliklar=None, baglam=None,
          yetkisiz=False):
    basliklar = dict(basliklar or {})
    if baglam is None and not yetkisiz and "Authorization" not in basliklar \
            and "Cookie" not in basliklar:
        basliklar["Authorization"] = "Bearer " + cihazlar.olustur(
            "test-yerel", 1)[1]
    if baglam is not None:
        c = http.client.HTTPSConnection("127.0.0.1", port, context=baglam,
                                        timeout=10)
    else:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request(yontem, yol, body=govde, headers=basliklar)
    r = c.getresponse()
    veri = r.read()
    c.close()
    return r.status, veri


JSON = {"Content-Type": "application/json"}


class YerelSunucu(TemizVeri):

    def setUp(self):
        super().setUp()
        self.ulgen = Ulgen()
        self.srv = sunucu.yerel_sunucu(self.ulgen, 0)
        sunucu.arka_planda_calistir(self.srv)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_normal_istek(self):
        self.assertEqual(istek(self.port, "/saglik")[0], 200)
        d, _ = istek(self.port, "/sohbet", "POST",
                     json.dumps({"metin": "saat kaç"}), JSON)
        self.assertEqual(d, 200)

    def test_loopback_dinleme(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")

    def test_dns_rebinding_host_reddedilir(self):
        self.assertEqual(istek(self.port, "/durum", basliklar={
            "Host": "kotu.example.com"})[0], 403)

    def test_csrf_origin_reddedilir(self):
        b = dict(JSON, Origin="http://kotu.example.com")
        self.assertEqual(istek(self.port, "/sohbet", "POST",
                               json.dumps({"metin": "x"}), b)[0], 403)
        b = dict(JSON, **{"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(istek(self.port, "/durum", basliklar=b)[0], 403)
        b = dict(JSON, Origin="null")
        self.assertEqual(istek(self.port, "/durum", basliklar=b)[0], 403)

    def test_ayni_kaynak_origin_kabul(self):
        b = dict(JSON, Origin="http://127.0.0.1:%d" % self.port,
                 Host="127.0.0.1:%d" % self.port)
        self.assertEqual(istek(self.port, "/sohbet", "POST",
                               json.dumps({"metin": "saat kaç"}), b)[0], 200)

    def test_text_plain_post_reddedilir(self):
        d, _ = istek(self.port, "/sohbet", "POST",
                     json.dumps({"metin": "saat kaç"}),
                     {"Content-Type": "text/plain"})
        self.assertEqual(d, 415)
        d, _ = istek(self.port, "/sohbet", "POST", "metin=x",
                     {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(d, 415)

    def test_buyuk_ve_bozuk_govde(self):
        d, _ = istek(self.port, "/sohbet", "POST", "{bozuk", JSON)
        self.assertEqual(d, 200)    # boş mesaj gibi işlenir, çökmez
        self.assertEqual(istek(self.port, "/saglik")[0], 200)


class UzakSunucu(TemizVeri):
    """Cihaz belirteci isteyen HTTPS dinleyici (127.0.0.1 üzerinde sınanır)."""

    def setUp(self):
        super().setUp()
        self.ulgen = Ulgen()
        self.baglam = tls.ssl_baglami(["127.0.0.1"])
        self.limit = sunucu.HizSiniri(sinir=3, sure=60)
        self.srv = sunucu.uzak_sunucu(self.ulgen, "127.0.0.1", 0,
                                      self.baglam, self.limit)
        sunucu.arka_planda_calistir(self.srv)
        self.port = self.srv.server_address[1]
        self.guvenilen = ssl.create_default_context(
            cafile=tls.yollar()["ca_sert"])
        _, self.belirtec = cihazlar.olustur("deneme")

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def al(self, yol, belirtec=None, **kw):
        b = dict(JSON)
        if belirtec:
            b["Authorization"] = "Bearer " + belirtec
        return istek(self.port, yol, basliklar=b, baglam=self.guvenilen, **kw)

    def test_yetkisiz_401(self):
        self.assertEqual(self.al("/durum")[0], 401)
        self.assertEqual(self.al("/durum", "yanlis")[0], 401)

    def test_gecerli_belirtec_ve_tls_dogrulamasi(self):
        self.assertEqual(self.al("/durum", self.belirtec)[0], 200)

    def test_guvenilmeyen_ca_ile_baglanti_olmaz(self):
        with self.assertRaises(ssl.SSLError):
            istek(self.port, "/saglik", baglam=ssl.create_default_context())

    def test_duz_http_tls_portuna_calismaz(self):
        with self.assertRaises(Exception):
            istek(self.port, "/saglik")

    def test_yanlis_deneme_siniri_engeller(self):
        for _ in range(3):
            self.assertEqual(self.al("/durum", "yanlis")[0], 401)
        self.assertEqual(self.al("/durum", "yanlis")[0], 429)
        self.assertEqual(self.al("/durum", self.belirtec)[0], 429)

    def test_iptal_edilen_belirtec(self):
        kimlik = cihazlar.listele()[0]["id"]
        self.assertEqual(cihazlar.iptal(kimlik), 1)
        self.assertEqual(self.al("/durum", self.belirtec)[0], 401)

    def test_suresi_dolan_belirtec(self):
        _, b = cihazlar.olustur("kisa", gun=1)
        from ulgen import veritabani
        veritabani.sorgu("UPDATE cihazlar SET son_gecerlilik = "
                         "'2000-01-01 00:00:00' WHERE ad = 'kisa'")
        self.assertEqual(self.al("/durum", b)[0], 401)

    def test_post_belirtecsiz(self):
        d, _ = istek(self.port, "/sohbet", "POST",
                     json.dumps({"metin": "saat kaç"}), JSON,
                     baglam=self.guvenilen)
        self.assertEqual(d, 401)


class Belirtec(TemizVeri):

    def test_ozet_saklanir_belirtec_saklanmaz(self):
        _, b = cihazlar.olustur("x")
        from ulgen import ayar
        with open(ayar.VERI_TABANI, "rb") as f:
            self.assertNotIn(b.encode(), f.read())

    def test_eski_anahtar_tasinir(self):
        from ulgen import ayar
        with open(ayar.ANAHTAR_DOSYASI, "w") as f:
            f.write("eski-anahtar-degeri")
        self.assertTrue(cihazlar.eski_anahtari_tasi())
        self.assertFalse(os.path.exists(ayar.ANAHTAR_DOSYASI))
        self.assertIsNotNone(cihazlar.dogrula("eski-anahtar-degeri"))

    def test_hiz_siniri_sure_dolunca_acilir(self):
        h = sunucu.HizSiniri(sinir=2, sure=10)
        h.hata("1.1.1.1", 100)
        h.hata("1.1.1.1", 100)
        self.assertTrue(h.kilitli_mi("1.1.1.1", 105))
        self.assertFalse(h.kilitli_mi("1.1.1.1", 111))
        self.assertFalse(h.kilitli_mi("2.2.2.2", 105))

    def test_host_denetimi(self):
        for iyi in ("127.0.0.1:8765", "10.1.2.3", "[::1]:8765", "localhost"):
            self.assertTrue(sunucu.host_gecerli_mi(iyi), iyi)
        for kotu in ("kotu.com", "", "a.b.c:80", "127.0.0.1.kotu.com"):
            self.assertFalse(sunucu.host_gecerli_mi(kotu), kotu)


class Sertifika(TemizVeri):

    def test_adres_degisince_yenilenir(self):
        tls.ssl_baglami(["10.1.2.3"])
        ilk = open(tls.yollar()["sert"], "rb").read()
        tls.ssl_baglami(["10.1.2.3"])
        self.assertEqual(ilk, open(tls.yollar()["sert"], "rb").read())
        tls.ssl_baglami(["10.1.2.3", "10.9.9.9"])
        self.assertNotEqual(ilk, open(tls.yollar()["sert"], "rb").read())

    def test_ca_anahtari_sifreli_ve_izinli(self):
        tls.ssl_baglami(["10.1.2.3"])
        y = tls.yollar()
        self.assertNotIn(b"PRIVATE KEY", open(y["ca_anahtar"], "rb").read())
        self.assertEqual(oct(os.stat(y["ca_anahtar"]).st_mode & 0o777),
                         "0o600")
        self.assertEqual(oct(os.stat(y["anahtar"]).st_mode & 0o777), "0o600")


if __name__ == "__main__":
    unittest.main()
