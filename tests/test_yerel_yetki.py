import json
import time
import unittest

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import ayar, cihazlar, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class YerelYetki(TemizVeri):

    def baslat(self):
        self.u = Ulgen()
        self.srv = sunucu.yerel_sunucu(self.u, 0)
        sunucu.arka_planda_calistir(self.srv)
        self.port = self.srv.server_address[1]
        self.addCleanup(self.srv.shutdown)

    def test_belirtecsiz_reddedilir_ama_acik_uclar_acik(self):
        self.baslat()
        kod, ham = istek(self.port, "/sistem", yetkisiz=True)
        self.assertEqual(kod, 401)
        self.assertTrue(json.loads(ham)["giris"])
        self.assertEqual(istek(self.port, "/saglik", yetkisiz=True)[0], 200)
        self.assertEqual(istek(self.port, "/", yetkisiz=True)[0], 200)

    def test_giris_anahtari_tek_kullanimlik_ve_cerez(self):
        self.baslat()
        anahtar = cihazlar.giris_anahtari_uret()
        c = __import__("http.client").client.HTTPConnection(
            "127.0.0.1", self.port, timeout=10)
        c.request("GET", "/giris?t=" + anahtar)
        r = c.getresponse()
        r.read()
        self.assertIn(r.status, (200, 302, 303))
        cerez = r.getheader("Set-Cookie")
        c.close()
        self.assertIn("ulgen_oturum=", cerez)
        self.assertIn("HttpOnly", cerez)
        self.assertIn("SameSite=Strict", cerez)
        deger = cerez.split(";")[0]
        self.assertEqual(istek(self.port, "/sistem", basliklar={
            "Cookie": deger}, yetkisiz=True)[0], 200)
        # ikinci kullanım reddedilir
        c = __import__("http.client").client.HTTPConnection(
            "127.0.0.1", self.port, timeout=10)
        c.request("GET", "/giris?t=" + anahtar)
        r = c.getresponse()
        r.read()
        c.close()
        self.assertIn(r.status, (400, 401, 403))
        self.assertIsNone(r.getheader("Set-Cookie"))

    def test_sureli_anahtar_kullanilamaz(self):
        anahtar = cihazlar.giris_anahtari_uret()
        gercek = time.time
        try:
            time.time = lambda: gercek() + cihazlar.GIRIS_OMRU_SN + 5
            self.assertIsNone(cihazlar.giris_anahtari_tuket(anahtar))
        finally:
            time.time = gercek

    def test_iptal_edilen_cihaz_reddedilir(self):
        self.baslat()
        kimlik, belirtec = cihazlar.olustur("gecici", 1)
        bas = {"Authorization": "Bearer " + belirtec}
        self.assertEqual(istek(self.port, "/sistem", basliklar=bas,
                               yetkisiz=True)[0], 200)
        cihazlar.iptal(kimlik)
        self.assertEqual(istek(self.port, "/sistem", basliklar=bas,
                               yetkisiz=True)[0], 401)

    def test_eski_kip_yerel_yetki_kapali(self):
        a = ayar.yukle()
        a["yerel_yetki"] = False
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)
        self.baslat()
        kod, ham = istek(self.port, "/sistem", yetkisiz=True)
        self.assertEqual(kod, 200)
        self.assertFalse(json.loads(ham)["yerel_yetki"])


if __name__ == "__main__":
    unittest.main()
