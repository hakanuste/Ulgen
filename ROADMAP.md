> Güncel durum için PROJECT_STATUS.md tek kaynaktır; bu dosya yalnız plandır.

# ÜLGEN – TEK ANA GELİŞTİRME PLANI

Ana şartname + Ek şartname (2026-11-02) birleştirildi; tekrar eden maddeler tek satırda.
Kural: önce güvenlik ve veri bütünlüğü; her aşama testi geçmeden sonraki başlamaz; yalnızca arayüzü yapılmış özellik "tamamlandı" sayılmaz.

## Durum sözlüğü
- **T** Tamamlandı ve test edildi (simülasyon/Linux testi; gerçek cihaz gerektirmeyen)
- **C** Kodlandı, gerçek cihaz testi bekliyor
- **K** Kısmen tamamlandı
- **G** Geliştirilmedi
- **E** Teknik engel var

## Özellik matrisi (gerçek kod incelenerek doğrulandı, Aşama 1 sonu)

| Özellik | Durum | Aşama | Doğrulanan gerçek durum / not |
|---|---|---|---|
| Güvenlik çekirdeği (izin listesi, HTTPS, cihaz belirteci, AES-256-GCM, şifreli yedek) | **T** (Mac/iPhone adımları **C**) | 1 ✔ | 49 test |
| Mac'te otomatik başlama | **C** | 1 ✔ | launchd LaunchAgent; Mac'te denenmedi. Oturum açılınca başlar, öncesinde değil |
| iPhone–Mac güvenli eşleştirme, yetkisiz cihaz engeli, uzaktan erişim (ZeroTier) | **T** + **C** | 1 ✔ | Sunucu tarafı testli; iPhone sertifika yükleme denenmedi |
| Bağlantı kopunca yeniden bağlanma (istemci) | **G** | 5 | arayüzde yok |
| Ortak hafıza (tek kaynak = Mac; iPhone ayrı veri tutmaz) | **K** | 2 | memory.json var; şema yok. "Senkronizasyon çakışması" iPhone yerel kopya tutarsa doğar → tek kaynak kararıyla çakışma yok; çevrimdışı iPhone kopyası native uygulamaya bağlı |
| Sohbet/proje geçmişi, geçmişte arama | **K** | 2 | sohbet tablosu var, arama yok |
| Gelişmiş hafıza: tür, proje, kaynak (kullanıcı/çıkarım ayrımı), güven, güncelleme/düzeltme, eskimiş işareti, hassas ayrı | **G** | 2 | |
| Veritabanı: WAL, sürümlü göç, transaction, bütünlük, zamanlı yedek | **G** | 2 | yalnızca elle şifreli yedek (**T**) |
| Sağlayıcılar: Ollama, llama.cpp, Gemini | **T** (sahte sunucuyla) | – | gerçek bağlantı **C** |
| Sağlayıcılar: Groq, Mistral, OpenRouter(:free) + ortak yönetici, göreve göre model | **G** | 3 | |
| Kota/kullanım kaydı (RPM, TPM, RPD, token, kalan, yenilenme, gecikme, hata oranı, maliyet=0), gerçek/tahmini ayrımı | **G** | 3 | |
| Kota dolunca kalıcı kuyruk, yerel modele geçiş, ücretli geçiş yok | **G** | 3 | şu an 429 → hata mesajı |
| AI çökse de zamanlayıcı/ilaç/bildirim sürer | **K** | 3–4 | zamanlayıcı modelden bağımsız çalışıyor (mimari olarak doğru), testi yok |
| Görev/rutin/randevu motoru (günlük, haftalık, kalıcı) | **K** | 4 | tek seferlik hatırlatıcı var; rutin/randevu/görev yok |
| **İlaç takibi: ayrı ilaç/doz kimliği, ayrı onay** | **G** | 4 | **DÜZELTME:** "mevcut ayrı ilaç onay arayüzü" bu kod tabanında YOK (arayüzde "ilaç" geçmiyor, ilaç tablosu yok). Mevcut `tamam` backend'de tüm kalıcı hatırlatmaları toplu onaylıyor — arayüz de ayrı bir onay sunmuyor. Başka bir yerde ayrı arayüz varsa o bu pakette değildir |
| Bildirim yanıtları: Aldım/Almadım/Ertele/Tamamlandı/Atlandı, yeniden hatırlatma aralığı, geçmiş, tekrar işleme engeli, sessiz kaybolmama | **G** | 4 | 24 tekrar sonrası sessiz vazgeçme hatası var (V4) |
| İlaç dozunu Ülgen değiştirmez (model araçlarına yazma yok) | **G** | 4 | tasarım kuralı, testle doğrulanacak |
| Mac kapalıyken iPhone hatırlatması | **E** | 4/5 | Aşağıdaki "Teknik engeller" |
| iPhone arayüzü (sekmeler, görevler, ilaçlar, onaylar, sistem) | **K** | 5 | yalnızca sohbet + yaklaşan liste |
| Sistem yönetim paneli (CPU/RAM/disk, sunucu, DB, modeller, kota, kuyruk, zamanlayıcı, bildirim, hata, günlük) | **G** | 5 | `/durum` yalnızca beyin adı |
| Özel Kasa (AES-256-GCM, dosya/not, erişim kaydı, iptal, kurtarma) | **G** | 6 | şifreleme altyapısı var (**T**), Kasa yok |
| Face ID/passkey ile tek kullanımlık, süreli, kapsamlı onay; AI kasayı açamaz | **E** (PWA) / **G** | 6 | HTTPS altyapısı var; gerçek Face ID için PWA'da WebAuthn ya da native uygulama; iPhone'da doğrulanamaz |
| Çevrimdışı STT/TTS (Mac), uyandırma, mikrofon yönetimi | **K** | 7 | Mac TTS `say` çevrimdışı; STT şu an Google (internetli) — **çevrimdışı değil**. Çevrimdışı STT yok |
| iPhone'da çevrimdışı ses | **E** | 7 | Safari'nin tanıma servisi çevrimdışı güvenilir değil; native uygulama gerekir |
| Sabah raporu (haber+sağlık) | **K** | 8 | var; görev/ilaç/randevu birleşik rapor yok |
| Akşam ve haftalık rapor, eksik veri belirtme | **G** | 8 | |
| Sağlık: CSV/JSON/Apple Health export.xml okuma, içgörü | **K** | 7 | **elle dışa aktarma ile** çalışıyor (**T**); otomatik aktarım, kaynak kaydı, tekilleştirme, gerçek/tahmini ayrımı, aylık karşılaştırma yok |
| F800 saat / Joeme Fit entegrasyonu | **E** | 7 | veri yolu doğrulanmadı (aşağıda) |
| Apple Health otomatik aktarım | **E** | 7 | web'den okunamaz; native uygulama ya da Kestirmeler köprüsü gerekir |
| Dosya/PDF ajanı, araştırma, ekran çözümleme (izinli), müzik | **T** (Mac kısmı **C**) | – | |

