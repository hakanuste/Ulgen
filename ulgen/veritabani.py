"""Yerel SQLite veri tabanı (WAL, sürümlü göç, işlem, bütünlük denetimi).

  * Tek kalıcı bağlantı + kilit; WAL kipi, ``foreign_keys`` açık.
  * ``PRAGMA user_version`` ile sürümlü göç (``GOCLER``); göçler tek işlemdedir,
    yarıda kesilirse geri alınır. Eski (v2.0) veritabanı v1 göçüyle uyumludur.
  * ``islem()`` ile çok adımlı yazmalar tek işlem olur.
  * ``butunluk_denetimi()`` açılışta çalıştırılır (bkz. yedek.veritabani_kurtar).
"""

import contextlib
import hashlib
import os
import re
import shutil
import sqlite3
import threading
import time

from . import ayar

try:                                   # SQLCipher: şeffaf, tam dosya şifreleme
    import sqlcipher3.dbapi2 as _sc
except Exception:                      # kurulu değilse şifresiz çalışılır
    _sc = None

DUZ_BASLIK = b"SQLite format 3\x00"
SIFRELI = False        # şu anki bağlantı şifreli mi (panelde gösterilir)
GOC_NOTU = ""          # açılışta şifrelemeye geçildiyse kullanıcıya not


class VeriTabaniHatasi(Exception):
    """Anahtar yanlış/eksik ya da SQLCipher yok: dosyaya DOKUNULMAZ."""


DB_HATALARI = (sqlite3.DatabaseError,) + (
    (_sc.DatabaseError,) if _sc is not None else ())

SURUM = 8
FTS_VAR = False

_KILIT = threading.RLock()
_BAGLANTI = None
_YOL = None
_DERINLIK = 0


def sifreleme_var():
    return _sc is not None


def _anahtar_hex():
    """Ana anahtardan veritabanı anahtarı türetir (ham 256 bit)."""
    from . import gizli
    return hashlib.sha256(b"ulgen-veritabani-v1" + gizli.ana_anahtar()
                          ).hexdigest()


def _anahtar_sql():
    return "x'%s'" % _anahtar_hex()


def dosya_turu(yol):
    """'yok' | 'duz' (şifresiz SQLite) | 'sifreli' (başlık SQLite değil)."""
    if not os.path.exists(yol) or os.path.getsize(yol) == 0:
        return "yok"
    with open(yol, "rb") as f:
        return "duz" if f.read(16) == DUZ_BASLIK else "sifreli"


def _sifreli_ac(yol):
    baglanti = _sc.connect(yol, check_same_thread=False,
                           isolation_level=None)
    baglanti.execute("PRAGMA key = \"%s\"" % _anahtar_sql())
    try:
        baglanti.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except _sc.DatabaseError as hata:
        baglanti.close()
        raise VeriTabaniHatasi(
            "Veritabanı açılamadı: anahtar yanlış/eksik ya da dosya bozuk. "
            "Dosyaya dokunulmadı.") from hata
    return baglanti


def _sifirla_dosya(yol):
    """Dosyanın içeriğini sıfırlayıp siler (SSD'de kesin silmeyi garanti
    etmez; APFS anlık görüntüleri/aşınma dengeleme eski blokları tutabilir)."""
    try:
        boyut = os.path.getsize(yol)
        with open(yol, "r+b") as f:
            for _ in range(0, boyut, 1 << 20):
                f.write(b"\0" * min(1 << 20, boyut))
            f.flush()
            os.fsync(f.fileno())
    finally:
        try:
            os.remove(yol)
        except OSError:
            pass


