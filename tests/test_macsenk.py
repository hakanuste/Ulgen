"""Mac Takvim/Hatırlatıcılar eşitlemesi ve Mac bildirimi (AppleScript yerine sahte)."""

import json
from datetime import datetime

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import ayar, macsenk, sunucu, veritabani
from ulgen.cekirdek import Ulgen

SU_AN = datetime(2030, 1, 15, 10, 0)


def sahte(takvim="", hatirlatici="", takvim_hata=None):
    def calistir(betik):
        if "Calendar" in betik and "Reminders" not in betik:
            if takvim_hata:
                raise macsenk.MacSenkHatasi(takvim_hata)
            return takvim
        return hatirlatici
    return calistir


def satirlar(*kayit):
    return "".join("\t".join(k) + "\n" for k in kayit)


def acik(tur=None):
    s = "SELECT * FROM gorev WHERE kaynak='mac' AND durum='acik'"
    if tur:
        s += " AND tur='%s'" % tur
    return veritabani.sorgu(s + " ORDER BY id", (), True)


class AyiklaTesti(TemizVeri):

    def test_gecerli_ve_bozuk_satirlar(self):
        c = ("u1\tDiş hekimi\t2030-01-20 14:30\n"
             "bozuk satır\n"
             "u2\t\t2030-01-20 15:00\n"          # adsız
             "u3\tHatalı zaman\t20.01.2030\n"
             "h1\tSüt al\t\n")
        k = macsenk.ayikla(c)
        self.assertEqual([x["kimlik"] for x in k], ["u1", "h1"])
        self.assertIsNone(k[1]["zaman"])


class EsitleTesti(TemizVeri):

    def test_yeni_kayitlar_gelir(self):
        r = macsenk.esitle(SU_AN, sahte(
            satirlar(("u1", "Diş hekimi", "2030-01-20 14:30")),
            satirlar(("h1", "Süt al", "2030-01-16 09:00"), ("h2", "Not", ""))))
        self.assertEqual(r["sayilar"]["yeni"], 3)
        self.assertEqual([g["baslik"] for g in acik("randevu")], ["Diş hekimi"])
        self.assertEqual(len(acik("gorev")), 2)
        self.assertEqual(acik("randevu")[0]["onceden_dk"], 60)

    def test_ikinci_kosu_cift_kayit_yapmaz_degisiklik_gunceller(self):
        t = satirlar(("u1", "Diş hekimi", "2030-01-20 14:30"))
        macsenk.esitle(SU_AN, sahte(t, ""))
        r = macsenk.esitle(SU_AN, sahte(t, ""))
        self.assertEqual(r["sayilar"]["yeni"], 0)
        self.assertEqual(len(acik("randevu")), 1)
        macsenk.esitle(SU_AN, sahte("", satirlar(("h1", "Süt al", "2030-01-16 09:00"))))
        r = macsenk.esitle(SU_AN, sahte("", satirlar(
            ("h1", "Süt ve ekmek al", "2030-01-17 09:00"))))
        self.assertEqual(r["sayilar"]["guncel"], 1)
        g = acik("gorev")
        self.assertEqual((g[0]["baslik"], g[0]["zaman"]),
                         ("Süt ve ekmek al", "2030-01-17 09:00"))

    def test_gecmis_hatirlatici_bildirim_yagdirmaz(self):
        bildirimler = []
        macsenk.esitle(SU_AN, sahte("", satirlar(("h1", "Eski", "2030-01-10 09:00"))))
        u = Ulgen()
        u.zamanlayici.gorev._bildir = lambda m, e=None: bildirimler.append(m)
        u.zamanlayici.adim(SU_AN)
        self.assertEqual(bildirimler, [])

    def test_kaynaktan_kalkan_kapanir(self):
        macsenk.esitle(SU_AN, sahte(
            satirlar(("u1", "Gelecek", "2030-01-20 14:30"),
                     ("u2", "Geçmiş", "2030-01-15 10:30")),
            satirlar(("h1", "Süt al", ""))))
        r = macsenk.esitle(datetime(2030, 1, 15, 12, 0), sahte("", ""))
        self.assertEqual(r["sayilar"]["kapandi"], 2)   # gelecek randevu + hatırlatıcı
        self.assertEqual([g["baslik"] for g in acik()], ["Geçmiş"])

    def test_ulgende_silinen_geri_gelmez_bitirilen_acilmaz(self):
        u = Ulgen()
        t = satirlar(("u1", "Diş hekimi", "2030-01-20 14:30"))
        h = satirlar(("h1", "Süt al", ""))
        macsenk.esitle(SU_AN, sahte(t, h))
        rid, gid = acik("randevu")[0]["id"], acik("gorev")[0]["id"]
        self.assertIn("Sildim", u.zamanlayici.gorev.sil(rid))
        u.zamanlayici.gorev.bitir(gid)
        macsenk.esitle(SU_AN, sahte(t, h))
        self.assertEqual(acik(), [])

    def test_izin_hatasi_digerini_engellemez(self):
        r = macsenk.esitle(SU_AN, sahte(
            "", satirlar(("h1", "Süt al", "")),
            takvim_hata="İzin verilmemiş: Otomasyon"))
        self.assertEqual(r["sayilar"]["yeni"], 1)
        self.assertTrue(any("Takvim" in h and "İzin" in h for h in r["hata"]))
        self.assertEqual(macsenk.durum()["hata"], r["hata"])

    def test_betikler(self):
        self.assertIn("allday event", macsenk.TAKVIM_BETIGI)
        self.assertIn("completed is false", macsenk.HATIRLATICI_BETIGI)
        self.assertIn("quit", macsenk.TAKVIM_BETIGI)


