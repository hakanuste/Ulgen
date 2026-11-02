"""HTTP/HTTPS sunucuları.

  * Mac'in kendisi : http://127.0.0.1:8765   (yalnızca bu makineden erişilir)
  * iPhone         : https://<ZeroTier adresi>:8443  (cihaz belirteci gerekir)
  * CA indirme     : http://<ZeroTier adresi>:8766   (yalnızca genel CA sertifikası)

Tüm dinleyiciler SALT belirtilen adreslere bağlanır (0.0.0.0 kullanılmaz).
Her istekte Host (DNS rebinding), Origin/Sec-Fetch-Site (CSRF) ve POST için
Content-Type: application/json denetlenir. Uzak istekler cihaz belirteciyle
doğrulanır; art arda yanlış denemede IP geçici engellenir.
"""

import ipaddress
import json
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import ayar, cihazlar, kodpenceresi, kota, kuyruk, tls, veritabani
from .arayuz import SAYFA

YEREL_AD = "localhost"
AZAMI_ESZAMANLI = 32
DENEME_SINIRI = 5
ENGEL_SURESI = 300

GUVENLIK_BASLIKLARI = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"),
}


class HizSiniri:
    """Yanlış belirteç denemelerini IP başına sayar ve geçici engeller."""

    def __init__(self, sinir=DENEME_SINIRI, sure=ENGEL_SURESI):
        self._sinir = sinir
        self._sure = sure
        self._kayit = {}
        self._kilit = threading.Lock()

    def kilitli_mi(self, ip, simdi=None):
        simdi = simdi or time.time()
        with self._kilit:
            sayi, bitis = self._kayit.get(ip, (0, 0))
            return sayi >= self._sinir and simdi < bitis

    def hata(self, ip, simdi=None):
        simdi = simdi or time.time()
        with self._kilit:
            sayi, bitis = self._kayit.get(ip, (0, 0))
            if simdi >= bitis:
                sayi = 0
            self._kayit[ip] = (sayi + 1, simdi + self._sure)

    def basarili(self, ip):
        with self._kilit:
            self._kayit.pop(ip, None)


class Sunucu(ThreadingHTTPServer):
    """Eşzamanlı bağlantı sınırlı, isteğe bağlı TLS'li sunucu."""

    daemon_threads = True
    request_queue_size = 32

    def __init__(self, adres, isleyici, yerel=False, ssl_baglami=None):
        self.yerel = yerel
        self.ssl_baglami = ssl_baglami
        self._sinir = threading.BoundedSemaphore(AZAMI_ESZAMANLI)
        super().__init__(adres, isleyici)

    def process_request(self, request, client_address):
        if not self._sinir.acquire(blocking=False):
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._sinir.release()

    def finish_request(self, request, client_address):
        if self.ssl_baglami is not None:
            try:
                request.settimeout(10)
                request = self.ssl_baglami.wrap_socket(request,
                                                       server_side=True)
            except (ssl.SSLError, OSError):
                return
            try:
                super().finish_request(request, client_address)
            finally:
                try:
                    request.close()
                except OSError:
                    pass
            return
        super().finish_request(request, client_address)


def _host_adi(baslik):
    """Host başlığından ad/IP kısmını ayıklar ([::1]:8765 dahil)."""
    baslik = (baslik or "").strip().lower()
    if baslik.startswith("["):
        return baslik[1:baslik.find("]")] if "]" in baslik else ""
    return baslik.rsplit(":", 1)[0] if ":" in baslik else baslik


def host_gecerli_mi(baslik):
    """IP adresi, 'localhost' ya da izinli_hostlar içindeki adlar kabul edilir.

    Başka alan adları reddedilir; böylece DNS rebinding işe yaramaz.
    """
    ad = _host_adi(baslik)
    if not ad:
        return False
    if ad == YEREL_AD or ad in ayar.yukle().get("izinli_hostlar", []):
        return True
    try:
        ipaddress.ip_address(ad)
        return True
    except ValueError:
        return False


