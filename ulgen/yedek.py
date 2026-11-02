"""Şifreli yedek alma ve geri yükleme (parola + scrypt + AES-256-GCM).

Yedek tek dosyadır; içinde veritabanı (tutarlı anlık kopya), hafıza (düz
JSON, yedek dosyası şifreli olduğu için) ve ayar.json (API anahtarları
HARİÇ) bulunur. Parola bilinmeden açılamaz; parolayı unutursanız yedek
kurtarılamaz. Geri yükleme mevcut dosyaları SİLMEZ, "yedekler/onceki-..."
klasörüne taşır.
"""

import io
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
from datetime import datetime

from . import ayar, gizli

BASLIK = b"ULGENYEDEK1"
ISIM_VERI = "veri.db"
ISIM_HAFIZA = "memory.json"
ISIM_AYAR = "ayar.json"
IZINLI = (ISIM_VERI, ISIM_HAFIZA, ISIM_AYAR)
AZAMI_BOYUT = 2_000_000_000


class YedekHatasi(Exception):
    pass


def _anahtar(parola, tuz):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    if len(parola) < 8:
        raise YedekHatasi("Parola en az 8 karakter olmalı.")
    return Scrypt(salt=tuz, length=32, n=2 ** 15, r=8, p=1).derive(
        parola.encode("utf-8"))


def _tutarli_veritabani(hedef):
    kaynak = sqlite3.connect(ayar.VERI_TABANI)
    try:
        yedek = sqlite3.connect(hedef)
        try:
            kaynak.backup(yedek)
        finally:
            yedek.close()
    finally:
        kaynak.close()


def al(hedef, parola):
    """Şifreli yedeği ``hedef`` dosyasına yazar; dosya yolunu döndürür."""
    gecici = tempfile.mkdtemp()
    try:
        if os.path.exists(ayar.VERI_TABANI):
            _tutarli_veritabani(os.path.join(gecici, ISIM_VERI))
        if os.path.exists(ayar.HAFIZA_DOSYASI):
            with open(ayar.HAFIZA_DOSYASI, "rb") as f:
                ham = gizli.coz(f.read())
            with open(os.path.join(gecici, ISIM_HAFIZA), "wb") as f:
                f.write(ham)
        a = ayar.yukle()
        for alan in ayar.SIRLAR.values():
            a.pop(alan, None)
        with open(os.path.join(gecici, ISIM_AYAR), "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False, indent=2)
        tampon = io.BytesIO()
        with tarfile.open(fileobj=tampon, mode="w:gz") as arsiv:
            for ad in IZINLI:
                yol = os.path.join(gecici, ad)
                if os.path.exists(yol):
                    arsiv.add(yol, arcname=ad)
        tuz = os.urandom(16)
        sifreli = gizli.aes_sifrele(_anahtar(parola, tuz), tampon.getvalue(),
                                    BASLIK)
        gecici_dosya = hedef + ".tmp"
        with open(gecici_dosya, "wb") as f:
            f.write(BASLIK + tuz + sifreli)
        os.chmod(gecici_dosya, 0o600)
        os.replace(gecici_dosya, hedef)
        return hedef
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _ac(dosya, parola, cikis):
    """Yedeği çözüp yalnızca izinli üyeleri ``cikis`` klasörüne açar."""
    with open(dosya, "rb") as f:
        ham = f.read(AZAMI_BOYUT)
    if not ham.startswith(BASLIK) or len(ham) < len(BASLIK) + 16 + 28:
        raise YedekHatasi("Bu bir Ülgen yedeği değil.")
    tuz = ham[len(BASLIK):len(BASLIK) + 16]
    try:
        duz = gizli.aes_coz(_anahtar(parola, tuz),
                            ham[len(BASLIK) + 16:], BASLIK)
    except gizli.AnahtarYok as hata:
        raise YedekHatasi("Parola yanlış ya da yedek bozuk.") from hata
    with tarfile.open(fileobj=io.BytesIO(duz), mode="r:gz") as arsiv:
        for uye in arsiv.getmembers():
            if uye.name not in IZINLI or not uye.isfile() \
                    or uye.size > AZAMI_BOYUT:
                raise YedekHatasi("Yedek beklenmeyen içerik taşıyor.")
            with arsiv.extractfile(uye) as kaynak, \
                    open(os.path.join(cikis, uye.name), "wb") as hedef:
                shutil.copyfileobj(kaynak, hedef)


def dogrula(dosya, parola):
    """Yedeği açıp bütünlüğünü sınar. Sorunsuzsa üye adlarını döndürür."""
    gecici = tempfile.mkdtemp()
    try:
        _ac(dosya, parola, gecici)
        yol = os.path.join(gecici, ISIM_VERI)
        if os.path.exists(yol):
            baglanti = sqlite3.connect(yol)
            try:
                sonuc = baglanti.execute("PRAGMA integrity_check").fetchone()
            finally:
                baglanti.close()
            if sonuc[0] != "ok":
                raise YedekHatasi("Yedekteki veritabanı bozuk.")
        return sorted(os.listdir(gecici))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def geri_yukle(dosya, parola):
    """Yedeği doğrular, mevcut dosyaları 'yedekler/onceki-...' içine taşır
    ve yedekten geri yükler. Taşınan klasörün yolunu döndürür."""
    uyeler = dogrula(dosya, parola)
    gecici = tempfile.mkdtemp()
    try:
        _ac(dosya, parola, gecici)
        ayar.klasor_hazirla()
        onceki = os.path.join(ayar.KLASOR, "yedekler", "onceki-%s"
                              % datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(onceki, mode=0o700)
        hedefler = {ISIM_VERI: ayar.VERI_TABANI,
                    ISIM_HAFIZA: ayar.HAFIZA_DOSYASI,
                    ISIM_AYAR: ayar.AYAR_DOSYASI}
        for ad in uyeler:
            hedef = hedefler[ad]
            if os.path.exists(hedef):
                shutil.move(hedef, os.path.join(onceki, ad))
            for ek in ("-wal", "-shm"):
                if os.path.exists(hedef + ek):
                    shutil.move(hedef + ek, os.path.join(onceki, ad + ek))
            shutil.copy2(os.path.join(gecici, ad), hedef)
            os.chmod(hedef, 0o600)
        return onceki
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
