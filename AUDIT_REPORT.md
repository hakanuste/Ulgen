# ÜLGEN – DENETİM RAPORU (Aşama 0)

Tarih: 2026-11-02 · Sürüm: 2.0 (git etiketi `temel-2.0`) · Kod değişikliği: yok (yalnızca git deposu ve yedek oluşturuldu)

## 1. Yöntem

- Kodun tamamı (≈3.200 satır, 17 modül) yeniden okundu.
- Güvenlik savlarının her biri çalışan bir deneme ile **kanıtlandı** (aşağıda "Kanıt" sütunu). Kanıtsız madde "varsayım" diye işaretlendi.
- Yedek: `Ulgen_2.0_yedek.zip` + git deposu (`temel-2.0` etiketi). Kullanıcı verisine (`~/ÜlgenVeri`) dokunulmadı.
- Sınama ortamı Linux'tur; Mac'e özgü adımlar (Anahtar Zinciri, `say`, `osascript`, launchd) ve iPhone burada **denenemez**. Bunlar her raporda "cihazda doğrulanmadı" diye anılacak.

## 2. Özet

Çekirdek sağlam ve çalışıyor (sohbet, hafıza, araçlar, zamanlayıcı, dosya/PDF, sağlık, sabah özeti). Ancak istenen "gerçek hayatta kullanılabilir, güvenli" düzeyin altında. En önemli 5 sorun:

1. **Komut kara listesi atlatılabiliyor** (`python3 -c`, `find -delete`, `git clean`, `perl`, `tar`…) → modele enjekte edilmiş bir istem, onaysız dosya silebilir.
2. **Tarayıcıdan sunucuya kötü niyetli istek (CSRF / DNS rebinding)**: Host ve Origin denetimi yok, `text/plain` POST kabul ediliyor; yerel makineden gelen istek anahtarsız yetkili sayılıyor.
3. **"tamam" tüm ilaç/kalıcı hatırlatmaları toplu onaylıyor** (istenen kuralın tam tersi); ilaç kaydı/doz kimliği/alındı günlüğü yok.
4. **Sunucu tüm ağ arayüzlerinde (0.0.0.0) dinliyor**, tek sabit anahtar, deneme sınırı yok, HTTPS yok.
5. **Yedek yok; veritabanı şifresiz** (`veri.db`: tüm sohbetler, notlar, hatırlatmalar); `ayar.json` içinde API anahtarı düz yazı.

## 3. Bulgular

Önem: **K**ritik · **Y**üksek · **O**rta · **D**üşük

### 3.1 Güvenlik

| # | Ö | Bulgu | Kanıt | Aşama |
|---|---|-------|-------|-------|
| S1 | K | Terminal aracı kara liste ile korunuyor. `python3 -c …`, `find … -delete`, `find … -exec rm`, `git clean -fdx`, `perl -e`, `tar`, `open -a` onay istemiyor. Kara liste yöntemi doğası gereği atlatılabilir. | `komut_analiz` denemesi: 7 atlatma, hepsi `False` | 1 |
| S2 | K | Host/Origin denetimi yok; `Content-Type: text/plain` ile JSON kabul ediliyor → başka bir sitenin sayfası Mac'teki tarayıcıdan `127.0.0.1:8765/sohbet`'e istek gönderebilir (CSRF); `Host: kotu.example` ile de yanıt veriliyor (DNS rebinding). Yerel adres anahtarsız yetkili. | `Origin: kotu`, `Host: kotu.example` → 200 | 1 |
| S3 | Y | `0.0.0.0` dinleme: Wi-Fi/yerel ağdaki herkes kapıya ulaşır, yalnızca ZeroTier değil. | `server_address = ('0.0.0.0', …)` | 1 |
| S4 | Y | Tek sabit taşıyıcı anahtar; cihaz başına değil, iptal/yenileme yok, yanlış deneme sınırı yok, zaman sabit karşılaştırma var ama günlük/uyarı yok. | kod incelemesi | 1 |
| S5 | Y | HTTPS yok; anahtar ve içerik ZeroTier'in kendi şifrelemesine güveniyor (ZeroTier uçtan uca şifreler, ama tarayıcı "güvenli bağlam" saymaz → mikrofon, Face ID/WebAuthn, web bildirimi kapalı). | kod + tarayıcı kuralı | 1/5/6 |
| S6 | Y | Model, `hafiza_unut` aracıyla kullanıcı onayı olmadan bellek kaydı silebilir; `unut:`/`sil:` komutu da onaysız toplu siler. | kod incelemesi | 1/2 |
| S7 | Y | Terminal aracında çıktı/ortam sızıntısı: `cat veri.db`, `cat memory.json` engelli değil (`veri.db` kritik listede yok). | `cat ~/ÜlgenVeri/veri.db` → `False` | 1 |
| S8 | O | `ayar.json` içinde Gemini anahtarı düz yazı (izin 600). Anahtar Zinciri'ne taşınmalı. | kod | 1 |
| S9 | O | Şifreleme Fernet (AES-128-CBC + HMAC). İstek AES-256-GCM. `veri.db` ve yedekler şifresiz. | kod | 1/6 |
| S10 | O | İstek boyutu sınırı var (200 KB) ama eşzamanlı bağlantı ve zaman aşımı sınırı yok (yavaş bağlantı saldırısı). | kod | 1 |
| S11 | D | Web sayfasında `localStorage` ile anahtar saklanıyor; XSS yoksa kabul edilebilir, ama CSP başlığı yok. | kod | 5 |

