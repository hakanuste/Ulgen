import json
import unittest
from datetime import datetime

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import saglik_veri, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class AjanKestirmeVerisiniGorur(TemizVeri):

    def test_dosya_yokken_kestirme_verisi_kullanilir(self):
        u = Ulgen()
        self.assertIn("Sağlık verisi bulunamadı", u.saglik.rapor())
        bugun = datetime.now()
        d = bugun.strftime("%Y-%m-%d")
        saglik_veri.ekle([
            {"tur": "adim", "deger": 6000, "zaman": d + "T12:00:00"},
            {"tur": "nabiz", "deger": 70, "zaman": d + "T10:00:00"},
            {"tur": "nabiz", "deger": 90, "zaman": d + "T11:00:00"},
            {"tur": "uyku", "deger": 420, "zaman": d + "T06:00:00"}])
        yanit = u.saglik.rapor()
        self.assertIn("Sağlık özeti", yanit)
        self.assertIn("6000", yanit)
        df = u.saglik.yukle()
        self.assertEqual(float(df.iloc[-1]["uyku_saat"]), 7.0)
        self.assertEqual(float(df.iloc[-1]["nabiz_ort"]), 80.0)

    def test_dosya_ve_kestirme_birlesir_kestirme_oncelikli(self):
        import os
        u = Ulgen()
        klasor = u.saglik.klasor()
        os.makedirs(klasor, exist_ok=True)
        bugun = datetime.now().strftime("%Y-%m-%d")
        with open(os.path.join(klasor, "ozet.csv"), "w", encoding="utf-8") as f:
            f.write("tarih,adim\n2020-01-01,1000\n%s,100\n" % bugun)
        saglik_veri.ekle([{"tur": "adim", "deger": 5000,
                           "zaman": bugun + "T12:00:00"}])
        df = u.saglik.yukle()
        self.assertEqual(float(df[df["tarih"] == bugun].iloc[0]["adim"]), 5000.0)
        self.assertIn("2020-01-01", list(df["tarih"]))


class KestirmeOzeti(TemizVeri):

    def test_sayi_oku_turkce_bicimler(self):
        o = saglik_veri.sayi_oku
        self.assertEqual((o(8421), o("8421"), o("8.421"), o("8,421"), o("72,5")),
                         (8421, 8421, 8421, 8421, 72.5))
        self.assertEqual(o("1 234"), 1234)
        with self.assertRaises(ValueError):
            o("x")

    def test_ozet_ekle_ve_ayni_gun_guncelleme(self):
        simdi = datetime(2026, 11, 2, 19, 0)
        self.assertEqual(saglik_veri.ozet_ekle(
            {"adim": "6.100", "nabiz": 72, "uyku_saat": 7.5}, simdi), (3, 0))
        self.assertEqual(saglik_veri.ozet_ekle({"adim": 8421}, simdi), (1, 0))
        b = saglik_veri.bugun(simdi)
        self.assertEqual((b["adim"], b["nabiz"], b["uyku_dk"]), (8421, 72, 450))

    def test_gecersiz(self):
        simdi = datetime(2026, 11, 2, 19, 0)
        self.assertEqual(saglik_veri.ozet_ekle({"adim": "x", "nabiz": 70}, simdi), (1, 1))
        for kotu in ({}, {"adim": ""}, [1]):
            with self.assertRaises(saglik_veri.SaglikHatasi):
                saglik_veri.ozet_ekle(kotu, simdi)


class SaglikVeri(TemizVeri):

    def setUp(self):
        super().setUp()
        veritabani.kur()

    def test_ekle_dogrula_ve_ozet(self):
        simdi = datetime(2026, 11, 2, 19, 0)
        e, a = saglik_veri.ekle([
            {"tur": "adim", "deger": 4000, "zaman": "2026-11-02T12:00:00"},
            {"tur": "adim", "deger": 4320, "zaman": "2026-11-02T18:00:00"},
            {"tur": "nabiz", "deger": 78, "zaman": "2026-11-02T18:30:00"},
            {"tur": "uyku", "deger": 432, "zaman": "2026-11-02T06:30:00"},
            {"tur": "nabiz", "deger": 999, "zaman": "2026-11-02T18:31:00"},
            {"tur": "bilinmez", "deger": 1, "zaman": "2026-11-02T18:31:00"},
            {"tur": "adim", "deger": "x", "zaman": "2026-11-02T18:31:00"},
        ])
        self.assertEqual((e, a), (4, 3))
        b = saglik_veri.bugun(simdi)
        self.assertEqual((b["adim"], b["nabiz"], b["uyku_dk"]),
                         (4320, 78, 432))
        self.assertEqual(saglik_veri.uyku_yazi(432), "7s 12dk")
        # aynı tür+zaman tekrar gelirse güncellenir, çoğalmaz
        saglik_veri.ekle([{"tur": "adim", "deger": 4500,
                           "zaman": "2026-11-02T18:00:00"}])
        self.assertEqual(saglik_veri.bugun(simdi)["adim"], 4500)

    def test_http_yetki_ve_sinir(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        govde = json.dumps({"olcumler": [
            {"tur": "adim", "deger": 10, "zaman": "2026-11-02T10:00:00"}]})
        self.assertEqual(istek(port, "/saglik/veri", "POST", govde, JSON,
                               yetkisiz=True)[0], 401)
        kod, ham = istek(port, "/saglik/veri", "POST", govde, JSON)
        self.assertEqual((kod, json.loads(ham)["eklenen"]), (200, 1))
        kod, ham = istek(port, "/saglik/veri", "POST", json.dumps(
            {"olcumler": [{}] * 501}), JSON)
        self.assertEqual(kod, 400)

    def test_http_ozet(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        govde = json.dumps({"adim": "5.432", "nabiz": 70, "uyku_saat": 7})
        self.assertEqual(istek(port, "/saglik/ozet", "POST", govde, JSON,
                               yetkisiz=True)[0], 401)
        kod, ham = istek(port, "/saglik/ozet", "POST", govde, JSON)
        self.assertEqual((kod, json.loads(ham)), (200, {"eklenen": 3, "atlanan": 0}))
        self.assertEqual(istek(port, "/saglik/ozet", "POST", "{}", JSON)[0], 400)
        b = json.loads(istek(port, "/saglik/bugun")[1])
        self.assertEqual((b["adim"], b["uyku_dk"]), (5432, 420))


if __name__ == "__main__":
    unittest.main()


class ListedenToplamTesti(TemizVeri):

    def test_liste_toplanir_nabizda_ilk(self):
        from ulgen import saglik_veri as sv
        self.assertEqual(sv._deger("adim", "120\n80,5\n300"), 500.5)
        self.assertEqual(sv._deger("adim", ["1", 2, "3"]), 6)
        self.assertEqual(sv._deger("nabiz", "71\n64\n80"), 71)
        self.assertEqual(sv._deger("adim", "8.421"), 8421)
        e, a = sv.ozet_ekle({"adim": "100\n200\n300"})
        self.assertEqual((e, a), (1, 0))
        self.assertEqual(sv.bugun()["adim"], 600)
