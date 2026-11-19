import unittest
from unittest import mock

from ulgen import ses


class MacSesTesti(unittest.TestCase):
    def test_say_yoksa_false(self):
        with mock.patch.object(ses.shutil, "which", return_value=None):
            self.assertFalse(ses.mac_oku("merhaba"))

    def test_metin_stdin_ile_verilir(self):
        surec = mock.Mock(returncode=0)
        surec.poll.return_value = 0
        with mock.patch.object(ses.shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(ses.subprocess, "Popen", return_value=surec) as p:
            self.assertTrue(ses.mac_oku("-rf merhaba", "Yelda"))
        komut = p.call_args[0][0]
        self.assertEqual(komut, ["say", "-v", "Yelda", "-f", "-"])
        surec.communicate.assert_called_once()
        self.assertEqual(surec.communicate.call_args[0][0], "-rf merhaba".encode("utf-8"))

    def test_gecersiz_ses_adi_kullanilmaz(self):
        surec = mock.Mock(returncode=0)
        with mock.patch.object(ses.shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(ses.subprocess, "Popen", return_value=surec) as p:
            ses.mac_oku("selam", "Yelda; rm -rf /")
        self.assertEqual(p.call_args[0][0], ["say", "-f", "-"])


    def test_ses_yukluyse_degil_varsayilan_sesle_yeniden(self):
        hatali, iyi = mock.Mock(returncode=1), mock.Mock(returncode=0)
        with mock.patch.object(ses.shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(ses.subprocess, "Popen", side_effect=[hatali, iyi]) as p:
            self.assertTrue(ses.mac_oku("selam", "Yelda"))
        self.assertEqual(p.call_args_list[1][0][0], ["say", "-f", "-"])


if __name__ == "__main__":
    unittest.main()
