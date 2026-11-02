import hashlib
import json
import os
import unittest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from .temel import TemizVeri
from .test_sunucu import istek, JSON
from ulgen import cbor, ozelkasa, sunucu, veritabani, webauthn
from ulgen.cekirdek import Ulgen

RP = "10-147-17-5.sslip.io"
ORIGIN = "https://" + RP
PAROLA = "dogru-parola-123"


class YazilimFaceID:
    """Sınama için yazılım 'Face ID' (gerçek iPhone değildir)."""

    def __init__(self, rp=RP, origin=ORIGIN, uv=True):
        self.anahtar = ec.generate_private_key(ec.SECP256R1())
        self.cred = os.urandom(16)
        self.rp, self.origin, self.uv, self.sayac = rp, origin, uv, 0
        self.prf = os.urandom(32)

    def _istemci(self, tur, ch, origin=None):
        return json.dumps({"type": tur, "challenge": ch,
                           "origin": origin or self.origin}).encode()

    def kayit(self, ch):
        n = self.anahtar.public_key().public_numbers()
        cose = cbor.kodla_deneme({1: 2, 3: -7, -1: 1,
                                  -2: n.x.to_bytes(32, "big"),
                                  -3: n.y.to_bytes(32, "big")})
        auth = (hashlib.sha256(self.rp.encode()).digest()
                + bytes([0x45 if self.uv else 0x41]) + b"\0\0\0\0"
                + b"\0" * 16 + len(self.cred).to_bytes(2, "big")
                + self.cred + cose)
        return {"clientDataJSON": webauthn.b64(self._istemci(
                    "webauthn.create", ch)),
                "attestationObject": webauthn.b64(cbor.kodla_deneme(
                    {"fmt": "none", "attStmt": {}, "authData": auth}))}

    def giris(self, ch, origin=None):
        self.sayac += 1
        auth = (hashlib.sha256(self.rp.encode()).digest()
                + bytes([0x05 if self.uv else 0x01])
                + self.sayac.to_bytes(4, "big"))
        ham = self._istemci("webauthn.get", ch, origin)
        imza = self.anahtar.sign(auth + hashlib.sha256(ham).digest(),
                                 ec.ECDSA(hashes.SHA256()))
        return {"id": webauthn.b64(self.cred),
                "clientDataJSON": webauthn.b64(ham),
                "authenticatorData": webauthn.b64(auth),
                "signature": webauthn.b64(imza)}


class KasaTemel(TemizVeri):

    def setUp(self):
        super().setUp()
        veritabani.kur()
        ozelkasa._DENEME.update(adet=0, bekle=0.0)

    def kur(self):
        return ozelkasa.kur(PAROLA)

    def faceid_bagla(self):
        f = YazilimFaceID()
        k = ozelkasa.kayit_baslat()
        ozelkasa.kayit_bitir(k["kimlik"], f.kayit(k["challenge"]), RP, ORIGIN)
        ozelkasa.prf_bagla(webauthn.b64(f.cred), f.prf, {"parola": PAROLA})
        return f

    def passkey_acma(self, f, kapsam, origin=None):
        g = ozelkasa.giris_baslat(kapsam)
        v = f.giris(g["challenge"], origin)
        cred = ozelkasa.passkey_dogrula(g["kimlik"], v, RP, ORIGIN, kapsam)
        return {"prf": f.prf, "cred": cred}


class Sifreleme(KasaTemel):

    def test_disk_uzerinde_sifreli_ve_parola_gerekli(self):
        self.kur()
        ozelkasa.oge_ekle("banka", "IBAN TR99 GIZLI", {"parola": PAROLA})
        ham = bytes(veritabani.sorgu("SELECT veri FROM kasa_oge", (),
                                     True)[0]["veri"])
        self.assertNotIn(b"GIZLI", ham)
        self.assertEqual(ozelkasa.oge_oku("banka", {"parola": PAROLA}),
                         "IBAN TR99 GIZLI")
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.oge_oku("banka", {"parola": "yanlis-parola-1"})

    def test_yanlis_denemeler_kilitlenir(self):
        self.kur()
        for _ in range(5):
            with self.assertRaises(ozelkasa.KasaHatasi):
                ozelkasa.oge_oku("x", {"parola": "yanlis-parola-1"})
        with self.assertRaisesRegex(ozelkasa.KasaHatasi, "bekleyin"):
            ozelkasa.oge_oku("x", {"parola": PAROLA})

    def test_kurtarma_kodu_ve_anahtar_paketi(self):
        kod = self.kur()
        ozelkasa.oge_ekle("a", "gizli", {"parola": PAROLA})
        self.assertEqual(ozelkasa.oge_oku("a", {"kod": kod}), "gizli")
        yol = os.path.join(os.path.expanduser("~"), "ÜlgenVeri",
                           "kurtarma.paket")
        from ulgen import gizli
        asil = gizli.ana_anahtar()
        with self.assertRaises(ozelkasa.KasaHatasi):   # anahtar zaten var
            ozelkasa.ana_anahtar_kurtar(yol, kod)
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.ana_anahtar_kurtar(yol, "YANL-ISKO-DXXX")
        self.assertEqual(len(asil), 32)


