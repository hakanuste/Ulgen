# Değişiklik Günlüğü

## [2.1-aşama1] – 2026-11-02
### Güvenlik
- Terminal aracı: kara liste yerine izin listesi.
- Host/Origin/Content-Type denetimi; güvenlik başlıkları.
- Yalnızca 127.0.0.1 ve ZeroTier adreslerinde dinleme; HTTPS (yerel CA).
- Cihaz başına belirteç (özet saklanır, iptal, süre), yanlış deneme sınırı.
- Hafıza silme araçları ONAY ister.
- AES-256-GCM (hafıza, CA anahtarı, yedek, sırlar); API anahtarları Anahtar Zinciri'nde.
- Şifreli yedek / geri yükleme (`--yedek-al`, `--yedek-yukle`).
### Eklendi
- `tests/` (49 test), `AUDIT_REPORT.md`, `SECURITY_REPORT.md`, `TEST_REPORT.md`.
- CLI: `--cihaz-ekle`, `--cihazlar`, `--cihaz-iptal`, `--sir-kaydet`.
### Değişti (uyumsuz)
- ZeroTier üzerinden düz HTTP kaldırıldı; yerine HTTPS 8443 (+ sertifika için 8766).
- `--anahtar` artık yeni bir cihaz belirteci üretir.

## [2.0] – temel çizgi
- İlk modüler sürüm (git etiketi `temel-2.0`).

## [belgeler] – 2026-11-02
- Ek şartname birleştirildi: tek ana plan (ROADMAP.md), durum sözlüğü, özellik matrisi, teknik engeller, değişmez mimari kararlar (ARCHITECTURE.md).
- AUDIT_REPORT.md: "mevcut ayrı ilaç arayüzü" varsayımı kod incelemesiyle yanlışlandı.

## Aşama 2 — Veritabanı bütünlüğü ve gelişmiş hafıza
- Veritabanı: tek kalıcı bağlantı, WAL, `user_version` ile sürümlü göç (v1→v2), `islem()` ile geri alınabilir işlemler, açılışta `integrity_check`, günlük otomatik şifreli yedek, bozulmada son sağlam yedekten kurtarma (bozuk dosya `yedekler/bozuk-*` olarak saklanır, silinmez).
- Hafıza: her öğede kaynak (kullanıcı/çıkarım), güven, tarih, durum (geçerli/eskimiş/çelişki), düzeltme zinciri; projeler (takma adlarla); ayrı duyarlı depo (`memory_hassas.json`).
- Gizlilik: duyarlı sohbet satırları işaretlenir, bulut beyne gitmez; bulut beyinde kişisel araçlar çalışmaz; çıkarım, kullanıcı bilgisinin yerine geçmez.
- Yeni komutlar: `hatırla/karar/teknik/rutin (PROJE): ...`, `düzelt #id: ...`, `teyit #id`, `bilgi #id`, `proje ekle: ...`, `hafızada ara: ...`, `<proje> kararları`, `çelişkiler`, `eskiyen bilgiler`.
- Testler: 49 → 76 (tests/test_veritabani.py, tests/test_hafiza.py).

## Aşama 3 — Sağlayıcılar, kota, kalıcı kuyruk
- Yeni sağlayıcılar: Groq, Mistral, OpenRouter (OpenAI uyumlu) + mevcut Gemini, Ollama, llama.cpp. Sıra: yerel → `bulut_sirasi`.
- `kota.py`: her çağrı sayılır (istek, giriş/çıkış token, gecikme, hata). GERÇEK (sağlayıcı bildirdi: yanıt başlıkları, `usage`) ile TAHMİNİ (kendi sayacım) ayrı gösterilir. 429 → `Retry-After` kadar engel; sınırlar belgeden, `kota_sinirlari` ile düzeltilir. Gemini günü Pasifik gece yarısı, diğerleri UTC.
- Ücretli kullanım koddan kapalı: `UCRETLI_YASAK`; OpenRouter'da yalnızca `:free`/`openrouter/free`; ayar dosyasında "ücretli geç" seçeneği yok. Maliyet her zaman 0.
- `kuyruk.py`: hepsi dolunca ya da kişisel mesajda yerel beyin yokken istek SQLite kuyruğuna girer; yeniden başlatmada korunur; 24 saatte süresi dolarsa bildirilir; `kuyruk`, `kuyruk iptal N` komutları.
- Komutlar: `kota`, `kuyruk`; uç noktalar `/kota`, `/kuyruk`; `--modeller [sağlayıcı]`.
- Testler 76 → 97 (tests/test_saglayici.py, sahte yerel sunucularla).

## Kod penceresi (Aşama 3 eki)
- Arayüzde "</> Kod" düğmesi: dosya seç/kaydet, Python/Node/Bash yaz-çalıştır, çıktı, "Ülgen'e sor". Kodlar `~/ÜlgenVeri/kod`; üzerine yazılan sürüm `_surumler`'e kopyalanır; silme yok.
- Güvenlik: kum havuzu DEĞİL (kullanıcı yetkisiyle çalışır). Ortam değişkenleri geçmez, 30 sn (en çok 120) sınır, 20 KB çıktı, tek seferde bir çalıştırma. Modelin araç listesinde yok. iPhone'dan çalıştırma varsayılan KAPALI (`uzaktan_kod_calistir`).
- Testler 97 → 111.