def origin_gecerli_mi(origin, host, fetch_site):
    """Aynı kaynak (same-origin) olmayan tarayıcı isteklerini reddeder."""
    if fetch_site and fetch_site.lower() not in ("same-origin", "none"):
        return False
    if not origin:
        return True
    if origin == "null":
        return False
    return urlparse(origin).netloc.lower() == (host or "").lower()


def istek_sinifi(ulgen, limit):
    """Ulgen nesnesine bağlı ana istek işleyici sınıfı."""

    class Istek(BaseHTTPRequestHandler):
        timeout = 15
        server_version = "Ulgen"
        sys_version = ""

        def _cevap(self, durum, govde, tur="application/json; charset=utf-8"):
            if isinstance(govde, (dict, list)):
                govde = json.dumps(govde, ensure_ascii=False).encode("utf-8")
            elif isinstance(govde, str):
                govde = govde.encode("utf-8")
            self.send_response(durum)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            for ad, deger in GUVENLIK_BASLIKLARI.items():
                self.send_header(ad, deger)
            self.end_headers()
            self.wfile.write(govde)

        def _on_denetim(self):
            """Host/Origin denetimi; geçmezse yanıtlar ve False döndürür."""
            if not host_gecerli_mi(self.headers.get("Host")):
                self._cevap(403, {"hata": "geçersiz host"})
                return False
            if not origin_gecerli_mi(self.headers.get("Origin"),
                                     self.headers.get("Host"),
                                     self.headers.get("Sec-Fetch-Site")):
                self._cevap(403, {"hata": "başka kaynaktan istek"})
                return False
            return True

        def _yetkili(self):
            if self.server.yerel:
                return True
            ip = self.client_address[0]
            if limit.kilitli_mi(ip):
                self._cevap(429, {"hata": "çok fazla yanlış deneme"})
                return False
            baslik = self.headers.get("Authorization", "")
            belirtec = baslik[7:] if baslik.startswith("Bearer ") else ""
            if cihazlar.dogrula(belirtec):
                limit.basarili(ip)
                return True
            limit.hata(ip)
            self._cevap(401, {"hata": "yetkisiz"})
            return False

        def _govde(self):
            try:
                uzunluk = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                return {}
            if uzunluk <= 0 or uzunluk > 200000:
                return {}
            try:
                veri = json.loads(self.rfile.read(uzunluk).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}
            return veri if isinstance(veri, dict) else {}

        def do_GET(self):
            if not self._on_denetim():
                return
            adres = urlparse(self.path)
            yol = adres.path
            if yol in ("/", "/index.html"):
                return self._cevap(200, SAYFA, "text/html; charset=utf-8")
            if yol == "/saglik":
                return self._cevap(200, {"durum": "tamam"})
            if not self._yetkili():
                return
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
            if yol == "/kota":
                return self._cevap(200, kota.tablo())
            if yol == "/kuyruk":
                return self._cevap(200, kuyruk.bekleyenler())
            if yol == "/kod/liste":
                return self._cevap(200, kodpenceresi.liste())
            if yol == "/kod/oku":
                try:
                    ad = parse_qs(adres.query).get("ad", [""])[0]
                    return self._cevap(200, {"ad": ad,
                                             "icerik": kodpenceresi.oku(ad)})
                except kodpenceresi.KodHatasi as hata:
                    return self._cevap(400, {"hata": str(hata)})
            if yol == "/ilac/bugun":
                return self._cevap(
                    200, ulgen.zamanlayici.ilac.bugun_json())
            if yol == "/ozet":
                satirlar = veritabani.sorgu(
                    "SELECT zaman, mesaj FROM hatirlaticilar WHERE "
                    "onaylandi = 0 AND (bildirildi = 0 OR kalici = 1) "
                    "ORDER BY zaman LIMIT 15", (), True)
                return self._cevap(200, {"hatirlaticilar": satirlar})
            return self._cevap(404, {"hata": "bulunamadı"})

        def do_POST(self):
            if not self._on_denetim():
                return
            tur = (self.headers.get("Content-Type") or "").lower()
            if not tur.startswith("application/json"):
                return self._cevap(415, {"hata": "application/json gerekli"})
            veri = self._govde()    # önce gövde okunur (bağlantı sıfırlanmasın)
            if not self._yetkili():
                return
            if urlparse(self.path).path == "/sohbet":
                return self._cevap(
                    200, ulgen.sohbet_isle(str(veri.get("metin", ""))))
            if urlparse(self.path).path == "/ilac/yanit":
                return self._doz_yanit(veri)
            if urlparse(self.path).path.startswith("/kod/"):
                return self._kod(urlparse(self.path).path, veri)
            return self._cevap(404, {"hata": "bulunamadı"})

        def _doz_yanit(self, veri):
            """TEK doz: {"doz": 12, "yanit": "alindi|ertele|almadi|atlandi",
            "dk": 15}. Başka hiçbir doza dokunmaz."""
            doz, yanit = veri.get("doz"), veri.get("yanit")
            dk = veri.get("dk", 15)
            if not isinstance(doz, int) or isinstance(doz, bool) \
                    or not isinstance(yanit, str) \
                    or not isinstance(dk, int):
                return self._cevap(400, {"hata": "doz(int) ve yanit gerekli"})
            return self._cevap(200, {"yanit": ulgen.zamanlayici.ilac.yanit(
                doz, yanit, dk, "arayuz")})

        def _kod(self, yol, veri):
            try:
                if yol == "/kod/kaydet":
                    ad = kodpenceresi.kaydet(str(veri.get("ad", "")),
                                             str(veri.get("icerik", "")))
                    return self._cevap(200, {"ad": ad})
                if yol == "/kod/calistir":
                    return self._cevap(200, kodpenceresi.calistir(
                        str(veri.get("icerik", "")),
                        str(veri.get("dil", "python")),
                        veri.get("sure", 30) if isinstance(
                            veri.get("sure", 30), int) else 30,
                        uzaktan=not self.server.yerel))
            except kodpenceresi.KodHatasi as hata:
                return self._cevap(400, {"hata": str(hata)})
            return self._cevap(404, {"hata": "bulunamadı"})

        def log_message(self, *args):
            pass

    return Istek