def _duzden_sifrele(yol):
    """Şifresiz veritabanını şifreliye çevirir.

    Sıra: (1) şifreli kopya üret + doğrula, (2) eski şifresiz dosyayı AES-GCM
    ile ŞİFRELİ arşive al ve geri çözülebildiğini doğrula, (3) dosyaları
    değiştir, (4) eski düz dosyayı sıfırla. Her adım hata verirse eski dosya
    yerinde kalır."""
    global GOC_NOTU
    from . import gizli
    yeni = yol + ".yeni"
    for ek in ("", "-wal", "-shm"):
        if os.path.exists(yeni + ek):
            os.remove(yeni + ek)
    kaynak = _sc.connect(yol)
    try:
        kaynak.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        sonuc = kaynak.execute("PRAGMA integrity_check").fetchone()[0]
        if sonuc != "ok":
            raise VeriTabaniHatasi("Şifresiz veritabanı bozuk (%s); "
                                   "şifreleme yapılmadı." % sonuc[:60])
        surum = kaynak.execute("PRAGMA user_version").fetchone()[0]
        kaynak.execute("ATTACH DATABASE '%s' AS enc KEY \"%s\""
                       % (yeni.replace("'", "''"), _anahtar_sql()))
        kaynak.execute("SELECT sqlcipher_export('enc')")
        kaynak.execute("PRAGMA enc.user_version = %d" % int(surum))
        kaynak.execute("DETACH DATABASE enc")
        tablolar = [r[0] for r in kaynak.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name "
            "NOT LIKE 'sqlite_%'").fetchall()]
        say = {t: kaynak.execute('SELECT COUNT(*) FROM "%s"' % t)
               .fetchone()[0] for t in tablolar}
    finally:
        kaynak.close()
    hedef = _sifreli_ac(yeni)
    try:
        if hedef.execute("PRAGMA integrity_check").fetchone()[0] != "ok" \
                or hedef.execute("PRAGMA user_version").fetchone()[0] != surum:
            raise VeriTabaniHatasi("Şifreli kopya doğrulanamadı.")
        for t, n in say.items():
            if hedef.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] \
                    != n:
                raise VeriTabaniHatasi("Şifreli kopyada satır sayısı "
                                       "tutmuyor (%s)." % t)
    finally:
        hedef.close()
    # eski düz dosyanın ŞİFRELİ arşivi
    with open(yol, "rb") as f:
        ham = f.read()
    arsiv_dizini = os.path.join(ayar.KLASOR, "yedekler")
    os.makedirs(arsiv_dizini, mode=0o700, exist_ok=True)
    arsiv = os.path.join(arsiv_dizini, "onceki-sifresiz-%s.db.sifreli"
                         % time.strftime("%Y%m%d_%H%M%S"))
    anahtar = gizli.ana_anahtar()
    with open(arsiv, "wb") as f:
        f.write(gizli.aes_sifrele(anahtar, ham, b"ULGENDBDUZ1"))
    os.chmod(arsiv, 0o600)
    with open(arsiv, "rb") as f:
        if gizli.aes_coz(anahtar, f.read(), b"ULGENDBDUZ1") != ham:
            raise VeriTabaniHatasi("Şifreli arşiv doğrulanamadı.")
    # değiştir
    eski = yol + ".eski"
    os.replace(yol, eski)
    try:
        os.replace(yeni, yol)
        os.chmod(yol, 0o600)
    except OSError:
        os.replace(eski, yol)
        raise
    for ek in ("-wal", "-shm"):
        if os.path.exists(yol + ek):
            os.remove(yol + ek)
    _sifirla_dosya(eski)
    GOC_NOTU = ("Veritabanı şifrelendi (SQLCipher). Eski şifresiz kopya "
                "yalnızca şifreli arşiv olarak saklandı: %s" % arsiv)


