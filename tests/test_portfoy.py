import http.server
import tempfile
import threading
import unittest
from datetime import date
from unittest import mock

from .temel import TemizVeri
from ulgen import oturum, portfoy

X = "<svg><path d='M1 1L9 9M9 1L1 9'/></svg>"
V = "<svg><path d='M1 5L4 9L9 1'/></svg>"


def hucre(t="", s=""):
    return {"t": t, "s": s}


def satir(kod, oneri, tr, hedef, son, getiri, simge):
    return [hucre("1"), hucre(kod), hucre(oneri), hucre(tr), hucre(hedef),
            hucre("G" + son), hucre("% " + getiri), hucre("", simge)]


class Ayristirma(unittest.TestCase):

    def test_sayi_ve_tarih(self):
        self.assertEqual(portfoy.sayi("% -45,42"), -45.42)
        self.assertEqual(portfoy.sayi("G331,75"), 331.75)
        self.assertEqual(portfoy.sayi("1.234,50"), 1234.5)
        self.assertEqual(portfoy.tarih("6 Kas 2026"), date(2026, 11, 6))
        self.assertEqual(portfoy.tarih("16 Tem 2026"), date(2026, 7, 16))
        self.assertIsNone(portfoy.tarih("merhaba"))

    def test_yon(self):
        self.assertEqual(portfoy.yon("Al"), "olumlu")
        self.assertEqual(portfoy.yon("Endeks altı"), "olumsuz")
        self.assertEqual(portfoy.yon("Tut"), "nötr")

    def test_satir_coz_ekran_goruntusu_satirlari(self):
        k = portfoy.satir_coz(satir("MGROS", "Al", "6 Kas 2026", "950,00",
                                    "468,75", "102,67", V))
        self.assertEqual((k["kod"], k["oneri"], k["hedef"], k["son"]),
                         ("MGROS", "Al", 950.0, 468.75))
        self.assertEqual(k["tarih"], date(2026, 11, 6))
        k2 = portfoy.satir_coz(satir("VAKBN", "Endeks altı", "16 Tem 2026",
                                     "30,80", "33,06", "-6,84", X))
        self.assertEqual((k2["oneri"], k2["getiri"]), ("Endeks altı", -6.84))
        self.assertIsNone(portfoy.satir_coz([hucre("#"), hucre("Öneri")]))

    def test_metinden_coz(self):
        m = ("1 ASELS Al 1 Eki 2026 575,00 G331,75 % 73,32 ✕\\n"
             "2 VAKBN Endeks altı 16 Tem 2026 30,80 G33,06 % -6,84")
        k = portfoy.metinden_coz(m.replace("\\n", "\n"))
        self.assertEqual([x["kod"] for x in k], ["ASELS", "VAKBN"])
        self.assertEqual(k[1]["oneri"], "Endeks altı")

    def test_kurum_kodlari(self):
        b = ["/araci-kurumlar/YKR", "/araci-kurumlar/MLB/hacim-analizi",
             "/araci-kurumlar/YKR/analist-tavsiyeleri", "/hisse/THYAO", None]
        self.assertEqual(portfoy.kurum_kodlari(b), ["YKR", "MLB"])


