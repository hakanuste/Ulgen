"""Görev, randevu ve rutin: düzenle / sil; yapay zekâ kipi yerele sabit."""

import json
from datetime import datetime, timedelta

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import ayar, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class GorevDuzenleTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.u = Ulgen()
        self.g = self.u.zamanlayici.gorev
        gelecek = (datetime.now() + timedelta(days=3)).strftime("%d.%m")
        self.u.sohbet_isle("görev ekle: faturayı ode")
        self.u.sohbet_isle("randevu ekle: %s 14:30 dis hekimi" % gelecek)
        self.u.sohbet_isle("rutin ekle: her gün 07:00 yuruyus")
        self.id = {x["tur"]: x["id"] for x in self.g.liste_json()}

    def test_gorev_duzenle_ve_zamansiz(self):
        k = self.id["gorev"]
        self.assertIn("Düzelttim", self.g.duzenle(k, "Faturayı öde", "2030-02-01T10:00"))
        satir = [x for x in self.g.liste_json() if x["id"] == k][0]
        self.assertEqual((satir["baslik"], satir["zaman"]), ("Faturayı öde", "2030-02-01 10:00"))
        self.assertIn("Düzelttim", self.g.duzenle(k, "Faturayı öde", ""))
        self.assertIsNone([x for x in self.g.liste_json() if x["id"] == k][0]["zaman"])
        self.assertIn("boş", self.g.duzenle(k, "  ", ""))
        self.assertIn("biçiminde", self.g.duzenle(k, "x", "yarın"))

    def test_randevu_gecmis_reddedilir_ve_asama_sifirlanir(self):
        k = self.id["randevu"]
        self.assertIn("geçmiş", self.g.duzenle(k, "Diş", "2020-01-01 10:00"))
        veritabani.sorgu("UPDATE gorev SET asama=2 WHERE id=?", (k,))
        yeni = (datetime.now() + timedelta(days=9)).strftime("%Y-%m-%d %H:%M")
        self.assertIn("Düzelttim", self.g.duzenle(k, "Diş hekimi", yeni))
        self.assertEqual(veritabani.sorgu(
            "SELECT asama FROM gorev WHERE id=?", (k,), True)[0]["asama"], 0)

    def test_rutin_saat_gun_dogrulama(self):
        k = self.id["rutin"]
        self.assertIn("SS:DD", self.g.duzenle(k, "Yürüyüş", "7:5", "0,1"))
        self.assertIn("gün", self.g.duzenle(k, "Yürüyüş", "07:30", ""))
        self.assertIn("gün", self.g.duzenle(k, "Yürüyüş", "07:30", "9"))
        self.assertIn("Düzelttim", self.g.duzenle(k, "Yürüyüş", "07:30", "4,0,0"))
        s = [x for x in self.g.liste_json() if x["id"] == k][0]
        self.assertEqual((s["zaman"], s["tekrar"]), ("07:30", "0,4"))

    def test_sil_ve_olmayan_kayit(self):
        k = self.id["gorev"]
        self.assertIn("Sildim", self.g.sil(k))
        self.assertIn("yok", self.g.sil(k))
        self.assertIn("yok", self.g.duzenle(k, "x", ""))
        self.assertIn("yok", self.g.sil("1 OR 1=1"))
        self.assertNotIn(k, [x["id"] for x in self.g.liste_json()])

    def test_sohbet_komutlari(self):
        k = self.id["rutin"]
        self.assertIn("Düzelttim", self.u.sohbet_isle(
            "rutin düzelt #%d: her pazartesi ve cuma 18:00 dans" % k)["yanit"])
        s = [x for x in self.g.liste_json() if x["id"] == k][0]
        self.assertEqual((s["zaman"], s["tekrar"]), ("18:00", "0,4"))
        y = self.u.sohbet_isle("rutin sil %d" % k)["yanit"]
        self.assertIn("onay", y)
        self.assertIn(k, [x["id"] for x in self.g.liste_json()])
        self.assertIn("Sildim", self.u.sohbet_isle("rutin sil %d onay" % k)["yanit"])

    def test_http(self):
        srv = sunucu.yerel_sunucu(self.u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p, k = srv.server_address[1], self.id["gorev"]
        kod, h = istek(p, "/gorev/duzenle", "POST", json.dumps(
            {"id": k, "baslik": "Yeni ad", "zaman": ""}), JSON)
        self.assertEqual(kod, 200)
        self.assertIn("Düzelttim", json.loads(h)["yanit"])
        self.assertEqual(istek(p, "/gorev/duzenle", "POST", json.dumps({"id": "x"}), JSON)[0], 400)
        self.assertEqual(istek(p, "/gorev/sil", "POST", json.dumps({"id": k}), JSON)[0], 400)
        kod, h = istek(p, "/gorev/sil", "POST", json.dumps({"id": k, "onay": True}), JSON)
        self.assertEqual(kod, 200)
        self.assertIn("Sildim", json.loads(h)["yanit"])


class BeyinKipiTesti(TemizVeri):

    def test_varsayilan_yerel_ve_eski_kurulum_bir_kez_sabitlenir(self):
        self.assertEqual(ayar.VARSAYILAN["beyin"], "yerel")
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump({"beyin": "otomatik"}, f)
        self.assertTrue(ayar.beyni_yerele_sabitle())
        self.assertEqual(ayar.yukle()["beyin"], "yerel")
        ayar.guncelle("beyin", "otomatik")        # kullanıcı bilerek seçti
        self.assertFalse(ayar.beyni_yerele_sabitle())
        self.assertEqual(ayar.yukle()["beyin"], "otomatik")

    def test_mod_ucu(self):
        u = Ulgen()
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        self.assertEqual(istek(p, "/yz/mod", "POST", json.dumps({"mod": "hepsi"}), JSON)[0], 400)
        kod, h = istek(p, "/yz/mod", "POST", json.dumps({"mod": "bulut"}), JSON)
        self.assertEqual(kod, 400)
        kod, h = istek(p, "/yz/mod", "POST", json.dumps({"mod": "bulut", "onay": True}), JSON)
        self.assertEqual(kod, 200)
        self.assertEqual(ayar.yukle()["beyin"], "bulut")
        istek(p, "/yz/mod", "POST", json.dumps({"mod": "yerel"}), JSON)
        self.assertEqual(ayar.yukle()["beyin"], "yerel")


class HatirlaticiDuzenleTesti(TemizVeri):

    def test_duzenle_sil_http(self):
        u = Ulgen()
        u.sohbet_isle("23:50 su iç diye hatırlat")
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        kod, h = istek(p, "/ozet")
        kim = json.loads(h)["hatirlaticilar"][0]["id"]
        kod, h = istek(p, "/hatirlatici/duzenle", "POST", json.dumps(
            {"id": kim, "mesaj": "Su iç", "zaman": "2030-01-01T10:00"}), JSON)
        self.assertIn("Düzelttim", json.loads(h)["yanit"])
        self.assertEqual(istek(p, "/hatirlatici/duzenle", "POST", json.dumps(
            {"id": kim, "mesaj": "", "zaman": "2030-01-01T10:00"}), JSON)[0], 200)
        self.assertEqual(istek(p, "/hatirlatici/sil", "POST", json.dumps({"id": kim}), JSON)[0], 400)
        kod, h = istek(p, "/hatirlatici/sil", "POST", json.dumps({"id": kim, "onay": True}), JSON)
        self.assertIn("Sildim", json.loads(h)["yanit"])
        self.assertEqual(json.loads(istek(p, "/ozet")[1])["hatirlaticilar"], [])
