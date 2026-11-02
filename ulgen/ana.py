"""Komut satırı giriş noktası.

Kullanım:
  python -m ulgen                 web sunucusunu başlatır (varsayılan)
  python -m ulgen --terminal      terminalde yazışma
  python -m ulgen --ses           mikrofonla 'Ülgen' diyerek konuşma
  python -m ulgen --sabah         sabah raporunu yazdırır
  python -m ulgen --ac             tarayıcıda yerel giriş (tek kullanımlık bağlantı)
  python -m ulgen --tani           Mac/iPhone cihaz denetimi raporu
  python -m ulgen --modeller [gemini|groq|mistral|openrouter]  modelleri listeler
  python -m ulgen --cihaz-ekle AD  yeni cihaz belirteci üretir (bir kez gösterilir)
  python -m ulgen --cihazlar       kayıtlı cihazları listeler
  python -m ulgen --cihaz-iptal N  cihazı iptal eder
  python -m ulgen --sir-kaydet AD  API anahtarını Anahtar Zinciri'ne yazar
                                   (gemini, groq, mistral, openrouter)
  python -m ulgen --yedek-al DOSYA        şifreli yedek alır
  python -m ulgen --yedek-yukle DOSYA     yedekten geri yükler
"""

import sys

from . import __surum__, ayar, cihazlar, gizli, sunucu, veritabani, yedek
from .beyin import BeyinHatasi, GeminiBeyin, OpenAIUyumluBeyin
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


def modelleri_goster(saglayici="gemini"):
    """Seçilen sağlayıcıda kullanılabilir (OpenRouter'da yalnızca ücretsiz)
    modelleri listeler."""
    a = ayar.yukle()
    anahtar = a.get(saglayici + "_anahtar")
    if not anahtar:
        print("%s anahtarı yok (--sir-kaydet %s)." % (saglayici, saglayici))
        return 1
    try:
        if saglayici == "gemini":
            beyin = GeminiBeyin(anahtar, "")
        elif saglayici in OpenAIUyumluBeyin.TABANLAR:
            beyin = OpenAIUyumluBeyin(saglayici, anahtar, "")
        else:
            print("Bilinmeyen sağlayıcı:", saglayici)
            return 1
        for ad in beyin.modelleri_listele():
            print(ad)
    except BeyinHatasi as hata:
        print("Hata:", hata)
        return 1
    return 0


def yerel_giris_ac(tarayici_ac):
    """Tek kullanımlık giriş bağlantısı üretir ve tarayıcıda açar."""
    veritabani.kur()
    adres = "http://127.0.0.1:%d/giris?t=%s" % (
        ayar.PORT, cihazlar.giris_anahtari_uret())
    if tarayici_ac:
        import webbrowser
        webbrowser.open(adres)
        print("Tarayıcıda açılıyor (bağlantı 60 sn geçerli, tek kullanımlık).")
    else:
        print(adres)
    return 0


def sunucuyu_calistir(ulgen):
    ulgen.arka_plani_baslat()
    dinleme = sunucu.Dinleme(ulgen)
    try:
        dinleme.yerel_baslat()
    except OSError:
        print("Port %d dolu. Ülgen zaten çalışıyor olabilir." % ayar.PORT,
              flush=True)
        return 1
    import threading
    threading.Thread(target=dinleme.dongu, daemon=True).start()
    print("Ülgen çalışıyor: http://127.0.0.1:%d" % ayar.PORT, flush=True)
    try:
        dinleme.servis()
    except KeyboardInterrupt:
        pass
    return 0


def _deger(argv, bayrak):
    i = argv.index(bayrak)
    return argv[i + 1] if i + 1 < len(argv) else ""


def _parola(yeni):
    import getpass
    ilk = getpass.getpass("Yedek parolası: ")
    if yeni and getpass.getpass("Parola (yeniden): ") != ilk:
        raise yedek.YedekHatasi("Parolalar eşleşmedi.")
    return ilk


def yonetim(argv):
    """Sunucu açmayan yönetim komutları. İşlenmediyse None döndürür."""
    if "--cihaz-ekle" in argv or "--anahtar" in argv:
        veritabani.kur()
        ad = _deger(argv, "--cihaz-ekle") if "--cihaz-ekle" in argv else ""
        kimlik, belirtec = cihazlar.olustur(ad or "iPhone")
        print("Cihaz #%d oluşturuldu. Belirteç (yalnızca şimdi gösterilir):"
              % kimlik)
        print(belirtec)
        return 0
    if "--cihazlar" in argv:
        veritabani.kur()
        for c in cihazlar.listele():
            print("#%d %s | oluşturma %s | son kullanım %s%s" % (
                c["id"], c["ad"], c["olusturma"], c["son_kullanim"] or "-",
                " | İPTAL" if c["iptal"] else ""))
        return 0
    if "--cihaz-iptal" in argv:
        veritabani.kur()
        print("İptal edildi." if cihazlar.iptal(_deger(argv, "--cihaz-iptal"))
              else "Cihaz bulunamadı.")
        return 0
    if "--ac" in argv or "--giris-adresi" in argv:
        return yerel_giris_ac("--ac" in argv)
    if "--takvim-deneme" in argv:
        from . import tani
        return tani.takvim_deneme()
    if "--tani" in argv:
        from . import tani
        return tani.calistir()
    if "--sir-kaydet" in argv:
        ad = _deger(argv, "--sir-kaydet")
        if ad not in ayar.SIRLAR:
            print("Ad şunlardan biri olmalı:", ", ".join(ayar.SIRLAR))
            return 1
        if sys.stdin.isatty():
            import getpass
            deger = getpass.getpass("%s anahtarı: " % ad)
        else:
            deger = sys.stdin.read()
        if not deger.strip():
            print("Boş anahtar kaydedilmedi.")
            return 1
        print("Kaydedildi (%s)." % gizli.sir_yaz(ad, deger.strip()))
        return 0
    try:
        if "--yedek-al" in argv:
            veritabani.kur()
            print("Yedek yazıldı:", yedek.al(_deger(argv, "--yedek-al"),
                                             _parola(True)))
            return 0
        if "--yedek-yukle" in argv:
            onceki = yedek.geri_yukle(_deger(argv, "--yedek-yukle"),
                                      _parola(False))
            print("Geri yüklendi. Önceki dosyalar şurada: %s" % onceki)
            return 0
    except yedek.YedekHatasi as hata:
        print("Hata:", hata)
        return 1
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    sonuc = yonetim(argv)
    if sonuc is not None:
        return sonuc
    if "--modeller" in argv:
        sira = argv.index("--modeller") + 1
        return modelleri_goster(argv[sira] if sira < len(argv) else "gemini")
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