## Aşamalar (birleşik)

| Aşama | Kapsam | Çıkış ölçütü |
|---|---|---|
| 0 ✔ | Denetim | AUDIT_REPORT.md |
| 1 ✔ | Kritik güvenlik | 49 test |
| **2** | Veritabanı bütünlüğü + gelişmiş hafıza + geçmişte arama + zamanlı yedek + `veri.db` bütünlük/otomatik kurtarma | göç, geri yükleme, kaynak/güven, düzeltme, FTS arama, hassas ayrı depolama testleri |
| **3** | Sağlayıcı yöneticisi + kota/kullanım kaydı + kalıcı kuyruk + gizlilik filtresi + yerel yedek model | sahte sağlayıcılarla kota dolması, kuyruk kalıcılığı (yeniden başlatma), ücretli yolun kodla kapalı olması, hassas veri sızmaması |
| **4** | Görev/rutin/randevu motoru + **doz başına ilaç takibi** + yanıtlar (Aldım/Almadım/Ertele/Tamamlandı/Atlandı) + yeniden hatırlatma + geçmiş | ilaçların ayrı onayı, yeniden başlatmada geri yükleme, çift işleme engeli, AI kapalıyken sürmesi |
| **5** | iPhone arayüzü (sekmeler, onay ekranı, yeniden bağlanma) + sistem yönetim paneli + bildirim durumu | Playwright (iPhone boyutu) testleri; push/bildirim **gerçek cihaz** |
| **6** | Özel Kasa + işlem bazlı tek kullanımlık onay (WebAuthn sunucu tarafı) + erişim kaydı + iptal + kurtarma | AI-kasa kapalı testi, kapsam/süre/tek kullanım testleri; Face ID **gerçek cihaz** |
| **7** | Çevrimdışı STT (Mac) ölçümlü, TTS, sağlık veri köprüsü (tekilleştirme, kaynak, gerçek/tahmini, karşılaştırma) | birim testleri; STT doğruluğu ve CPU/RAM **Mac'te ölçülür**; saat/Apple Health **gerçek cihaz** |
| **8** | Birleşik sabah/akşam/haftalık rapor + bütünleşik testler (16 senaryo) + güvenlik denetimi | TEST_REPORT'ta simülasyon ve gerçek cihaz ayrı |

10 günlük MVP = 2, 3 (yerel + Gemini + kuyruk), 4, 5 (çekirdek). Kasa, ses, sağlık köprüsü ve birleşik raporlar MVP dışı; ancak MVP'nin "çalışıyor" sayılması için Mac/iPhone üzerinde sizin doğrulamanız gerekir.

