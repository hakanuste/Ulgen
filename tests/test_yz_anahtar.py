import json
from unittest import mock

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import gizli, sunucu, veritabani
from ulgen.cekirdek import Ulgen


class AnahtarKutusu(TemizVeri):

    def _sunucu(self):
        srv = sunucu.yerel_sunucu(Ulgen(), 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        return srv, srv.server_address[1]

    def test_yaz_dogrula_ve_sizinti_yok(self):
        srv, p = self._sunucu()
        g = lambda d: json.dumps(d)
        k, h = istek(p, "/yz/anahtar", "POST",
                     g({"saglayici": "nvidia", "anahtar": "nvapi-GIZLI-12345"}), JSON)
        self.assertEqual(k, 200)
        self.assertNotIn(b"GIZLI", h)
        self.assertEqual(gizli.sir_oku("nvidia"), "nvapi-GIZLI-12345")
        gunluk = veritabani.sorgu("SELECT * FROM gunluk", (), True)
        self.assertNotIn("GIZLI", json.dumps([dict(x) for x in gunluk], default=str))
        for kotu in ({"saglayici": "x", "anahtar": "abcdefgh12"},
                     {"saglayici": "nvidia", "anahtar": "kisa"},
                     {"saglayici": "nvidia", "anahtar": "bosluk var burada"},
                     {"saglayici": "nvidia", "anahtar": 5}):
            self.assertEqual(istek(p, "/yz/anahtar", "POST", g(kotu), JSON)[0], 400)
        self.assertEqual(istek(p, "/yz/anahtar", "POST", g(
            {"saglayici": "nvidia", "anahtar": "abcdefgh12"}), JSON,
            yetkisiz=True)[0], 401)

    def test_uzaktan_reddedilir_ve_dene(self):
        srv, p = self._sunucu()
        body = json.dumps({"saglayici": "gemini", "anahtar": "abcdefgh1234"})
        srv.yerel = False
        self.assertEqual(istek(p, "/yz/anahtar", "POST", body, JSON)[0], 403)
        srv.yerel = True
        with mock.patch("ulgen.tani.dene", return_value=0):
            k, h = istek(p, "/yz/dene", "POST", json.dumps({"saglayici": "gemini"}), JSON)
        self.assertEqual((k, json.loads(h)["calisti"]), (200, True))


class AnahtarListeSilTesti(AnahtarKutusu):

    def test_durum_ekle_degistir_sil(self):
        srv, p = self._sunucu()
        g = json.dumps
        k, h = istek(p, "/yz/anahtarlar")
        d = json.loads(h)
        self.assertEqual(k, 200)
        self.assertFalse(d["gemini"]["var"])
        istek(p, "/yz/anahtar", "POST", g({"saglayici": "gemini", "anahtar": "AIza-ILK-ANAHTAR-1111"}), JSON)
        d = json.loads(istek(p, "/yz/anahtarlar")[1])
        self.assertTrue(d["gemini"]["var"])
        self.assertEqual(d["gemini"]["son4"], "1111")
        self.assertNotIn("ILK", json.dumps(d))
        istek(p, "/yz/anahtar", "POST", g({"saglayici": "gemini", "anahtar": "AIza-YENI-ANAHTAR-2222"}), JSON)
        self.assertEqual(gizli.sir_oku("gemini"), "AIza-YENI-ANAHTAR-2222")
        self.assertEqual(istek(p, "/yz/anahtar-sil", "POST", g({"saglayici": "gemini"}), JSON)[0], 400)
        kotu = g({"saglayici": "x", "onay": True})
        self.assertEqual(istek(p, "/yz/anahtar-sil", "POST", kotu, JSON)[0], 400)
        k, h = istek(p, "/yz/anahtar-sil", "POST", g({"saglayici": "gemini", "onay": True}), JSON)
        self.assertEqual(k, 200)
        self.assertFalse(json.loads(istek(p, "/yz/anahtarlar")[1])["gemini"]["var"])
        self.assertEqual(gizli.sir_oku("gemini"), "")

    def test_ayar_json_icindeki_anahtar_gorunur_ve_silinir(self):
        from ulgen import ayar
        srv, p = self._sunucu()
        ayar.guncelle("groq_anahtar", "gsk-DUZ-METIN-9999")
        d = json.loads(istek(p, "/yz/anahtarlar")[1])
        self.assertEqual((d["groq"]["yer"], d["groq"]["son4"]), ("ayar.json", "9999"))
        istek(p, "/yz/anahtar-sil", "POST", json.dumps({"saglayici": "groq", "onay": True}), JSON)
        self.assertFalse(json.loads(istek(p, "/yz/anahtarlar")[1])["groq"]["var"])

    def test_uzaktan_reddedilir(self):
        srv, p = self._sunucu()
        srv.yerel = False
        self.assertEqual(istek(p, "/yz/anahtarlar")[0], 403)
        self.assertEqual(istek(p, "/yz/anahtar-sil", "POST", json.dumps(
            {"saglayici": "gemini", "onay": True}), JSON)[0], 403)
