"""Kalıcı istek kuyruğu: kota dolunca ya da yerel beyin kapalıyken.

Kayıtlar SQLite'tadır; Ülgen yeniden başlasa da kaybolmaz. İşleniyor
durumunda kalmış kayıtlar açılışta yeniden beklemeye alınır. Süresi dolan
istek sessizce silinmez; durumu "suresi_doldu" olur ve kullanıcıya bildirilir.
"""

import time

from . import ayar, veritabani

AZAMI_BEKLEYEN = 50


def kurtar():
    """Açılışta: yarıda kalan 'isleniyor' kayıtları yeniden sıraya koyar."""
    return veritabani.sorgu(
        "UPDATE kuyruk SET durum='bekliyor' WHERE durum='isleniyor'",
        sayi=True)


def ekle(metin, duyarli=False):
    """Kuyruğa ekler; kimliği döndürür, kuyruk doluysa None."""
    if len(bekleyenler()) >= AZAMI_BEKLEYEN:
        return None
    return veritabani.sorgu(
        "INSERT INTO kuyruk (olusturma, metin, duyarli) VALUES (?,?,?)",
        (time.time(), metin[:4000], int(duyarli)))


def bekleyenler():
    return veritabani.sorgu(
        "SELECT * FROM kuyruk WHERE durum IN ('bekliyor','isleniyor') "
        "ORDER BY id", (), True)


def sonrakini_al():
    """En eski bekleyeni 'isleniyor' yapıp döndürür."""
    with veritabani.islem():
        satir = veritabani.sorgu(
            "SELECT * FROM kuyruk WHERE durum='bekliyor' ORDER BY id LIMIT 1",
            (), True)
        if not satir:
            return None
        veritabani.sorgu(
            "UPDATE kuyruk SET durum='isleniyor', deneme=deneme+1, "
            "son_deneme=? WHERE id=?", (time.time(), satir[0]["id"]))
        return satir[0]


def bitir(kimlik, durum, beyin="", sonuc=""):
    veritabani.sorgu(
        "UPDATE kuyruk SET durum=?, beyin=?, sonuc=? WHERE id=?",
        (durum, beyin, sonuc, kimlik))


def beklemeye_al(kimlik):
    veritabani.sorgu("UPDATE kuyruk SET durum='bekliyor' WHERE id=?",
                     (kimlik,))


def iptal(kimlik):
    return veritabani.sorgu(
        "UPDATE kuyruk SET durum='iptal' WHERE id=? AND durum IN "
        "('bekliyor','isleniyor')", (kimlik,), sayi=True)


def suresi_dolanlar():
    """Ömrünü doldurmuş bekleyenleri 'suresi_doldu' yapar; listesini verir."""
    sinir = time.time() - ayar.yukle().get("kuyruk_omru_saat", 24) * 3600
    dolanlar = veritabani.sorgu(
        "SELECT * FROM kuyruk WHERE durum='bekliyor' AND olusturma<?",
        (sinir,), True)
    for k in dolanlar:
        bitir(k["id"], "suresi_doldu")
    return dolanlar


def metin():
    liste = bekleyenler()
    if not liste:
        return "Kuyrukta bekleyen istek yok."
    return "\n".join("#%d  %s%s" % (
        k["id"], k["metin"][:70], "  [kişisel: yalnızca yerel beyin]"
        if k["duyarli"] else "") for k in liste)