### 3.2 Veri bütünlüğü ve kayıp

| # | Ö | Bulgu | Aşama |
|---|---|-------|-------|
| V1 | Y | Yedekleme / geri yükleme yok. | 1/2 |
| V2 | O | SQLite: her sorguda yeni bağlantı, WAL yok, `PRAGMA integrity_check` yok, sürümlü göç (migration) yok (yalnızca `ALTER TABLE` ile ekleme), çok adımlı işlemler tek transaction değil. | 2 |
| V3 | O | Tek global `_sohbet_kilit`: sabah özeti (dakikalarca) çalışırken tüm sohbet kilitleniyor. | 2/7 |
| V4 | O | Kalıcı hatırlatma 24 tekrardan sonra **sessizce** `onaylandi=2` yapılıp bırakılıyor; kullanıcıya bildirilmiyor (ilaç için tehlikeli). | 4 |
| V5 | D | Sohbet geçmişi sınırsız büyür; temizleme/dışa aktarma yok. | 2 |

### 3.3 Eksik özellikler (istenenlere göre)

| İstek | Durum |
|-------|-------|
| Sağlayıcılar: Ollama, llama.cpp, Gemini ✔ · **Groq, Mistral, OpenRouter ✘** | kısmen |
| RPM/TPM/RPD/token kota takibi, **kalıcı istek kuyruğu** | ✘ (yalnızca 429 → hata) |
| Hafıza: kısa/uzun süreli ✔ · proje hafızası, güven düzeyi, kaynak, güncelleme ✘ | kısmen |
| Zamanlayıcı: tek seferlik ✔ · günlük/haftalık rutin, randevu, görev ✘ | kısmen |
| İlaç takibi (ad, doz, saat, doz başına kimlik, alındı durumu) | ✘ (S3) |
| iPhone arayüzü: sohbet ✔ · görevler, ilaç ekranı, bildirim, sesli, onay ekranı ✘ | kısmen |
| Özel Kasa (AES-256-GCM, Face ID onayı) | ✘ |
| Çevrimdışı STT | ✘ (yalnızca tarayıcının Web Speech'i; iPhone'da ses Apple sunucularına gidebilir) |
| Sistem izleme / yönetim ekranı (CPU, RAM, disk, kota, hata) | ✘ |
| Test paketi, belgeler | ✘ (testler yalnızca geçici betik; depoda yok) |

### 3.4 Donanım (MacBook Air 2017, i5-5350U, 8 GB)

- 3B parametreli, 4 bit modeller ≈ 2–2,5 GB bellek, saniyede birkaç belirteç (token) hızı bekleniyor (**ölçülmedi**). Büyük model (7B+) önerilmez.
- pandas ve PDF/OCR işleri bellek yer; Apple Health `export.xml` akışlı okunuyor (iyi).
- Çevrimdışı STT için whisper.cpp "tiny/base" ya da Vosk küçük Türkçe model düşünülebilir; Türkçe doğruluk **denenmeden** vaat edilmeyecek.

