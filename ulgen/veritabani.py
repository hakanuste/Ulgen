"""Yerel SQLite veri tabanı (WAL, sürümlü göç, işlem, bütünlük denetimi).

  * Tek kalıcı bağlantı + kilit; WAL kipi, ``foreign_keys`` açık.
  * ``PRAGMA user_version`` ile sürümlü göç (``GOCLER``); göçler tek işlemdedir,
    yarıda kesilirse geri alınır. Eski (v2.0) veritabanı v1 göçüyle uyumludur.
  * ``islem()`` ile çok adımlı yazmalar tek işlem olur.
  * ``butunluk_denetimi()`` açılışta çalıştırılır (bkz. yedek.veritabani_kurtar).
"""

import contextlib
import os
import re
import sqlite3
import threading

from . import ayar

SURUM = 3
FTS_VAR = False

_KILIT = threading.RLock()
_BAGLANTI = None
_YOL = None
_DERINLIK = 0


def _baglan():
    """Kalıcı bağlantıyı verir; veritabanı yolu değiştiyse yeniden açar."""
    global _BAGLANTI, _YOL
    yol = ayar.VERI_TABANI
    if _BAGLANTI is not None and _YOL == yol:
        return _BAGLANTI
    if _BAGLANTI is not None:
        _BAGLANTI.close()
        _BAGLANTI = None
    ayar.klasor_hazirla()
    baglanti = sqlite3.connect(yol, check_same_thread=False,
                               isolation_level=None)
    baglanti.row_factory = sqlite3.Row
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


GOCLER = {1: _goc_1, 2: _goc_2, 3: _goc_3}


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
    """(sorunsuz_mu, ayrıntı). ``yol`` verilirse o dosya ayrıca denetlenir."""
    try:
        if yol is None:
            with _KILIT:
                satirlar = _baglan().execute(
                    "PRAGMA integrity_check").fetchall()
        else:
            baglanti = sqlite3.connect(yol)
            try:
                satirlar = baglanti.execute(
                    "PRAGMA integrity_check").fetchall()
            finally:
                baglanti.close()
    except sqlite3.DatabaseError as hata:
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
