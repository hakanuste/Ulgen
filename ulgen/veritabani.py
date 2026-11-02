"""Yerel SQLite veri tabanı.

Hatırlatıcılar, notlar, sohbet geçmişi ve konuşma özeti burada tutulur.
Eski sürümden kalan tablolar ``kur()`` içinde yeni sütunlarla güncellenir.
"""

import sqlite3
import threading

from . import ayar

_KILIT = threading.RLock()


def sorgu(sql, args=(), getir=False, sayi=False):
    """Tek bir SQL komutunu güvenle çalıştırır.

    getir=True ise satırları sözlük listesi olarak döndürür, sayi=True ise
    etkilenen satır sayısını, aksi hâlde son eklenen satırın numarasını.
    """
    with _KILIT:
        baglanti = sqlite3.connect(ayar.VERI_TABANI, check_same_thread=False)
        baglanti.row_factory = sqlite3.Row
        try:
            imlec = baglanti.execute(sql, args)
            if getir:
                sonuc = [dict(satir) for satir in imlec.fetchall()]
            elif sayi:
                sonuc = imlec.rowcount
            else:
                sonuc = imlec.lastrowid
            baglanti.commit()
            return sonuc
        finally:
            baglanti.close()


def _sutun_ekle(tablo, sutun, tanim):
    """Tabloda yoksa sütunu ekler (eski sürümden geçiş için)."""
    var = [s["name"] for s in sorgu("PRAGMA table_info(%s)" % tablo, (), True)]
    if sutun not in var:
        sorgu("ALTER TABLE %s ADD COLUMN %s %s" % (tablo, sutun, tanim))


def kur():
    """Tüm tabloları oluşturur ve gerekirse eski tabloları günceller."""
    ayar.klasor_hazirla()
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
