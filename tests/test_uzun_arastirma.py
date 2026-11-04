"""Uzun araştırma görevi: maddeleme, Obsidian notları, kaldığı yerden devam."""

import json
import os
import shutil

from .temel import TemizVeri
from ulgen import ajan_kayit, ajanlar, ayar, iptal, uzun_arastirma

OZAN = (
    "Odaklanılacak Ozanlar ve Eserler Listesi:\n"
    "1. 12-13. Yüzyıl: Hoca Ahmed Yesevî (Divan-ı Hikmet), "
    "Yunus Emre (Divan, Risâletü'n-Nushiyye), Hacı Bektaş Veli (Makâlât).\n"
    "2. 14. Yüzyıl: Gülşehrî (Mantıku't-Tayr, Feleknâme), "
    "Sultan Veled (Türkçe Manzumeler).\n"
    "Araştırma ve Analiz İstekleri:\n"
    "1. Kronolojik kelime kadrosu ve söz varlığı analizi yap.\n")


class SahteAjan:
    def __init__(self, patla_sorgu=None):
        self.sorgular = []
        self.patla = patla_sorgu

    def ara(self, sorgu, adet=5):
        self.sorgular.append(sorgu)
        if self.patla and self.patla in sorgu:
            raise RuntimeError("limit")
        return [{"baslik": "K " + sorgu, "adres": "https://ornek.org/" +
                 str(len(self.sorgular)), "ozet": "özet"},
                {"baslik": "Kitap", "adres": "https://ornek.org/k.pdf",
                 "ozet": "pdf"}]

    def sayfa_metni(self, adres, hedef=3000):
        return "sayfa içeriği " + adres


class AyirmaTesti(TemizVeri):

    def test_ozan_listesi_maddelere_ayrilir(self):
        m = uzun_arastirma.maddelere_ayir(OZAN)
        adlar = [x["ad"] for x in m]
        self.assertEqual(adlar, ["Hoca Ahmed Yesevî", "Yunus Emre",
                                 "Hacı Bektaş Veli", "Gülşehrî", "Sultan Veled"])
        self.assertIn("Yunus Emre Risâletü'n-Nushiyye", m[1]["sorgular"])
        self.assertEqual(len(m[3]["sorgular"]), 3)

    def test_numarali_satirlar_ve_tek_gorev(self):
        g = "Şunları araştır:\n1. Zeytin budama zamanlaması nedir\n2. Biyokömür nasıl yapılır\n"
        self.assertEqual([x["ad"] for x in uzun_arastirma.maddelere_ayir(g)],
                         ["Zeytin budama zamanlaması nedir",
                          "Biyokömür nasıl yapılır"])
        self.assertEqual(len(uzun_arastirma.maddelere_ayir("kısa konu")), 1)

    def test_uzunluk_siniri(self):
        m = uzun_arastirma.maddelere_ayir("a" * 100000)
        self.assertLessEqual(len(m[0]["sorgular"][0]), 300)


class CalistirTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.kasa = os.path.join(os.path.expanduser("~"), "ObsidyenAra")
        shutil.rmtree(self.kasa, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.kasa, True)
        os.makedirs(os.path.join(self.kasa, ".obsidian"))
        a = ayar.yukle()
        a["kasa"] = self.kasa
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(a, f)
        iptal.temizle()
        ajan_kayit.sifirla()

    def notlar(self):
        s = []
        for k, _, a in os.walk(os.path.join(self.kasa, "Ülgen")):
            s += [os.path.join(k, x) for x in a]
        return sorted(os.path.relpath(x, self.kasa) for x in s)

    def test_notlar_ve_dizin_yazilir(self):
        ajan = SahteAjan()
        ozet = uzun_arastirma.calistir(OZAN, ajan, bekle=lambda s: None)
        self.assertIn("5 madde araştırıldı", ozet)
        n = self.notlar()
        self.assertEqual(len(n), 6)               # 5 madde + dizin
        yunus = [x for x in n if x.endswith("Yunus Emre.md")][0]
        with open(os.path.join(self.kasa, yunus), encoding="utf-8") as f:
            ic = f.read()
        self.assertIn("sayfa içeriği https://ornek.org/", ic)
        self.assertIn("PDF bağlantıları", ic)
        dizin = [x for x in n if x.endswith("00 Dizin.md")][0]
        with open(os.path.join(self.kasa, dizin), encoding="utf-8") as f:
            self.assertIn("[[Yunus Emre]]", f.read())

    def test_hata_olursa_not_yine_yazilir_ve_belirtilir(self):
        ajan = SahteAjan(patla_sorgu="Gülşehrî")
        ozet = uzun_arastirma.calistir(OZAN, ajan, bekle=lambda s: None)
        self.assertIn("bazı aramalar alınamadı", ozet)
        gul = [x for x in self.notlar() if x.endswith("Gülşehrî.md")][0]
        with open(os.path.join(self.kasa, gul), encoding="utf-8") as f:
            self.assertIn("Alınamayanlar", f.read())

    def test_iptal_sonrasi_kalan_maddelerden_surer(self):
        ajan = SahteAjan()
        say = []

        def bekle(s):
            say.append(1)
            if len(say) == 8:
                iptal.ayarla()
        with self.assertRaises(iptal.Iptal):
            uzun_arastirma.calistir(OZAN, ajan, bekle=bekle)
        iptal.temizle()
        yazilan = len(self.notlar())
        self.assertTrue(0 < yazilan < 5)
        ikinci = SahteAjan()
        ozet = uzun_arastirma.calistir(OZAN, ikinci, bekle=lambda s: None)
        self.assertIn("5 madde araştırıldı", ozet)
        self.assertEqual(len(self.notlar()), 6)
        self.assertLess(len(ikinci.sorgular), 15)   # yapılanlar tekrarlanmadı

    def test_arastirma_ajani_uzun_gorevi_yonlendirir(self):
        class Baglam:
            def metin_ozetle(self, m, h):
                return m[:h]
        aj = ajanlar.ArastirmaAjani(Baglam())
        aj.ara = SahteAjan().ara
        aj.sayfa_metni = SahteAjan().sayfa_metni
        old = uzun_arastirma.SORGU_ARASI_SN
        uzun_arastirma.SORGU_ARASI_SN = 0
        try:
            ozet = aj.arastir(OZAN)
        finally:
            uzun_arastirma.SORGU_ARASI_SN = old
        self.assertIn("madde araştırıldı", ozet)