## 4. Gerçekçilik notları (kural: "test edilmemiş özelliği tamamlandı gösterme")

1. **Gerçek Face ID**: Yerel uygulama (Xcode, Apple geliştirici kaydı) olmadan Safari'de Face ID yalnızca **WebAuthn / geçiş anahtarı** (passkey) ile olur: biyometrik doğrulama cihazda kalır, sunucu yalnızca imzayı görür (istenen "biyometrik veri cihaz dışına çıkmaz" koşulunu karşılar). **Önkoşul: HTTPS ve güvenilir sertifika.** Sunucu tarafını sahte bir doğrulayıcıyla test edebilirim; gerçek Face ID akışı yalnızca sizin iPhone'unuzda denenebilir → rapora "cihazda doğrulanmadı" yazılır.
2. **HTTPS**: ZeroTier adresine herkese açık sertifika verilemez. Yol: Ülgen kendi yerel sertifika yetkilisini (CA) üretir; iPhone'a bir kez profil yüklenir (Ayarlar → Genel → VPN ve Aygıt Yönetimi, sonra Sertifika Güven Ayarları'ndan tam güven). Kazanım: mikrofon, Face ID, anlık bildirim (ana ekrana eklenmiş uygulama) çalışır.
3. **Ücretsiz sağlayıcılar (Groq, Mistral, OpenRouter, Gemini)**: kota sayıları ve "veri eğitimde kullanılır mı" koşulları sağlayıcıya göre değişir ve sık değişir. Bunları **bu raporda sabit yazmıyorum**; Aşama 3'te güncel kaynaktan doğrulayıp ayar dosyasına işleyeceğim, kotayı ayrıca yanıt başlıklarından (`x-ratelimit-*`) okuyacağım. Kişisel veri buluta **gitmez** (mevcut kural korunur). OpenRouter'da yalnızca `:free` modeller; ücretli modele kendiliğinden geçiş **kodla engellenir**.
4. **Bildirim**: iOS'ta sayfa kapalıyken bildirim yalnızca HTTPS + ana ekrana eklenmiş uygulama + web push ile olur. Bu da (2)'ye bağlı. Güvenilirliği iOS sürümüne bağlıdır, **cihazda denenmeden** garanti edilmez.
5. **Uzun süreli çalışma testi** burada yalnızca hızlandırılmış zaman ile (sahte saat) yapılabilir; gerçek 7 günlük sınama sizde olur.

## 5. Uygulama planı

Her aşama: kod → test (depoda `tests/`) → belge güncelleme → git commit. **Başarısız test varsa sonraki aşamaya geçilmez.**

