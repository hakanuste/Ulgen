"""İlaç dozu başına onay, hatırlatma döngüsü, yeniden başlatma, görevler."""

import json
from datetime import datetime, timedelta

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import ayar, kota, sunucu, veritabani
from ulgen.cekirdek import Ulgen
from ulgen.zamanlayici import Zamanlayici

G1 = datetime(2030, 1, 15)         # sabit deneme günü (Salı)


def an(gun, sa, dk=0, sn=30):
    return gun.replace(hour=sa, minute=dk, second=sn)


class Taban(TemizVeri):

    def setUp(self):
        super().setUp()
        self.mesajlar = []
        self.z = Zamanlayici(lambda m, e=None: self.mesajlar.append((m, e)))

    def plan_basi(self):
        """Planların oluşturma anını deneme gününün başına çeker."""
        veritabani.sorgu("UPDATE ilac_plan SET olusturma=?",
                         (G1.timestamp(),))

    def kur_ab(self):
        self.z.ilac.ekle("Alfa 08:00 20:00 yemekten sonra")
        self.z.ilac.ekle("Beta 08:00")
        self.plan_basi()

    def dozlar(self):
        return {d["id"]: d for d in veritabani.sorgu("SELECT * FROM doz", (), True)}

    def durum(self, ad, saat, gun=G1):
        for d in veritabani.sorgu("SELECT * FROM doz", (), True):
            if d["ilac_ad"] == ad and d["planli"] == gun.strftime(
                    "%Y-%m-%d ") + saat:
                return d["durum"]
        return None


class DozBasinaOnayTesti(Taban):

    def test_kabul_senaryosu_A08_A20_B08(self):
        self.kur_ab()
        self.z.adim(an(G1, 8))
        self.assertEqual({d["ilac_ad"] for d in self.dozlar().values()},
                         {"Alfa", "Beta"})
        self.assertEqual(len(self.mesajlar), 2)
        self.assertEqual(self.mesajlar[0][1]["tur"], "doz")
        # A-08 onayı yalnızca A-08'i değiştirir
        a08 = [i for i, d in self.dozlar().items() if d["ilac_ad"] == "Alfa"][0]
        self.assertIn("alındı", self.z.ilac.metinden_yanit("aldım D%d" % a08, an(G1, 8)))
        self.assertEqual(self.durum("Alfa", "08:00"), "alindi")
        self.assertEqual(self.durum("Beta", "08:00"), "bekliyor")
        self.z.adim(an(G1, 20))
        self.assertEqual(self.durum("Alfa", "20:00"), "bekliyor")
        self.assertEqual(self.durum("Alfa", "08:00"), "alindi")
        # ertesi gün A-08 yeni bir doz; dünkü onaydan etkilenmez
        self.z.adim(an(G1 + timedelta(days=1), 8))
        yarin = G1 + timedelta(days=1)
        self.assertEqual(self.durum("Alfa", "08:00", yarin), "bekliyor")
        self.assertEqual(self.durum("Alfa", "20:00"), "bekliyor")   # hâlâ açık
        self.assertEqual(self.durum("Beta", "08:00"), "bekliyor")

    def test_ciplak_tamam_hicbir_dozu_onaylamaz(self):
        self.kur_ab()
        self.z.adim(an(G1, 8))
        yanit = self.z.ilac.metinden_yanit("tamam", an(G1, 8))
        self.assertIn("onaylamaz", yanit)
        self.assertTrue(all(d["durum"] == "bekliyor"
                            for d in self.dozlar().values()))

    def test_birden_cok_doz_varken_belirsiz_aldim_sorar(self):
        self.kur_ab()
        self.z.adim(an(G1, 8))
        yanit = self.z.ilac.metinden_yanit("aldım", an(G1, 8))
        self.assertIn("Hangi doz", yanit)
        self.assertTrue(all(d["durum"] == "bekliyor"
                            for d in self.dozlar().values()))

    def test_ilac_adiyla_yanit(self):
        self.kur_ab()
        self.z.adim(an(G1, 8))
        self.z.ilac.metinden_yanit("beta aldım", an(G1, 8))
        self.assertEqual(self.durum("Beta", "08:00"), "alindi")
        self.assertEqual(self.durum("Alfa", "08:00"), "bekliyor")

    def test_tek_acik_doz_varsa_aldim_onu_kapatir(self):
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        self.z.adim(an(G1, 8))
        self.z.ilac.metinden_yanit("aldım", an(G1, 8))
        self.assertEqual(self.durum("Alfa", "08:00"), "alindi")

    def test_ilgisiz_cumle_dozu_etkilemez(self):
        self.kur_ab()
        self.z.adim(an(G1, 8))
        for c in ("marketten ekmek aldım", "kitabı aldım ve okudum bugün çok güzeldi"):
            self.assertIsNone(self.z.ilac.metinden_yanit(c, an(G1, 8)))
        self.assertTrue(all(d["durum"] == "bekliyor"
                            for d in self.dozlar().values()))

    def test_cifte_dokunus_ikinci_kez_degistirmez(self):
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        self.z.adim(an(G1, 8))
        self.z.ilac.yanit(1, "alindi")
        self.assertIn("zaten", self.z.ilac.yanit(1, "almadi"))
        self.assertEqual(self.durum("Alfa", "08:00"), "alindi")

    def test_almadim_ve_atla_ayri_durumlar(self):
        self.kur_ab()
        self.z.adim(an(G1, 8))
        self.z.ilac.metinden_yanit("almadım D1", an(G1, 8))
        self.z.ilac.metinden_yanit("atla D2", an(G1, 8))
        self.assertEqual(self.durum("Alfa", "08:00"), "almadi")
        self.assertEqual(self.durum("Beta", "08:00"), "atlandi")

    def test_duzelt_gecmiste_iz_birakir(self):
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        self.z.adim(an(G1, 8))
        self.z.ilac.yanit(1, "almadi")
        self.z.ilac.metinden_yanit("düzelt D1 aldım", an(G1, 8))
        self.assertEqual(self.durum("Alfa", "08:00"), "alindi")
        self.assertIn("almadi", self.z.ilac.gecmis_metni())


