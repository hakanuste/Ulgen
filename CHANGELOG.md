# Değişiklik Günlüğü

## [2.7] – 2026-11-02
- Kendi sesiniz (bulut) sessizce kadın sesine düşmesin: tek ses öğesi ilk dokunuşta "kilidi açılır" (Safari/Chrome otomatik çalma engeli), çalınamazsa neden sohbette yazılır; Ayarlar > Ses seçimi > "Kendi sesimi dene" düğmesi (2.7.32).
- API anahtarlarım: GitHub satırının açıklaması netleştirildi (isteğe bağlı; herkese açık depoda gerekmez) (2.7.31).
- Kılavuzlar → Obsidian: Belgeler/Klavuzlar klasöründeki yeni PDF/md/txt dosyaları 10 dakikada bir kendiliğinden (ya da "Şimdi aktar" ile) kasaya not olarak aktarılır (50 sayfalık parçalar + Dizin notu; artımlı; eski araçla aktarılanlar yeniden yazılmaz). Ayarlar'da durum, klasör ve açma/kapama (2.7.30).
- Güncelleme deposu varsayılan olarak hakanuste/Ulgen (2.7.29).
- Kendini güncelleme: Ayarlar > Güncelleme (GitHub deposundan; `--guncelle`, `--guncelle-zip`, `--guncelle-geri-al`). Yalnız kod değişir; ortam, veri, anahtarlar korunur; eski kod yedeklenir ve geri alınabilir; bozuk/güvensiz zip reddedilir.
- Ses seçimi > "Yalnız benim sesim": kendi sesiniz (bulut) okuyamazsa kadın sistem sesine geçmez, yanıt yazı olarak kalır (varsayılan kapalı).
- Kurulum: elle/eski başlatılmış Ülgen sunucuları durdurulur (eski kod sunmaya devam etmesin); kurulum sonunda çalışan sürüm ile kurulan sürüm karşılaştırılır, farklıysa yeniden başlatılır. `/saglik` sürümü de bildirir. Launchpad temizliği silinen kayıtları listeler.
- Sürüm numarası artık yapıyı da gösterir (2.7.25); hangi yapının çalıştığı arayüzde görülür.
- Sesle "dur / sus / kes / yeter" ("Ülgen" demeden de) sürekli dinleme açıkken anında yakalanır; konuşmayı ve süren işi durdurur.
- "dur" ve "Sus" artık sunucuda süren sohbet/araştırma işini de durdurur (`/sohbet/iptal`, ara adımlarda denetim).
- Görevler sekmesinde "+ Görev / + Randevu / + Rutin" formları (hiç kayıt yokken de görünür).
- Yapay Zekâ sayfasında "API anahtarlarım": her sağlayıcı için anahtar VAR/YOK, saklandığı yer, son 4 hane; Ekle, Değiştir, Bağlantıyı dene, Sil (onaylı; yalnız Mac'in kendi tarayıcısı).
- "Beyin yanıt veremedi" iletisi artık denenen tüm beyinlerin hatasını gösterir; Gemini modeli de emekli olursa (404/410) yenisi seçilir.
- "dur / sus / kes / yeter" yazınca ya da söyleyince (ve yeni "Sus" düğmesiyle) tüm konuşma anında kesilir; yeni yanıt eskisini keser.
- Uzun yanıtlar (araştırma) da bulut sesiyle, ≤700 karakterlik parçalar hâlinde okunur; kota/hassas içerik olursa yalnız kalanı yerel sesle sürer.
- Hatırlatıcılar da düzeltilebilir ve silinebilir (Görevler sekmesi; silme onaylı).
- Sağlayıcı modeli emekli olursa (HTTP 404/410; örn. NVIDIA llama-3.3-70b) model listesi sorulup uygun yeni model kendiliğinden seçilir ve ayar.json'a yazılır.
- Launchpad'de çoğalan Ülgen simgeleri: kurulum sonunda eski/yinelenen kayıtlar silinir (`ulgen/varlik/simge_temizle.sh`; dosya ve veriye dokunmaz).
- Görev, randevu ve rutin: Düzelt ve Sil (onaylı) arayüzde; sohbette "görev|randevu|rutin düzelt #N: …" ve "… sil N [onay]". Zaman/gün doğrulaması, düzeltince bildirim aşaması sıfırlanır.
- Yapay zekâ kipi varsayılan olarak "yalnız yerel" (sabit). Eski kurulumlar bir kez yerele alınır; Ayarlar > Yapay Zekâ'dan (yalnız Mac'in kendi tarayıcısı, onaylı) "önce yerel, sonra bulut" ya da "yalnız bulut" seçilebilir.
- İlaç düzeltme (ad, not, saat) ve silme: arayüzde "Kayıtlı ilaçlar" + Sil (onaylı), sohbette "ilaç sil: Ad" (+ "onay").
- Hava durumu cihazın konumuna göre (izin verilirse; en yakın il adı çevrimdışı bulunur; son konum raporlarda kullanılır).
- Ayarlar > "Ses seçimi": okuma sesi (ad, hız, perde) ve sabit cümleler için kendi mp3 dosyalarınızı yükleme.
- Bulut sesi (ElevenLabs, kendi sesiniz): yanıt metinleri isteğe bağlı okutulur (varsayılan kapalı; hassas içerik gitmez; önbellek; aylık sınır; hata olursa yerel ses).
- Kendi sesiniz (ElevenLabs): sabit cümleler bir kez üretilip yerelde saklanır (`--ses-uret`); kişisel veri bulutta okutulmaz, aylık karakter sınırı sayılır.
- Obsidian: kasa otomatik bulunur; erişim/izin hatası açık yazılır. certifi ile TLS (macOS sertifika hatası).
- Yapay Zekâ sayfasında "Bulut anahtarı ekle" kutusu (yalnız 127.0.0.1; Anahtar Zinciri; "Bağlantıyı dene").
- Raporlar: sabah/akşam/haftalık (`ulgen/rapor.py`, göç 9, `rapor_acik`, `rapor_saatleri`).
- `--dene [sağlayıcı]`: gerçek bulut isteği, süre/token/hata ipucu.
- Çevrimdışı ses: `CevrimdisiTanima`, `/ses/yaz`, `/ses/durum`, `--ses-modeli-indir`.
- Resmî renk standardı: `--ulgen-*` değişkenleri; eski renkler bunlara bağlandı.
- Kurulum yedeği tutarlılığı, SQLCipher zorunluluğu, CSP, sağlık köprüsü, hava (önceki sürümlerden).

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

