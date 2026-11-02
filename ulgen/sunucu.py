"""Yerel HTTP sunucusu: Mac'teki tarayıcıya ve iPhone'a hizmet verir.

  * 127.0.0.1 (Mac'in kendisi): anahtar gerekmez.
  * Başka cihazlar (ZeroTier üzerinden iPhone): 'Authorization: Bearer
    <anahtar>' gerekir. Anahtar ~/ÜlgenVeri/anahtar.txt dosyasındadır.
Veri Mac'te kalır; sunucu yalnızca yerel ağ/ZeroTier'de dinler.
"""

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import ayar, veritabani
from .arayuz import SAYFA

YEREL_ADRESLER = ("127.0.0.1", "::1")


def istek_sinifi(ulgen, anahtar):
    """Ulgen nesnesine bağlı istek işleyici sınıfı üretir."""

    class Istek(BaseHTTPRequestHandler):

        def _cevap(self, durum, govde, tur="application/json; charset=utf-8"):
            if isinstance(govde, (dict, list)):
                govde = json.dumps(govde, ensure_ascii=False).encode("utf-8")
            elif isinstance(govde, str):
                govde = govde.encode("utf-8")
            self.send_response(durum)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(govde)

        def _yetkili(self):
            if self.client_address[0] in YEREL_ADRESLER:
                return True
            baslik = self.headers.get("Authorization", "")
            return baslik.startswith("Bearer ") and hmac.compare_digest(
                baslik[7:].encode(), anahtar.encode())

        def _govde(self):
            uzunluk = int(self.headers.get("Content-Length", 0) or 0)
            if uzunluk <= 0 or uzunluk > 200000:
                return {}
            try:
                return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}

        def do_GET(self):
            adres = urlparse(self.path)
            yol = adres.path
            if yol in ("/", "/index.html"):
                return self._cevap(200, SAYFA, "text/html; charset=utf-8")
            if yol == "/saglik":
                return self._cevap(200, {"durum": "tamam"})
            if not self._yetkili():
                return self._cevap(401, {"hata": "yetkisiz"})
            if yol == "/bildirimler":
                try:
                    son = int(parse_qs(adres.query).get("son", ["0"])[0])
                except ValueError:
                    son = 0
                return self._cevap(200, ulgen.bildirimler(son))
            if yol == "/durum":
                durum = ulgen.yonlendirici.durum()
                bildirimler = ulgen.bildirimler(0)
                durum["son_bildirim"] = (bildirimler[-1]["id"]
                                         if bildirimler else 0)
                return self._cevap(200, durum)
            if yol == "/ozet":
                satirlar = veritabani.sorgu(
                    "SELECT zaman, mesaj FROM hatirlaticilar WHERE "
                    "onaylandi = 0 AND (bildirildi = 0 OR kalici = 1) "
                    "ORDER BY zaman LIMIT 15", (), True)
                return self._cevap(200, {"hatirlaticilar": satirlar})
            return self._cevap(404, {"hata": "bulunamadı"})

        def do_POST(self):
            if not self._yetkili():
                return self._cevap(401, {"hata": "yetkisiz"})
            if urlparse(self.path).path == "/sohbet":
                veri = self._govde()
                return self._cevap(
                    200, ulgen.sohbet_isle(str(veri.get("metin", ""))))
            return self._cevap(404, {"hata": "bulunamadı"})

        def log_message(self, *args):
            pass

    return Istek


def baslat(ulgen, port=ayar.PORT):
    """Sunucuyu oluşturur (başlatmaz). Port doluysa OSError fırlatır."""
    anahtar = ayar.anahtar_al()
    return ThreadingHTTPServer(("0.0.0.0", port), istek_sinifi(ulgen, anahtar))


def arka_planda_calistir(sunucu):
    kanal = threading.Thread(target=sunucu.serve_forever, daemon=True)
    kanal.start()
    return kanal
