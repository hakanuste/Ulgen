"""Ajan kaydı: her ajanın durumunu, son çalışmasını ve sonucunu tutar.

Ajan nesnelerinin yöntemleri ``sar`` ile sarılır; böylece sohbetten, araçtan
ya da Ajanlar sekmesinden yapılan her çalıştırma aynı kayda düşer.
"""
import threading
import time

_KILIT = threading.Lock()
_DURUM = {}
KATALOG = {
    "arastirma": {"ad": "Araştırma Ajanı", "ne": "Web'de arar, sayfaları okur, özetler.",
                  "girdi": "Aranacak konu"},
    "saglik": {"ad": "Sağlık Ajanı", "girdi": "",
               "ne": "Dışa aktarılmış sağlık verisini özetler (tıbbi öneri vermez)."},
    "dosya": {"ad": "Dosya Ajanı", "ne": "Klasörlerde dosya arar, en yenileri bulur, özetler.",
              "girdi": "Aranacak sözcük (boş bırakılabilir)"},
    "sabah": {"ad": "Sabah Özeti", "ne": "Haber ve sağlık içeren sabah raporunu hazırlar.",
              "girdi": ""},
}


def _bos(kimlik):
    return {"id": kimlik, "durum": "bosta", "son_calisma": None, "sure_sn": None,
            "ozet": "", "hata": "", "sayac": 0}


def _kayit(kimlik):
    return _DURUM.setdefault(kimlik, _bos(kimlik))


def _kisalt(deger, sinir=700):
    metin = deger if isinstance(deger, str) else str(deger)
    metin = " ".join(metin.split())
    return metin if len(metin) <= sinir else metin[:sinir - 1] + "…"


def sar(kimlik, islev):
    """``islev``i çalışma durumunu kaydeden bir sargıyla değiştirir."""
    def sarili(*args, **kw):
        t0 = time.time()
        with _KILIT:
            k = _kayit(kimlik)
            k["durum"] = "calisiyor"
            k["hata"] = ""
        try:
            sonuc = islev(*args, **kw)
        except BaseException as hata:       # Iptal dahil; kayıt tutulur, hata yeniden fırlatılır
            with _KILIT:
                k = _kayit(kimlik)
                k.update(durum="hata", son_calisma=time.strftime("%Y-%m-%d %H:%M:%S"),
                         sure_sn=round(time.time() - t0, 1), hata=_kisalt(repr(hata), 200))
                k["sayac"] += 1
            raise
        with _KILIT:
            k = _kayit(kimlik)
            k.update(durum="bosta", son_calisma=time.strftime("%Y-%m-%d %H:%M:%S"),
                     sure_sn=round(time.time() - t0, 1), ozet=_kisalt(sonuc), hata="")
            k["sayac"] += 1
        return sonuc
    sarili.__wrapped__ = islev
    return sarili


def liste():
    with _KILIT:
        return [dict(KATALOG[k], **_kayit(k)) for k in KATALOG]


def sifirla():
    with _KILIT:
        _DURUM.clear()
