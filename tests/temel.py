"""Testler için ortak taban sınıf: her testte temiz bir ÜlgenVeri."""

import os
import shutil
import unittest

from . import TEST_EV  # noqa: F401  (HOME'u ayarlar)
from ulgen import ayar, gizli, veritabani  # noqa: E402


class TemizVeri(unittest.TestCase):

    def setUp(self):
        veritabani.kapat()
        shutil.rmtree(ayar.KLASOR, ignore_errors=True)
        os.makedirs(ayar.KLASOR, mode=0o700)
        gizli._SIR_ONBELLEK.clear()
        with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
            f.write('{"rapor_acik": false}')
        veritabani.kur()