## Aşama 4 — Görev motoru ve ilaç takibi
- `ilac.py`: ilaç → plan saati → doz örneği (kendi kimliği: D12). Bir yanıt YALNIZCA bir doz satırını değiştirir. Çıplak "tamam" hiçbir dozu onaylamaz, hangisi diye sorar. Yanıtlar: aldım / almadım / ertele N / atla / düzelt Dn (eski durum geçmişte). Azami hatırlatmadan sonra doz "yanıtsız" olur ve bildirilir (sessiz vazgeçme yok). Kapalıyken kaçan doz geç hatırlatılır ya da "yanıtsız" kaydedilir. Durum SQLite'ta; yeniden başlatmada sürer. Yapay zekâ/kota durumundan bağımsız. Model araçlarında ilaç yazma yetkisi yok.
- `gorev.py`: görev (gecikmiş işaretli), randevu (önceden + zamanında iki bildirim), rutin (her gün/belirli günler, günde bir kez). Saat için `14:30`, tarih için `25.11`.
- Kusur giderildi: genel kalıcı hatırlatıcılarda "tamam" hepsini onaylıyordu; artık tek tek (`tamam #N`), birden çok varsa sorar.
- Bildirimlere `eylem` eklendi; arayüzde her doz için Aldım/Ertele/Almadım/Atla düğmeleri (yalnızca kendi dozunu gönderir). Uç noktalar: `/ilac/bugun`, `/ilac/yanit`.
- Komutlar: `ilaç ekle: Ad 08:00 20:00 [not] [hafta içi|hafta sonu]`, `ilaçlarım`, `ilaçlar`, `ilaç geçmişi`, `ilaç durdur: Ad`, `aldım D3`, `ertele 30 D3`, `görev/randevu/rutin ekle: ...`, `görevlerim`, `randevularım`, `rutinlerim`, `görev tamam N`.
- Testler 111 → 138.

## Aşama 5 — iPhone arayüzü (sürüm 2.5)
- Sekmeler: Sohbet, Görevler (görev/randevu/rutin/hatırlatıcı, "Tamamlandı" düğmesi), İlaç (bugünkü dozlar, her doz için kendi düğmeleri), Bildirim (oturum geçmişi), Sistem (yönetim paneli: sürüm, veritabanı bütünlüğü, son yedek, beyin, kuyruk, kota gerçek/tahmini ayrı, cihazlar, son günlük).
- Bağlantı izleme: kopunca kırmızı uyarı, artan bekleme (5→60 sn) ile yeniden deneme, dönünce otomatik yenileme; sayfa öne gelince bildirim ve sekme yenilenir.
- Uç noktalar: `/gorevler`, `/gorev/bitir`, `/sistem` (salt okunur; belirteç/özet sızdırmaz).
- Cihaz iptali arayüzden DEĞİL, Mac'te `--cihaz-iptal` ile (uzaktaki cihaz kendi yetkisini kaldırmasın diye).
- Testler 138 → 139.

## iPhone takvim aktarımı (Mac kapalıyken alarm)
- Kullanıcı kararı: kritik hatırlatmalar iPhone'da olmalı. `takvim.py` ilaç planlarını, randevuları, saatli görevleri ve rutinleri `.ics`'e çevirir; iPhone'un kendi takvimi Mac'siz ve ağsız alarm çalar. İlaç saati başına 6 ayrı olay (5 dk arayla) = tekrar alarmı.
- İlaç sekmesinde "iPhone takvimine aktar" düğmesi: tek kullanımlık, 2 dakikalık bağlantı (cihaz belirteci URL'ye girmez).
- Başlıklar varsayılan GENEL ("Ülgen: ilaç zamanı"; takvim iCloud'a eşlenirse ilaç adı bulutta görünmesin). `takvim_ayrintili: true` ile ad yazılır.
- Kapalıyken kaçan "yanıtsız" dozlar için arayüzde "Aldım (kaydı düzelt)/Almadım" düğmeleri (`/ilac/duzelt`).
- Testler 139 → 150.

## NVIDIA Build sağlayıcısı
- `nvidia` eklendi (OpenAI uyumlu, `https://integrate.api.nvidia.com/v1`): anahtar `--sir-kaydet nvidia` (nvapi-...), modeller `--modeller nvidia`, varsayılan `meta/llama-3.3-70b-instruct` (NVIDIA model adlarını sık değiştirir). Sıra: Gemini → NVIDIA → Groq → Mistral → OpenRouter (`bulut_sirasi`).
- Kota: resmi sayı yok; yerel sınır 40 istek/dk (üçüncü taraf bildirimi, ayardan düzeltilir). 429'da diğer sağlayıcıya geçer.
- Uyarı: NVIDIA deneme uç noktaları "araştırma, geliştirme ve test" lisansıyla verilir, üretim için değildir; kişisel kullanımın bu kapsama girip girmediğini lisans metninden siz değerlendirin. Veri bulut sayılır: kişisel mesajlar gitmez.
- Testler 150 → 151.