def _baglan():
    """Kalıcı bağlantıyı verir; veritabanı yolu değiştiyse yeniden açar.

    SQLCipher kuruluysa dosya TAM şifrelidir (tablolar, dizinler, WAL, FTS).
    Eski şifresiz dosya ilk açılışta doğrulanarak şifreliye çevrilir. Anahtar
    yanlışsa ya da SQLCipher yokken şifreli dosya varsa dosyaya dokunulmaz."""
    global _BAGLANTI, _YOL, SIFRELI
    yol = ayar.VERI_TABANI
    if _BAGLANTI is not None and _YOL == yol:
        return _BAGLANTI
    if _BAGLANTI is not None:
        _BAGLANTI.close()
        _BAGLANTI = None
    ayar.klasor_hazirla()
    tur = dosya_turu(yol)
    if _sc is not None:
        if tur == "duz":
            _duzden_sifrele(yol)
        baglanti = _sifreli_ac(yol)
        baglanti.row_factory = _sc.Row
        SIFRELI = True
    else:
        if tur == "sifreli":
            raise VeriTabaniHatasi(
                "Veritabanı şifreli ama SQLCipher kurulu değil: "
                "pip install sqlcipher3-wheels")
        # GÜVENLİ VARSAYILAN: SQLCipher yoksa ÇALIŞMAYI REDDET. Şifresiz
        # çalışma yalnızca kullanıcı bilerek ayar.json'a
        # "sifresiz_veritabani_izni": true yazarsa olur.
        if ayar.yukle().get("sifresiz_veritabani_izni") is not True:
            raise VeriTabaniHatasi(
                "SQLCipher kurulu değil; veritabanı şifrelenemiyor. Ülgen "
                "güvenlik gereği başlamadı. Çözüm: pip install "
                "sqlcipher3-wheels (Kur.command bunu yapar). Bilerek şifresiz "
                "çalışmak için ayar.json'a \"sifresiz_veritabani_izni\": true "
                "yazın (önerilmez).")
        baglanti = sqlite3.connect(yol, check_same_thread=False,
                                   isolation_level=None)
        baglanti.row_factory = sqlite3.Row
        SIFRELI = False
    baglanti.execute("PRAGMA busy_timeout=5000")
    baglanti.execute("PRAGMA journal_mode=WAL")
    baglanti.execute("PRAGMA synchronous=NORMAL")
    baglanti.execute("PRAGMA foreign_keys=ON")
    try:
        os.chmod(yol, 0o600)
    except OSError:
        pass
    _BAGLANTI, _YOL = baglanti, yol
    return baglanti


def duz_kopya(hedef):
    """Canlı veritabanının ŞİFRESİZ ve tutarlı bir kopyasını ``hedef``e yazar
    (parola korumalı taşınabilir yedek için; geçici dosyayı çağıran siler)."""
    with _KILIT:
        baglanti = _baglan()
        if not SIFRELI:
            hedef_b = sqlite3.connect(hedef)
            try:
                baglanti.backup(hedef_b)
            finally:
                hedef_b.close()
            return
        surum = baglanti.execute("PRAGMA user_version").fetchone()[0]
        baglanti.execute("ATTACH DATABASE '%s' AS duz KEY ''"
                         % hedef.replace("'", "''"))
        try:
            baglanti.execute("SELECT sqlcipher_export('duz')")
            baglanti.execute("PRAGMA duz.user_version = %d" % int(surum))
        finally:
            baglanti.execute("DETACH DATABASE duz")


def kapat():
    """Bağlantıyı kapatır (dosya değiştirilecekse önce çağrılır)."""
    global _BAGLANTI, _YOL
    with _KILIT:
        if _BAGLANTI is not None:
            try:
                _BAGLANTI.close()
            finally:
                _BAGLANTI, _YOL = None, None


def sorgu(sql, args=(), getir=False, sayi=False):
    """Tek SQL komutu çalıştırır (işlem içindeyse işleme katılır).

    getir=True: satırlar sözlük listesi; sayi=True: etkilenen satır sayısı;
    aksi hâlde son eklenen satırın numarası.
    """
    with _KILIT:
        imlec = _baglan().execute(sql, args)
        if getir:
            return [dict(satir) for satir in imlec.fetchall()]
        if sayi:
            return imlec.rowcount
        return imlec.lastrowid


@contextlib.contextmanager
def islem():
    """Çok adımlı yazma için işlem: hata olursa tümü geri alınır."""
    global _DERINLIK
    with _KILIT:
        baglanti = _baglan()
        if _DERINLIK:           # iç içe çağrı dış işleme katılır
            yield
            return
        baglanti.execute("BEGIN IMMEDIATE")
        _DERINLIK = 1
        try:
            yield
            baglanti.execute("COMMIT")
        except BaseException:
            baglanti.execute("ROLLBACK")
            raise
        finally:
            _DERINLIK = 0


def _sutun_ekle(tablo, sutun, tanim):
    """Tabloda yoksa sütunu ekler."""
    var = [s["name"] for s in sorgu("PRAGMA table_info(%s)" % tablo, (), True)]
    if sutun not in var:
        sorgu("ALTER TABLE %s ADD COLUMN %s %s" % (tablo, sutun, tanim))


# ----------------------------------------------------------------- göçler

