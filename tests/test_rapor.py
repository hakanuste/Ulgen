import unittest
from datetime import datetime
from unittest import mock

from .temel import TemizVeri
from ulgen import ayar, rapor, saglik_veri, veritabani
from ulgen.gorev import Gorevler
from ulgen.rapor import Raporlar


class RaporTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            f.write('{"rapor_acik": true}')
        veritabani.kur()
        self.gelen = []
        self.r = Raporlar(self.gelen.append)
        self.simdi = datetime(2026, 11, 2, 7, 31)   # pazartesi

    def _doz(self, ad, saat, durum):
        veritabani.sorgu(
            "INSERT INTO ilac (ad, aktif, olusturma) VALUES (?, 1, 0)", (ad,))
        iid = veritabani.sorgu("SELECT id FROM ilac WHERE ad=?", (ad,),
                               True)[0]["id"]
        pid = veritabani.sorgu(
            "INSERT INTO ilac_plan (ilac_id, saat, olusturma) "
            "VALUES (?,?,0)", (iid, saat))
        veritabani.sorgu(
            "INSERT INTO doz (ilac_id, plan_id, ilac_ad, planli, durum, "
            "sonraki) VALUES (?,?,?,?,?,0)",
            (iid, pid, ad, "2026-11-02 " + saat, durum))

    def test_sabah_icerik(self):
        self._doz("Aspirin", "08:00", "bekliyor")
        Gorevler(lambda *a: None).gorev_ekle("faturayı öde bugün 10:00",
                                              self.simdi)
        saglik_veri.ekle([{"tur": "adim", "deger": 1200,
                           "zaman": "2026-11-02T07:00:00"}])
        with mock.patch("ulgen.rapor.hava.getir", return_value=None):
            m = rapor.sabah(self.simdi)
        self.assertIn("Günaydın", m)
        self.assertIn("08:00 Aspirin (bekliyor)", m)
        self.assertIn("faturayı öde", m)
        self.assertIn("1.200 adım", m)

    def test_aksam_ve_haftalik(self):
        self._doz("Aspirin", "08:00", "alindi")
        self._doz("Vitamin", "20:00", "yanitsiz")
        m = rapor.aksam(datetime(2026, 11, 2, 21, 0))
        self.assertIn("1 alındı", m)
        self.assertIn("Vitamin hâlâ 'yanıtsız'", m.replace("20:00 ", ""))
        h = rapor.haftalik(datetime(2026, 11, 2, 21, 0))
        self.assertIn("2 dozun 1'i alındı", h)
        self.assertIn("Aspirin: 1/1", h)

    def test_bir_kez_uretilir_ve_saatten_once_uretilmez(self):
        with mock.patch("ulgen.rapor.hava.getir", return_value=None):
            self.r.adim(datetime(2026, 11, 2, 7, 0))
            self.assertEqual(self.gelen, [])
            self.r.adim(datetime(2026, 11, 2, 7, 31))
            self.r.adim(datetime(2026, 11, 2, 7, 45))
            self.assertEqual(len(self.gelen), 1)
            self.r.adim(datetime(2026, 11, 2, 21, 5))
            self.assertEqual(len(self.gelen), 2)      # akşam
            self.r.adim(datetime(2026, 11, 8, 20, 5))  # pazar
            turler = [g.split(" raporu")[0] for g in self.gelen]
            self.assertIn("Haftalık", turler)
        self.assertEqual(len(rapor.Raporlar.son()), len(self.gelen))

    def test_cikmaz_bos_veri(self):
        with mock.patch("ulgen.rapor.hava.getir", return_value=None):
            self.assertIn("planlı ilaç dozu yok", rapor.sabah(self.simdi))
        self.assertIn("Sağlık ölçümü kaydı yok", rapor.haftalik(self.simdi))


if __name__ == "__main__":
    unittest.main()


class DeneTesti(TemizVeri):
    def test_anahtarsiz_atlar_ve_sahte_yanit(self):
        import io
        from contextlib import redirect_stdout
        from ulgen import tani, beyin
        veritabani.kur()
        g = io.StringIO()
        with redirect_stdout(g):
            self.assertEqual(tani.dene(["nvidia"]), 0)
        self.assertIn("anahtar yok", g.getvalue())
        from ulgen import ayar
        a = ayar.yukle()
        a["nvidia_anahtar"] = "x"
        with mock.patch("ulgen.ayar.yukle", return_value=a), \
                mock.patch.object(beyin.OpenAIUyumluBeyin, "yanitla",
                                  return_value="Merhaba"):
            g = io.StringIO()
            with redirect_stdout(g):
                self.assertEqual(tani.dene(["nvidia"]), 0)
        self.assertIn("ÇALIŞTI", g.getvalue())
        with mock.patch("ulgen.ayar.yukle", return_value=a), \
                mock.patch.object(beyin.OpenAIUyumluBeyin, "yanitla",
                                  side_effect=beyin.BeyinHatasi("HTTP 401")):
            g = io.StringIO()
            with redirect_stdout(g):
                self.assertEqual(tani.dene(["nvidia"]), 1)
        self.assertIn("anahtar geçersiz", g.getvalue())