class HatirlatmaDongusuTesti(Taban):

    def test_bbes_dakikada_bir_tekrar_ve_ertele(self):
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        self.z.adim(an(G1, 8))                     # 1. bildirim
        self.z.adim(an(G1, 8, 2))                  # erken: yok
        self.assertEqual(len(self.mesajlar), 1)
        self.z.adim(an(G1, 8, 6))                  # 2. bildirim
        self.assertEqual(len(self.mesajlar), 2)
        self.assertIn("Tekrar", self.mesajlar[1][0])
        self.z.ilac.yanit(1, "ertele", 30, simdi=an(G1, 8, 6).timestamp())
        self.assertEqual(self.durum("Alfa", "08:00"), "ertelendi")
        self.z.adim(an(G1, 8, 20))                 # ertelenmiş: susar
        self.assertEqual(len(self.mesajlar), 2)
        self.z.adim(an(G1, 8, 40))                 # süre doldu: yeniden
        self.assertEqual(len(self.mesajlar), 3)

    def test_sessizce_vazgecmez_yanitsiz_olur_ve_bildirir(self):
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump({"ilac_azami_tekrar": 3}, f)
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        for dk in (0, 6, 12, 18):
            self.z.adim(an(G1, 8, dk))
        self.assertEqual(self.durum("Alfa", "08:00"), "yanitsiz")
        self.assertIn("YANITSIZ", self.mesajlar[-1][0])
        self.assertIn("bilmiyorum", self.mesajlar[-1][0])

    def test_yeniden_baslatmada_kalinan_yerden_surer(self):
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        self.z.adim(an(G1, 8))
        yeni = []
        z2 = Zamanlayici(lambda m, e=None: yeni.append(m))    # "yeniden başlat"
        z2.adim(an(G1, 8, 6))
        self.assertEqual(len(yeni), 1)
        self.assertIn("Tekrar", yeni[0])
        self.assertEqual(veritabani.sorgu(
            "SELECT bildirim_sayisi FROM doz", (), True)[0]["bildirim_sayisi"], 2)

    def test_kapaliyken_kacan_doz_gec_hatirlatilir_ya_da_yanitsiz(self):
        self.z.ilac.ekle("Alfa 08:00")
        self.plan_basi()
        self.z.adim(an(G1, 10))          # 2 saat geç: hatırlatılır
        self.assertEqual(self.durum("Alfa", "08:00"), "bekliyor")
        veritabani.sorgu("DELETE FROM doz")
        self.z.adim(an(G1, 15))          # 7 saat geç: yanıtsız + bilgi
        self.assertEqual(self.durum("Alfa", "08:00"), "yanitsiz")
        self.assertIn("alınıp alınmadığını bilmiyorum", self.mesajlar[-1][0])

    def test_plandan_once_dogan_doz_uretilmez(self):
        self.z.ilac.ekle("Alfa 08:00")
        veritabani.sorgu("UPDATE ilac_plan SET olusturma=?",
                         (an(G1, 12).timestamp(),))   # plan 12:00'de kuruldu
        self.z.adim(an(G1, 12, 31))
        self.assertEqual(self.dozlar(), {})

    def test_hafta_ici_plani(self):
        self.z.ilac.ekle("Alfa 08:00 hafta sonu")
        self.plan_basi()
        self.z.adim(an(G1, 8))             # salı: doz yok
        self.assertEqual(self.dozlar(), {})
        cmt = datetime(2030, 1, 19)
        veritabani.sorgu("UPDATE ilac_plan SET olusturma=?", (G1.timestamp(),))
        self.z.adim(an(cmt, 8))
        self.assertEqual(len(self.dozlar()), 1)


