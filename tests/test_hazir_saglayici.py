import unittest
from unittest import mock

from tests.temel import TemizVeri
from ulgen import ayar, hazir_saglayici as hs


class HazirSaglayiciTesti(TemizVeri):
    def test_model_degistir_ve_durum(self):
        hs.model_degistir("nvidia", "moonshotai/kimi-k3.1-pro")
        self.assertEqual(ayar.yukle()["nvidia_model"], "moonshotai/kimi-k3.1-pro")
        self.assertEqual(hs.durum()["nvidia"]["model"], "moonshotai/kimi-k3.1-pro")

    def test_ucretli_ve_gecersiz_reddedilir(self):
        with self.assertRaises(hs.HazirHatasi):
            hs.model_degistir("openrouter", "anthropic/claude-sonnet")
        with self.assertRaises(hs.HazirHatasi):
            hs.model_degistir("nvidia", "kötü ad; rm -rf")
        with self.assertRaises(hs.HazirHatasi):
            hs.model_degistir("bilinmeyen", "x")
        hs.model_degistir("openrouter", "qwen/qwen3:free")

    def test_one_al(self):
        hs.one_al("nvidia")
        self.assertTrue(hs.durum()["nvidia"]["one"])
        hs.one_al("nvidia", False)
        self.assertFalse(hs.durum()["nvidia"]["one"])

    def test_modeller_sohbet_disini_ayiklar(self):
        sahte = mock.Mock()
        sahte.modelleri_listele.return_value = [
            "moonshotai/kimi-k3.1-pro", "nvidia/nemotron-3.5-embed-1b",
            "nvidia/nemotron-3.5-rerank-8b", "nvidia/nemotron-3.5-parse",
            "mistralai/mistral-large-4", "google/gemma-4-31b-it"]
        with mock.patch.object(hs, "_beyin", return_value=sahte):
            m = hs.modeller("nvidia")
        self.assertEqual(m, ["moonshotai/kimi-k3.1-pro", "mistralai/mistral-large-4",
                             "google/gemma-4-31b-it"])

    def test_anahtarsiz_liste_hatasi(self):
        with self.assertRaises(hs.HazirHatasi):
            hs.modeller("groq")


if __name__ == "__main__":
    unittest.main()


class AnahtarOnceligiTesti(TemizVeri):
    def test_zincirdeki_yeni_anahtar_eski_duz_anahtari_gecer(self):
        from ulgen import gizli
        ayar.guncelle("nvidia_anahtar", "nvapi-ESKIDUZANAHTAR")
        with mock.patch.object(gizli, "sir_oku",
                               side_effect=lambda ad: "nvapi-YENI1234" if ad == "nvidia" else ""):
            self.assertEqual(ayar.yukle()["nvidia_anahtar"], "nvapi-YENI1234")
        with mock.patch.object(gizli, "sir_oku", return_value=""):
            self.assertEqual(ayar.yukle()["nvidia_anahtar"], "nvapi-ESKIDUZANAHTAR")


class BosYanitTesti(unittest.TestCase):
    def test_bos_yanitta_sistem_kullaniciya_katilip_yeniden_denenir(self):
        from ulgen import beyin
        gonderilen = []

        def sahte(adres, govde=None, basliklar=None, zaman=60, baslik_don=False):
            gonderilen.append(govde)
            icerik = "" if len(gonderilen) == 1 else "Merhaba"
            return {"choices": [{"message": {"content": icerik}}]}, {}
        b = beyin.OpenAIUyumluBeyin("nvidia", "nvapi-x", "google/gemma-3-12b-it")
        with mock.patch.object(beyin, "_json_gonder", side_effect=sahte):
            self.assertEqual(b.yanitla("Kısa yanıt ver.",
                                       [{"role": "user", "content": "selam"}], 30),
                             "Merhaba")
        self.assertEqual(gonderilen[0]["messages"][0]["role"], "system")
        self.assertEqual([m["role"] for m in gonderilen[1]["messages"]], ["user"])
        self.assertIn("Kısa yanıt ver.", gonderilen[1]["messages"][0]["content"])
        self.assertGreater(gonderilen[1]["max_tokens"], 30)

    def test_iki_kez_bossa_anlasilir_hata(self):
        from ulgen import beyin
        b = beyin.OpenAIUyumluBeyin("nvidia", "nvapi-x", "m")
        with mock.patch.object(beyin, "_json_gonder", return_value=(
                {"choices": [{"message": {"content": "<think>x</think>"}}]}, {})):
            with self.assertRaises(beyin.BeyinHatasi) as h:
                b.yanitla("s", [{"role": "user", "content": "u"}], 30)
        self.assertIn("başka model seçin", str(h.exception))