def _goc_1():
    """Temel tablolar (v2.0 ile uyumlu, tekrar çalıştırılabilir)."""
    sorgu("""CREATE TABLE IF NOT EXISTS hatirlaticilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zaman TEXT NOT NULL,
        mesaj TEXT NOT NULL,
        bildirildi INTEGER NOT NULL DEFAULT 0)""")
    _sutun_ekle("hatirlaticilar", "kalici", "INTEGER NOT NULL DEFAULT 0")
    _sutun_ekle("hatirlaticilar", "tekrar", "INTEGER NOT NULL DEFAULT 0")
    _sutun_ekle("hatirlaticilar", "onaylandi", "INTEGER NOT NULL DEFAULT 0")
    sorgu("""CREATE TABLE IF NOT EXISTS notlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metin TEXT NOT NULL,
        zaman TEXT NOT NULL)""")
    sorgu("""CREATE TABLE IF NOT EXISTS sohbet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rol TEXT NOT NULL,
        metin TEXT NOT NULL,
        zaman TEXT NOT NULL)""")
    _sutun_ekle("sohbet", "ozetlendi", "INTEGER NOT NULL DEFAULT 0")
    sorgu("""CREATE TABLE IF NOT EXISTS ozet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metin TEXT NOT NULL,
        zaman TEXT NOT NULL)""")
    sorgu("""CREATE TABLE IF NOT EXISTS cihazlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        ozet TEXT NOT NULL UNIQUE,
        olusturma TEXT NOT NULL,
        son_gecerlilik TEXT,
        son_kullanim TEXT,
        iptal INTEGER NOT NULL DEFAULT 0)""")


def _goc_2():
    """Duyarlı sohbet işareti, tam metin arama (FTS5), sistem günlüğü."""
    global FTS_VAR
    _sutun_ekle("sohbet", "duyarli", "INTEGER NOT NULL DEFAULT 0")
    sorgu("""CREATE TABLE IF NOT EXISTS gunluk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zaman TEXT NOT NULL,
        seviye TEXT NOT NULL,
        kaynak TEXT NOT NULL,
        metin TEXT NOT NULL)""")
    try:
        sorgu("""CREATE VIRTUAL TABLE IF NOT EXISTS sohbet_fts USING fts5(
            metin, content='sohbet', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2')""")
    except sqlite3.OperationalError:
        return      # bu SQLite derlemesinde FTS5 yok; arama LIKE'a düşer
    sorgu("""CREATE TRIGGER IF NOT EXISTS sohbet_ai AFTER INSERT ON sohbet
        BEGIN INSERT INTO sohbet_fts(rowid, metin) VALUES (new.id, new.metin);
        END""")
    sorgu("""CREATE TRIGGER IF NOT EXISTS sohbet_ad AFTER DELETE ON sohbet
        BEGIN INSERT INTO sohbet_fts(sohbet_fts, rowid, metin)
        VALUES ('delete', old.id, old.metin); END""")
    sorgu("""CREATE TRIGGER IF NOT EXISTS sohbet_au AFTER UPDATE OF metin
        ON sohbet BEGIN
        INSERT INTO sohbet_fts(sohbet_fts, rowid, metin)
        VALUES ('delete', old.id, old.metin);
        INSERT INTO sohbet_fts(rowid, metin) VALUES (new.id, new.metin);
        END""")
    sorgu("INSERT INTO sohbet_fts(sohbet_fts) VALUES ('rebuild')")


def _goc_3():
    """Sağlayıcı kotası olayları, kota durumu ve kalıcı istek kuyruğu."""
    sorgu("""CREATE TABLE IF NOT EXISTS kota_olay (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        saglayici TEXT NOT NULL,
        model TEXT NOT NULL DEFAULT '',
        zaman REAL NOT NULL,
        giris_token INTEGER NOT NULL DEFAULT 0,
        cikis_token INTEGER NOT NULL DEFAULT 0,
        gercek INTEGER NOT NULL DEFAULT 0,
        durum TEXT NOT NULL,
        gecikme_ms INTEGER NOT NULL DEFAULT 0)""")
    sorgu("CREATE INDEX IF NOT EXISTS kota_olay_sz ON kota_olay "
          "(saglayici, zaman)")
    sorgu("""CREATE TABLE IF NOT EXISTS kota_durum (
        saglayici TEXT PRIMARY KEY,
        engel_son REAL NOT NULL DEFAULT 0,
        engel_neden TEXT NOT NULL DEFAULT '',
        gercek TEXT NOT NULL DEFAULT '{}',
        gercek_zaman REAL NOT NULL DEFAULT 0,
        son_hata TEXT NOT NULL DEFAULT '')""")
    sorgu("""CREATE TABLE IF NOT EXISTS kuyruk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        olusturma REAL NOT NULL,
        metin TEXT NOT NULL,
        duyarli INTEGER NOT NULL DEFAULT 0,
        durum TEXT NOT NULL DEFAULT 'bekliyor',
        deneme INTEGER NOT NULL DEFAULT 0,
        son_deneme REAL NOT NULL DEFAULT 0,
        beyin TEXT NOT NULL DEFAULT '',
        sonuc TEXT NOT NULL DEFAULT '')""")