class YetkiVeBagimsizlikTesti(Taban):

    def test_model_ilac_yazamaz(self):
        u = Ulgen()
        self.assertNotIn("ilac", u.araclar.katalog().lower())
        self.assertIn("Bilinmeyen", u.araclar.calistir(
            "ilac_ekle", {"metin": "Zehir 08:00"}))
        self.assertEqual(veritabani.sorgu("SELECT * FROM ilac", (), True), [])

    def test_yapay_zeka_kapaliyken_de_dozlar_calisir(self):
        u = Ulgen()
        for ad in ("gemini", "groq", "mistral", "openrouter"):
            kota.engel_koy(ad, 3600, "kota")
        t = datetime.now() - timedelta(minutes=2)
        u.sohbet_isle("ilaç ekle: Alfa %02d:%02d" % (t.hour, t.minute))
        veritabani.sorgu("UPDATE ilac_plan SET olusturma=?",
                         (t.timestamp() - 3600,))
        u.zamanlayici.adim(datetime.now())
        self.assertTrue(u.bildirimler())
        self.assertEqual(u.bildirimler()[-1]["eylem"]["tur"], "doz")
        r = u.sohbet_isle("aldım D1")
        self.assertIn("alındı", r["yanit"])
        self.assertEqual(r["beyin"], "hızlı komut")

    def test_ilac_komutlari(self):
        u = Ulgen()
        self.assertIn("Kaydettim", u.sohbet_isle("ilaç ekle: Alfa 08:00 20:00")["yanit"])
        self.assertIn("Alfa", u.sohbet_isle("ilaçlarım")["yanit"])
        self.assertIn("durdurdum", u.sohbet_isle("ilaç durdur: alfa")["yanit"])
        self.assertEqual(veritabani.sorgu(
            "SELECT COUNT(*) AS n FROM ilac", (), True)[0]["n"], 1)   # silinmedi


