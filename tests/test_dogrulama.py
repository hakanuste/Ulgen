import unittest

from .temel import TemizVeri
from ulgen import ayar, dogrulama
from ulgen.cekirdek import Ulgen

YANIT = ("Musso 1993'te tanıtıldı. Aracı İngiliz Ken Greenley tasarladı. "
         "Benzinli seçeneklerde Mercedes M104 ailesinden 3.2 litrelik motor "
         "bulunur. Genel olarak sağlam sayılır ve çok kullanılır, sevilir.")


class SahteArastirma:
    def __init__(self, metin, hata=False):
        self.metin, self.hata = metin, hata

    def ara(self, sorgu, adet=5):
        if self.hata:
            raise OSError("ağ yok")
        return [{"baslik": "Sayfa", "adres": "https://ornek.org/x",
                 "ozet": self.metin}]

    def sayfa_metni(self, adres, hedef=3000):
        return self.metin


class Dogrulama(TemizVeri):

    def test_iddialar_sayi_ya_da_ozel_ad_icerir(self):
        i = dogrulama.iddialar_ayikla(YANIT)
        self.assertTrue(any("Greenley" in c for c in i))
        self.assertFalse(any(c.startswith("Genel olarak") for c in i))

    def test_puanlama_destek_ve_eksik(self):
        oran, _ = dogrulama.puanla(
            "Aracı İngiliz Ken Greenley tasarladı.",
            "The car was designed by Briton Ken Greenley ingiliz")
        self.assertGreaterEqual(oran, dogrulama.DESTEK)
        oran2, eksik = dogrulama.puanla("Aracı Ken Greenley 1993 yaptı.",
                                        "alakasız metin")
        self.assertEqual(dogrulama.durum_adi(oran2), "bulunamadı")
        self.assertTrue(eksik)

    def test_calistir_bildirir(self):
        gelen = []
        s = dogrulama.calistir(
            YANIT, SahteArastirma("Ken Greenley Mercedes M104 1993 3.2 "
                                  "Musso İngiliz"), gelen.append)
        self.assertTrue(s)
        self.assertIn("Doğrulama bitti", gelen[0])
        self.assertIn("yanlış:", gelen[0])

    def test_ag_yoksa_sessiz(self):
        gelen = []
        dogrulama.calistir(YANIT, SahteArastirma("", hata=True), gelen.append)
        self.assertEqual(gelen, [])

    def test_uygunluk(self):
        ayar.guncelle("dogrulama", True)
        self.assertTrue(dogrulama.uygun_mu("musso?", YANIT))
        self.assertFalse(dogrulama.uygun_mu("musso?", YANIT, True))
        self.assertFalse(dogrulama.uygun_mu("musso?", "kısa yanıt"))
        self.assertFalse(dogrulama.uygun_mu("ilaç dozu nedir", YANIT))
        ayar.guncelle("dogrulama", False)
        self.assertFalse(dogrulama.uygun_mu("musso?", YANIT))

    def test_yanlis_komutu_hafizaya_yazar(self):
        self.assertEqual(dogrulama.duzeltme_mi("yanlış: motor 3.2 değil"),
                         "motor 3.2 değil")
        self.assertIsNone(dogrulama.duzeltme_mi("yanlış"))
        u = Ulgen()
        sonuc = u.sohbet_isle("Yanlış: aracım 1998 model")
        self.assertIn("kaydettim", sonuc["yanit"])


if __name__ == "__main__":
    unittest.main()
