"""Cihaz tanı raporu: gerçek Mac'te neyin çalıştığını ölçer.

Linux/Chromium testleri Mac'e özgü parçaları (Anahtar Zinciri, launchd,
ZeroTier arayüzü, Launchpad) kanıtlamaz. ``python -m ulgen --tani`` bunları
Mac'te denetler ve sır içermeyen bir rapor yazar; raporu paylaşabilirsiniz.
iPhone'a özgü adımlar (sertifika, bildirim, Takvim alarmı) elle denenir; rapor
sonunda kontrol listesi verilir.
"""

import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta

from . import ayar, gizli, sunucu, tls, veritabani

MAC = sys.platform == "darwin"


def _satir(sonuc, ad, ayrinti=""):
    isaret = {"TAMAM": "[TAMAM] ", "UYARI": "[UYARI] ", "HATA": "[HATA]  ",
              "ATLA": "[ATLA]  "}[sonuc]
    print(isaret + ad + ((" — " + ayrinti) if ayrinti else ""))
    return sonuc


def _calistir(komut, sure=8):
    try:
        s = subprocess.run(komut, capture_output=True, text=True, timeout=sure)
        return s.returncode, (s.stdout + s.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as hata:
        return 1, str(hata)


def _kapi_acik(adres, kapi, sure=2):
    try:
        with socket.create_connection((adres, kapi), timeout=sure):
            return True
    except OSError:
        return False


def calistir():
    sonuclar = []
    ekle = sonuclar.append
    print("ÜLGEN TANI RAPORU — %s" % datetime.now().strftime("%d.%m.%Y %H:%M"))
    print("(sır ve anahtar içermez)\n")

    # ---- sistem
    ekle(_satir("TAMAM", "Sistem", "%s %s, %s, Python %s" % (
        platform.system(), platform.mac_ver()[0] or platform.release(),
        platform.machine(), platform.python_version())))
    if not MAC:
        ekle(_satir("UYARI", "Bu bir Mac değil",
                    "Mac'e özgü denetimler atlanacak"))
    if sys.version_info < (3, 8):
        ekle(_satir("HATA", "Python çok eski", "3.8+ gerekir"))

    # ---- kütüphaneler
    for modul, zorunlu in (("cryptography", True), ("requests", True),
                           ("bs4", True), ("pypdf", True), ("ddgs", False),
                           ("sqlcipher3", False)):
        try:
            __import__(modul)
            ekle(_satir("TAMAM", "Kütüphane " + modul))
        except ImportError:
            ekle(_satir("HATA" if zorunlu else "UYARI", "Kütüphane " + modul
                        + " yok",
                        "pip install sqlcipher3-wheels" if modul ==
                        "sqlcipher3" else ""))

    # ---- veri klasörü, izinler
    ayar.klasor_hazirla()
    mod = oct(os.stat(ayar.KLASOR).st_mode & 0o777)
    ekle(_satir("TAMAM" if mod == "0o700" else "UYARI",
                "Veri klasörü izni " + mod, "0o700 olmalı"))
    for yol in (ayar.VERI_TABANI, ayar.AYAR_DOSYASI, ayar.ANAHTAR_DOSYASI,
                os.path.join(ayar.KLASOR, "bellek.anahtar")):
        if os.path.exists(yol):
            m = oct(os.stat(yol).st_mode & 0o777)
            ekle(_satir("TAMAM" if m == "0o600" else "UYARI",
                        "%s izni %s" % (os.path.basename(yol), m)))

    # ---- anahtar yeri
    zincirde = bool(gizli._zincirden_oku(gizli.HIZMET)) if MAC else False
    if MAC:
        ekle(_satir("TAMAM" if zincirde else "UYARI", "Ana anahtar",
                    "Anahtar Zinciri'nde" if zincirde else
                    "Anahtar Zinciri'nde DEĞİL (dosyada); zincire yazılamamış"))
    else:
        ekle(_satir("ATLA", "Anahtar Zinciri", "Mac değil"))

    # ---- veritabanı
    try:
        veritabani.kur()
        saglam, ayr = veritabani.butunluk_denetimi()
        ekle(_satir("TAMAM" if veritabani.SIFRELI else "HATA",
                    "Veritabanı diskte " + ("ŞİFRELİ (SQLCipher)"
                                            if veritabani.SIFRELI
                                            else "ŞİFRESİZ"),
                    "" if veritabani.SIFRELI else
                    "pip install sqlcipher3-wheels, sonra yeniden başlatın"))
        ekle(_satir("TAMAM" if saglam else "HATA", "Veritabanı bütünlüğü",
                    "sürüm %d" % veritabani.surum() if saglam else ayr))
    except Exception as hata:
        ekle(_satir("HATA", "Veritabanı açılamadı", str(hata)[:120]))

    # ---- sunucu, yetki
    ekle(_satir("TAMAM" if _kapi_acik("127.0.0.1", ayar.PORT) else "HATA",
                "Yerel sunucu 127.0.0.1:%d" % ayar.PORT,
                "çalışmıyorsa: launchctl load ~/Library/LaunchAgents/"
                "com.ulgen.sunucu.plist"))
    yetki = ayar.yukle().get("yerel_yetki", True)
    ekle(_satir("TAMAM" if yetki else "UYARI", "Yerel erişim yetkisi",
                "açık (çerez/belirteç ister)" if yetki else
                "KAPALI: aynı Mac'teki her süreç erişebilir"))

    # ---- launchd, Launchpad
    if MAC:
        kod, cikti = _calistir(["launchctl", "list"])
        ekle(_satir("TAMAM" if "com.ulgen.sunucu" in cikti else "HATA",
                    "launchd görevi com.ulgen.sunucu"))
        ajan = os.path.expanduser(
            "~/Library/LaunchAgents/com.ulgen.sunucu.plist")
        ekle(_satir("TAMAM" if os.path.exists(ajan) else "HATA",
                    "LaunchAgent dosyası"))
        uyg = [y for y in ("/Applications/Ülgen.app",
                           os.path.expanduser("~/Applications/Ülgen.app"))
               if os.path.exists(y)]
        ekle(_satir("TAMAM" if uyg else "UYARI", "Launchpad uygulaması",
                    uyg[0] if uyg else "bulunamadı"))
        ekle(_satir("UYARI", "Mac açılışta kendiliğinden başlar mı?",
                    "LaunchAgent oturum AÇILINCA başlar; şifre ekranında "
                    "değil. Otomatik oturum açma gerekebilir"))
    else:
        ekle(_satir("ATLA", "launchd / Launchpad", "Mac değil"))

    # ---- ZeroTier ve HTTPS
    zt = sunucu.zerotier_adresleri()
    if zt:
        ekle(_satir("TAMAM", "ZeroTier adresleri", ", ".join(zt)))
        for a in zt:
            ekle(_satir("TAMAM" if _kapi_acik(a, ayar.yukle()["https_port"])
                        else "UYARI", "HTTPS %s:%d" % (
                            a, ayar.yukle()["https_port"]),
                        "açık değilse günlüğe bakın"))
    else:
        ekle(_satir("UYARI" if MAC else "ATLA", "ZeroTier adresi bulunamadı",
                    "ZeroTier açık mı? 'ifconfig | grep zt' denetleyin; "
                    "ya da ayar.json 'dinleme_adresleri'"))
    try:
        y = tls.yollar()
        if os.path.exists(y.get("ca", "")):
            ekle(_satir("TAMAM", "Yerel CA sertifikası var"))
        else:
            ekle(_satir("UYARI", "Yerel CA henüz üretilmemiş",
                        "ZeroTier adresi bulununca üretilir"))
    except Exception as hata:
        ekle(_satir("UYARI", "TLS denetimi", str(hata)[:80]))

    # ---- beyin ve anahtarlar
    a = ayar.yukle()
    anahtarlar = [ad for ad, alan in ayar.SIRLAR.items() if a.get(alan)]
    ekle(_satir("TAMAM" if anahtarlar else "UYARI", "Bulut anahtarları",
                ", ".join(anahtarlar) or "hiçbiri kayıtlı"))
    for ad, adres in (("Ollama", a["ollama_adres"]),
                      ("llama.cpp", a["llamacpp_adres"])):
        host = adres.split("//")[-1]
        ana, _, kapi = host.partition(":")
        ok = _kapi_acik(ana, int(kapi.split("/")[0] or 80))
        ekle(_satir("TAMAM" if ok else "UYARI", "Yerel beyin " + ad,
                    "ulaşılabilir" if ok else "kapalı/yok"))

    # ---- özet ve elle denenecekler
    hata = sonuclar.count("HATA")
    uyari = sonuclar.count("UYARI")
    print("\nÖZET: %d hata, %d uyarı, %d tamam" % (
        hata, uyari, sonuclar.count("TAMAM")))
    print("""
iPHONE'DA ELLE DENENECEKLER (bu rapor bunları ölçemez)
  [ ] Safari http://<ZeroTier adresi>:8766 > sertifika indirilip yüklendi
  [ ] Ayarlar > Genel > Hakkında > Sertifika Güven Ayarları > Ülgen Yerel CA AÇIK
  [ ] https://<ZeroTier adresi>:8443 açıldı, belirteç girildi, sohbet çalışıyor
  [ ] Ana Ekrana Ekle ile uygulama olarak açıldı
  [ ] Mikrofon izni (HTTPS üzerinde) verildi
  [ ] python -m ulgen --takvim-deneme dosyası iPhone'a aktarıldı: 3 dk sonra
      alarm kilit ekranında çaldı mı? Sessiz/Odak kipinde ne oldu?
  [ ] İlaç sekmesinden 'iPhone takvimine aktar' denendi
  [ ] Mac uyurken takvim alarmı çaldı mı?
Sonuçları yazın; "gerçek cihazda doğrulandı" ancak o zaman denir.""")
    return 1 if hata else 0


def takvim_deneme():
    """3 dakika sonrası için tek alarmlı deneme takvimi yazar."""
    from . import takvim
    t = datetime.now() + timedelta(minutes=3)
    satirlar = ["BEGIN:VCALENDAR", "VERSION:2.0",
                "PRODID:-//Ulgen//Deneme//TR", "X-WR-CALNAME:Ülgen deneme"]
    satirlar += takvim._olay("deneme-%d@ulgen" % int(time.time()),
                             "Ülgen: alarm denemesi", t, 5, "", (0,))
    satirlar.append("END:VCALENDAR")
    yol = os.path.join(ayar.KLASOR, "ulgen-deneme.ics")
    with open(yol, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(takvim._katla(s) for s in satirlar) + "\r\n")
    os.chmod(yol, 0o600)
    print("Deneme dosyası: %s\nOlay saati: %s (alarm tam o anda)\n"
          "iPhone'a AirDrop ile gönderin, açıp 'Tümünü Ekle' deyin; Mac'i "
          "kapatıp alarmı bekleyin." % (yol, t.strftime("%H:%M")))
    return 0
