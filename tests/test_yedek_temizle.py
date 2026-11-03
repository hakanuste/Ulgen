"""yedekler klasöründe eski kopyaların temizlenmesi."""

import os

from tests.temel import TemizVeri
from ulgen import ayar, yedek


class EskiTemizleTesti(TemizVeri):

    def test_her_turden_en_yeni_uc_kalir(self):
        kok = os.path.join(ayar.KLASOR, "yedekler")
        os.makedirs(os.path.join(kok, "otomatik"), exist_ok=True)
        for n in range(6):
            d = os.path.join(kok, "kurulum-2026110%d-000000" % (n + 1))
            os.makedirs(d)
            open(os.path.join(d, "veri.db"), "w").write("x")
        for n in range(5):
            open(os.path.join(kok, "onceki-sifresiz-2026110%d_1.db.sifreli" % n), "w").write("x")
        open(os.path.join(kok, "otomatik", "veri-1.db.enc"), "w").write("x")
        open(os.path.join(kok, "faceid-1.ulgenyedek"), "w").write("x")
        silinen = yedek.eskiyi_temizle()
        self.assertEqual(len(silinen), 3 + 2)
        kalan = sorted(os.listdir(kok))
        self.assertEqual(len([a for a in kalan if a.startswith("kurulum-")]), 3)
        self.assertIn("kurulum-20261106-000000", kalan)
        self.assertNotIn("kurulum-20261101-000000", kalan)
        self.assertEqual(len([a for a in kalan if a.startswith("onceki-")]), 3)
        self.assertIn("faceid-1.ulgenyedek", kalan)           # başka kopyalara dokunmaz
        self.assertTrue(os.path.exists(os.path.join(kok, "otomatik", "veri-1.db.enc")))

    def test_klasor_yoksa_hata_vermez(self):
        self.assertEqual(yedek.eskiyi_temizle(), [])
