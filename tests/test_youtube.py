import json
import unittest
from unittest import mock

from ulgen import youtube
from tests.temel import TemizVeri

VID = "W7N3DG9cjsg"


def sahte(altyazi=True):
    oyuncu = {"videoDetails": {"title": "Finans asistanı yapımı", "author": "Kanal",
                               "lengthSeconds": "2250", "shortDescription": "Açıklama"},
              "captions": {"playerCaptionsTracklistRenderer": {"captionTracks": [
                  {"baseUrl": "https://www.youtube.com/api/timedtext?v=x&lang=en",
                   "languageCode": "en"},
                  {"baseUrl": "https://www.youtube.com/api/timedtext?v=x&lang=tr",
                   "languageCode": "tr", "kind": "asr"}]}} if altyazi else {}}
    olaylar = {"events": [{"tStartMs": i * 10000, "segs": [
        {"utf8": "telegram bot ile bildirim" if i == 40 else "cümle %d" % i}]}
        for i in range(60)]}

    def indir(adres):
        if "/watch" in adres:
            return ("<script>var ytInitialPlayerResponse = %s;var x=1;</script>"
                    % json.dumps(oyuncu))
        assert "lang=tr" in adres          # Türkçe altyazı önce seçilir
        return json.dumps(olaylar)
    return indir


class Youtube(TemizVeri):

    def test_baglanti_bicimleri(self):
        for a in ("https://www.youtube.com/watch?v=%s" % VID,
                  "https://youtu.be/%s?si=abc" % VID,
                  "https://m.youtube.com/watch?feature=x&v=%s" % VID,
                  "https://www.youtube.com/shorts/%s" % VID):
            self.assertEqual(youtube.kimlik_bul("bak: " + a), VID)
        self.assertIsNone(youtube.kimlik_bul("https://example.com/watch?v=" + VID))

    def test_dokum_ve_zaman_imleri(self):
        b = youtube.getir(VID, sahte())
        self.assertEqual(b["baslik"], "Finans asistanı yapımı")
        self.assertEqual(b["dil"], "tr")
        self.assertIn("[6:30] cümle 39 telegram bot", b["metin"])

    def test_iletiye_ekle_soruya_gore(self):
        with mock.patch.object(youtube, "ILETI_SINIRI", 300):
            m = youtube.iletiye_ekle(
                "https://youtu.be/%s bu videoda bildirim nasıl gönderiliyor?" % VID, sahte())
        self.assertIn("[YOUTUBE VİDEO: Finans asistanı yapımı", m)
        self.assertIn("telegram bot ile bildirim", m)
        self.assertTrue(m.startswith("bu videoda bildirim"))

    def test_altyazi_yoksa_durust(self):
        m = youtube.iletiye_ekle("https://youtu.be/%s" % VID, sahte(altyazi=False))
        self.assertIn("altyazısı (konuşma metni) alınamadı", m)
        self.assertIn("tahmin etme", m)

    def test_ekli_ileti_komut_tetiklemez(self):
        from ulgen import niyet
        from ulgen.cekirdek import Ulgen
        u = Ulgen()
        m = youtube.iletiye_ekle("https://youtu.be/%s yorumla" % VID, sahte())
        with mock.patch.object(niyet, "yonlendir") as yon, \
                mock.patch.object(u, "_beyinle_dene",
                                  return_value=("tamam", "YORUM", "sahte")):
            c = u.sohbet_isle(m + "\nTHYAO analiz et")
        yon.assert_not_called()
        self.assertEqual(c["yanit"], "YORUM")


if __name__ == "__main__":
    unittest.main()