## Teknik engeller (doğrulanmış mantık / doğrulanmamış olanlar ayrı)

1. **Mac uyurken/kapalıyken sunucu kodu çalışmaz** (fiziksel). iPhone'un kendi tarafında planlı yerel bildirim gerekir. Safari/PWA **yerel zamanlanmış bildirim kuramaz**; web push ise gönderen sunucunun (Mac) açık olmasını ister. Seçenekler:
   - **A.** Mac'ten iPhone'a Apple Hatırlatıcılar/Takvim üzerinden alarm (iCloud ile eşleşir). Kapalı Mac'te çalışır. Bedeli: ilaç hatırlatması Apple iCloud'a gider; başlıkta ilaç adı yerine genel ifade ("İlaç 1 – 08:00") kullanılabilir. Yanıtlar (Aldım vb.) Ülgen'e ancak Mac açılınca/iPhone'dan girilince işlenir.
   - **B.** `pmset repeat wakeorpoweron` ile Mac'i doz saatlerinden önce uyandırmak (sınırlı, pil/ısı; kapak kapalıyken güvenilirliği **doğrulanmadı**).
   - **C.** Native iOS uygulaması (yerel bildirim + Face ID + HealthKit). Kod yazılabilir ama bu ortamda **derlenemez/denenemez**; Mac'inizdeki Xcode sürümü macOS 12.7.6 ile sınırlı ve iPhone'unuzun iOS sürümüyle uyumu **doğrulanmadı**.
2. **F800/Joeme Fit**: Joeme Fit'in Apple Sağlık'a yazıp yazmadığı **doğrulanamadı** (kaynak bulunamadı). Doğrulama yolu: iPhone → Sağlık → Paylaşım/Veri Kaynakları'nda Joeme Fit var mı; ya da Joeme Fit'ten dışa aktarma menüsü. Doğrulanmadan entegrasyon "var" sayılmayacak.
3. **Apple Health otomatik aktarım**: web'den okunamaz. Olası: Kestirmeler (Shortcuts) kişisel otomasyonu → HTTPS ile Ülgen'e gönderme (**doğrulanmadı**) ya da native uygulama (C).
4. **Çevrimdışı STT**: Mac'te whisper.cpp/Vosk adayı; Türkçe doğruluk ve i5-5350U/8 GB hız **ölçülmeden** vaat edilmez.
5. **Face ID**: PWA'da WebAuthn ile mümkün görünür (HTTPS var) ama iPhone'da **denenmeden** tamamlandı denmez.
6. **Hassas veri bulutta olmaz** ilkesi ile A seçeneği (iCloud) çelişir; karar sizindir.

## Bekleyen kararlar
1. Mac kapalıyken kritik hatırlatma için ara çözüm: **A** (genel başlıkla Apple Hatırlatıcılar), **B**, ya da yalnızca **C**'yi bekle?
2. Native iOS uygulaması (C) kaynak kodunu yazayım mı? (Xcode'da sizin derlemeniz gerekir; test edilmemiş kod olarak etiketlenir.)

## Güncelleme: Aşama 2 bitti (T = tamamlandı ve test edildi, benzetim). Sıradaki: Aşama 3 (sağlayıcı yöneticisi, kota, kalıcı kuyruk).

## Güncelleme: Aşama 3 kodlandı ve benzetimde test edildi. Sıradaki: Aşama 4 (görev motoru, ilaç dozu başına onay).

## Güncelleme: Aşama 4 bitti (benzetimde). Sıradaki: Aşama 5 (iPhone arayüzü sekmeleri, ilaç/görev/kota panelleri, yeniden bağlanma).

## Güncelleme: Aşama 5 bitti (benzetimde). Sıradaki: Aşama 6 (Özel Kasa + Face ID/WebAuthn onayı).

## Güncelleme: Mac kapalıyken hatırlatma için iPhone takvim aktarımı (kullanıcı: "iPhone'da olmalı") kodlandı; cihaz testi bekliyor. Yerel iOS uygulaması için iPhone iOS sürümü gerekli.

## Aşama 6 tasarım notu: parola unutulursa iPhone Face ID ile kurtarma
- Veritabanı anahtarı bir parola değil, Mac'teki ana anahtardan türer; "unutulacak parola" yalnız parolalı yedekte vardır.
- Plan: Face ID (WebAuthn, ağda tek kullanımlık, kapsamlı onay) ile (a) yedek parolasını sıfırlama ve (b) taze parolalı yedek çıkarma yetkisi.
- Mac diski/anahtarı tümden kaybolursa Face ID tek başına yetmez: kurtarma anahtarı iPhone'da (WebAuthn PRF, iOS 18+ gerekir) saklanmalıdır. iOS sürümü öğrenilince karar verilecek.
