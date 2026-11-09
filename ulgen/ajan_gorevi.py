"""Ajan görev penceresi: görev arka planda yürür, sonuç sohbet sayfasında yayınlanır."""

import threading

from . import ajan_kayit, uzmanlar, uzun_arastirma

AZAMI_UZMAN = 4000
AZAMI_SONUC = 12000
_KILIT = threading.Lock()


def dogrula(ajan, gorev):
    """-> (ajan adı, görev) ; hata varsa (hata iletisi, '')."""
    gorev = str(gorev or "").strip()
    ad = str(ajan or "").strip()
    if ad.lower() == "arastirma":
        ad = "arastirma"
        sinir = uzun_arastirma.AZAMI_GOREV
    else:
        ad = uzmanlar._uzman_adi(ad)
        if not ad:
            return "Bilinmeyen ajan", ""
        sinir = AZAMI_UZMAN
    if not gorev:
        return "Görev boş", ""
    return ad, gorev[:sinir]


def calistir(ulgen, ad, gorev):
    """Görevi eşzamanlı yürütür, sonucu sohbete yazar ve bildirir."""
    etiket = "Araştırma ajanı" if ad == "arastirma" else ad
    try:
        if ad == "arastirma":
            sonuc = ulgen.arastirma.arastir(gorev)
            ulgen._kaydet("kullanici", "[Ajan görevi: %s] %s"
                          % (etiket, gorev[:300]))
            ulgen._kaydet("asistan", sonuc[:AZAMI_SONUC])
        else:
            is_ = ajan_kayit.sar(uzmanlar.kimlik(ad), lambda g: ulgen.sohbet_isle(
                "%s: %s" % (ad, g))["yanit"])
            sonuc = is_(gorev)
    except BaseException as hata:       # iptal dahil; kullanıcı bilsin
        sonuc = "Görev tamamlanamadı: %s" % str(hata)[:200]
    ulgen.bildir("🤖 %s – görev sonucu\n\n%s" % (etiket, str(sonuc)[:AZAMI_SONUC]),
                 {"tur": "ajan_sonuc", "ajan": ad})


def arka_planda(ulgen, ad, gorev):
    def kos():
        with _KILIT:                      # görevler sırayla
            calistir(ulgen, ad, gorev)
    t = threading.Thread(target=kos, daemon=True)
    t.start()
    return t
