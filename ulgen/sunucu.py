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
import os
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import gizli, hava, obsidyen, saglik_veri, ses, ses_klip
from . import (__surum__, ayar, cihazlar, kodpenceresi, kota, kuyruk, ozelkasa,
               takvim, webauthn,
               tls, veritabani, yedek)
from .arayuz import BETIK, SAYFA

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
        "default-src 'self'; script-src 'self'; media-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'"),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "microphone=(self), geolocation=(self), publickey-credentials-get=(self), "
        "publickey-credentials-create=(self), camera=()"),
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
        pass
    # Face ID için: <ip-tireli>.sslip.io yalnız KENDİ dinlediğimiz adreslerden
    if ad.endswith(".sslip.io"):
        try:
            ip = ad[:-len(".sslip.io")].replace("-", ".")
            ipaddress.IPv4Address(ip)
        except ValueError:
            return False
        ayarli = ayar.yukle().get("dinleme_adresleri") or []
        return ip in (ayarli or zerotier_adresleri())
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


VARLIKLAR = {"/varlik/simge.png": ("simge.png", "image/png")}
for _ad in ("logo", "afis", "sahne", "zemin", "kure", "pusula"):
    VARLIKLAR["/varlik/%s.webp" % _ad] = (_ad + ".webp", "image/webp")


def _gorevler_json():
    satirlar = veritabani.sorgu(
        "SELECT id, tur, baslik, zaman, tekrar FROM gorev WHERE "
        "durum='acik' ORDER BY COALESCE(zaman,'9999'), id", (), True)
    return {"gorev": [x for x in satirlar if x["tur"] == "gorev"],
            "randevu": [x for x in satirlar if x["tur"] == "randevu"],
            "rutin": [x for x in satirlar if x["tur"] == "rutin"]}


def _donanim():
    """CPU/RAM/disk özeti (sır içermez); okunamayan alan atlanır."""
    sonuc = {}
    try:
        import os
        import shutil
        sonuc["cpu"] = min(100.0, os.getloadavg()[0] / (os.cpu_count() or 1)
                           * 100)
        d = shutil.disk_usage(os.path.expanduser("~"))
        sonuc["disk_toplam"] = round(d.total / 1e9)
        sonuc["disk_kullanilan"] = round((d.total - d.free) / 1e9)
    except (OSError, AttributeError):
        pass
    try:
        if sys.platform == "darwin":
            toplam = int(subprocess.run(["sysctl", "-n", "hw.memsize"],
                                        capture_output=True, text=True,
                                        timeout=3).stdout)
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True,
                                timeout=3).stdout
            sayfa = int(re.search(r"page size of (\d+)", vm).group(1))
            bos = sum(int(re.search(a + r":\s+(\d+)", vm).group(1))
                      for a in ("Pages free", "Pages inactive",
                                "Pages speculative"))
            kul = toplam - bos * sayfa
        else:
            bilgi = {}
            with open("/proc/meminfo") as f:
                for satir in f:
                    a, _, b = satir.partition(":")
                    bilgi[a] = int(b.split()[0]) * 1024
            toplam = bilgi["MemTotal"]
            kul = toplam - bilgi["MemAvailable"]
        sonuc["ram_toplam"] = round(toplam / 1e9, 1)
        sonuc["ram_kullanilan"] = round(kul / 1e9, 1)
    except (OSError, ValueError, AttributeError, KeyError, subprocess.SubprocessError):
        pass
    return sonuc