class GenelHatirlaticiOnayTesti(Taban):
    """Bilinen kusur düzeltmesi: 'tamam' tüm hatırlatıcıları onaylıyordu."""

    def test_tamam_birden_cok_varken_sorar_ve_yalniz_birini_onaylar(self):
        simdi = datetime(2030, 1, 15, 10, 0)
        self.z.hatirlatici_kur("10:00 tansiyon ölç diye hatırlat", True, simdi - timedelta(hours=1))
        self.z.hatirlatici_kur("10:00 hap al diye hatırlat", True, simdi - timedelta(hours=1))
        self.z.adim(simdi)
        self.assertEqual(len(self.z.onay_bekleyenler()), 2)
        self.assertIn("Hangisi", self.z.onayla())
        self.assertEqual(len(self.z.onay_bekleyenler()), 2)
        self.assertIn("Yalnızca onu", self.z.onayla(2))
        kalan = self.z.onay_bekleyenler()
        self.assertEqual([h["id"] for h in kalan], [1])

    def test_tek_varsa_tamam_onu_onaylar(self):
        simdi = datetime(2030, 1, 15, 10, 0)
        self.z.hatirlatici_kur("10:00 hap al diye hatırlat", True, simdi - timedelta(hours=1))
        self.z.adim(simdi)
        self.assertIn("alındı", self.z.onayla())
        self.assertEqual(self.z.onay_bekleyenler(), [])


class GorevTesti(Taban):

    def test_gorev_ekle_bildir_tamamla(self):
        self.assertIn("Görev #1", self.z.gorev.gorev_ekle("faturayı öde yarın 10:00", an(G1, 9)))
        self.z.adim(an(G1, 12))
        self.assertEqual(self.mesajlar, [])
        self.z.adim(an(G1 + timedelta(days=1), 10, 1))
        self.assertIn("Görev zamanı", self.mesajlar[-1][0])
        self.z.adim(an(G1 + timedelta(days=1), 10, 20))   # bir kez bildirir
        self.assertEqual(len(self.mesajlar), 1)
        self.assertIn("GECİKMİŞ", self.z.gorev.listele("gorev", an(G1 + timedelta(days=1), 11)))
        self.assertIn("tamamlandı", self.z.gorev.bitir(1))
        self.assertEqual(self.z.gorev.listele("gorev"), "Açık görev yok.")

    def test_randevu_iki_asamali(self):
        self.assertIn("Randevu #1", self.z.gorev.randevu_ekle("16.01 14:30 diş hekimi", an(G1, 9)))
        self.z.adim(an(G1 + timedelta(days=1), 12))
        self.assertEqual(self.mesajlar, [])
        self.z.adim(an(G1 + timedelta(days=1), 13, 31))
        self.assertIn("yaklaşıyor", self.mesajlar[-1][0])
        self.z.adim(an(G1 + timedelta(days=1), 14, 31))
        self.assertIn("Randevu zamanı", self.mesajlar[-1][0])
        self.assertEqual(len(self.mesajlar), 2)

    def test_gecmis_randevu_reddedilir(self):
        self.assertIn("geçmişte", self.z.gorev.randevu_ekle("10.01.2030 14:30 x", an(G1, 9)))

    def test_rutin_gunde_bir_kez_ve_gun_filtresi(self):
        self.z.gorev.rutin_ekle("her pazartesi ve cuma 18:00 dans çalışması", an(G1, 9))
        satir = veritabani.sorgu("SELECT * FROM gorev", (), True)[0]
        self.assertEqual(satir["tekrar"], "0,4")
        self.z.adim(an(G1, 18, 1))             # salı: yok
        self.assertEqual(self.mesajlar, [])
        pzt = datetime(2030, 1, 21)
        self.z.adim(an(pzt, 18, 1))
        self.z.adim(an(pzt, 18, 20))
        self.assertEqual(len(self.mesajlar), 1)
        self.assertIn("dans", self.mesajlar[0][0])

    def test_her_gun_rutini_yeniden_baslatmada_cift_bildirmez(self):
        self.z.gorev.rutin_ekle("her gün 07:00 yürüyüş", an(G1, 5))
        self.z.adim(an(G1, 7, 1))
        yeni = []
        Zamanlayici(lambda m, e=None: yeni.append(m)).adim(an(G1, 7, 5))
        self.assertEqual(len(self.mesajlar), 1)
        self.assertEqual(yeni, [])

    def test_komutlar_hizli_yoldan(self):
        u = Ulgen()
        self.assertIn("Görev #1", u.sohbet_isle("görev ekle: rapor yaz yarın 11:00")["yanit"])
        self.assertIn("rapor yaz", u.sohbet_isle("görevlerim")["yanit"])
        self.assertIn("Rutin #2", u.sohbet_isle("rutin ekle: her gün 07:00 yürüyüş")["yanit"])
        self.assertIn("yürüyüş", u.sohbet_isle("rutinlerim")["yanit"])
        self.assertIn("tamamlandı", u.sohbet_isle("görev tamam 1")["yanit"])