def _goc_4():
    """İlaç planı, doz örnekleri (her birinin kendi kimliği), görevler."""
    sorgu("""CREATE TABLE IF NOT EXISTS ilac (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        doz_notu TEXT NOT NULL DEFAULT '',
        aktif INTEGER NOT NULL DEFAULT 1,
        olusturma REAL NOT NULL)""")
    sorgu("""CREATE TABLE IF NOT EXISTS ilac_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ilac_id INTEGER NOT NULL REFERENCES ilac(id),
        saat TEXT NOT NULL,
        gunler TEXT NOT NULL DEFAULT '0,1,2,3,4,5,6',
        aktif INTEGER NOT NULL DEFAULT 1,
        olusturma REAL NOT NULL)""")
    sorgu("""CREATE TABLE IF NOT EXISTS doz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ilac_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        ilac_ad TEXT NOT NULL,
        doz_notu TEXT NOT NULL DEFAULT '',
        planli TEXT NOT NULL,
        durum TEXT NOT NULL DEFAULT 'bekliyor',
        bildirim_sayisi INTEGER NOT NULL DEFAULT 0,
        sonraki REAL NOT NULL DEFAULT 0,
        yanit_zaman REAL NOT NULL DEFAULT 0,
        kaynak TEXT NOT NULL DEFAULT '',
        UNIQUE (plan_id, planli))""")
    sorgu("""CREATE TABLE IF NOT EXISTS doz_gecmis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doz_id INTEGER NOT NULL,
        zaman REAL NOT NULL,
        olay TEXT NOT NULL,
        ayrinti TEXT NOT NULL DEFAULT '')""")
    sorgu("""CREATE TABLE IF NOT EXISTS gorev (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tur TEXT NOT NULL,
        baslik TEXT NOT NULL,
        zaman TEXT,
        tekrar TEXT NOT NULL DEFAULT '',
        durum TEXT NOT NULL DEFAULT 'acik',
        onceden_dk INTEGER NOT NULL DEFAULT 0,
        asama INTEGER NOT NULL DEFAULT 0,
        son_bildirim TEXT NOT NULL DEFAULT '',
        olusturma REAL NOT NULL)""")


def _goc_5():
    """Yerel tarayıcı girişi için tek kullanımlık, kısa ömürlü anahtarlar."""
    sorgu("""CREATE TABLE IF NOT EXISTS giris_anahtari (
        ozet TEXT PRIMARY KEY,
        bitis REAL NOT NULL,
        kullanildi INTEGER NOT NULL DEFAULT 0)""")


def _goc_6():
    """Özel Kasa: sarılı anahtarlar, şifreli öğeler, Face ID anahtarları."""
    sorgu("CREATE TABLE IF NOT EXISTS kasa_meta (ad TEXT PRIMARY KEY, "
          "deger BLOB NOT NULL)")
    sorgu("CREATE TABLE IF NOT EXISTS kasa_oge (ad TEXT PRIMARY KEY, "
          "veri BLOB NOT NULL, olusturma REAL NOT NULL)")
    sorgu("""CREATE TABLE IF NOT EXISTS kasa_anahtar (
        kimlik TEXT PRIMARY KEY, ad TEXT, x BLOB NOT NULL, y BLOB NOT NULL,
        rp TEXT NOT NULL, sayac INTEGER NOT NULL DEFAULT 0, sarmali BLOB,
        olusturma REAL NOT NULL)""")
    sorgu("""CREATE TABLE IF NOT EXISTS kasa_istek (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kapsam TEXT NOT NULL,
        bitis REAL NOT NULL, durum TEXT NOT NULL DEFAULT 'bekliyor')""")


