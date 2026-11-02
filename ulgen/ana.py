"""Komut satırı giriş noktası.

Kullanım:
  python -m ulgen                 web sunucusunu başlatır (varsayılan)
  python -m ulgen --terminal      terminalde yazışma
  python -m ulgen --ses           mikrofonla 'Ülgen' diyerek konuşma
  python -m ulgen --sabah         sabah raporunu yazdırır
  python -m ulgen --modeller      Gemini'de kullanılabilir modelleri listeler
  python -m ulgen --anahtar       iPhone için bağlantı anahtarını yazdırır
"""

import sys

from . import __surum__, ayar, sunucu
from .beyin import BeyinHatasi, GeminiBeyin
from .cekirdek import Ulgen


def terminal(ulgen):
    print("Ülgen %s. Çıkmak için 'çık' yazın." % __surum__)
    while True:
        try:
            metin = input("Siz: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if metin.lower() in ("çık", "cik", "exit", "quit"):
            return
        for b in ulgen.bildirimler(0)[-3:]:
            print("[bildirim]", b["metin"])
        print("Ülgen:", ulgen.sohbet_isle(metin)["yanit"])


def ses_kipi(ulgen):
    from .ses import Dinleyici, Konusmaci
    if not Dinleyici.kullanilabilir_mi():
        print("Ses için: pip install -r requirements-ses.txt "
              "(PyAudio için Mac'te önce 'brew install portaudio').")
        return 1
    ulgen.arka_plani_baslat()
    Dinleyici().dinle(lambda m: ulgen.sohbet_isle(m)["yanit"], Konusmaci())
    return 0


def modelleri_goster():
    anahtar = ayar.yukle().get("gemini_anahtar")
    if not anahtar:
        print("ayar.json içinde gemini_anahtar yok.")
        return 1
    try:
        for ad in GeminiBeyin(anahtar, "").modelleri_listele():
            print(ad)
    except BeyinHatasi as hata:
        print("Hata:", hata)
        return 1
    return 0


def sunucuyu_calistir(ulgen):
    ulgen.arka_plani_baslat()
    try:
        http = sunucu.baslat(ulgen)
    except OSError:
        print("Port %d dolu. Ülgen zaten çalışıyor olabilir." % ayar.PORT,
              flush=True)
        return 1
    print("Ülgen çalışıyor: http://127.0.0.1:%d" % ayar.PORT, flush=True)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--anahtar" in argv:
        print(ayar.anahtar_al())
        return 0
    if "--modeller" in argv:
        return modelleri_goster()
    ulgen = Ulgen()
    if "--terminal" in argv:
        terminal(ulgen)
        return 0
    if "--ses" in argv:
        return ses_kipi(ulgen)
    if "--sabah" in argv:
        print(ulgen.sabah.hazirla())
        return 0
    return sunucuyu_calistir(ulgen)