## 2.5 — İnceleme düzeltmeleri
- Canlı veritabanı SQLCipher ile şifreli; düz dosyadan güvenli göç.
- Kurulum betiği: `rm -rf` kaldırıldı; kurulum öncesi veri yedeği, geçici dizinde hazırlık, eski sürümler `~/Ülgen/eski` altına taşınır, sağlık denetimi başarısızsa geri alma.
- Yerel 127.0.0.1 erişimi yetki ister (tek kullanımlık giriş + çerez); `yerel_yetki:false` ile eski kip.
- `--tani`, `--takvim-deneme`, TEST_DEVICE.md. Durum tablosu PROJECT_STATUS.md'de birleştirildi.

## 2.6 — Aşama 6: Özel Kasa
- ozelkasa.py, webauthn.py, cbor.py; Kasa sekmesi; kurtarma kodu/paketi; `--ana-anahtar-kurtar`; sslip.io Host/SAN desteği; veritabanı göçü 6.

## 2.6 (devam)
- Obsidian arama dizini (not_fts, artımlı, yalnız okuma, PDF dahil); yeni arayüz teması ve pano; /sistem'e donanım ölçümü; veritabanı göçü 7.

## 2.7.33
- Ana sayfa panosu yüklenemezse artık sessizce boş kalmaz; hata nedeni kartta görünür.

## 2.7.34
- Yerel ses denemesi aracı (XTTS-v2): `ulgen/varlik/Yerel Ses Denemesi.command`. Ülgen'e dokunmaz; sesinizi bu Mac'te üretip hızını ölçer. Gerçek cihaz testi bekliyor.

## 2.7.35
- Yeni **Ajanlar** sekmesi: Araştırma, Sağlık, Dosya ajanları ve Sabah Özeti için durum, son çalışma, süre, sonuç özeti ve "Şimdi çalıştır" düğmesi. Sohbetten yapılan çalıştırmalar da aynı kayda düşer (`ulgen/ajan_kayit.py`, `/ajanlar`, `/ajanlar/calistir`).

## 2.7.36
- Launchpad simgesi açılmıyordu: uygulama `python -m ulgen` komutunu paket klasörü dışında çalıştırıyordu ("No module named ulgen"). Artık önce klasöre girer, çıktıyı `~/ÜlgenVeri/simge.log` dosyasına yazar ve hata olursa pencere gösterir. Simge oluşturma `ulgen/varlik/simge_kur.sh` dosyasına taşındı; güncellemeden sonra elle de çalıştırılabilir.

## 2.7.37
- Pano hata iletisi artık hangi isteğin neden başarısız olduğunu gösterir (örn. "/ilac/bugun → çok fazla yanlış deneme"); sunucu hata gövdesi dönünce "reading length" gibi anlamsız iletiler çıkmaz.
