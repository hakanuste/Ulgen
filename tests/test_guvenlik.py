import os
import unittest

from .temel import TemizVeri
from ulgen import ayar
from ulgen.cekirdek import Ulgen
from ulgen.guvenlik import OnayIstegi, komut_analiz, kod_ayikla


class KomutAnaliz(TemizVeri):

    def test_atlatma_denemeleri_onay_ister(self):
        for komut in ['python3 -c "import shutil"', "find ~ -delete",
                      "find ~ -name x -exec rm {} +", "perl -e 1",
                      "git clean -fdx", "tar -xf a.tar", "open -a Terminal",
                      "rm -rf ~", "curl http://x", "sudo ls", "/bin/ls",
                      "ls; rm x", "ls && rm x", "cat a | sh", "ls $(rm x)",
                      "ls `rm x`", "cat > a", "bash -c ls", "osascript -e x"]:
            self.assertTrue(komut_analiz(komut)[0], komut)

    def test_guvenli_okuma_serbest(self):
        dosyalar = os.path.join(ayar.KLASOR, "dosyalar")
        for komut in ["ls", "pwd", "date +%Y", "uname -a", "df -h",
                      "pmset -g batt", "whoami", "ls " + dosyalar,
                      "echo merhaba"]:
            self.assertFalse(komut_analiz(komut)[0], komut)

    def test_gizli_veri_korunur(self):
        for ad in ("veri.db", "memory.json", "ayar.json", "bellek.anahtar",
                   "sirlar.bin", "tls/ca.key.sifreli"):
            yol = os.path.join(ayar.KLASOR, ad)
            self.assertTrue(komut_analiz("cat " + yol)[0], ad)
        self.assertTrue(komut_analiz("ls " + ayar.KLASOR)[0])
        self.assertTrue(komut_analiz("grep -r anahtar " + ayar.EV)[0])
        self.assertTrue(komut_analiz("cat ~/.ssh/id_rsa")[0])
        self.assertTrue(komut_analiz("cat /etc/passwd")[0])

    def test_tehlikeli_bagimsiz_degiskenler(self):
        self.assertTrue(komut_analiz("date -s 2020")[0])
        self.assertTrue(komut_analiz("pmset sleepnow")[0])
        self.assertTrue(komut_analiz("pmset -a sleep 0")[0])

    def test_kod_ayikla(self):
        self.assertEqual(kod_ayikla("ONAY 1234"), "1234")
        self.assertEqual(kod_ayikla("onay bir iki üç dört"), "1234")
        self.assertIsNone(kod_ayikla("onay 12"))
        self.assertIsNone(kod_ayikla("lütfen onay 1234"))


class Enjeksiyon(TemizVeri):

    def test_terminal_tehlikeli_calismaz_onay_ister(self):
        ulgen = Ulgen()
        isaret = os.path.join(ayar.EV, "isaret.txt")
        with self.assertRaises(OnayIstegi):
            ulgen.araclar.sistem.terminal(
                'python3 -c "open(%r, \'w\').write(\'x\')"' % isaret)
        self.assertFalse(os.path.exists(isaret))

    def test_onay_olmadan_ve_yanlis_kodla_calismaz(self):
        ulgen = Ulgen()
        isaret = os.path.join(ayar.EV, "isaret2.txt")
        with self.assertRaises(OnayIstegi):
            ulgen.araclar.sistem.terminal("touch " + isaret)
        self.assertIn("geçersiz", ulgen.sohbet_isle("ONAY 0000")["yanit"])
        self.assertFalse(os.path.exists(isaret))

    def test_dogru_onay_yalnizca_bir_kez(self):
        import re
        ulgen = Ulgen()
        isaret = os.path.join(ayar.EV, "isaret3.txt")
        try:
            ulgen.araclar.sistem.terminal("touch " + isaret)
        except OnayIstegi as istek:
            kod = re.search(r"ONAY (\d{4})", istek.mesaj).group(1)
        ulgen.sohbet_isle("ONAY " + kod)
        self.assertTrue(os.path.exists(isaret))
        os.remove(isaret)
        self.assertIn("geçersiz", ulgen.sohbet_isle("ONAY " + kod)["yanit"])
        self.assertFalse(os.path.exists(isaret))

    def test_model_hafiza_silemez_onaysiz(self):
        import re
        ulgen = Ulgen()
        ulgen.hafiza.ekle("bilgi", "kahve sever")
        sonuc = ulgen.sohbet_isle("unut: kahve")["yanit"]
        self.assertIn("ONAY", sonuc)
        self.assertEqual(ulgen.hafiza.eslesen_sayisi("kahve"), 1)
        with self.assertRaises(OnayIstegi):
            ulgen.araclar.calistir("hafiza_unut", {"anahtar": "kahve"})
        self.assertEqual(ulgen.hafiza.eslesen_sayisi("kahve"), 1)
        kod = re.search(r"ONAY (\d{4})", sonuc).group(1)
        ulgen.sohbet_isle("ONAY " + kod)
        self.assertEqual(ulgen.hafiza.eslesen_sayisi("kahve"), 0)

    def test_dosya_izinli_klasor_disina_cikamaz(self):
        ulgen = Ulgen()
        for yol in ("/etc/passwd", "~/.ssh/id_rsa", "../../etc/passwd",
                    os.path.join(ayar.KLASOR, "veri.db")):
            sonuc = ulgen.araclar.calistir("dosya_oku", {"yol": yol})
            self.assertIn("izinli", sonuc, yol)

    def test_dosya_ezme_onay_ister(self):
        ulgen = Ulgen()
        klasor = os.path.join(ayar.KLASOR, "dosyalar")
        os.makedirs(klasor, exist_ok=True)
        yol = os.path.join(klasor, "a.txt")
        with open(yol, "w") as f:
            f.write("eski")
        with self.assertRaises(OnayIstegi):
            ulgen.araclar.calistir("dosya_yaz", {"yol": yol, "icerik": "y"})
        with open(yol) as f:
            self.assertEqual(f.read(), "eski")


if __name__ == "__main__":
    unittest.main()


class ArazDuyarliTesti(unittest.TestCase):
    def test_arazi_tapu_konum_duyarli_sayilir(self):
        from ulgen.guvenlik import duyarli_mi
        for m in ("arazim kaç metrekare?", "tapu bilgilerim neydi", "parsel numarası",
                  "adresim ne"):
            self.assertTrue(duyarli_mi(m), m)
        self.assertFalse(duyarli_mi("zeytin ne zaman budanır"))
