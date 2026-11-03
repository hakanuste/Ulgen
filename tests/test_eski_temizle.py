"""Ülgen/eski klasörünün budanması."""

import os
import tempfile
import unittest

from ulgen import guncelle


class EskiBudaTesti(unittest.TestCase):

    def test_en_yeniler_kalir(self):
        kok = tempfile.mkdtemp()
        eski = os.path.join(kok, "eski")
        for n in range(6):
            os.makedirs(os.path.join(eski, "guncelleme-2026110%d-000000" % (n + 1), "ulgen"))
        for n in range(3):
            os.makedirs(os.path.join(eski, "Ülgen.app-2026110%d-1" % (n + 1)))
        for n in range(2):
            os.makedirs(os.path.join(eski, "ulgen-2026110%d-1" % (n + 1)))
        os.makedirs(os.path.join(eski, "baska"))
        silinen = guncelle.eskiyi_temizle(kok)
        self.assertEqual(len(silinen), 3 + 2 + 1)
        kalan = sorted(os.listdir(eski))
        self.assertEqual(kalan, sorted(["Ülgen.app-20261103-1",
                                 "baska",
                                 "guncelleme-20261104-000000",
                                 "guncelleme-20261105-000000",
                                 "guncelleme-20261106-000000",
                                 "ulgen-20261102-1"]))
        self.assertEqual(guncelle.yedekler(kok)[-1], "guncelleme-20261106-000000")

    def test_klasor_yoksa_bos(self):
        self.assertEqual(guncelle.eskiyi_temizle(tempfile.mkdtemp()), [])


if __name__ == "__main__":
    unittest.main()
