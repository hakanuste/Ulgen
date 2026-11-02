"""Kod penceresi: dosya güvenliği, çalıştırma, zaman aşımı, ortam, uzak kapı."""

import json
import os
import threading
import time

from tests.temel import TemizVeri
from ulgen import ayar, kodpenceresi as kp


class KodPenceresiTesti(TemizVeri):

    def test_python_calisir(self):
        r = kp.calistir("print(6*7)")
        self.assertEqual(r["cikis"], 0)
        self.assertIn("42", r["cikti"])

    def test_hata_ciktisi_ve_cikis_kodu(self):
        r = kp.calistir("raise ValueError('x')")
        self.assertNotEqual(r["cikis"], 0)
        self.assertIn("ValueError", r["cikti"])

    def test_zaman_asimi_sureci_oldurur(self):
        bas = time.time()
        r = kp.calistir("import time\ntime.sleep(30)", sure=1)
        self.assertTrue(r["zaman_asimi"])
        self.assertLess(time.time() - bas, 10)

    def test_cikti_kisaltilir(self):
        r = kp.calistir("print('a' * 100000)")
        self.assertLessEqual(len(r["cikti"]), kp.CIKTI_SINIRI + 60)

    def test_ortam_degiskenleri_gecmez(self):
        os.environ["ULGEN_TEST_SIR"] = "gizli123"
        try:
            r = kp.calistir("import os; print(os.environ.get('ULGEN_TEST_SIR'))")
        finally:
            del os.environ["ULGEN_TEST_SIR"]
        self.assertIn("None", r["cikti"])
        self.assertNotIn("gizli123", r["cikti"])

    def test_gecici_dosya_temizlenir(self):
        kp.calistir("print(1)")
        self.assertEqual([a for a in os.listdir(kp.klasor())
                          if a.startswith(".calisan-")], [])

    def test_uzaktan_varsayilan_kapali(self):
        with self.assertRaises(kp.KodHatasi):
            kp.calistir("print(1)", uzaktan=True)

    def test_uzaktan_ayarla_acilir(self):
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            json.dump({"uzaktan_kod_calistir": True}, f)
        self.assertIn("1", kp.calistir("print(1)", uzaktan=True)["cikti"])

    def test_bilinmeyen_dil(self):
        with self.assertRaises(kp.KodHatasi):
            kp.calistir("x", dil="ruby")

    def test_tek_seferde_tek_calistirma(self):
        sonuc = []
        t = threading.Thread(target=lambda: sonuc.append(
            kp.calistir("import time; time.sleep(2)")))
        t.start()
        time.sleep(0.5)
        with self.assertRaises(kp.KodHatasi):
            kp.calistir("print(1)")
        t.join()

    def test_dosya_adi_dogrulama(self):
        for kotu in ("../x.py", "a/b.py", "x.exe", ".gizli.py", "", "x" * 80 + ".py"):
            with self.assertRaises(kp.KodHatasi, msg=kotu):
                kp.kaydet(kotu, "1")

    def test_kaydet_oku_ve_eski_surum_saklanir(self):
        kp.kaydet("deneme.py", "print(1)")
        kp.kaydet("deneme.py", "print(2)")
        self.assertEqual(kp.oku("deneme.py"), "print(2)")
        self.assertEqual(kp.liste(), ["deneme.py"])
        surumler = os.listdir(os.path.join(kp.klasor(), "_surumler"))
        self.assertEqual(len(surumler), 1)

    def test_olmayan_dosya(self):
        with self.assertRaises(kp.KodHatasi):
            kp.oku("yok.py")

    def test_model_araci_degil(self):
        from ulgen.cekirdek import Ulgen
        katalog = Ulgen().araclar.katalog()
        self.assertNotIn("kod", katalog.lower().replace("kod_ayikla", ""))
