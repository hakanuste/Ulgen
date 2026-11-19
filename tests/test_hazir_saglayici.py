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
