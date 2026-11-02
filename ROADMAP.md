# Yol Haritası

Tamamlanan: Aşama 0 (denetim), Aşama 1 (kritik güvenlik).

| Aşama | Kapsam | Durum |
|-------|--------|-------|
| 2 | Veritabanı (WAL, sürümlü göç, transaction, bütünlük, zamanlı yedek) + hafıza şeması (tür, proje, kaynak, güven, güncelleme) | sırada |
| 3 | Sağlayıcı altyapısı (Ollama, llama.cpp, Gemini, Groq, Mistral, OpenRouter `:free`), kota izleme, kalıcı kuyruk | |
| 4 | Görev/rutin motoru, ilaç/doz takibi (her doz ayrı kimlik ve onay) | |
| 5 | iPhone arayüzü (sekmeler, PWA, web push) | |
| 6 | Özel Kasa (AES-256-GCM) + WebAuthn/Face ID onayı | |
| 7 | Çevrimdışı STT, TTS, otomasyon, sistem izleme | |
| 8 | Bütünleşik test, uzun süreli çalışma, güvenlik denetimi | |

MVP önceliği: 2 → 4 → 5 (çekirdek) → 3 (yerel + Gemini + kuyruk).

## Ek gereksinimler (2026-11-02) ve aşamalara dağılımı

| # | Gereksinim | Aşama | Not |
|---|-----------|-------|-----|
| 1 | Mac açılınca otomatik başlama | 2 | launchd oturum açılışında başlar; oturum açmadan önce başlamaz (bkz. kısıtlar) |
| 1 | Tek ortak hafıza (Mac+iPhone), evde yerel ağ / dışarıda internet | 2 | iPhone ayrı veri tutmaz, Mac'teki hafızaya ZeroTier ile bağlanır; "aynı hafıza" budur |
| 1 | Mac uyurken/kapalıyken kritik hatırlatma | 4 | **Mac'e bağımlı olamaz**; iPhone tarafı alarm katmanı gerekir (bkz. kısıtlar) |
| 2 | Aldım / Ertele / Alamadım, yanıt gelmezse yeniden hatırlat, kayıt, rapor, randevu+rutin | 4 | doz başına kimlik |
| 3 | F800 saat + Joeme Fit + Apple Health: adım, nabız, uyku, karşılaştırma, sabah/akşam özeti | 7 | veri yolu doğrulanmadan söz verilmez (bkz. kısıtlar) |
| 4 | Kota/maliyet paneli, kalan kota, yenilenme, ücretli kapalı, kota bitince yerel | 3 + 5 | |
| 5 | Groq, Mistral, OpenRouter `:free`, ortak yönetici, göreve göre model, kalıcı kuyruk | 3 | |
| 6 | Proje/geçmiş/karar hafızası, kaynak, güven, düzeltme, yedek | 2 | |
| 7 | Çevrimdışı Türkçe STT/TTS, uyandırma kelimesi, Mac+iPhone | 7 | iPhone mikrofonu HTTPS gerektirir (Aşama 1'de var) |
| 8 | Özel Kasa, passkey/Face ID, işlem bazlı yetki, erişim kaydı, güvenli kurtarma | 6 | |
| 9 | Sistem yönetim paneli | 5 | |
| 10 | Günlük/haftalık akıllı rapor (görev, kaçırılan, sağlık, proje) | 7 | Aşama 4 ve 7 verilerini birleştirir |

### Kısıtlar (kanıtlanmış olanlar ve doğrulanmamış olanlar)
- **Uyuyan/kapalı Mac'te hiçbir Ülgen kodu çalışmaz.** Bu fiziksel bir sınırdır. Çözüm adayları: (a) kritik hatırlatmaları iPhone'un kendi alarm sistemine (Apple Hatırlatıcılar/Takvim, iCloud ile eşleşir) yazmak; (b) `pmset repeat wakeorpoweron` ile Mac'i doz saatinden önce uyandırmak; (c) 7/24 açık küçük bir cihaz. Hiçbiri henüz uygulanmadı.
- "Mac açıldığında başlasın": launchd **LaunchAgent** kullanıcı oturumu açılınca başlar. Oturumdan önce başlatmak LaunchDaemon ve Anahtar Zinciri/otomatik oturum konularını değiştirir (güvenlik ödünü).
- iPhone'dan Apple Health verisine Ülgen doğrudan erişemez (yerel uygulama gerekir). Olası yol: iPhone Kestirmeleri (Shortcuts) kişisel otomasyonu ile veriyi Ülgen'e HTTPS ile göndermek. **Doğrulanmadı.**
- Joeme Fit'in Apple Sağlık'a yazıp yazmadığı **doğrulanamadı** (aramada mağaza kaydı bulundu, HealthKit desteği teyit edilemedi).