class BildirimTesti(TemizVeri):

    def test_komut_metni_arguman_olarak_gecer(self):
        k = macsenk.bildirim_komutu('Doz "zamanı"\n$(rm -rf ~)', "Ülgen")
        self.assertEqual(k[0], "osascript")
        self.assertIn('Doz "zamanı" $(rm -rf ~)', k)       # tek parça, kabuk yok
        self.assertEqual(k[-1], "Ülgen")

    def test_mac_degilse_ya_da_kapaliysa_gostermez(self):
        orijinal = macsenk.mac_mi
        try:
            macsenk.mac_mi = lambda: False
            self.assertFalse(macsenk.bildirim_goster("x"))
            macsenk.mac_mi = lambda: True
            ayar.guncelle("mac_bildirim", False)
            self.assertFalse(macsenk.bildirim_goster("x"))
        finally:
            macsenk.mac_mi = orijinal

    def test_bildir_mac_bildirimini_cagirir(self):
        gelen = []
        orijinal = macsenk.bildirim_goster
        macsenk.bildirim_goster = lambda m, b="Ülgen": gelen.append(m)
        try:
            Ulgen().bildir("Hatırlatma zamanı: su iç.")
        finally:
            macsenk.bildirim_goster = orijinal
        self.assertIn("Hatırlatma zamanı: su iç.", gelen)


class SunucuTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.u = Ulgen()
        self.srv = sunucu.yerel_sunucu(self.u, 0)
        sunucu.arka_planda_calistir(self.srv)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_durum_ve_ayar(self):
        d, g = istek(self.port, "/mac/durum")
        self.assertEqual(d, 200)
        j = json.loads(g)
        self.assertTrue(j["senk"] and j["bildirim"])
        d, g = istek(self.port, "/mac/ayar", "POST",
                     json.dumps({"senk": False, "bildirim": False}), JSON)
        j = json.loads(g)
        self.assertEqual(d, 200)
        self.assertFalse(j["senk"] or j["bildirim"])
        self.assertFalse(ayar.yukle()["mac_senk"])

    def test_gocte_sutunlar_var(self):
        sut = [r["name"] for r in veritabani.sorgu(
            "PRAGMA table_info(gorev)", (), True)]
        self.assertIn("kaynak", sut)
        self.assertIn("dis_kimlik", sut)


class TakvimAyarSunucuTesti(SunucuTesti):

    def test_get_ve_post(self):
        d, g = istek(self.port, "/takvim/ayar")
        self.assertEqual((d, json.loads(g)["tekrar"]), (200, 6))
        d, g = istek(self.port, "/takvim/ayar", "POST",
                     json.dumps({"tekrar": 1, "aralik": 10}), JSON)
        self.assertEqual((d, json.loads(g)["tekrar"], json.loads(g)["aralik"]),
                         (200, 1, 10))
        d, _ = istek(self.port, "/takvim/ayar", "POST",
                     json.dumps({"tekrar": 99}), JSON)
        self.assertEqual(d, 400)


class BelirtecBicimleriTesti(SunucuTesti):

    def _dene(self, basliklar):
        return istek(self.port, "/saglik/ozet", "POST", '{"adim": 5}',
                     dict(JSON, **basliklar), yetkisiz=True)[0]

    def test_gorunmez_karakterli_ve_ozel_baslik(self):
        from ulgen import cihazlar
        t = cihazlar.olustur("kestirme", 1)[1]
        self.assertEqual(self._dene({"Authorization": "Bearer " + t}), 200)
        # yapıştırmadan gelen bölünmez boşluk (UTF-8: \xc2\xa0) ve fazladan boşluk
        self.assertEqual(self._dene(
            {"Authorization": "Bearer " + t + "  "}), 200)
        self.assertEqual(self._dene({"Authorization": "bearer " + t}), 401)
        self.assertEqual(self._dene({"X-Ulgen-Token": " " + t + " "}), 200)
        self.assertEqual(self._dene({"X-Ulgen-Token": t[:-1] + "x"}), 401)
        self.assertEqual(self._dene({}), 401)

    def test_govdede_belirtec(self):
        from ulgen import cihazlar
        t = cihazlar.olustur("kestirme", 1)[1]
        d, g = istek(self.port, "/saglik/ozet", "POST",
                     json.dumps({"belirtec": t + " \u00a0", "adim": 5}), JSON,
                     yetkisiz=True)
        self.assertEqual(d, 200)
        d, _ = istek(self.port, "/saglik/ozet", "POST",
                     json.dumps({"belirtec": t[:-1] + "x", "adim": 5}), JSON,
                     yetkisiz=True)
        self.assertEqual(d, 401)
        d, _ = istek(self.port, "/sohbet", "POST",
                     json.dumps({"belirtec": t, "metin": "a"}), JSON,
                     yetkisiz=True)
        self.assertEqual(d, 401)      # yalnız /saglik/ozet'te geçerli