class FaceID(KasaTemel):

    def test_faceid_ile_ac_ve_tek_kullanimlik(self):
        self.kur()
        ozelkasa.oge_ekle("kart", "4111", {"parola": PAROLA})
        f = self.faceid_bagla()
        acma = self.passkey_acma(f, "oku:kart")
        self.assertEqual(ozelkasa.oge_oku("kart", acma), "4111")
        # aynı challenge ikinci kez kullanılamaz
        g = ozelkasa.giris_baslat("oku:kart")
        v = f.giris(g["challenge"])
        ozelkasa.passkey_dogrula(g["kimlik"], v, RP, ORIGIN, "oku:kart")
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.passkey_dogrula(g["kimlik"], v, RP, ORIGIN, "oku:kart")

    def test_kapsam_baska_islemde_gecmez(self):
        self.kur()
        f = self.faceid_bagla()
        g = ozelkasa.giris_baslat("oku:kart")
        v = f.giris(g["challenge"])
        with self.assertRaisesRegex(ozelkasa.KasaHatasi, "bu işlem"):
            ozelkasa.passkey_dogrula(g["kimlik"], v, RP, ORIGIN, "sil:kart")

    def test_yuz_dogrulanmadiysa_ve_yanlis_origin_reddedilir(self):
        self.kur()
        f = self.faceid_bagla()
        f.uv = False
        g = ozelkasa.giris_baslat("oku:a")
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.passkey_dogrula(g["kimlik"], f.giris(g["challenge"]),
                                     RP, ORIGIN, "oku:a")
        f.uv = True
        g = ozelkasa.giris_baslat("oku:a")
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.passkey_dogrula(
                g["kimlik"], f.giris(g["challenge"], "https://kotu.example"),
                RP, ORIGIN, "oku:a")

    def test_sureli_challenge(self):
        self.kur()
        f = self.faceid_bagla()
        g = ozelkasa.giris_baslat("oku:a")
        webauthn._BEKLEYEN[g["kimlik"]] = (
            webauthn._BEKLEYEN[g["kimlik"]][0],
            webauthn._BEKLEYEN[g["kimlik"]][1], 0)
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.passkey_dogrula(g["kimlik"], f.giris(g["challenge"]),
                                     RP, ORIGIN, "oku:a")

    def test_parola_unutuldu_faceid_ile_yeni_parola(self):
        self.kur()
        ozelkasa.oge_ekle("a", "veri", {"parola": PAROLA})
        f = self.faceid_bagla()
        ozelkasa.parola_degistir(self.passkey_acma(f, "parola-sifirla"),
                                 "yepyeni-parola-9")
        self.assertEqual(ozelkasa.oge_oku("a", {"parola": "yepyeni-parola-9"}),
                         "veri")
        with self.assertRaises(ozelkasa.KasaHatasi):
            ozelkasa.oge_oku("a", {"parola": PAROLA})


