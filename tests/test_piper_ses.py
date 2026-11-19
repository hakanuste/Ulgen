import io
import os
import unittest
import wave
from unittest import mock

from tests.temel import TemizVeri
from ulgen import piper_ses, ses_kaydi


def wav_yap(sure=2.0, hiz=22050, kanal=1):
    t = io.BytesIO()
    with wave.open(t, "wb") as w:
        w.setnchannels(kanal)
        w.setsampwidth(2)
        w.setframerate(hiz)
        w.writeframes(b"\x00\x00" * int(sure * hiz) * kanal)
    return t.getvalue()


class PiperSesTesti(TemizVeri):
    def _ses_koy(self, ad):
        for u in (".onnx", ".onnx.json"):
            open(os.path.join(piper_ses.klasor(), ad + u), "w").close()

    def test_ses_listesi_ve_secim(self):
        self.assertEqual(piper_ses.sesler(), [])
        self._ses_koy("tr_TR-dfki-medium")
        open(os.path.join(piper_ses.klasor(), "yarim.onnx"), "w").close()   # json yok
        self.assertEqual(piper_ses.sesler(), ["tr_TR-dfki-medium"])
        self._ses_koy("tr_TR-hakan-medium")
        self.assertEqual(piper_ses.secili(), "tr_TR-hakan-medium")   # kendi sesi önce
        piper_ses.ayarla(ses="tr_TR-dfki-medium")
        self.assertEqual(piper_ses.secili(), "tr_TR-dfki-medium")
        with self.assertRaises(piper_ses.PiperHatasi):
            piper_ses.ayarla(ses="yok")
        with self.assertRaises(piper_ses.PiperHatasi):
            piper_ses.ayarla(hiz=3)

    def test_acmak_icin_ses_gerekir(self):
        with self.assertRaises(piper_ses.PiperHatasi):
            piper_ses.ayarla(acik=True)

    def test_sentez_wav_dondurur(self):
        self._ses_koy("tr_TR-dfki-medium")
        sahte = mock.Mock()
        sahte.synthesize_wav.side_effect = lambda m, w, syn_config=None: (
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(22050),
            w.writeframes(b"\x00\x00" * 100))
        with mock.patch.object(piper_ses, "_ses_yukle", return_value=sahte):
            ham = piper_ses.sentezle("**Merhaba** https://x.com dünya")
        self.assertTrue(ham.startswith(b"RIFF"))
        self.assertEqual(sahte.synthesize_wav.call_args[0][0], "Merhaba dünya")

    def test_bilinmeyen_hazir_ses_indirilmez(self):
        with self.assertRaises(piper_ses.PiperHatasi):
            piper_ses.indir_arka_planda("kotu")


class SesKaydiTesti(TemizVeri):
    def test_sirayla_kayit_metadata_ve_paket(self):
        ilk = ses_kaydi.siradaki()
        self.assertEqual(ilk["adet"], 0)
        dosya = ses_kaydi.kaydet(ilk["metin"], wav_yap())
        self.assertEqual(dosya, "0001.wav")
        ikinci = ses_kaydi.siradaki()
        self.assertNotEqual(ikinci["metin"], ilk["metin"])
        self.assertEqual(ikinci["adet"], 1)
        with open(os.path.join(ses_kaydi.klasor(), "metadata.csv"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "0001.wav|%s\n" % ilk["metin"])
        import zipfile
        with zipfile.ZipFile(ses_kaydi.paketle()) as z:
            self.assertEqual(sorted(z.namelist()), ["metadata.csv", "wavs/0001.wav"])
        self.assertEqual(ses_kaydi.son_kaydi_sil(), ilk["metin"])
        self.assertEqual(ses_kaydi.siradaki()["metin"], ilk["metin"])

    def test_atla_ve_yinelenen(self):
        c = ses_kaydi.siradaki()["metin"]
        ses_kaydi.atla(c)
        self.assertNotEqual(ses_kaydi.siradaki()["metin"], c)
        d = ses_kaydi.siradaki()["metin"]
        ses_kaydi.kaydet(d, wav_yap())
        with self.assertRaises(ses_kaydi.KayitHatasi):
            ses_kaydi.kaydet(d, wav_yap())

    def test_wav_denetimi(self):
        with self.assertRaises(ses_kaydi.KayitHatasi):
            ses_kaydi.kaydet("Bir cümle.", b"bozuk")
        with self.assertRaises(ses_kaydi.KayitHatasi):
            ses_kaydi.kaydet("Bir cümle.", wav_yap(kanal=2))
        with self.assertRaises(ses_kaydi.KayitHatasi):
            ses_kaydi.kaydet("Bir cümle.", wav_yap(sure=0.3))
        with self.assertRaises(ses_kaydi.KayitHatasi):
            ses_kaydi.kaydet("a|b", wav_yap())

    def test_kitap_cumlesi_uygunlugu(self):
        self.assertTrue(ses_kaydi.uygun_mu(
            "Bu bölümde hekim, hastalığın belirtilerini ayrıntılı olarak anlatır."))
        self.assertFalse(ses_kaydi.uygun_mu("Kısa."))
        self.assertFalse(ses_kaydi.uygun_mu("SAYFA 123 ve e t c bozuk ocr artığı burada duruyor."))
        self.assertFalse(ses_kaydi.uygun_mu(
            "Tansiyon ilacımı her sabah içiyorum ve şifremi unuttum ben."))


if __name__ == "__main__":
    unittest.main()


class PiperIsciTesti(TemizVeri):
    """Ayrı ortamdaki işçi süreci: sahte bir 'piper' paketiyle uçtan uca."""

    def test_isci_sureci_wav_uretir(self):
        import sys
        import tempfile
        kok = tempfile.mkdtemp()
        os.makedirs(os.path.join(kok, "piper"))
        with open(os.path.join(kok, "piper", "__init__.py"), "w") as f:
            f.write(
                "class SynthesisConfig:\n"
                "    def __init__(self, length_scale=1.0): self.length_scale = length_scale\n"
                "class PiperVoice:\n"
                "    @staticmethod\n"
                "    def load(m): return PiperVoice()\n"
                "    def synthesize_wav(self, metin, w, syn_config=None):\n"
                "        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)\n"
                "        w.writeframes(b'\\x00\\x00' * len(metin))\n")
        isci = piper_ses._Isci()
        with mock.patch.dict(os.environ, {"PYTHONPATH": kok}), \
                mock.patch.object(piper_ses, "_ortam_python", return_value=sys.executable):
            ham = isci.sentezle("/yok/model.onnx", "merhaba", 1.0)
            ham2 = isci.sentezle("/yok/model.onnx", "ikinci", 1.0)    # aynı süreç
        with wave.open(io.BytesIO(ham)) as w:
            self.assertEqual(w.getnframes(), len("merhaba"))
        self.assertTrue(ham2.startswith(b"RIFF"))
        isci._p.terminate()

    def test_uygun_python_surum_araligi(self):
        with mock.patch.object(piper_ses, "_surum", return_value=(3, 13)):
            self.assertEqual(piper_ses.uygun_python(), "")
        with mock.patch.object(piper_ses, "_surum", return_value=(3, 9)):
            self.assertTrue(piper_ses.uygun_python())