| Aşama | Kapsam | Kabul ölçütü (testle) |
|-------|--------|------------------------|
| **1 Kritik güvenlik** | Terminal: kara liste yerine **izin listesi** (salt okunur komutlar), diğerleri her zaman ONAY; Host/Origin/Content-Type denetimi; yalnızca 127.0.0.1 + ZeroTier arayüzüne bağlanma; cihaz başına belirteç (süreli, iptal edilebilir, yalnızca özeti saklanır), yanlış deneme sınırı; `veri.db`/anahtar yolları korunur; model silme araçları onaylı; API anahtarları Anahtar Zinciri; yerel CA ile HTTPS; AES-256-GCM yedek şifrelemesi | S1–S4, S6–S10 saldırı testleri geçer; yetkisiz erişim 401/403 |
| **2 Veritabanı + hafıza** | Bağlantı havuzu + WAL, sürümlü göç, işlem (transaction), bütünlük denetimi, şifreli yedek/geri yükleme (düzenli + elle), hafıza şeması (tür, proje, kaynak, güven, güncelleme, silme), sohbet temizleme | göç ileri/geri, yedekten geri yükleme eşitlik testi, bozuk veritabanı kurtarma |
| **3 Sağlayıcılar + kota** | Ortak sağlayıcı arayüzü; Ollama, llama.cpp, Gemini, Groq, Mistral, OpenRouter(`:free`); yerel öncelik; kota izleyici (RPM/TPM/RPD/token); dolunca **kalıcı kuyruk** (yeniden başlatmada korunur), kota yenilenince işlenir; ücretli geçiş yok | sahte sağlayıcılarla kota dolması, kuyruk kalıcılığı, ağ kesintisi, 429 |
| **4 Zamanlayıcı + ilaç** | Görev tablosu (tek sefer, günlük, haftalık, randevu); **ilaç/doz tablosu: her doz ayrı kimlik**, "alındı/atlandı/ertelendi" günlüğü; onay yalnızca ilgili doza; yeniden başlatmada geri yükleme; kaçan doz bildirimi; sessiz vazgeçme yok | iki ilaçtan birinin onayı diğerini etkilemez; yeniden başlatma; sahte saatle gün/hafta döngüsü |
| **5 iPhone arayüzü** | Sekmeler: Sohbet, Görevler, İlaçlar, Bildirimler, Onaylar, Sistem; telefon (iPhone 14 Plus) ölçüsü; ana ekrana ekleme (PWA); web push | tarayıcı (Playwright, iPhone boyutu) ile arayüz testleri; push **cihazda doğrulanmadı** |
| **6 Özel Kasa + Face ID** | AES-256-GCM, anahtar türetme (Scrypt) + Anahtar Zinciri; şifreli not/dosya; kasa işlemleri için WebAuthn onayı (kullanıcı doğrulaması zorunlu) | şifreleme/kurcalama/yanlış anahtar testleri; WebAuthn sunucu tarafı sahte doğrulayıcıyla; **Face ID cihazda doğrulanmadı** |
| **7 Ses + otomasyon** | Çevrimdışı STT (whisper.cpp/Vosk, ses dosyası yükleme), TTS (`say`); PDF analizi (OCR yok), kaynaklı araştırma, sistem izleme (CPU/RAM/disk), görev otomasyonu; sohbet kilidinin işten ayrılması | birim testleri; STT doğruluğu Mac'inizde ölçülür |
| **8 Bütünleşik test** | İnternetsiz, kota dolması, yeniden başlatma, ilaç onayı, yetkisiz erişim, komut enjeksiyonu, şifreleme, yedek geri yükleme, hızlandırılmış uzun süre; SECURITY/TEST raporları | tüm paket yeşil |

Belgeler (her aşamada güncellenir): `PROJECT_STATUS.md`, `AUDIT_REPORT.md`, `SECURITY_REPORT.md`, `TEST_REPORT.md`, `INSTALLATION.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `ROADMAP.md`.

**MVP (öncelik):** Aşama 1, 2, 4 ve 5'in çekirdeği (güvenli çekirdek, hafıza, görev/ilaç motoru, temel mobil arayüz) + Aşama 3'ün yerel/Gemini ve kuyruk kısmı. Çevrimdışı STT, Kasa/Face ID ve ek sağlayıcılar sonraya.

## 6. Karar bekleyen sorular

1. **HTTPS (yerel CA + iPhone'a tek seferlik profil)** onaylanıyor mu? Onay yoksa mikrofon, Face ID ve bildirim **olmaz**.
2. Terminal aracı **izin listesi** ile sınırlansın (varsayılan: salt okunur komutlar serbest, gerisi ONAY) – uygun mu?
3. Groq/Mistral/OpenRouter için kendi **ücretsiz** API anahtarlarınızı alacaksınız (kayıt gerekir). Anahtarlar Anahtar Zinciri'nde tutulur. Uygun mu?

---
## Ek (2026-11-02): Ek şartname doğrulaması

Ek şartname "mevcut ayrı ilaç onay arayüzünü koru" diyor. **Kod incelemesi:** bu pakette böyle bir arayüz yoktur — `arayuz.py` içinde "ilaç" geçmez, veritabanında ilaç/doz tablosu yoktur, yalnızca "kalıcı hatırlatıcı" vardır ve `Zamanlayici.onayla()` bekleyen **tüm** kalıcı hatırlatmaları tek sorguda onaylar. Yani istenen davranış (ayrı onay) şu an **mevcut değil**; "koru" yerine **sıfırdan geliştirilecek** (Aşama 4). Başka bir ortamda ayrı bir ilaç arayüzü kullandıysanız o kod bu paketin parçası değildir.

Diğer doğrulamalar için ROADMAP.md özellik matrisine bakın (her satır gerçek koddan doğrulandı).
