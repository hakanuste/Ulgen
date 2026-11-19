"""Kendi sesinizle Piper modeli eğitmek için ses kaydı veri seti.

Kayıtlar ~/ÜlgenVeri/ses_kaydi/ altında Piper'ın beklediği biçimde
tutulur:  wavs/0001.wav ...  ve  metadata.csv  ("0001.wav|cümle").
Tarayıcı sesi 22050 Hz, tek kanal, 16 bit WAV olarak gönderir (dönüştürme
gerekmez). "Paket" bu klasörü tek bir zip yapar; Google Colab'daki eğitim
defteri (docs/piper_egitim.ipynb) bu zip'i kullanır.
"""

import io
import os
import re
import threading
import wave
import zipfile

from . import ayar
from .ses_cumleleri import CUMLELER

AZAMI_BAYT = 6 * 1024 * 1024        # ~2 dk WAV
HEDEF_DAKIKA = 45
_KILIT = threading.Lock()


class KayitHatasi(Exception):
    pass


def klasor():
    yol = os.path.join(ayar.KLASOR, "ses_kaydi")
    os.makedirs(os.path.join(yol, "wavs"), exist_ok=True)
    return yol


def _metadata_yolu():
    return os.path.join(klasor(), "metadata.csv")


def _atlanan_yolu():
    return os.path.join(klasor(), "atlanan.txt")


def kayitlar():
    """[(dosya, cümle)] metadata.csv'deki sırayla."""
    try:
        with open(_metadata_yolu(), encoding="utf-8") as f:
            return [tuple(s.rstrip("\n").split("|", 1)) for s in f if "|" in s]
    except OSError:
        return []


def _atlananlar():
    try:
        with open(_atlanan_yolu(), encoding="utf-8") as f:
            return set(s.strip() for s in f if s.strip())
    except OSError:
        return set()


def kitap_cumleleri(azami=3000):
    """Kasadaki kılavuz/kitap notlarından okumaya uygun cümleler (yedek)."""
    from . import obsidyen
    kasa = obsidyen.kasa_yolu() if obsidyen.hazir_mi() else ""
    sonuc = []
    if not kasa or not os.path.isdir(kasa):
        return sonuc
    for kok, _, dosyalar in os.walk(kasa):
        for ad in sorted(dosyalar):
            if not ad.endswith(".md") or "Bölüm" not in ad:
                continue
            try:
                with open(os.path.join(kok, ad), encoding="utf-8") as f:
                    metin = f.read()
            except OSError:
                continue
            for c in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", metin)):
                if uygun_mu(c):
                    sonuc.append(c.strip())
                    if len(sonuc) >= azami:
                        return sonuc
    return sonuc


def uygun_mu(cumle):
    """Okunabilir cümle mi: 30-160 harf, yalnız Türkçe harf ve noktalama,
    sayı ve büyük harf yığını (OCR artığı) yok, kişisel veri yok."""
    from . import guvenlik
    c = cumle.strip()
    if not 30 <= len(c) <= 160 or not c[-1] in ".!?":
        return False
    if re.search(r"[^A-Za-zÇĞİÖŞÜçğıöşüâîû0-9 ,.;:!?'\"()-]", c):
        return False
    if re.search(r"\d", c) or re.search(r"[A-ZÇĞİÖŞÜ]{4,}", c):
        return False
    if len(re.findall(r"\b\w\b", c)) > 2:            # tek harfli parçalar: OCR
        return False
    return not guvenlik.duyarli_mi(c)


def siradaki():
    """Okunacak sonraki cümle ve ilerleme."""
    okunan = {m for _, m in kayitlar()} | _atlananlar()
    cumle = next((c for c in CUMLELER if c not in okunan), None)
    kaynak = "hazır"
    if cumle is None:
        cumle = next((c for c in kitap_cumleleri() if c not in okunan), None)
        kaynak = "kitap"
    return dict(ilerleme(), metin=cumle, kaynak=kaynak)


def ilerleme():
    toplam = 0.0
    liste = kayitlar()
    for dosya, _ in liste:
        try:
            with wave.open(os.path.join(klasor(), "wavs", dosya)) as w:
                toplam += w.getnframes() / float(w.getframerate())
        except (OSError, wave.Error, EOFError):
            pass
    return {"adet": len(liste), "dakika": round(toplam / 60.0, 1),
            "hedef_dakika": HEDEF_DAKIKA}


def wav_denetle(ham):
    """WAV mı, tek kanal, 16 bit, 16-48 kHz, 1-30 saniye mi?"""
    try:
        with wave.open(io.BytesIO(ham)) as w:
            kanal, genislik, hiz, kare = (w.getnchannels(), w.getsampwidth(),
                                          w.getframerate(), w.getnframes())
    except (wave.Error, EOFError) as hata:
        raise KayitHatasi("Ses WAV değil: %s" % hata)
    if kanal != 1 or genislik != 2 or not 16000 <= hiz <= 48000:
        raise KayitHatasi("Ses tek kanal, 16 bit olmalı.")
    sure = kare / float(hiz)
    if not 1.0 <= sure <= 30.0:
        raise KayitHatasi("Kayıt 1 ile 30 saniye arasında olmalı (%.1f sn)." % sure)
    return sure


def kaydet(cumle, ham):
    """Cümlenin kaydını ekler; dosya adını döndürür."""
    cumle = re.sub(r"\s+", " ", str(cumle or "")).strip()
    if not cumle or "|" in cumle or len(cumle) > 300:
        raise KayitHatasi("Cümle geçersiz.")
    if len(ham) > AZAMI_BAYT:
        raise KayitHatasi("Kayıt çok büyük.")
    wav_denetle(ham)
    with _KILIT:
        liste = kayitlar()
        if any(m == cumle for _, m in liste):
            raise KayitHatasi("Bu cümle zaten kaydedilmiş.")
        no = max([int(d[:-4]) for d, _ in liste if d[:-4].isdigit()] or [0]) + 1
        dosya = "%04d.wav" % no
        with open(os.path.join(klasor(), "wavs", dosya), "wb") as f:
            f.write(ham)
        with open(_metadata_yolu(), "a", encoding="utf-8") as f:
            f.write("%s|%s\n" % (dosya, cumle))
    return dosya


def atla(cumle):
    with _KILIT, open(_atlanan_yolu(), "a", encoding="utf-8") as f:
        f.write(re.sub(r"\s+", " ", str(cumle or "")).strip() + "\n")


def son_kaydi_sil():
    """Son kaydı geri alır (yanlış okunduysa)."""
    with _KILIT:
        liste = kayitlar()
        if not liste:
            return None
        dosya, cumle = liste[-1]
        try:
            os.remove(os.path.join(klasor(), "wavs", dosya))
        except OSError:
            pass
        with open(_metadata_yolu(), "w", encoding="utf-8") as f:
            f.writelines("%s|%s\n" % x for x in liste[:-1])
        return cumle


def paketle():
    """metadata.csv + wavs/ -> ses_veri.zip (Colab'a yüklenecek)."""
    liste = kayitlar()
    if not liste:
        raise KayitHatasi("Henüz kayıt yok.")
    yol = os.path.join(klasor(), "ses_veri.zip")
    gecici = yol + ".tmp"
    with zipfile.ZipFile(gecici, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(_metadata_yolu(), "metadata.csv")
        for dosya, _ in liste:
            tam = os.path.join(klasor(), "wavs", dosya)
            if os.path.exists(tam):
                z.write(tam, "wavs/" + dosya)
    os.replace(gecici, yol)
    return yol