def _goc_7():
    """Obsidian kasası arama dizini (kasa dosyaları kendi yerinde kalır)."""
    sorgu("""CREATE TABLE IF NOT EXISTS not_dizin (
        yol TEXT PRIMARY KEY, mtime REAL NOT NULL, boyut INTEGER NOT NULL)""")
    sorgu("CREATE VIRTUAL TABLE IF NOT EXISTS not_fts USING fts5("
          "yol UNINDEXED, baslik, icerik, tokenize='unicode61')")


def _goc_8():
    """iPhone Sağlık köprüsü ölçümleri."""
    sorgu("""CREATE TABLE IF NOT EXISTS saglik_olcum (
        tur TEXT NOT NULL, deger REAL NOT NULL, zaman TEXT NOT NULL,
        kaynak TEXT, PRIMARY KEY (tur, zaman))""")


GOCLER = {1: _goc_1, 2: _goc_2, 3: _goc_3, 4: _goc_4, 5: _goc_5, 6: _goc_6, 7: _goc_7, 8: _goc_8}


def surum():
    with _KILIT:
        return _baglan().execute("PRAGMA user_version").fetchone()[0]


def kur():
    """Tüm göçleri sırayla uygular; FTS durumunu belirler."""
    global FTS_VAR
    ayar.klasor_hazirla()
    with _KILIT:
        mevcut = surum()
        for hedef in range(mevcut + 1, SURUM + 1):
            with islem():
                GOCLER[hedef]()
                sorgu("PRAGMA user_version=%d" % hedef)
        FTS_VAR = bool(sorgu(
            "SELECT 1 FROM sqlite_master WHERE name='sohbet_fts'", (), True))


# ------------------------------------------------------ bütünlük ve günlük

def butunluk_denetimi(yol=None):
    """(sorunsuz_mu, ayrıntı). Canlı dosya (yol yok ya da canlı yol) anahtarla,
    başka dosyalar (yedek/geçici) şifresiz ya da anahtarla denetlenir."""
    try:
        if yol is None or os.path.abspath(yol) == os.path.abspath(
                ayar.VERI_TABANI):
            with _KILIT:
                satirlar = _baglan().execute(
                    "PRAGMA integrity_check").fetchall()
        else:
            if dosya_turu(yol) == "sifreli" and _sc is not None:
                baglanti = _sifreli_ac(yol)
            else:
                baglanti = sqlite3.connect(yol)
            try:
                satirlar = baglanti.execute(
                    "PRAGMA integrity_check").fetchall()
            finally:
                baglanti.close()
    except VeriTabaniHatasi as hata:
        return False, str(hata)
    except DB_HATALARI as hata:
        return False, str(hata)
    ilk = satirlar[0][0] if satirlar else "bos"
    return ilk == "ok", "; ".join(str(s[0]) for s in satirlar[:5])


def gunluge_yaz(seviye, kaynak, metin):
    """Sistem günlüğüne kayıt ekler (hata ayıklama ve yönetim paneli için)."""
    from datetime import datetime
    sorgu("INSERT INTO gunluk (zaman, seviye, kaynak, metin) VALUES (?,?,?,?)",
          (datetime.now().isoformat(timespec="seconds"), seviye, kaynak,
           str(metin)[:1000]))


def sohbet_ara(sorgu_metni, adet=8):
    """Geçmiş konuşmalarda arar. [{id, rol, metin, zaman}] döndürür."""
    kelimeler = re.findall(r"\w{2,}", sorgu_metni.lower())[:8]
    if not kelimeler:
        return []
    if FTS_VAR:
        ifade = " ".join('"%s"*' % k.replace('"', "") for k in kelimeler)
        try:
            return sorgu(
                "SELECT s.id, s.rol, s.metin, s.zaman, s.duyarli FROM "
                "sohbet_fts f JOIN sohbet s ON s.id = f.rowid "
                "WHERE sohbet_fts MATCH ? ORDER BY rank LIMIT ?",
                (ifade, adet), True)
        except sqlite3.OperationalError:
            pass
    kosul = " AND ".join("lower(metin) LIKE ?" for _ in kelimeler)
    return sorgu(
        "SELECT id, rol, metin, zaman, duyarli FROM sohbet WHERE " + kosul
        + " ORDER BY id DESC LIMIT ?",
        tuple("%" + k + "%" for k in kelimeler) + (adet,), True)
