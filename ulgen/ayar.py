"""Ülgen ayarları.

Bu modül dosya yollarını, varsayılan ayarları ve ``ayar.json`` okuma/yazma
işlerini barındırır. Tüm veriler kullanıcının ev klasöründeki ``ÜlgenVeri``
dizininde tutulur; kullanıcı açıkça bulut beynini seçmedikçe cihazdan
dışarı çıkmaz.
"""

import copy
import json
import os

EV = os.path.expanduser("~")
KLASOR = os.path.join(EV, "ÜlgenVeri")
AYAR_DOSYASI = os.path.join(KLASOR, "ayar.json")
ANAHTAR_DOSYASI = os.path.join(KLASOR, "anahtar.txt")
VERI_TABANI = os.path.join(KLASOR, "veri.db")
HAFIZA_DOSYASI = os.path.join(KLASOR, "memory.json")
HASSAS_DOSYASI = os.path.join(KLASOR, "memory_hassas.json")
PORT = 8765

# Varsayılan ayarlar. ayar.json içindeki değerler bunların üzerine yazılır.
VARSAYILAN = {
    # Beyin seçimi: "yerel" (varsayılan, sabit), "otomatik" (önce yerel,
    # olmazsa bulut), "bulut". Bulut yalnız kullanıcı açıkça seçerse kullanılır.
    "beyin": "yerel",
    # Yerel beyin türü: "otomatik", "ollama" ya da "llamacpp"
    "yerel_tur": "otomatik",
    "ollama_adres": "http://127.0.0.1:11434",
    "ollama_model": "llama3.2:3b",
    "llamacpp_adres": "http://127.0.0.1:8080",
    # Google AI Studio'dan alınan ücretsiz anahtar (isteğe bağlı)
    "gemini_anahtar": "",
    "gemini_model": "gemini-3.5-flash-lite",
    # Ücretsiz bulut sağlayıcıları (modeller --modeller ile listelenir)
    "groq_model": "llama-3.3-70b-versatile",
    "mistral_model": "mistral-small-latest",
    "openrouter_model": "openrouter/free",     # yalnızca ":free" kabul edilir
    # NVIDIA Build (build.nvidia.com) ücretsiz deneme uç noktaları. Model
    # adları sürümle değişir: python -m ulgen --modeller nvidia
    "nvidia_model": "meta/llama-3.3-70b-instruct",
    "bulut_sirasi": ["gemini", "nvidia", "groq", "mistral", "openrouter"],
    # Arayüzden kapatılan beyinler (örn. ["gemini"]); kapalı beyin hiç denenmez.
    "kapali_beyinler": [],
    # Mac Takvim/Hatırlatıcılar → Ülgen eşitlemesi ve Ülgen → Mac bildirimi
    # iPhone takvim aktarımı: olay saatleri bu dilimde yazılır (cihazın yaz
    # saati kuralına bağlı kalmaz). Boş = "yüzen" (cihazın saat dilimi).
    "takvim_saat_dilimi": "Europe/Istanbul",
    "mac_senk": True,
    "mac_senk_dk": 30,
    "mac_bildirim": True,
    # Mac'te hap/ilaç ve hatırlatmaları sesli okur
    "hatirlatma_sesi": True,
    # Obsidian'a yazma: yalnız kasadaki bu alt klasöre, yeni not olarak; kullanıcının
    # kendi notlarının üzerine yazılmaz, hiçbir şey silinmez.
    "obsidyen_yazma": True,
    "obsidyen_yazma_klasoru": "Ülgen",
    "ocr_dil": "tur+eng",          # tesseract dilleri
    "ocr_dpi": 250,                # taranmış sayfa çözünürlüğü (yüksek = yavaş, doğru)
    "kota_sinirlari": {},          # örn. {"groq": {"rpm": 20}} belgeden düzeltme
    "kuyruk_omru_saat": 24,
    # Ücretli servise geçiş KODDA kapalıdır; böyle bir ayar yoktur.
    # Ücretsiz Gemini katmanında gönderilen metinler Google tarafından
    # ürün geliştirmede kullanılabilir. Bu yüzden hafıza, sağlık verisi ve
    # kasa notları varsayılan olarak buluta GİTMEZ.
    "bulut_kisisel_veri": False,
    # Ekran çözümleme için ekran görüntüsünü Gemini'ye göndermeye izin
    "ekran_buluta_gonder": False,
    # Ağ: Mac'te http://127.0.0.1:8765, iPhone'da ZeroTier üzerinden HTTPS
    "https_port": 8443,
    "ca_port": 8766,
    "dinleme_adresleri": [],       # boşsa ZeroTier (zt*) adresleri bulunur
    "izinli_hostlar": [],          # IP dışında kabul edilen adlar
    # Konuşma
    "ses": "Yelda",
    "tts_motor": "otomatik",
    "uyandirma_sozcukleri": ["ülgen", "ulgen", "ülgün", "ulgun"],
    # Dosya ve veri klasörleri
    "kasa": "",                    # boşsa Obsidian kasası kendiliğinden aranır
    "elevenlabs_ses_kimligi": "J17lijyP1BHYcM7ld0Rg",  # "dede korkut" (Voices > Copy Voice ID)
    # Kendini güncelleme: "kullanici/depo" (GitHub); özel depo için "github" anahtarı
    # Kılavuzlar: boşsa Belgeler/Masaüstü'nde "klavuz" adlı klasör aranır
    "kilavuz_klasoru": "",
    "kilavuz_otomatik": True,        # yeni PDF'ler 10 dakikada bir Obsidian'a aktarılır
    "guncelleme_depo": "hakanuste/Ulgen",
    "guncelleme_dal": "main",
    "elevenlabs_bulut_ses": False,  # True: yanıt metinleri ElevenLabs'e gider (isteğe bağlı)
    "elevenlabs_model": "eleven_flash_v2_5",
    "elevenlabs_kararlilik": 0.66,
    "elevenlabs_hiz": 1.15,
    "elevenlabs_aylik_sinir": 8000,  # ücretsiz katman 10000 karakter
    "izinli_klasorler": [
        "~/Documents/Obsidyen",
        "~/Documents/Ülgen Genel Asistan",
        "~/ÜlgenVeri/dosyalar",
    ],
    "saglik_klasoru": "~/ÜlgenVeri/saglik",
    # Sabah özeti
    "sabah_ozeti_dakika": 10,
    "rss": [
        {"ad": "AA Güncel", "bolum": "Türkiye",
         "adres": "https://www.aa.com.tr/tr/rss/default?cat=guncel"},
        {"ad": "AA Dünya", "bolum": "Dünya",
         "adres": "https://www.aa.com.tr/tr/rss/default?cat=dunya"},
        {"ad": "AA Ekonomi", "bolum": "Ekonomi",
         "adres": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"},
        {"ad": "BBC Türkçe", "bolum": "Dünya",
         "adres": "https://feeds.bbci.co.uk/turkce/rss.xml"},
        {"ad": "DW Türkçe", "bolum": "Dünya",
         "adres": "https://rss.dw.com/rdf/rss-tur-all"},
    ],
}

# ayar.json ilk kez yazılırken kullanılan sade şablon
SABLON = {
    "beyin": "yerel",
    "beyin_sabit": True,
    "yerel_tur": "otomatik",
    "ollama_model": "llama3.2:3b",
    "llamacpp_adres": "http://127.0.0.1:8080",
    "gemini_anahtar": "",
    "gemini_model": "gemini-3.5-flash-lite",
    "bulut_kisisel_veri": False,
    "ses": "Yelda",
    "kasa": "",                    # boşsa Obsidian kasası kendiliğinden aranır
    "sabah_ozeti_dakika": 10,
    "hava_acik": True,
    "rapor_acik": True,
    "hava_konum": {"ad": "Aydın", "enlem": 37.85, "boylam": 27.84},
}


# Sır adı -> ayar alanı (Anahtar Zinciri'nden okunur)
SIRLAR = {"gemini": "gemini_anahtar", "groq": "groq_anahtar",
          "nvidia": "nvidia_anahtar",
          "mistral": "mistral_anahtar", "openrouter": "openrouter_anahtar",
          "elevenlabs": "elevenlabs_anahtar",
          "github": "github_anahtar"}


def yol_ac(yol):
    """``~`` işaretini ev klasörüne çevirip mutlak yol döndürür."""
    return os.path.expanduser(yol)


def klasor_hazirla():
    """ÜlgenVeri klasörünü (yalnızca kullanıcıya açık) oluşturur."""
    os.makedirs(KLASOR, mode=0o700, exist_ok=True)


def yukle():
    """Varsayılanları ayar.json ile birleştirip ayar sözlüğünü döndürür."""
    sonuc = copy.deepcopy(VARSAYILAN)
    try:
        with open(AYAR_DOSYASI, "r", encoding="utf-8") as dosya:
            kullanici = json.load(dosya)
        if isinstance(kullanici, dict):
            sonuc.update(kullanici)
    except (OSError, ValueError):
        pass
    # API anahtarları ayar.json yerine Anahtar Zinciri'nde tutulur
    from . import gizli
    for ad, alan in SIRLAR.items():
        if not sonuc.get(alan):
            sonuc[alan] = gizli.sir_oku(ad)
    return sonuc


def guncelle(alan, deger):
    """ayar.json içinde tek bir alanı yazar (diğer alanlara dokunmaz)."""
    klasor_hazirla()
    try:
        with open(AYAR_DOSYASI, "r", encoding="utf-8") as dosya:
            mevcut = json.load(dosya)
        if not isinstance(mevcut, dict):
            mevcut = {}
    except (OSError, ValueError):
        mevcut = {}
    mevcut[alan] = deger
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as dosya:
        json.dump(mevcut, dosya, ensure_ascii=False, indent=2)
    os.chmod(AYAR_DOSYASI, 0o600)


def beyni_yerele_sabitle():
    """Eski kurulumlarda bir kez: beyin seçimini yerele sabitler.

    Kullanıcı sonradan arayüzden başka bir kip seçerse ``beyin_sabit``
    işareti kalır ve bir daha dokunulmaz."""
    try:
        with open(AYAR_DOSYASI, "r", encoding="utf-8") as dosya:
            mevcut = json.load(dosya)
    except (OSError, ValueError):
        return False
    if not isinstance(mevcut, dict) or mevcut.get("beyin_sabit"):
        return False
    mevcut["beyin"] = "yerel"
    mevcut["beyin_sabit"] = True
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as dosya:
        json.dump(mevcut, dosya, ensure_ascii=False, indent=2)
    os.chmod(AYAR_DOSYASI, 0o600)
    return True


def sablon_olustur():
    """ayar.json yoksa sade bir şablonla oluşturur."""
    klasor_hazirla()
    if os.path.exists(AYAR_DOSYASI):
        beyni_yerele_sabitle()
        return
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as dosya:
        json.dump(SABLON, dosya, ensure_ascii=False, indent=2)
    os.chmod(AYAR_DOSYASI, 0o600)
