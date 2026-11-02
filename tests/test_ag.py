import ssl
import unittest
from unittest import mock

from ulgen import ag, beyin


class AgTesti(unittest.TestCase):
    def test_baglam_certifi_ile_dogrulamali(self):
        ag._BAGLAM = None
        b = ag.baglam()
        self.assertEqual(b.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(b.check_hostname)
        self.assertIs(ag.baglam(), b)       # önbellekli

    def test_json_gonder_baglami_kullanir(self):
        sahte = mock.MagicMock()
        sahte.__enter__.return_value.read.return_value = b"{}"
        with mock.patch("urllib.request.urlopen", return_value=sahte) as u:
            beyin._json_gonder("https://example.org/x")
        self.assertIs(u.call_args.kwargs["context"], ag.baglam())


if __name__ == "__main__":
    unittest.main()