class SunucuDozTesti(Taban):
    """Gerçek HTTP arka ucuna karşı: bir istek yalnızca bir dozu değiştirir."""

    def test_http_yaniti_tek_doz(self):
        u = Ulgen()
        u.zamanlayici.ilac.ekle("Alfa 08:00 20:00")
        u.zamanlayici.ilac.ekle("Beta 08:00")
        self.plan_basi()
        u.zamanlayici.adim(an(G1, 8))
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        try:
            port = srv.server_address[1]
            kod, ham = istek(port, "/ilac/yanit", "POST", json.dumps(
                {"doz": 1, "yanit": "alindi"}), JSON)
            self.assertEqual(kod, 200)
            self.assertIn("Diğer dozlara dokunmadım", json.loads(ham)["yanit"])
            bugun = json.loads(istek(port, "/ilac/bugun")[1])
            durumlar = {d["id"]: d["durum"] for d in bugun}
            self.assertEqual(durumlar, {1: "alindi", 2: "bekliyor"})
            # geçersiz gövdeler reddedilir
            for kotu in ({"doz": "1", "yanit": "alindi"}, {"doz": True, "yanit": "alindi"},
                         {"yanit": "alindi"}, {"doz": 2}):
                self.assertEqual(istek(port, "/ilac/yanit", "POST",
                                       json.dumps(kotu), JSON)[0], 400)
            self.assertEqual(self.dozlar()[2]["durum"], "bekliyor")
            # olmayan doz
            _, ham = istek(port, "/ilac/yanit", "POST",
                           json.dumps({"doz": 99, "yanit": "alindi"}), JSON)
            self.assertIn("yok", json.loads(ham)["yanit"])
        finally:
            srv.shutdown()
            srv.server_close()


class PanelUcNoktalariTesti(Taban):

    def test_gorevler_ve_sistem_json_sir_icermez(self):
        from ulgen import cihazlar
        u = Ulgen()
        u.sohbet_isle("görev ekle: rapor yaz yarın 11:00")
        u.sohbet_isle("rutin ekle: her gün 07:00 yürüyüş")
        belirtec = cihazlar.olustur("iPhone")[1]
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        try:
            port = srv.server_address[1]
            g = json.loads(istek(port, "/gorevler")[1])
            self.assertEqual(len(g["gorev"]), 1)
            self.assertEqual(len(g["rutin"]), 1)
            kod, ham = istek(port, "/sistem")
            self.assertEqual(kod, 200)
            sistem = json.loads(ham)
            self.assertTrue(sistem["butunluk"]["saglam"])
            self.assertEqual(sistem["cihazlar"][0]["ad"], "iPhone")
            self.assertNotIn(belirtec, ham.decode())      # belirteç sızmaz
            self.assertNotIn("ozet", sistem["cihazlar"][0])   # özet (hash) de yok
            kod, ham = istek(port, "/gorev/bitir", "POST",
                             json.dumps({"id": 1}), JSON)
            self.assertIn("tamamlandı", json.loads(ham)["yanit"])
            self.assertEqual(istek(port, "/gorev/bitir", "POST",
                                   json.dumps({"id": "1"}), JSON)[0], 400)
        finally:
            srv.shutdown()
            srv.server_close()
