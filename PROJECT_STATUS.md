# Ülgen — Gerçek Durum Tablosu (TEK KAYNAK)

Bu tablo tek doğru durumdur. CHANGELOG, TEST_REPORT ve ROADMAP buna uyar; çelişirse bu dosya geçerlidir.
Sürüm 2.5 · Otomatik test: 167 geçti (Linux benzetimi) · Gerçek cihaz testi: HİÇBİRİ yapılmadı.

Durum sözlüğü: **T** = Tamamlandı ve test edildi (otomatik, Linux) · **K** = Kodlandı, gerçek cihaz testi bekliyor ·
**Kı** = Kısmen · **G** = Geliştirilmedi · **E** = Teknik engel

| Aşama | Konu | Durum | Kanıt (otomatik) | Gerçek cihazda doğrulandı |
|---|---|---|---|---|
| 0 | Denetim, git, yedek, plan | T | AUDIT_REPORT | — |
| 1 | Güvenlik çekirdeği (AES-GCM, cihaz belirteci, izin listesi, ONAY, HTTPS, hız sınırı) | K | test_guvenlik, test_sunucu, test_sifreleme | Hayır (Anahtar Zinciri, TLS/iPhone) |
| 1b | Canlı veritabanı şifreleme (SQLCipher) + göç + yedek | K | test_db_sifreleme (11) | Hayır (Mac'te wheel çalışması) |
| 1c | Yerel erişim yetkisi (tek kullanımlık giriş, çerez) | K | test_yerel_yetki | Hayır (Launchpad akışı) |
| 2 | Çoklu ücretsiz yapay zekâ, kota, kuyruk (Gemini/Groq/Mistral/OpenRouter/NVIDIA/Ollama/llama.cpp) | K | test_saglayici | Hayır (gerçek hesaplar) |
| 3 | Hafıza, FTS5, SQLite bütünlük/yedek | T | test_hafiza, test_veritabani | — |
| 4 | Zamanlayıcı, doz bazlı ilaç takibi, görevler | K | test_ilac | Hayır (iPhone bildirimi) |
| 5 | iPhone arayüzü, Kod penceresi, Takvim (.ics) hatırlatma | K | test_kodpenceresi, test_takvim, Chromium | Hayır (Safari, Takvim alarmı) |
| 5b | Kurulum betiği: yedek, güvenli değişim, geri alma | K | Linux kuru çalıştırma + bozuk sürümle geri alma denendi | Hayır (macOS, launchd, osacompile) |
| 6 | Özel Kasa + Face ID (WebAuthn) + kurtarma | G | — | — |
| 7 | Çevrimdışı ses, sağlık köprüsü | G | — | — |
| 8 | Raporlar, 16 senaryolu bütünleşik test | G | — | — |
| — | Yerel iOS uygulaması | G (iOS sürümü bekleniyor) | — | — |

## Bilinen sınırlar
- Otomatik yedekler ana anahtarla şifrelidir; anahtar kaybolursa yalnız parolalı yedek (`--yedek-al`) kurtarır.
- SSD/APFS'te eski düz dosyanın sıfırlanması kalıntıyı kesin silmez; FileVault açık olmalı.
- Takvim alarmı yalnız çalar; "aldım" geri bildirimi yoktur.
- Kod penceresi sandbox değildir.
- Gerçek cihaz kontrol listesi: TEST_DEVICE.md ve `python -m ulgen --tani`.
