"""iPhone takvim aktarımı (.ics): içerik, gizlilik, tek kullanımlık bağlantı."""

import json
import time
from datetime import datetime

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import ayar, sunucu, takvim, veritabani
from ulgen.cekirdek import Ulgen

G1 = datetime(2030, 1, 15, 6, 0)


def olaylar(metin):
    import icalendar
    return [c for c in icalendar.Calendar.from_ical(metin).walk("VEVENT")]


class TakvimTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.u = Ulgen()
        self.u.sohbet_isle("ilaç ekle: Alfa 08:00 20:00 yemekten sonra")
        self.u.sohbet_isle("ilaç ekle: Beta 09:00 hafta içi")
        self.u.zamanlayici.gorev.randevu_ekle("25.12.2030 14:30 diş hekimi", G1)
        self.u.zamanlayici.gorev.rutin_ekle("her gün 07:00 yürüyüş", G1)

    def test_gecerli_ics_ve_olay_sayisi(self):
        try:
            import icalendar  # noqa: F401
        except ImportError:
            self.skipTest("icalendar yok")
        metin = takvim.olustur(G1)
        self.assertTrue(metin.startswith("BEGIN:VCALENDAR\r\n"))
        ev = olaylar(metin)
        ilac = [e for e in ev if str(e["UID"]).startswith("ilac-")]
        self.assertEqual(len(ilac), 3 * 6)        # 3 plan saati x 6 tekrar
        self.assertEqual(len([e for e in ev if str(e["UID"]).startswith("randevu")]), 1)
        self.assertEqual(len([e for e in ev if str(e["UID"]).startswith("rutin")]), 1)

    def test_tekrar_kurallari_ve_alarmlar(self):
        try:
            import icalendar  # noqa: F401
        except ImportError:
            self.skipTest("icalendar yok")
        ev = {str(e["UID"]): e for e in olaylar(takvim.olustur(G1))}
        self.assertEqual(ev["ilac-1-0@ulgen"]["RRULE"]["FREQ"], ["DAILY"])
        hafta_ici = ev["ilac-3-0@ulgen"]["RRULE"]
        self.assertEqual(hafta_ici["BYDAY"], ["MO", "TU", "WE", "TH", "FR"])
        for e in ev.values():
            self.assertTrue(e.walk("VALARM"))
        rnd = ev["randevu-1@ulgen"]
        self.assertEqual(len(rnd.walk("VALARM")), 2)     # 60 dk önce + zamanında

    def test_varsayilan_basliklar_genel_ilac_adi_yok(self):
        metin = takvim.olustur(G1)
        for yasak in ("Alfa", "Beta", "yemekten", "diş hekimi", "yürüyüş"):
            self.assertNotIn(yasak, metin)
        self.assertIn("Ülgen: ilaç zamanı", metin)

    def test_ayrintili_acilinca_ad_yazilir(self):
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump({"takvim_ayrintili": True}, f)
        metin = takvim.olustur(G1)
        self.assertIn("İlaç: Alfa", metin)
        self.assertIn("diş hekimi", metin)

    def test_satirlar_75_sekizli_siniri(self):
        self.u.sohbet_isle("ilaç ekle: ÇokUzunİlaçAdı" + "ğ" * 60 + " 10:00")
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump({"takvim_ayrintili": True}, f)
        for satir in takvim.olustur(G1).split("\r\n"):
            self.assertLessEqual(len(satir.encode("utf-8")), 75)

    def test_durdurulan_ilac_cikmaz(self):
        self.u.sohbet_isle("ilaç durdur: Beta")
        self.assertNotIn("ilac-3-", takvim.olustur(G1))

    def test_gecmis_randevu_ve_tamam_gorev_cikmaz(self):
        sonra = datetime(2031, 1, 1)
        self.assertNotIn("randevu-1@", takvim.olustur(sonra))

    def test_baglanti_tek_kullanimlik_ve_omurlu(self):
        a = takvim.anahtar_uret()
        self.assertTrue(takvim.anahtar_tuket(a))
        self.assertFalse(takvim.anahtar_tuket(a))       # ikinci kez olmaz
        self.assertFalse(takvim.anahtar_tuket("uydurma"))
        b = takvim.anahtar_uret()
        takvim._TOKENLER[b] = time.time() - 1            # süresi dolmuş
        self.assertFalse(takvim.anahtar_tuket(b))


class TakvimSunucuTesti(TemizVeri):

    def test_http_akisi(self):
        u = Ulgen()
        u.sohbet_isle("ilaç ekle: Alfa 08:00")
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        try:
            port = srv.server_address[1]
            self.assertEqual(istek(port, "/takvim.ics", yetkisiz=True)[0], 403)       # anahtarsız
            self.assertEqual(istek(port, "/takvim.ics?t=uydurma", yetkisiz=True)[0], 403)
            kod, ham = istek(port, "/takvim/baglanti", "POST", "{}", JSON)
            adres = json.loads(ham)["adres"]
            kod, ics = istek(port, adres, yetkisiz=True)
            self.assertEqual(kod, 200)
            self.assertIn(b"BEGIN:VCALENDAR", ics)
            self.assertEqual(istek(port, adres)[0], 403)               # tekrar yok
        finally:
            srv.shutdown()
            srv.server_close()

    def test_uzak_sunucuda_baglanti_uretmek_belirtec_ister(self):
        """/takvim/baglanti POST'u yetki ister (yerel olmayan sunucuda)."""
        from ulgen import cihazlar, tls
        import ssl
        u = Ulgen()
        tls.ca_hazirla()
        baglam = tls.ssl_baglami(["127.0.0.1"])
        srv = sunucu.uzak_sunucu(u, "127.0.0.1", 0, baglam)
        sunucu.arka_planda_calistir(srv)
        try:
            port = srv.server_address[1]
            ist = ssl.create_default_context(cafile=tls.yollar()["ca"]) \
                if "ca" in tls.yollar() else ssl._create_unverified_context()
            ist.check_hostname = False
            kod, _ = istek(port, "/takvim/baglanti", "POST", "{}", JSON, ist)
            self.assertEqual(kod, 401)
            belirtec = cihazlar.olustur("iPhone")[1]
            kod, _ = istek(port, "/takvim/baglanti", "POST", "{}",
                           dict(JSON, Authorization="Bearer " + belirtec), ist)
            self.assertEqual(kod, 200)
        finally:
            srv.shutdown()
            srv.server_close()


class DuzeltUcNoktasiTesti(TemizVeri):

    def test_yanitsiz_doz_arayuzden_duzeltilir(self):
        u = Ulgen()
        u.zamanlayici.ilac.ekle("Alfa 08:00")
        veritabani.sorgu("UPDATE ilac_plan SET olusturma=?", (G1.timestamp() - 86400,))
        u.zamanlayici.adim(G1.replace(hour=15))      # Ülgen kapalıydı: yanıtsız
        self.assertEqual(veritabani.sorgu("SELECT durum FROM doz", (), True)[0]["durum"],
                         "yanitsiz")
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        try:
            port = srv.server_address[1]
            kod, ham = istek(port, "/ilac/duzelt", "POST",
                             json.dumps({"doz": 1, "yanit": "alindi"}), JSON)
            self.assertEqual(kod, 200)
            self.assertEqual(veritabani.sorgu("SELECT durum FROM doz", (), True)[0]["durum"],
                             "alindi")
            self.assertEqual(istek(port, "/ilac/duzelt", "POST",
                                   json.dumps({"doz": "1"}), JSON)[0], 400)
        finally:
            srv.shutdown()
            srv.server_close()