def _sistem_json(ulgen):
    """Yönetim paneli: salt okunur durum özeti (sır içermez)."""
    saglam, ayrinti = veritabani.butunluk_denetimi()
    son_yedek = yedek.otomatik_son_zaman()
    return {
        "surum": __surum__, "veritabani_surumu": veritabani.surum(),
        "butunluk": {"saglam": saglam, "ayrinti": ayrinti},
        "son_yedek": son_yedek or None,
        "cihazlar": [{"id": c["id"], "ad": c["ad"],
                      "son_kullanim": c["son_kullanim"],
                      "iptal": bool(c["iptal"])} for c in cihazlar.listele()],
        "veritabani_sifreli": veritabani.SIFRELI,
        "sqlcipher_kurulu": veritabani.sifreleme_var(),
        "yerel_yetki": bool(ayar.yukle().get("yerel_yetki", True)),
        "beyin": ulgen.yonlendirici.durum(),
        "kuyruk": len(kuyruk.bekleyenler()),
        "donanim": _donanim(),
        "kota": kota.tablo(),
        "gunluk": veritabani.sorgu(
            "SELECT zaman, seviye, kaynak, metin FROM gunluk "
            "ORDER BY id DESC LIMIT 15", (), True)}


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

        def _varlik(self, yol):
            ad, tur = VARLIKLAR[yol]
            with open(os.path.join(os.path.dirname(__file__), "varlik", ad),
                      "rb") as f:
                govde = f.read()
            self.send_response(200)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("X-Content-Type-Options", "nosniff")
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

        def _belirtec(self):
            baslik = self.headers.get("Authorization", "")
            if baslik.startswith("Bearer "):
                return baslik[7:]
            for parca in (self.headers.get("Cookie") or "").split(";"):
                ad, _, deger = parca.strip().partition("=")
                if ad == "ulgen_oturum":
                    return deger
            return ""

        def _yetkili(self):
            if self.server.yerel and not ayar.yukle().get("yerel_yetki", True):
                return True          # eski davranış (önerilmez; panelde uyarılır)
            ip = self.client_address[0]
            if limit.kilitli_mi(ip):
                self._cevap(429, {"hata": "çok fazla yanlış deneme"})
                return False
            if cihazlar.dogrula(self._belirtec()):
                limit.basarili(ip)
                return True
            limit.hata(ip)
            self._cevap(401, {"hata": "yetkisiz", "giris": self.server.yerel})
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
            if yol == "/varlik/uygulama.js":
                return self._cevap(200, BETIK,
                                   "text/javascript; charset=utf-8")
            if yol in VARLIKLAR:
                return self._varlik(yol)
            if yol == "/giris" and self.server.yerel:
                return self._giris(parse_qs(adres.query).get("t", [""])[0])
            if yol == "/takvim.ics":
                # Link tıklanınca başlık gönderilemez: kısa ömürlü TEK
                # KULLANIMLIK anahtar (cihaz belirteci değil) kabul edilir.
                if not takvim.anahtar_tuket(
                        parse_qs(adres.query).get("t", [""])[0]):
                    return self._cevap(403, {"hata": "bağlantı geçersiz ya da "
                                                     "kullanılmış"})
                veri = takvim.olustur().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type",
                                 "text/calendar; charset=utf-8")
                self.send_header("Content-Disposition",
                                 'attachment; filename="ulgen.ics"')
                self.send_header("Content-Length", str(len(veri)))
                for ad, deger in GUVENLIK_BASLIKLARI.items():
                    self.send_header(ad, deger)
                self.end_headers()
                self.wfile.write(veri)
                return
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
            if yol == "/gorevler":
                return self._cevap(200, _gorevler_json())
            if yol == "/bilgi/ara":
                q = parse_qs(adres.query).get("q", [""])[0][:200]
                ogeler = ulgen.hafiza.liste()
                if q:
                    ogeler = [o for o in ogeler
                              if q.lower() in o["metin"].lower()]
                return self._cevap(200, {
                    "hafiza": [{"id": o["id"], "metin": o["metin"][:300],
                                "kategori": o.get("kategori", "")}
                               for o in ogeler[-20:]],
                    "notlar": [{"baslik": b, "alinti": al[:400]}
                               for b, _, al in obsidyen.ara(q, 5)]
                    if q else [],
                    "dizin": obsidyen.durum()})
            if yol == "/projeler":
                return self._cevap(200, {
                    "hafiza": sorted(ulgen.hafiza.projeler()),
                    "kod": kodpenceresi.liste()})
            if yol == "/ayar/ozet":
                a = ayar.yukle()
                gizli_alan = ("anahtar", "token", "sifre")
                return self._cevap(200, {k: v for k, v in a.items()
                                         if not any(g in k for g in gizli_alan)})
            if yol == "/ses/klipler":
                return self._cevap(200, ses_klip.hazir_klipler())
            if yol == "/ses/cumleler":
                return self._cevap(200, [
                    {"ad": a, "metin": m, "var": os.path.isfile(
                        ses_klip.yol(a))}
                    for a, m in ses_klip.CUMLELER.items()])
            if yol.startswith("/ses/klip/"):
                ad = yol[len("/ses/klip/"):]
                try:
                    with open(ses_klip.yol(ad), "rb") as f:
                        ham = f.read()
                except (ses_klip.KlipHatasi, OSError):
                    return self._cevap(404, {"hata": "klip yok"})
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(ham)))
                self.send_header("Cache-Control", "private, max-age=3600")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(ham)
                return
            if yol == "/ses/durum":
                kul, _ = ses_klip.kullanilan()
                return self._cevap(200, {
                    "bulut": ses_klip.bulut_acik_mi(),
                    "bulut_kullanilan": kul,
                    "bulut_sinir": int(ayar.yukle().get(
                        "elevenlabs_aylik_sinir", 8000)),
                    "cevrimdisi": ses.CevrimdisiTanima.hazir_mi(),
                    "eksik": ses.CevrimdisiTanima.eksikler()})
            if yol == "/hava":
                q = parse_qs(adres.query)
                try:
                    enlem = float(q["enlem"][0]) if "enlem" in q else None
                    boylam = float(q["boylam"][0]) if "boylam" in q else None
                except ValueError:
                    return self._cevap(400, {"hata": "enlem/boylam sayı olmalı"})
                if (enlem is None) != (boylam is None) or (
                        enlem is not None and not (
                            -90 <= enlem <= 90 and -180 <= boylam <= 180)):
                    return self._cevap(400, {"hata": "koordinat geçersiz"})
                if enlem is not None:
                    hava.son_konum_yaz(enlem, boylam)
                return self._cevap(200, hava.getir(
                    enlem=enlem, boylam=boylam) or {})
            if yol == "/raporlar":
                return self._cevap(200, [
                    {"tur": r["tur"], "anahtar": r["anahtar"],
                     "metin": r["metin"]}
                    for r in ulgen.zamanlayici.rapor.son(10)])
            if yol == "/saglik/gecmis":
                return self._cevap(200, saglik_veri.gunluk())
            if yol == "/saglik/bugun":
                return self._cevap(200, saglik_veri.bugun())
            if yol == "/kasa/durum":
                return self._cevap(200, self._kasa_durum())
            if yol == "/sistem":
                return self._cevap(200, _sistem_json(ulgen))
            if yol == "/ilac/liste":
                return self._cevap(
                    200, ulgen.zamanlayici.ilac.liste_json())
            if yol == "/ilac/bugun":
                return self._cevap(
                    200, ulgen.zamanlayici.ilac.bugun_json())
            if yol == "/ozet":
                satirlar = veritabani.sorgu(
                    "SELECT id, zaman, mesaj FROM hatirlaticilar WHERE "
                    "onaylandi = 0 AND (bildirildi = 0 OR kalici = 1) "
                    "ORDER BY zaman LIMIT 15", (), True)
                return self._cevap(200, {"hatirlaticilar": satirlar})
            return self._cevap(404, {"hata": "bulunamadı"})

        def _yz_anahtar(self, yol, veri):
            """API anahtarını Anahtar Zinciri'ne yazar / bağlantıyı dener.

            YALNIZCA Mac'in kendi tarayıcısından (127.0.0.1). Anahtar yanıtta,
            günlükte ve veritabanında asla yer almaz."""
            if not self.server.yerel:
                return self._cevap(403, {"hata": "yalnız Mac'in kendi "
                                                 "tarayıcısından"})
            ad = veri.get("saglayici")
            if ad not in ayar.SIRLAR:
                return self._cevap(400, {"hata": "bilinmeyen sağlayıcı"})
            if yol == "/yz/anahtar" and ad == "elevenlabs" \
                    and veri.get("ses_kimligi"):
                kim = str(veri["ses_kimligi"]).strip()
                if not re.fullmatch(r"[A-Za-z0-9]{8,64}", kim):
                    return self._cevap(400, {"hata": "ses kimliği geçersiz"})
                try:
                    with open(ayar.AYAR_DOSYASI, "r", encoding="utf-8") as f:
                        mevcut = json.load(f)
                except (OSError, ValueError):
                    mevcut = {}
                mevcut["elevenlabs_ses_kimligi"] = kim
                with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
                    json.dump(mevcut, f, ensure_ascii=False, indent=2)
                os.chmod(ayar.AYAR_DOSYASI, 0o600)
                if not veri.get("anahtar"):
                    return self._cevap(200, {"tamam": True,
                                             "yer": "ayar.json (ses kimliği)"})
            if yol == "/yz/anahtar":
                anahtar = veri.get("anahtar")
                if (not isinstance(anahtar, str) or not 8 <= len(anahtar) <= 400
                        or re.search(r"\s", anahtar)
                        or not anahtar.isprintable()):
                    return self._cevap(400, {"hata": "anahtar geçersiz görünüyor"})
                yer = gizli.sir_yaz(ad, anahtar)
                veritabani.gunluge_yaz("bilgi", "anahtar", "%s anahtarı yazıldı" % ad)
                return self._cevap(200, {"tamam": True, "yer": yer})
            if ad == "elevenlabs":
                try:
                    return self._cevap(200, {
                        "calisti": True, "cikti": "ElevenLabs: " + ", ".join(
                            "%s %s" % (k, v) for k, v in
                            ses_klip.hepsini_uret().items())})
                except Exception as hata:      # ağ/anahtar: açık ileti
                    return self._cevap(200, {"calisti": False,
                                             "cikti": str(hata)[:200]})
            import io
            from contextlib import redirect_stdout
            from . import tani
            ara = io.StringIO()
            with redirect_stdout(ara):
                kod = tani.dene([ad])
            return self._cevap(200, {"calisti": kod == 0, "cikti": ara.getvalue()})

        def _klip_yukle(self, tur):
            """Kendi mp3'ünüzü sabit cümleye koyar (POST ham mp3, ≤ 4 MB)."""
            ad = urlparse(self.path).path[len("/ses/klip/"):]
            try:
                uzunluk = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                uzunluk = 0
            if ad not in ses_klip.CUMLELER:
                self._cevap(404, {"hata": "bilinmeyen cümle"})
                return
            if uzunluk <= 0 or uzunluk > ses_klip.AZAMI_BAYT:
                self._cevap(413, {"hata": "dosya boş ya da 4 MB'tan büyük"})
                return
            if not tur.startswith(("audio/", "application/octet-stream")):
                self._cevap(415, {"hata": "mp3 dosyası gerekli"})
                return
            govde = self.rfile.read(uzunluk)
            if not self._yetkili():
                return
            try:
                ses_klip.yukle(ad, govde)
            except ses_klip.KlipHatasi as hata:
                self._cevap(400, {"hata": str(hata)})
                return
            self._cevap(200, {"tamam": True})

        def _ses_yaz(self, tur):
            """Ham ses → metin (yerel, internetsiz). Gövde ≤ 8 MB."""
            try:
                uzunluk = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                uzunluk = 0
            if uzunluk <= 0 or uzunluk > ses.CevrimdisiTanima.AZAMI_BAYT:
                self._cevap(413, {"hata": "ses boş ya da 8 MB'tan büyük"})
                return
            if not tur.startswith(("audio/", "video/webm",
                                   "application/octet-stream")):
                self._cevap(415, {"hata": "ses dosyası gerekli"})
                return
            govde = self.rfile.read(uzunluk)
            if not self._yetkili():
                return
            try:
                self._cevap(200, {"metin": ses.CevrimdisiTanima.yaz(govde)})
            except RuntimeError as hata:
                self._cevap(503, {"hata": str(hata)})
            except (ValueError, OSError, subprocess.SubprocessError) as hata:
                self._cevap(400, {"hata": str(hata)[:200]})

        def do_POST(self):
            if not self._on_denetim():
                return
            tur = (self.headers.get("Content-Type") or "").lower()
            if urlparse(self.path).path == "/ses/yaz":
                return self._ses_yaz(tur)
            if urlparse(self.path).path.startswith("/ses/klip/"):
                return self._klip_yukle(tur)
            if not tur.startswith("application/json"):
                return self._cevap(415, {"hata": "application/json gerekli"})
            veri = self._govde()    # önce gövde okunur (bağlantı sıfırlanmasın)
            if not self._yetkili():
                return
            if urlparse(self.path).path == "/sohbet":
                return self._cevap(
                    200, ulgen.sohbet_isle(str(veri.get("metin", ""))))
            if urlparse(self.path).path == "/takvim/baglanti":
                return self._cevap(200, {
                    "adres": "/takvim.ics?t=" + takvim.anahtar_uret(),
                    "omur_sn": takvim.OMUR_SN})
            if urlparse(self.path).path == "/ses/oku":
                try:
                    ham = ses_klip.metni_oku(str(veri.get("metin", "")))
                except ses_klip.KlipHatasi as hata:
                    return self._cevap(409, {"hata": str(hata)})
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(ham)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(ham)
                return
            if urlparse(self.path).path == "/ses/bulut-ayar":
                if not self.server.yerel:
                    return self._cevap(403, {"hata": "yalnız Mac'in kendi "
                                                     "tarayıcısından"})
                acik = veri.get("acik")
                if not isinstance(acik, bool):
                    return self._cevap(400, {"hata": "acik(bool) gerekli"})
                try:
                    with open(ayar.AYAR_DOSYASI, "r", encoding="utf-8") as f:
                        mevcut = json.load(f)
                except (OSError, ValueError):
                    mevcut = {}
                mevcut["elevenlabs_bulut_ses"] = acik
                with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
                    json.dump(mevcut, f, ensure_ascii=False, indent=2)
                os.chmod(ayar.AYAR_DOSYASI, 0o600)
                return self._cevap(200, {"acik": acik})
            if urlparse(self.path).path == "/ses/klip-sil":
                ad = veri.get("ad")
                if ad not in ses_klip.CUMLELER:
                    return self._cevap(400, {"hata": "bilinmeyen cümle"})
                return self._cevap(200, {"silindi": ses_klip.sil(ad)})
            if urlparse(self.path).path == "/ilac/duzenle":
                kimlik = veri.get("id")
                if (not isinstance(kimlik, int) or isinstance(kimlik, bool)
                        or not isinstance(veri.get("ad"), str)
                        or not isinstance(veri.get("saatler"), str)):
                    return self._cevap(400, {"hata": "id, ad, saatler gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici.ilac
                                         .duzenle(kimlik, veri["ad"],
                                                  veri.get("doz_notu", ""),
                                                  veri["saatler"])})
            if urlparse(self.path).path == "/ilac/sil":
                kimlik = veri.get("id")
                if not isinstance(kimlik, int) or isinstance(kimlik, bool) \
                        or veri.get("onay") is not True:
                    return self._cevap(400, {"hata": "id(int) ve onay gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici.ilac
                                         .sil(kimlik)})
            if urlparse(self.path).path == "/ilac/duzelt":
                doz, yanit = veri.get("doz"), veri.get("yanit")
                if not isinstance(doz, int) or isinstance(doz, bool) \
                        or not isinstance(yanit, str):
                    return self._cevap(400, {"hata": "doz(int), yanit"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici.ilac
                                         .duzelt(doz, yanit)})
            if urlparse(self.path).path == "/gorev/duzenle":
                kimlik = veri.get("id")
                if (not isinstance(kimlik, int) or isinstance(kimlik, bool)
                        or not isinstance(veri.get("baslik"), str)):
                    return self._cevap(400, {"hata": "id, baslik gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici.gorev
                                         .duzenle(kimlik, veri["baslik"],
                                                  str(veri.get("zaman", "")),
                                                  str(veri.get("tekrar", "")))})
            if urlparse(self.path).path == "/hatirlatici/duzenle":
                kimlik = veri.get("id")
                if (not isinstance(kimlik, int) or isinstance(kimlik, bool)
                        or not isinstance(veri.get("mesaj"), str)
                        or not isinstance(veri.get("zaman"), str)):
                    return self._cevap(400, {"hata": "id, mesaj, zaman gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici
                                         .hatirlatici_duzenle(
                                             kimlik, veri["mesaj"],
                                             veri["zaman"])})
            if urlparse(self.path).path == "/hatirlatici/sil":
                kimlik = veri.get("id")
                if not isinstance(kimlik, int) or isinstance(kimlik, bool) \
                        or veri.get("onay") is not True:
                    return self._cevap(400, {"hata": "id(int) ve onay gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici
                                         .hatirlatici_sil(kimlik)})
            if urlparse(self.path).path == "/gorev/sil":
                kimlik = veri.get("id")
                if not isinstance(kimlik, int) or isinstance(kimlik, bool) \
                        or veri.get("onay") is not True:
                    return self._cevap(400, {"hata": "id(int) ve onay gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici.gorev
                                         .sil(kimlik)})
            if urlparse(self.path).path == "/yz/mod":
                if not self.server.yerel:
                    return self._cevap(403, {"hata": "yalnız Mac'in kendi "
                                                     "tarayıcısından"})
                if veri.get("mod") not in ("yerel", "otomatik", "bulut"):
                    return self._cevap(400, {"hata": "mod: yerel|otomatik|bulut"})
                if veri["mod"] != "yerel" and veri.get("onay") is not True:
                    return self._cevap(400, {"hata": "bulut kipi için onay gerekli"})
                ayar.guncelle("beyin", veri["mod"])
                ayar.guncelle("beyin_sabit", True)
                ulgen.yonlendirici.sifirla()
                veritabani.gunluge_yaz("bilgi", "ayar", "beyin kipi: %s"
                                       % veri["mod"])
                return self._cevap(200, {"mod": veri["mod"]})
            if urlparse(self.path).path == "/gorev/bitir":
                kimlik = veri.get("id")
                if not isinstance(kimlik, int) or isinstance(kimlik, bool):
                    return self._cevap(400, {"hata": "id(int) gerekli"})
                return self._cevap(200, {"yanit": ulgen.zamanlayici.gorev
                                         .bitir(kimlik)})
            if urlparse(self.path).path == "/ilac/yanit":
                return self._doz_yanit(veri)
            if urlparse(self.path).path in ("/yz/anahtar", "/yz/dene"):
                return self._yz_anahtar(urlparse(self.path).path, veri)
            if urlparse(self.path).path == "/saglik/veri":
                try:
                    e, a = saglik_veri.ekle(veri.get("olcumler"))
                except saglik_veri.SaglikHatasi as hata:
                    return self._cevap(400, {"hata": str(hata)})
                return self._cevap(200, {"eklenen": e, "atlanan": a})
            if urlparse(self.path).path.startswith("/kasa/"):
                return self._kasa(urlparse(self.path).path, veri)
            if urlparse(self.path).path.startswith("/kod/"):
                return self._kod(urlparse(self.path).path, veri)
            return self._cevap(404, {"hata": "bulunamadı"})

        # ------------------------------------------------------ Özel Kasa
        def _rp(self):
            host = (self.headers.get("Host") or "").lower()
            ad = _host_adi(host)
            sema = "https" if isinstance(self.connection, ssl.SSLSocket) \
                else "http"
            return ad, sema + "://" + host

        def _kasa_durum(self):
            ad, _ = self._rp()
            return {"kurulu": ozelkasa.kurulu_mu(),
                    "passkey": ozelkasa.passkey_sayisi(),
                    "adlar": ozelkasa.adlar() if ozelkasa.kurulu_mu() else [],
                    "istekler": ozelkasa.bekleyen_istekler(),
                    "rp": ad, "rp_onerisi": ozelkasa.rp_onerisi(ad)}

        def _acma(self, veri, kapsam):
            """Gövdeden açma yöntemini çıkarır; Face ID ise imzayı doğrular."""
            yontem = veri.get("yontem")
            if yontem == "parola":
                return {"parola": str(veri.get("parola", ""))}
            if yontem == "kod":
                return {"kod": str(veri.get("kod", ""))}
            if yontem == "passkey":
                ad, origin = self._rp()
                cred = ozelkasa.passkey_dogrula(
                    str(veri.get("kimlik", "")), veri.get("veri") or {},
                    ad, origin, kapsam)
                try:
                    prf = webauthn.b64coz(str(veri.get("prf", "")))
                except ValueError:
                    prf = b""
                return {"prf": prf, "cred": cred} if len(prf) == 32 else \
                    {"yalniz_dogrulama": True, "cred": cred}
            raise ozelkasa.KasaHatasi("açma yöntemi: parola | passkey | kod")

        def _kasa(self, yol, veri):
            try:
                return self._kasa_isle(yol, veri)
            except ozelkasa.KasaHatasi as hata:
                return self._cevap(400, {"hata": str(hata)})
            except webauthn.Hata as hata:
                return self._cevap(400, {"hata": str(hata)})

        def _kasa_isle(self, yol, veri):
            ad = str(veri.get("ad", ""))
            if yol == "/kasa/kur":
                return self._cevap(200, {"kurtarma_kodu": ozelkasa.kur(
                    str(veri.get("parola", "")))})
            if not ozelkasa.kurulu_mu():
                return self._cevap(400, {"hata": "Özel Kasa kurulu değil"})
            if yol == "/kasa/passkey/kayit-baslat":
                return self._cevap(200, ozelkasa.kayit_baslat())
            if yol == "/kasa/passkey/kayit-bitir":
                ho, origin = self._rp()
                return self._cevap(200, {"cred": ozelkasa.kayit_bitir(
                    str(veri.get("kimlik", "")), veri.get("veri") or {},
                    ho, origin, str(veri.get("ad", "iPhone"))[:40])})
            if yol == "/kasa/passkey/bagla":
                prf = webauthn.b64coz(str(veri.get("prf", "")))
                if len(prf) != 32:
                    return self._cevap(400, {"hata": "PRF çıktısı yok"})
                ozelkasa.prf_bagla(str(veri.get("cred", "")), prf,
                                   {"parola": str(veri.get("parola", ""))})
                return self._cevap(200, {"yanit": "Face ID kasaya bağlandı."})
            if yol == "/kasa/passkey/giris-baslat":
                kapsam = str(veri.get("kapsam", ""))
                if not re.fullmatch(r"(oku|sil|ekle):.{1,80}|parola-sifirla|"
                                    r"yedek-al", kapsam):
                    return self._cevap(400, {"hata": "kapsam geçersiz"})
                return self._cevap(200, ozelkasa.giris_baslat(kapsam))
            if yol == "/kasa/oku":
                istek = veri.get("istek")
                acma = self._acma(veri, "oku:" + ad)
                if istek is not None:
                    if not isinstance(istek, int) or isinstance(istek, bool) \
                            or not ozelkasa.istek_tuket(istek, ad):
                        return self._cevap(400, {"hata": "istek geçersiz, "
                                                 "süresi dolmuş ya da "
                                                 "kullanılmış"})
                if "yalniz_dogrulama" in acma:
                    return self._cevap(400, {"hata": "PRF yok; parolayla açın"})
                return self._cevap(200, {"ad": ad, "icerik": ozelkasa
                                         .oge_oku(ad, acma)})
            if yol == "/kasa/ekle":
                acma = self._acma(veri, "ekle:" + ad)
                ozelkasa.oge_ekle(ad, str(veri.get("icerik", "")), acma)
                return self._cevap(200, {"yanit": "Kasaya eklendi."})
            if yol == "/kasa/sil":
                acma = self._acma(veri, "sil:" + ad)
                return self._cevap(200, {"silinen": ozelkasa.oge_sil(ad,
                                                                     acma)})
            if yol == "/kasa/parola-sifirla":
                acma = self._acma(veri, "parola-sifirla")
                ozelkasa.parola_degistir(acma, str(veri.get("yeni", "")))
                return self._cevap(200, {"yanit": "Yeni parola kuruldu."})
            if yol == "/kasa/yedek":
                # Face ID ile: parolayı unuttuysanız YENİ parolayla taze yedek
                self._acma({"yontem": "passkey", **veri}, "yedek-al")
                from . import yedek
                import os
                hedef = os.path.join(ayar.KLASOR, "yedekler", "faceid-%d.ulgenyedek"
                                     % int(time.time()))
                os.makedirs(os.path.dirname(hedef), exist_ok=True)
                return self._cevap(200, {"dosya": yedek.al(
                    hedef, str(veri.get("yeni", "")))})
            return self._cevap(404, {"hata": "bulunamadı"})

        def _giris(self, anahtar):
            """Tek kullanımlık anahtarı oturum çerezine çevirir (yalnızca
            127.0.0.1). Çerez: HttpOnly, SameSite=Strict, 30 gün."""
            ip = self.client_address[0]
            if limit.kilitli_mi(ip):
                return self._cevap(429, {"hata": "çok fazla yanlış deneme"})
            belirtec = cihazlar.giris_anahtari_tuket(anahtar)
            if not belirtec:
                limit.hata(ip)
                return self._cevap(403, {"hata": "giriş bağlantısı geçersiz "
                                                 "ya da kullanılmış; "
                                                 "Launchpad'den Ülgen'i açın"})
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie", "ulgen_oturum=%s; Path=/; HttpOnly; "
                "SameSite=Strict; Max-Age=%d"
                % (belirtec, cihazlar.OTURUM_GUN * 86400))
            self.send_header("Content-Length", "0")
            for ad, deger in GUVENLIK_BASLIKLARI.items():
                self.send_header(ad, deger)
            self.end_headers()

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
