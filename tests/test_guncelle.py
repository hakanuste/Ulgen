"""Kendini güncelleme: zip uygulama, yedek, geri alma, güvenlik, uç noktalar."""

import json
import os
import tempfile
import zipfile
from unittest import mock

from tests.temel import TemizVeri
from tests.test_sunucu import JSON, istek
from ulgen import ayar, guncelle, sunucu
from ulgen.cekirdek import Ulgen


def zip_yap(yol, dosyalar, onek="Ulgen-main/"):
    with zipfile.ZipFile(yol, "w") as z:
        for ad, icerik in dosyalar.items():
            z.writestr(onek + ad, icerik)


class ZipUygulamaTesti(TemizVeri):

    def setUp(self):
        super().setUp()
        self.kok = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.kok, "ulgen"))
        with open(os.path.join(self.kok, "ulgen", "__init__.py"), "w") as f:
            f.write('__surum__ = "1.0.0"\n')
        with open(os.path.join(self.kok, "ulgen", "eski_dosya.py"), "w") as f:
            f.write("X = 1\n")
        with open(os.path.join(self.kok, "requirements.txt"), "w") as f:
            f.write("requests\n")
        os.makedirs(os.path.join(self.kok, "ortam"))                  # korunmalı
        with open(os.path.join(self.kok, "ortam", "kalir.txt"), "w") as f:
            f.write("venv")
        self.zip = os.path.join(self.kok, "yeni.zip")

    def test_uygula_yedekle_ve_geri_al(self):
        zip_yap(self.zip, {"ulgen/__init__.py": '__surum__ = "2.0.0"\n',
                           "ulgen/yeni.py": "Y = 2\n",
                           "requirements.txt": "requests\npypdf\n",
                           "tests/x.py": "bu dosya alınmaz\n",
                           "ortam/kotu.txt": "alınmaz\n"})
        s = guncelle.uygula_zip(self.zip, self.kok, bagimlilik_kur=False)
        self.assertEqual(s["yeni"], "2.0.0")
        self.assertTrue(os.path.isfile(os.path.join(self.kok, "ulgen", "yeni.py")))
        self.assertFalse(os.path.exists(os.path.join(self.kok, "ulgen", "eski_dosya.py")))
        self.assertFalse(os.path.exists(os.path.join(self.kok, "tests")))
        self.assertFalse(os.path.exists(os.path.join(self.kok, "ortam", "kotu.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.kok, "ortam", "kalir.txt")))
        self.assertIn("pypdf", open(os.path.join(self.kok, "requirements.txt")).read())
        self.assertEqual(len(guncelle.yedekler(self.kok)), 1)
        guncelle.geri_al(self.kok)
        self.assertIn('"1.0.0"', open(os.path.join(self.kok, "ulgen", "__init__.py")).read())
        self.assertTrue(os.path.isfile(os.path.join(self.kok, "ulgen", "eski_dosya.py")))
        self.assertNotIn("pypdf", open(os.path.join(self.kok, "requirements.txt")).read())

    def test_bagimlilik_yalniz_degisince_kurulur(self):
        zip_yap(self.zip, {"ulgen/__init__.py": '__surum__ = "2.0.0"\n',
                           "requirements.txt": "requests\n"})
        with mock.patch.object(guncelle, "_bagimlilik_kur") as k:
            guncelle.uygula_zip(self.zip, self.kok)
            k.assert_not_called()
        zip_yap(self.zip, {"ulgen/__init__.py": '__surum__ = "2.1.0"\n',
                           "requirements.txt": "requests\nyeni\n"})
        with mock.patch.object(guncelle, "_bagimlilik_kur") as k:
            guncelle.uygula_zip(self.zip, self.kok)
            k.assert_called_once()

    def test_bozuk_kod_reddedilir_eski_kalir(self):
        zip_yap(self.zip, {"ulgen/__init__.py": '__surum__ = "2.0.0"\n',
                           "ulgen/bozuk.py": "def (:\n"})
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "derlenemedi"):
            guncelle.uygula_zip(self.zip, self.kok)
        self.assertIn('"1.0.0"', open(os.path.join(self.kok, "ulgen", "__init__.py")).read())
        self.assertEqual(guncelle.yedekler(self.kok), [])

    def test_gecersiz_zipler(self):
        with open(self.zip, "wb") as f:
            f.write(b"zip degil")
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "bozuk"):
            guncelle.uygula_zip(self.zip, self.kok)
        zip_yap(self.zip, {"baska/dosya.py": "x=1\n"})
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "ulgen/__init__"):
            guncelle.uygula_zip(self.zip, self.kok)
        zip_yap(self.zip, {"ulgen/__init__.py": "# surum yok\n"})
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "sürüm"):
            guncelle.uygula_zip(self.zip, self.kok)

    def test_disariya_tasan_yol_reddedilir(self):
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("Ulgen-main/ulgen/__init__.py", '__surum__ = "2.0.0"\n')
            z.writestr("Ulgen-main/ulgen/../../kacak.py", "x = 1\n")
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "güvensiz"):
            guncelle.uygula_zip(self.zip, self.kok)
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.kok), "kacak.py")))

    def test_geri_alinacak_yedek_yok(self):
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "yok"):
            guncelle.geri_al(self.kok)