class Derleme(unittest.TestCase):

    def kayit(self, kod, oneri, gun, hedef, simge):
        return {"kod": kod, "oneri": oneri, "tarih": gun, "hedef": hedef,
                "son": 10.0, "getiri": 20.0, "simge": simge}

    def test_topla_ozet_rapor(self):
        bugun = date(2026, 11, 8)
        kurumlar = {
            "YKR": [self.kayit("MGROS", "Al", date(2026, 11, 6), 950, V),
                    self.kayit("ISCTR", "Al", date(2026, 11, 6), 17.5, X)],
            "MLB": [self.kayit("ISCTR", "Tut", date(2026, 7, 16), 17.2, X),
                    self.kayit("ESKI", "Al", date(2025, 1, 1), 5, X)],
            "AKM": [self.kayit("ISCTR", "Al", date(2026, 10, 1), 18, X),
                    self.kayit("OTKAR", "Sat", date(2026, 10, 1), 3, X)],
        }
        hisseler, yok = portfoy.topla(kurumlar, bugun)
        self.assertEqual(yok, X)
        self.assertNotIn("ESKI", hisseler)           # 180 günden eski
        self.assertEqual(hisseler["MGROS"]["model"], 1)
        r = portfoy.ozet(hisseler, 3)
        ilk = r[0]
        self.assertEqual(ilk["kod"], "ISCTR")
        self.assertEqual((ilk["kurum"], ilk["olumlu"], ilk["notr"]), (3, 2, 1))
        self.assertAlmostEqual(ilk["kapsam"], 100.0)
        self.assertEqual(ilk["hedef_ort"], 17.5)
        metin = portfoy.rapor(kurumlar, ["XYZ"], bugun)
        self.assertIn("| ISCTR | 3 | %100 | 2/1/0 |", metin)
        self.assertIn("bizim önerimiz değildir", metin)
        self.assertIn("XYZ", metin)


LISTE = """<html><body><a href="/araci-kurumlar/YKR">Yapı Kredi</a>
<a href="/araci-kurumlar/MLB">BofA</a><a href="/araci-kurumlar/BOS">Bos</a>
</body></html>"""


def kurum_sayfasi(satirlar):
    govde = "".join(
        "<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
        "<td>G%s</td><td>%% %s</td><td>%s</td></tr>" % (i, *s)
        for i, s in enumerate(satirlar, 1))
    return ("<html><body><table><tr><th>#</th><th>Hisse</th><th>Öneri</th>"
            "<th>Tarih</th><th>Hedef</th><th>Son</th><th>Getiri</th>"
            "<th>Model</th></tr>%s</table></body></html>" % govde)


class Sunucu(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        bugun = date.today()
        tr = "%d Kas %d" % (max(1, min(bugun.day, 28)), bugun.year)
        if self.path.startswith("/araci-kurumlar/YKR/"):
            sayfa = kurum_sayfasi([
                ("MGROS", "Al", tr, "950,00", "468,75", "102,67", "<svg><path d='M1 5L4 9L9 1'/></svg>"),
                ("ISCTR", "Al", tr, "17,50", "13,29", "31,68", "<svg><path d='M1 1L9 9M9 1L1 9'/></svg>"),
                ("VAKBN", "Tut", tr, "40,50", "33,06", "22,50", "<svg><path d='M1 1L9 9M9 1L1 9'/></svg>")])
        elif self.path.startswith("/araci-kurumlar/MLB/"):
            sayfa = kurum_sayfasi([
                ("ISCTR", "Tut", tr, "17,20", "13,29", "29,42", "<svg><path d='M1 1L9 9M9 1L1 9'/></svg>")])
        elif self.path.startswith("/araci-kurumlar/BOS/"):
            sayfa = "<html><body>Tavsiye yok</body></html>"
        else:
            sayfa = LISTE
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(sayfa.encode())


@unittest.skipUnless(oturum.hazir_mi(), "playwright kurulu değil")
class GercekTarayici(TemizVeri):

    def test_uctan_uca(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Sunucu)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        taban = "http://127.0.0.1:%d/araci-kurumlar" % srv.server_address[1]
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(oturum, "PROFIL", d), \
                mock.patch.object(portfoy, "LISTE_ADRESI", taban), \
                mock.patch.object(oturum, "hazirlik_hatasi",
                                  lambda a, g=True: None):
            r = portfoy.calistir(10, bekleme_sn=0.0)
        self.assertIn("2 kurum okundu", r)
        self.assertIn("BOS", r)                       # okunamayan listelenir
        self.assertIn("| ISCTR | 2 | %100 | 1/1/0 |", r)
        self.assertIn("| MGROS | 1 |", r)


if __name__ == "__main__":
    unittest.main()
