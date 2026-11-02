import json
import os
from unittest import mock

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import ayar, gizli, ses_klip, sunucu, veritabani
from ulgen.cekirdek import Ulgen


def _ayarla(**kv):
    with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(kv, f)


class Sahte:
    def __init__(self, veri):
        self._v = veri

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return self._v


class KlipTesti(TemizVeri):

    def test_anahtarsiz_uretmez(self):
        with self.assertRaises(ses_klip.KlipHatasi):
            ses_klip.uret("tamam")

    def test_uret_sakla_say_ve_tekrar_istemez(self):
        _ayarla(elevenlabs_anahtar="xi-GIZLI-123", elevenlabs_ses_kimligi="AbC123xyz789")
        with mock.patch("urllib.request.urlopen",
                        return_value=Sahte(b"ID3MP3")) as u:
            self.assertEqual(ses_klip.uret("tamam"), "uretildi")
            istek_ = u.call_args.args[0]
            self.assertIn("AbC123xyz789", istek_.full_url)
            self.assertEqual(istek_.get_header("Xi-api-key"), "xi-GIZLI-123")
            # yalnızca sabit cümle gönderilir
            self.assertEqual(json.loads(istek_.data)["text"], "Tamam.")
            self.assertEqual(ses_klip.uret("tamam"), "var")
            self.assertEqual(u.call_count, 1)
        self.assertEqual(ses_klip.kullanilan()[0], len("Tamam."))
        self.assertIn("tamam.", ses_klip.hazir_klipler())

    def test_aylik_sinir_asilmaz(self):
        _ayarla(elevenlabs_anahtar="xi-1234567", elevenlabs_ses_kimligi="AbC123xyz789",
                elevenlabs_aylik_sinir=5)
        with mock.patch("urllib.request.urlopen") as u:
            with self.assertRaises(ses_klip.KlipHatasi):
                ses_klip.uret("karsilama")
            u.assert_not_called()

    def test_gecersiz_ses_kimligi(self):
        _ayarla(elevenlabs_anahtar="xi-1234567", elevenlabs_ses_kimligi="../x")
        with self.assertRaises(ses_klip.KlipHatasi):
            ses_klip.uret("tamam")

    def test_sunucu_klip_ve_ses_kimligi(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        os.makedirs(ses_klip.klasor(), exist_ok=True)
        with open(ses_klip.yol("tamam"), "wb") as f:
            f.write(b"MP3VERI")
        k, h = istek(p, "/ses/klip/tamam")
        self.assertEqual((k, h), (200, b"MP3VERI"))
        self.assertEqual(istek(p, "/ses/klip/../../etc/passwd")[0], 404)
        self.assertEqual(istek(p, "/ses/klip/yok")[0], 404)
        self.assertEqual(istek(p, "/ses/klip/tamam", yetkisiz=True)[0], 401)
        k, h = istek(p, "/ses/klipler")
        self.assertEqual(json.loads(h), {"tamam.": "tamam"})
        k, h = istek(p, "/yz/anahtar", "POST", json.dumps(
            {"saglayici": "elevenlabs", "ses_kimligi": "AbC123xyz789"}), JSON)
        self.assertEqual(k, 200)
        self.assertEqual(ayar.yukle()["elevenlabs_ses_kimligi"], "AbC123xyz789")
        k, _ = istek(p, "/yz/anahtar", "POST", json.dumps(
            {"saglayici": "elevenlabs", "ses_kimligi": "../kotu"}), JSON)
        self.assertEqual(k, 400)


class KlipYuklemeTesti(TemizVeri):

    def test_yukle_dinle_sil_ve_sinirlar(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        p = srv.server_address[1]
        A = {"Content-Type": "audio/mpeg"}
        mp3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"x" * 50
        self.assertEqual(istek(p, "/ses/klip/tamam", "POST", mp3, A)[0], 200)
        self.assertEqual(istek(p, "/ses/klip/tamam")[1], mp3)
        k, h = istek(p, "/ses/cumleler")
        self.assertTrue([c for c in json.loads(h) if c["ad"] == "tamam"][0]["var"])
        self.assertEqual(istek(p, "/ses/klip/tamam", "POST", b"MZ-exe-degil-mp3", A)[0], 400)
        self.assertEqual(istek(p, "/ses/klip/olmayan", "POST", mp3, A)[0], 404)
        self.assertEqual(istek(p, "/ses/klip/tamam", "POST", mp3, {"Content-Type": "text/html"})[0], 415)
        self.assertEqual(istek(p, "/ses/klip/tamam", "POST", mp3, A, yetkisiz=True)[0], 401)
        k, h = istek(p, "/ses/klip-sil", "POST", json.dumps({"ad": "tamam"}), JSON)
        self.assertTrue(json.loads(h)["silindi"])
        self.assertEqual(istek(p, "/ses/klip/tamam")[0], 404)
        self.assertEqual(istek(p, "/ses/klip-sil", "POST", json.dumps({"ad": "../x"}), JSON)[0], 400)