class UzakTesti(TemizVeri):

    def test_yalniz_github_adresleri(self):
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "github"):
            guncelle._al("https://kotu.example.com/x.zip")
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "github"):
            guncelle._al("http://raw.githubusercontent.com/x")

    def test_depo_ayari_ve_surum_karsilastirma(self):
        self.assertEqual(guncelle.ayarlar()[0], "hakanuste/Ulgen")      # varsayılan
        ayar.guncelle("guncelleme_depo", "")
        with self.assertRaisesRegex(guncelle.GuncellemeHatasi, "Depo ayarlı değil"):
            guncelle.ayarlar()
        ayar.guncelle("guncelleme_depo", "hakanuste/Ulgen")
        yeni = ('__surum__ = "99.0.0"\n').encode()
        with mock.patch.object(guncelle, "_al", return_value=yeni):
            d = guncelle.durum()
        self.assertTrue(d["yeni_var"])
        self.assertEqual(d["uzak"], "99.0.0")
        with mock.patch.object(guncelle, "_al", return_value=b'__surum__ = "0.0.1"\n'):
            self.assertFalse(guncelle.durum()["yeni_var"])
        self.assertTrue(guncelle.surum_anahtari("2.7.10") > guncelle.surum_anahtari("2.7.9"))

    def test_depo_adi_kotu_biçim(self):
        ayar.guncelle("guncelleme_depo", "../etc/passwd")
        with self.assertRaises(guncelle.GuncellemeHatasi):
            guncelle.ayarlar()


class UcNoktaTesti(TemizVeri):

    def _sunucu(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        return srv, srv.server_address[1]

    def test_depo_onay_uzaktan(self):
        srv, p = self._sunucu()
        g = json.dumps
        self.assertEqual(istek(p, "/guncelle/depo", "POST", g({"depo": "../x"}), JSON)[0], 400)
        k, h = istek(p, "/guncelle/depo", "POST", g({"depo": "hakanuste/Ulgen"}), JSON)
        self.assertEqual(k, 200)
        self.assertEqual(ayar.yukle()["guncelleme_depo"], "hakanuste/Ulgen")
        self.assertEqual(istek(p, "/guncelle/uygula", "POST", g({}), JSON)[0], 400)
        yeni = '__surum__ = "99.0.0"\n'.encode()
        with mock.patch.object(guncelle, "_al", return_value=yeni):
            k, h = istek(p, "/guncelle/durum")
        self.assertEqual((k, json.loads(h)["yeni_var"]), (200, True))
        srv.yerel = False
        for yol, yontem in (("/guncelle/durum", "GET"), ("/guncelle/depo", "POST"),
                            ("/guncelle/uygula", "POST"), ("/guncelle/geri-al", "POST")):
            self.assertEqual(istek(p, yol, yontem, g({"onay": True}) if yontem == "POST" else None,
                                   JSON)[0], 403)

    def test_uygula_basarisiz_ileti(self):
        srv, p = self._sunucu()
        ayar.guncelle("guncelleme_depo", "hakanuste/Ulgen")
        with mock.patch.object(guncelle, "_al", side_effect=guncelle.GuncellemeHatasi("ağ yok")):
            k, h = istek(p, "/guncelle/uygula", "POST", json.dumps({"onay": True}), JSON)
        self.assertEqual(k, 200)
        d = json.loads(h)
        self.assertFalse(d["tamam"])
        self.assertIn("ağ yok", d["hata"])