CA_SAYFASI = """<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ülgen sertifikası</title>
<style>body{font-family:-apple-system,sans-serif;max-width:34em;margin:2em auto;
padding:0 1em;line-height:1.5}a.d{display:block;background:#0a84ff;color:#fff;
padding:14px;border-radius:12px;text-align:center;text-decoration:none}</style>
</head><body><h2>Ülgen güvenli bağlantı</h2>
<p><a class="d" href="/ca.crt">Sertifikayı indir</a></p>
<ol><li>"İzin ver" deyin (Profil indirildi).</li>
<li>Ayarlar &gt; Genel &gt; VPN ve Aygıt Yönetimi &gt; Ülgen Yerel CA &gt; Yükle.</li>
<li>Ayarlar &gt; Genel &gt; Hakkında &gt; Sertifika Güven Ayarları &gt;
Ülgen Yerel CA'yı açın.</li>
<li>Sonra Safari'de <b>https://%s:%d</b> adresini açın.</li></ol>
<p>Bu sertifika yalnızca Ülgen sunucunuzu doğrulamak içindir.</p></body></html>"""


def ca_istek_sinifi(adres_metni, https_port):
    """Yalnızca genel CA sertifikasını ve yönergeleri sunan işleyici."""

    class CaIstek(BaseHTTPRequestHandler):
        timeout = 15
        server_version = "Ulgen"
        sys_version = ""

        def do_GET(self):
            if not host_gecerli_mi(self.headers.get("Host")):
                self.send_error(403)
                return
            yol = urlparse(self.path).path
            if yol == "/ca.crt":
                govde = tls.ca_der()
                tur = "application/x-x509-ca-cert"
            elif yol in ("/", "/index.html"):
                govde = (CA_SAYFASI % (adres_metni, https_port)).encode()
                tur = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(govde)

        def log_message(self, *args):
            pass

    return CaIstek