class YapayZekaSiniri(KasaTemel):

    def test_sohbet_icerigi_gormez_yalniz_istek_acar(self):
        self.kur()
        ozelkasa.oge_ekle("sifre", "COK-GIZLI-ICERIK", {"parola": PAROLA})
        u = Ulgen()
        yanit = u.sohbet_isle("özel kasadan sifre getir")["yanit"]
        self.assertIn("Face ID", yanit)
        self.assertNotIn("COK-GIZLI", yanit)
        gecmis = json.dumps(veritabani.sorgu(
            "SELECT * FROM sohbet", (), True), default=str)
        self.assertNotIn("COK-GIZLI", gecmis)
        self.assertEqual(len(ozelkasa.bekleyen_istekler()), 1)
        self.assertIn("yok", u.sohbet_isle("özel kasadan yok-boyle getir")
                      ["yanit"])

    def test_arac_katmani_cozme_islevi_icermez(self):
        import inspect
        from ulgen import araclar, beyin, cekirdek, ajanlar
        for modul in (araclar, beyin, cekirdek, ajanlar):
            kaynak = inspect.getsource(modul)
            for yasak in ("oge_oku", "_k_ac", "oge_ekle", "oge_sil",
                          "parola_degistir"):
                self.assertNotIn(yasak, kaynak, (modul.__name__, yasak))

    def test_istek_tek_kullanimlik_ve_sureli(self):
        self.kur()
        ozelkasa.oge_ekle("a", "x", {"parola": PAROLA})
        ozelkasa.istek_olustur("a")
        kimlik = ozelkasa.bekleyen_istekler()[0]["id"]
        self.assertTrue(ozelkasa.istek_tuket(kimlik, "a"))
        self.assertFalse(ozelkasa.istek_tuket(kimlik, "a"))
        ozelkasa.istek_olustur("a")
        k2 = ozelkasa.bekleyen_istekler()[0]["id"]
        veritabani.sorgu("UPDATE kasa_istek SET bitis=0 WHERE id=?", (k2,))
        self.assertFalse(ozelkasa.istek_tuket(k2, "a"))
        ozelkasa.istek_olustur("a")
        k3 = ozelkasa.bekleyen_istekler()[0]["id"]
        self.assertFalse(ozelkasa.istek_tuket(k3, "baska"))   # kapsam


class Http(KasaTemel):

    def test_http_akisi(self):
        u = Ulgen()
        srv = sunucu.yerel_sunucu(u, 0)
        sunucu.arka_planda_calistir(srv)
        self.addCleanup(srv.shutdown)
        port = srv.server_address[1]
        host = "127.0.0.1:%d" % port

        def p(yol, govde):
            kod, ham = istek(port, yol, "POST", json.dumps(govde), JSON)
            return kod, json.loads(ham)
        kod, r = p("/kasa/kur", {"parola": PAROLA})
        self.assertEqual(kod, 200)
        self.assertEqual(p("/kasa/ekle", {"ad": "n", "icerik": "ICERIK",
                                          "yontem": "parola",
                                          "parola": PAROLA})[0], 200)
        # yanlış parola 400, içerik sızmaz
        kod, r = p("/kasa/oku", {"ad": "n", "yontem": "parola",
                                 "parola": "yanlis-parola-1"})
        self.assertEqual(kod, 400)
        self.assertNotIn("ICERIK", json.dumps(r))
        # yetkisiz erişim
        self.assertEqual(istek(port, "/kasa/durum", yetkisiz=True)[0], 401)
        d = json.loads(istek(port, "/kasa/durum")[1])
        self.assertEqual(d["adlar"], ["n"])
        # istek + Face ID (http://127.0.0.1 rpId'si bu testte kendisi)
        f = YazilimFaceID(rp="127.0.0.1", origin="http://" + host)
        kod, k = p("/kasa/passkey/kayit-baslat", {})
        kod, r = p("/kasa/passkey/kayit-bitir", {
            "kimlik": k["kimlik"], "veri": f.kayit(k["challenge"])})
        self.assertEqual(kod, 200)
        p("/kasa/passkey/bagla", {"cred": r["cred"], "parola": PAROLA,
                                  "prf": webauthn.b64(f.prf)})
        ozelkasa.istek_olustur("n")
        iid = ozelkasa.bekleyen_istekler()[0]["id"]

        def oku(istek_no):
            kod, g = p("/kasa/passkey/giris-baslat", {"kapsam": "oku:n"})
            return p("/kasa/oku", {
                "ad": "n", "yontem": "passkey", "kimlik": g["kimlik"],
                "veri": f.giris(g["challenge"]), "prf": webauthn.b64(f.prf),
                "istek": istek_no})
        kod, r = oku(iid)
        self.assertEqual((kod, r.get("icerik")), (200, "ICERIK"))
        kod, r = oku(iid)                     # aynı istek ikinci kez
        self.assertEqual(kod, 400)


if __name__ == "__main__":
    unittest.main()
