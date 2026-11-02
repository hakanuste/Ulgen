# Ülgen — Gerçek Durum Tablosu (TEK KAYNAK)

Bu tablo tek doğru durumdur. CHANGELOG, TEST_REPORT ve ROADMAP buna uyar; çelişirse bu dosya geçerlidir.
Sürüm 2.7 · Otomatik test: 245 geçti (Linux benzetimi) · Gerçek cihaz testi: HİÇBİRİ yapılmadı.

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
| 5c | Yeni arayüz teması (taslağa göre: sol menü, özet şeridi, sağ pano, telefonda alt çubuk) + Obsidian arama dizini (md+pdf) | K | test_obsidyen (4), Chromium ekran görüntüsü (tests/e2e_arayuz.py) | Hayır (iPhone Safari) |
| 6 | Özel Kasa (AES-256-GCM), Face ID/WebAuthn+PRF, tek kullanımlık kapsamlı onay, parola unutunca Face ID kurtarma, kurtarma kodu/paketi | K | test_ozelkasa (12) + Chromium sanal Face ID (tests/e2e_kasa.py) | Hayır (gerçek Face ID, sslip.io adı, iOS 27.2 PRF) |
| 5d | Resmî renk standardı (`--ulgen-*` değişkenleri, tek merkez) masaüstü + iPhone; yatay taşma denetimi (360/430/1672 px) | K | Chromium: renk kodları ve taşma ölçümü | Hayır (Safari, Dynamic Island) |
| 5e | SQLCipher zorunlu (yoksa Ülgen başlamaz), kurulum yedeği tutarlılığı (`--kurulum-yedegi`), CSP + çerez oturumu | K | test_db_sifreleme, test_csp, test_yerel_yetki | Hayır (Mac'te SQLCipher kurulumu) |
| 7a | Sağlık köprüsü: iPhone Kestirmeleri → `/saglik/veri` (adım, nabız, uyku); F800/Joeme Fit → Apple Sağlık → Kestirme | K | test_saglik_veri | Hayır (Kestirme, F800 eşleşmesi) |
| 7b | Çevrimdışı Türkçe ses tanıma (faster-whisper + ffmpeg, `/ses/yaz`, `--ses-modeli-indir`) | K | test_ses_cevrimdisi (sunucu yolu, sahte tanıma); gerçek model çalıştırılmadı | Hayır (model indirme, Mac hızı, iPhone kaydı) |
| 8a | Sabah / akşam / haftalık raporlar (yerel veriden; `rapor_saatleri`, `/raporlar`, sohbette "akşam raporu") | K | test_rapor (5) | Hayır (zamanında bildirim) |
| 2b | NVIDIA gerçek bağlantı denemesi: `python -m ulgen --dene nvidia` | K | test_rapor.DeneTesti (sahte yanıt) | **Hayır — kullanıcı çalıştırmalı** |
| 9a | Görev, randevu, rutin, hatırlatıcı: Ekle / Düzelt / Sil (arayüz formları + sohbet komutları, onaylı silme) | K | test_gorev_duzenle (15), Chromium (tests dışı e2e) | Hayır (Mac/iPhone Safari) |
| 9b | Yapay zekâ kipi varsayılan "yerel" (sabit); arayüzden onaylı değişim; eski kurulum bir kez yerele alınır | K | test_gorev_duzenle.BeyinKipiTesti | Hayır (Mac'te yerel model kurulu değil) |
| 9c | "API anahtarlarım": var/yok, ekle, değiştir, dene, sil (Anahtar Zinciri) | K | test_yz_anahtar (7), Chromium | Hayır (Mac Anahtar Zinciri) |
| 9d | Emekli model onarımı (HTTP 404/410: NVIDIA, Gemini) + tüm beyin hatalarını gösterme | K | test_model_emekli (5) | Hayır (gerçek hesaplar) |
| 9e | "dur"/Sus: konuşmayı ve sunucudaki sohbet/araştırma işini durdurma; uzun yanıtlar bulut sesiyle parça parça | K | test_iptal (3), Chromium | Hayır (gerçek ElevenLabs sesi, Safari sesi) |
| 9f | Launchpad yinelenen simge temizleme (`simge_temizle.sh`); Ses seçimi, kendi mp3'ler, bulut sesi, konuma göre hava, Obsidian otomatik bulma | K | test_ses_klip, test_hava, test_obsidyen; betik yalnız söz dizimi denendi | **Hayır** (Launchpad sorunu çözülmedi) |
| 8 | 16 senaryolu bütünleşik test | G | — | — |
| — | Yerel iOS uygulaması | G (iOS sürümü bekleniyor) | — | — |

## Bilinen sınırlar
- Face ID (WebAuthn) IP adresiyle çalışmaz; `<ip-tireli>.sslip.io` adı kullanılır (halka açık DNS gerekir, yalnız özel IP'ye çözülür). Gerçek iPhone'da denenmedi; olmazsa parola/kurtarma kodu yolu çalışır.
- Kasa öğe adları şifresiz saklanır.
- `/kasa/yedek` (Face ID ile yedek) otomatik testte yok.
- Mac tümden giderse: kurtarma.paket + kod gerekir; ikisi de Mac dışında saklanmalı.
- Otomatik yedekler ana anahtarla şifrelidir; anahtar kaybolursa yalnız parolalı yedek (`--yedek-al`) kurtarır.
- SSD/APFS'te eski düz dosyanın sıfırlanması kalıntıyı kesin silmez; FileVault açık olmalı.
- Takvim alarmı yalnız çalar; "aldım" geri bildirimi yoktur.
- Kod penceresi sandbox değildir.
- Gerçek cihaz kontrol listesi: TEST_DEVICE.md ve `python -m ulgen --tani`.