def zerotier_adresleri():
    """ZeroTier arayüzlerinin (zt...) IPv4 adreslerini bulur."""
    komut = (["ifconfig"] if sys.platform == "darwin"
             else ["ip", "-o", "-4", "addr", "show"])
    try:
        cikti = subprocess.run(komut, capture_output=True, text=True,
                               timeout=5, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    adresler = []
    if sys.platform == "darwin":
        arayuz = ""
        for satir in cikti.splitlines():
            if satir and not satir[0].isspace():
                arayuz = satir.split(":")[0]
            elif arayuz.startswith("zt"):
                eslesme = re.match(r"\s+inet (\d+\.\d+\.\d+\.\d+) ", satir)
                if eslesme:
                    adresler.append(eslesme.group(1))
    else:
        for satir in cikti.splitlines():
            eslesme = re.match(r"\d+:\s+(zt\S*)\s+inet (\d+\.\d+\.\d+\.\d+)",
                               satir)
            if eslesme:
                adresler.append(eslesme.group(2))
    return adresler


def yerel_sunucu(ulgen, port=None, limit=None):
    """127.0.0.1 üzerinde (yalnızca bu makineden) HTTP sunucusu."""
    port = ayar.PORT if port is None else port
    return Sunucu(("127.0.0.1", port),
                  istek_sinifi(ulgen, limit or HizSiniri()), yerel=True)


def uzak_sunucu(ulgen, adres, port, baglam, limit=None):
    """Belirli bir adreste HTTPS sunucusu (cihaz belirteci ister)."""
    return Sunucu((adres, port), istek_sinifi(ulgen, limit or HizSiniri()),
                  yerel=False, ssl_baglami=baglam)


def arka_planda_calistir(sunucu):
    kanal = threading.Thread(target=sunucu.serve_forever, daemon=True)
    kanal.start()
    return kanal


class Dinleme:
    """Yerel sunucuyu açar; ZeroTier adreslerini izleyip HTTPS'i yönetir."""

    TARAMA_ARALIGI = 30

    def __init__(self, ulgen):
        self._ulgen = ulgen
        self._limit = HizSiniri()
        self._yerel = None
        self._uzak = []
        self._adresler = ()
        self._kilit = threading.Lock()

    def yerel_baslat(self):
        self._yerel = yerel_sunucu(self._ulgen, limit=self._limit)
        arka_planda_calistir(self._yerel)

    def adresler(self):
        ayarli = ayar.yukle().get("dinleme_adresleri") or []
        return tuple(sorted(ayarli or zerotier_adresleri()))

    def tara(self):
        """Adresler değiştiyse uzak dinleyicileri yeniden kurar."""
        adresler = self.adresler()
        with self._kilit:
            if adresler == self._adresler:
                return
            for s in self._uzak:
                s.shutdown()
                s.server_close()
            self._uzak = []
            self._adresler = adresler
            if not adresler:
                return
            baglam = tls.ssl_baglami(adresler)
            a = ayar.yukle()
            for ip in adresler:
                try:
                    https = uzak_sunucu(self._ulgen, ip, a["https_port"],
                                        baglam, self._limit)
                    ca = Sunucu((ip, a["ca_port"]),
                                ca_istek_sinifi(ip, a["https_port"]))
                except OSError as hata:
                    print("Dinlenemedi %s: %s" % (ip, hata), flush=True)
                    continue
                for s in (https, ca):
                    arka_planda_calistir(s)
                    self._uzak.append(s)
                print("iPhone adresi: https://%s:%d  (sertifika: "
                      "http://%s:%d)" % (ip, a["https_port"], ip,
                                         a["ca_port"]), flush=True)

    def dongu(self):
        while True:
            try:
                self.tara()
            except Exception as hata:  # tarama döngüsü ölmemeli
                print("Dinleme hatası:", hata, flush=True)
            time.sleep(self.TARAMA_ARALIGI)

    def baslat(self):
        self.yerel_baslat()
        threading.Thread(target=self.dongu, daemon=True).start()

    def servis(self):
        self._yerel.serve_forever()
