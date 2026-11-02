"""Cihaz belirteçleri (token) yönetimi.

Her cihaza (iPhone vb.) ayrı, rastgele 256 bitlik bir belirteç verilir.
Veritabanında belirtecin kendisi DEĞİL, SHA-256 özeti tutulur; belirteç
yalnızca oluşturulurken bir kez gösterilir. Belirteç iptal edilebilir ve
isteğe bağlı olarak süresi dolar.
"""

import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta

from . import ayar, veritabani

BICIM = "%Y-%m-%d %H:%M:%S"


def _ozet(belirtec):
    return hashlib.sha256(belirtec.encode("utf-8")).hexdigest()


def _simdi():
    return datetime.now().strftime(BICIM)


def olustur(ad, gun=None):
    """Yeni cihaz belirteci üretir. (id, belirtec) döndürür."""
    belirtec = secrets.token_urlsafe(32)
    bitis = None
    if gun:
        bitis = (datetime.now() + timedelta(days=int(gun))).strftime(BICIM)
    kimlik = veritabani.sorgu(
        "INSERT INTO cihazlar (ad, ozet, olusturma, son_gecerlilik) "
        "VALUES (?, ?, ?, ?)", (ad.strip()[:60] or "cihaz", _ozet(belirtec),
                                _simdi(), bitis))
    return kimlik, belirtec


def dogrula(belirtec):
    """Belirteç geçerliyse cihaz kaydını, değilse None döndürür."""
    if not belirtec or len(belirtec) > 200:
        return None
    satirlar = veritabani.sorgu(
        "SELECT id, ad, son_gecerlilik, son_kullanim FROM cihazlar "
        "WHERE ozet = ? AND iptal = 0", (_ozet(belirtec),), True)
    if not satirlar:
        return None
    kayit = satirlar[0]
    if kayit["son_gecerlilik"] and kayit["son_gecerlilik"] < _simdi():
        return None
    # her istekte yazmamak için en çok dakikada bir güncelle
    if not kayit["son_kullanim"] or kayit["son_kullanim"][:16] != _simdi()[:16]:
        veritabani.sorgu("UPDATE cihazlar SET son_kullanim = ? WHERE id = ?",
                         (_simdi(), kayit["id"]))
    return kayit


def listele():
    return veritabani.sorgu(
        "SELECT id, ad, olusturma, son_gecerlilik, son_kullanim, iptal "
        "FROM cihazlar ORDER BY id", (), True)


def iptal(kimlik):
    """Cihazı iptal eder; iptal edilen sayısını verir."""
    return veritabani.sorgu(
        "UPDATE cihazlar SET iptal = 1 WHERE id = ? AND iptal = 0",
        (int(kimlik),), sayi=True)


def eski_anahtari_tasi():
    """Eski tek anahtarı (anahtar.txt) cihaz belirtecine çevirip dosyayı siler.

    Telefondaki kayıtlı anahtar çalışmaya devam eder; düz yazı dosya diskten
    kaldırılır.
    """
    if not os.path.exists(ayar.ANAHTAR_DOSYASI):
        return False
    try:
        with open(ayar.ANAHTAR_DOSYASI, "r", encoding="utf-8") as dosya:
            eski = dosya.read().strip()
    except OSError:
        return False
    if eski:
        veritabani.sorgu(
            "INSERT OR IGNORE INTO cihazlar (ad, ozet, olusturma) "
            "VALUES (?, ?, ?)", ("eski anahtar (iPhone)", _ozet(eski),
                                 _simdi()))
    os.remove(ayar.ANAHTAR_DOSYASI)
    return True


# ------------------------------------------- yerel tarayıcı girişi (127.0.0.1)
GIRIS_OMRU_SN = 60
OTURUM_GUN = 30


def giris_anahtari_uret():
    """Tek kullanımlık, 60 sn ömürlü giriş anahtarı (yalnızca özeti saklanır).

    Yalnızca Ülgen'in veritabanı anahtarına erişebilen (aynı kullanıcı) bir
    süreç üretebilir: ``python -m ulgen --ac``."""
    anahtar = secrets.token_urlsafe(32)
    veritabani.sorgu("DELETE FROM giris_anahtari WHERE bitis < ?",
                     (time.time(),))
    veritabani.sorgu(
        "INSERT INTO giris_anahtari (ozet, bitis) VALUES (?, ?)",
        (_ozet(anahtar), time.time() + GIRIS_OMRU_SN))
    return anahtar


def giris_anahtari_tuket(anahtar):
    """Geçerliyse tarayıcı oturum belirteci (30 gün, iptal edilebilir) üretir;
    anahtar yakılır. Geçersiz/kullanılmış/süresi dolmuşsa None."""
    if not anahtar or len(anahtar) > 200:
        return None
    adet = veritabani.sorgu(
        "UPDATE giris_anahtari SET kullanildi=1 WHERE ozet=? AND "
        "kullanildi=0 AND bitis>=?", (_ozet(anahtar), time.time()),
        sayi=True)
    if not adet:
        return None
    return olustur("Mac tarayıcı", OTURUM_GUN)[1]
