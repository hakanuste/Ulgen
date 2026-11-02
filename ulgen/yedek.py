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

from . import ayar, gizli, veritabani

BASLIK = b"ULGENYEDEK1"
ISIM_VERI = "veri.db"
ISIM_HAFIZA = "memory.json"
ISIM_HASSAS = "memory_hassas.json"
ISIM_AYAR = "ayar.json"
IZINLI = (ISIM_VERI, ISIM_HAFIZA, ISIM_HASSAS, ISIM_AYAR)
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
    veritabani.duz_kopya(hedef)


def al(hedef, parola):
    """Şifreli yedeği ``hedef`` dosyasına yazar; dosya yolunu döndürür."""
    gecici = tempfile.mkdtemp()
    try:
        if os.path.exists(ayar.VERI_TABANI):
            _tutarli_veritabani(os.path.join(gecici, ISIM_VERI))
        for ad, kaynak in ((ISIM_HAFIZA, ayar.HAFIZA_DOSYASI),
                           (ISIM_HASSAS, ayar.HASSAS_DOSYASI)):
            if os.path.exists(kaynak):
                with open(kaynak, "rb") as f:
                    ham = gizli.coz(f.read())
                with open(os.path.join(gecici, ad), "wb") as f:
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
        veritabani.kapat()
        hedefler = {ISIM_VERI: ayar.VERI_TABANI,
                    ISIM_HAFIZA: ayar.HAFIZA_DOSYASI,
                    ISIM_HASSAS: ayar.HASSAS_DOSYASI,
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


# ------------------------------------------------- otomatik yerel yedek

OTOMATIK_SAKLA = 7
OTOMATIK_ARALIK = 24 * 3600


def otomatik_dizin():
    yol = os.path.join(ayar.KLASOR, "yedekler", "otomatik")
    os.makedirs(yol, mode=0o700, exist_ok=True)
    return yol


def otomatik_listele():
    """Otomatik yedekleri yeniden eskiye doğru listeler."""
    return sorted((f for f in os.listdir(otomatik_dizin())
                   if f.endswith(".db.enc")), reverse=True)


def otomatik_al():
    """Veritabanının tutarlı, ana anahtarla şifreli bir kopyasını alır.

    Bu yedek BU Mac'e bağlıdır (ana anahtar gerekir). Mac kaybı için
    parolalı yedeği (``al``) kullanın. Son 7 otomatik yedek saklanır.
    """
    gecici = tempfile.mkdtemp()
    try:
        kopya = os.path.join(gecici, "kopya.db")
        veritabani.kapat()          # WAL'i dosyaya işleyip kopyala
        _tutarli_veritabani(kopya)
        with open(kopya, "rb") as f:
            sifreli = gizli.sifrele(f.read())
        ad = "veri-%s.db.enc" % datetime.now().strftime("%Y%m%d-%H%M%S")
        hedef = os.path.join(otomatik_dizin(), ad)
        with open(hedef + ".tmp", "wb") as f:
            f.write(sifreli)
        os.chmod(hedef + ".tmp", 0o600)
        os.replace(hedef + ".tmp", hedef)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    for eski in otomatik_listele()[OTOMATIK_SAKLA:]:
        os.remove(os.path.join(otomatik_dizin(), eski))
    return hedef


def otomatik_son_zaman():
    """En yeni otomatik yedeğin Unix zamanı (yoksa 0)."""
    liste = otomatik_listele()
    if not liste:
        return 0
    return os.path.getmtime(os.path.join(otomatik_dizin(), liste[0]))


def _otomatik_cozup_dogrula(ad, hedef):
    with open(os.path.join(otomatik_dizin(), ad), "rb") as f:
        ham = gizli.coz(f.read())
    with open(hedef, "wb") as f:
        f.write(ham)
    tamam, ayrinti = veritabani.butunluk_denetimi(hedef)
    if not tamam:
        raise YedekHatasi("Yedek bozuk: %s" % ayrinti)


def otomatik_geri_yukle(ad=None):
    """Seçilen (yoksa en yeni sağlam) otomatik yedeği geri yükler.

    Mevcut veritabanı silinmez; ``yedekler/onceki-...`` içine taşınır.
    """
    adaylar = [ad] if ad else otomatik_listele()
    gecici = tempfile.mkdtemp()
    try:
        secilen = None
        for aday in adaylar:
            yol = os.path.join(gecici, "aday.db")
            try:
                _otomatik_cozup_dogrula(aday, yol)
            except (YedekHatasi, gizli.AnahtarYok, OSError):
                continue
            secilen = aday
            break
        if secilen is None:
            raise YedekHatasi("Sağlam otomatik yedek bulunamadı.")
        veritabani.kapat()
        onceki = os.path.join(ayar.KLASOR, "yedekler", "onceki-%s"
                              % datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(onceki, mode=0o700, exist_ok=True)
        for ek in ("", "-wal", "-shm"):
            if os.path.exists(ayar.VERI_TABANI + ek):
                shutil.move(ayar.VERI_TABANI + ek,
                            os.path.join(onceki, "veri.db" + ek))
        shutil.copy2(os.path.join(gecici, "aday.db"), ayar.VERI_TABANI)
        os.chmod(ayar.VERI_TABANI, 0o600)
        return secilen, onceki
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def veritabani_kurtar():
    """Açılışta çalışır: veritabanı bozuksa yedekten kurtarır.

    Bozuk dosya silinmez, ``yedekler/bozuk-...`` içine taşınır. Kullanıcıya
    gösterilecek bir mesaj döndürür (sorun yoksa None).
    """
    if not os.path.exists(ayar.VERI_TABANI):
        return None
    tamam, ayrinti = veritabani.butunluk_denetimi(ayar.VERI_TABANI)
    if tamam:
        return None
    veritabani.kapat()
    hedef = os.path.join(ayar.KLASOR, "yedekler", "bozuk-%s"
                         % datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(hedef, mode=0o700, exist_ok=True)
    for ek in ("", "-wal", "-shm"):
        if os.path.exists(ayar.VERI_TABANI + ek):
            shutil.move(ayar.VERI_TABANI + ek,
                        os.path.join(hedef, "veri.db" + ek))
    try:
        secilen, _ = otomatik_geri_yukle()
    except YedekHatasi:
        return ("Veritabanı bozuktu (%s) ve sağlam yedek bulunamadı. Bozuk "
                "dosya şuraya taşındı: %s. Boş veritabanı oluşturuldu."
                % (ayrinti[:80], hedef))
    return ("Veritabanı bozuktu; %s yedeğinden kurtarıldı. Bozuk dosya: %s"
            % (secilen, hedef))


def otomatik_dongu(durdur):
    """Günde bir otomatik yedek alan arka plan döngüsü (durdur: Event)."""
    import time
    while not durdur.is_set():
        try:
            if time.time() - otomatik_son_zaman() > OTOMATIK_ARALIK:
                otomatik_al()
        except Exception as hata:  # yedek hatası uygulamayı durdurmasın
            try:
                veritabani.gunluge_yaz("hata", "yedek", hata)
            except Exception:
                pass
        durdur.wait(3600)


# ------------------------------------------------- kurulum öncesi yedek
def _ozet(yol):
    import hashlib
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def kurulum_yedegi(dizin):
    """Kurulumdan önce TUTARLI yedek: WAL işlenir (checkpoint), veritabanı
    kopyalanır, kopya bit bit doğrulanır ve bütünlük denetimi yapılır.
    Dosya adları ``MANIFEST.json`` içindeki SHA-256 ile kaydedilir.

    Şifreli veritabanının yedeği ana anahtar OLMADAN açılamaz: anahtar
    Anahtar Zinciri'ndeyse ayrıca saklanmaz (parolalı yedek için --yedek-al).
    Hata olursa YedekHatasi; kurulum çağıranca DURDURULUR."""
    os.makedirs(dizin, mode=0o700, exist_ok=True)
    manifest = {}
    yol = ayar.VERI_TABANI
    tur = veritabani.dosya_turu(yol)
    if tur != "yok":
        hedef = os.path.join(dizin, ISIM_VERI)
        try:
            if tur == "sifreli":
                if veritabani._sc is None:
                    raise YedekHatasi("şifreli veritabanı için SQLCipher yok")
                baglanti = veritabani._sifreli_ac(yol)
                try:
                    baglanti.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                finally:
                    baglanti.close()
                shutil.copy2(yol, hedef)
                if _ozet(yol) != _ozet(hedef):
                    raise YedekHatasi("kopya özeti kaynakla uyuşmuyor "
                                      "(yazan başka süreç olabilir)")
            else:
                kaynak = sqlite3.connect(yol)
                hedefb = sqlite3.connect(hedef)
                try:
                    kaynak.backup(hedefb)
                finally:
                    hedefb.close()
                    kaynak.close()
        except veritabani.VeriTabaniHatasi as hata:
            raise YedekHatasi(str(hata))
        except (OSError, sqlite3.Error) as hata:
            raise YedekHatasi("veritabanı yedeklenemedi: %s" % hata)
        saglam, ayr = veritabani.butunluk_denetimi(hedef)
        if not saglam:
            raise YedekHatasi("yedek bütünlük denetiminden geçmedi: %s" % ayr)
        manifest[ISIM_VERI] = _ozet(hedef)
    for ad in os.listdir(ayar.KLASOR):
        yolu = os.path.join(ayar.KLASOR, ad)
        if os.path.isfile(yolu) and (ad.endswith((".json", ".anahtar", ".key",
                                                  ".sifreli", ".paket"))):
            shutil.copy2(yolu, os.path.join(dizin, ad))
            manifest[ad] = _ozet(os.path.join(dizin, ad))
    kod = os.path.join(ayar.KLASOR, "kod")
    if os.path.isdir(kod):
        shutil.copytree(kod, os.path.join(dizin, "kod"), dirs_exist_ok=True)
    with open(os.path.join(dizin, "MANIFEST.json"), "w",
              encoding="utf-8") as f:
        json.dump({"zaman": datetime.now().isoformat(timespec="seconds"),
                   "dosyalar": manifest}, f, indent=1)
    return manifest
