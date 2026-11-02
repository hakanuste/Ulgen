"""iPhone Sağlık verisi köprüsü (adım, nabız, uyku).

Apple Sağlık'ın web arayüzü yoktur; veri iPhone'dan, "Kestirmeler" (Shortcuts)
otomasyonuyla Ülgen'e GÖNDERİLİR (HTTPS + cihaz belirteci). F800/Joeme Fit
verisi Apple Sağlık'a yazılıyorsa aynı yoldan gelir (doğrulanmadı).

Bu veri ASLA buluta gitmez; yalnızca gösterilir. Ülgen tıbbi öneri vermez.
"""

from datetime import datetime, timedelta

from . import veritabani

TURLER = {"adim": (0, 200000), "nabiz": (20, 260), "uyku": (0, 1440),
          "aktif_dakika": (0, 1440), "kalori": (0, 20000)}
EN_COK = 500


class SaglikHatasi(Exception):
    pass


def ekle(olcumler, kaynak="kestirme"):
    """[{"tur","deger","zaman"(ISO)}] -> (eklenen, atlanan). Aynı tür+zaman
    gelirse güncellenir (kestirme tekrar çalışabilir)."""
    if not isinstance(olcumler, list) or len(olcumler) > EN_COK:
        raise SaglikHatasi("olcumler: en çok %d öğelik liste" % EN_COK)
    eklenen = atlanan = 0
    with veritabani.islem():
        for o in olcumler:
            try:
                tur, deger = o["tur"], float(o["deger"])
                zaman = datetime.fromisoformat(str(o["zaman"])[:19])
            except (KeyError, TypeError, ValueError):
                atlanan += 1
                continue
            alt, ust = TURLER.get(tur, (None, None))
            if alt is None or not alt <= deger <= ust:
                atlanan += 1
                continue
            veritabani.sorgu(
                "INSERT OR REPLACE INTO saglik_olcum (tur, deger, zaman, "
                "kaynak) VALUES (?, ?, ?, ?)",
                (tur, deger, zaman.isoformat(timespec="seconds"), kaynak))
            eklenen += 1
    return eklenen, atlanan


def bugun(simdi=None):
    """{"adim", "nabiz", "nabiz_zaman", "uyku_dk", "veri_var"}"""
    simdi = simdi or datetime.now()
    gun = simdi.strftime("%Y-%m-%d")
    dun = (simdi - timedelta(days=1)).strftime("%Y-%m-%d")

    def tek(sql, args):
        s = veritabani.sorgu(sql, args, True)
        return s[0] if s else None
    adim = tek("SELECT MAX(deger) AS d FROM saglik_olcum WHERE tur='adim' "
               "AND zaman >= ?", (gun,))
    nabiz = tek("SELECT deger, zaman FROM saglik_olcum WHERE tur='nabiz' "
                "ORDER BY zaman DESC LIMIT 1", ())
    uyku = tek("SELECT SUM(deger) AS d FROM saglik_olcum WHERE tur='uyku' "
               "AND zaman >= ? AND zaman < ?", (dun + "T12:00:00",
                                                gun + "T12:00:00"))
    sonuc = {
        "adim": int(adim["d"]) if adim and adim["d"] is not None else None,
        "nabiz": int(nabiz["deger"]) if nabiz else None,
        "nabiz_zaman": nabiz["zaman"] if nabiz else None,
        "uyku_dk": int(uyku["d"]) if uyku and uyku["d"] else None}
    sonuc["veri_var"] = any(sonuc[k] is not None
                            for k in ("adim", "nabiz", "uyku_dk"))
    return sonuc


def uyku_yazi(dk):
    return "%ds %ddk" % (dk // 60, dk % 60) if dk is not None else "—"


def gunluk(gun=7, simdi=None):
    """Son ``gun`` günün özeti: [{gun, adim(en yüksek), nabiz(ort), uyku(top)}]"""
    simdi = simdi or datetime.now()
    bas = (simdi - timedelta(days=gun - 1)).strftime("%Y-%m-%d")
    satirlar = veritabani.sorgu(
        "SELECT substr(zaman,1,10) AS g, "
        "MAX(CASE WHEN tur='adim' THEN deger END) AS adim, "
        "AVG(CASE WHEN tur='nabiz' THEN deger END) AS nabiz, "
        "SUM(CASE WHEN tur='uyku' THEN deger END) AS uyku "
        "FROM saglik_olcum WHERE zaman >= ? GROUP BY g ORDER BY g DESC",
        (bas,), True)
    return [{"gun": s["g"], "adim": s["adim"], "nabiz": s["nabiz"],
             "uyku": s["uyku"]} for s in satirlar]
