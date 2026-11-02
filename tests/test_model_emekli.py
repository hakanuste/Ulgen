"""Sağlayıcı modeli emekli olursa (HTTP 410) yeni model kendiliğinden seçilir."""

from unittest import mock

from tests.temel import TemizVeri
from ulgen import ayar, beyin
from ulgen.beyin import BeyinHatasi, OpenAIUyumluBeyin


class ModelEmekliTesti(TemizVeri):

    def yap(self):
        return OpenAIUyumluBeyin("nvidia", "k", "meta/llama-3.3-70b-instruct")

    def test_410_olunca_yeni_model_secilir_ve_kalici_yazilir(self):
        b = self.yap()
        cagri = []

        def sahte(adres, govde=None, basliklar=None, zaman_asimi=120, baslik_don=False):
            if govde is None:                      # /models
                return {"data": [{"id": "nvidia/nv-embed-v1"}, {"id": "x/vision-vl"},
                                 {"id": "nvidia/nemotron-3.5-lightning-30b-a3b"},
                                 {"id": "meta/llama-3.3-70b-instruct"}]}
            cagri.append(govde["model"])
            if govde["model"] == "meta/llama-3.3-70b-instruct":
                raise BeyinHatasi("HTTP 410: Gone")
            return {"choices": [{"message": {"content": "merhaba"}}]}, {}

        with mock.patch.object(beyin, "_json_gonder", sahte):
            self.assertEqual(b.yanitla("s", [{"role": "user", "content": "x"}]), "merhaba")
        self.assertEqual(b.model, "nvidia/nemotron-3.5-lightning-30b-a3b")
        self.assertEqual(ayar.yukle()["nvidia_model"], b.model)
        self.assertEqual(len(cagri), 2)

    def test_baska_hata_model_degistirmez(self):
        b = self.yap()

        def sahte(adres, govde=None, *a, **k):
            raise BeyinHatasi("HTTP 500: hata")

        with mock.patch.object(beyin, "_json_gonder", sahte):
            with self.assertRaises(BeyinHatasi):
                b.yanitla("s", [{"role": "user", "content": "x"}])
        self.assertEqual(b.model, "meta/llama-3.3-70b-instruct")

    def test_uygun_model_yoksa_hata_aynen_doner(self):
        b = self.yap()

        def sahte(adres, govde=None, *a, **k):
            if govde is None:
                return {"data": [{"id": "nvidia/nv-embed-v1"}]}
            raise BeyinHatasi("HTTP 410: Gone")

        with mock.patch.object(beyin, "_json_gonder", sahte):
            with self.assertRaisesRegex(BeyinHatasi, "410"):
                b.yanitla("s", [{"role": "user", "content": "x"}])
