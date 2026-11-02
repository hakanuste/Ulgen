# ÜLGEN – TEST RAPORU

Çalıştırma: `python3 -W ignore -m unittest discover -s tests -t .` · Ortam: Linux, Python 3.13. Her test geçici bir `HOME` kullanır; gerçek `~/ÜlgenVeri`'ye dokunmaz.

## Sonuç (Aşama 1 sonu): 49 test, 49 başarılı · PEP 8 temiz

| Dosya | Test | Kapsam |
|-------|------|--------|
| `test_guvenlik.py` | 11 | komut izin listesi + 19 atlatma denemesi, gizli yollar, ONAY akışı (yanlış kod, tek kullanım), hafıza silme onayı, dosya izinli klasör dışına çıkamaz, dosya ezme onayı |
| `test_sunucu.py` | 21 | Host/Origin/Sec-Fetch-Site/Content-Type, TLS doğrulaması (CA ile), güvenilmeyen CA reddi, düz HTTP'nin TLS portunda çalışmaması, belirteçsiz/yanlış/iptal/süresi dolmuş belirteç, deneme sınırı, eski anahtar taşıma, sertifika yenileme ve izinleri |
| `test_sifreleme.py` | 17 | AES-256-GCM gidiş-dönüş, kurcalama, yanlış anahtar, eski Fernet, sırlar, hafıza şifreleme/geçiş/anahtar kaybı, yedek al/geri yükle/yanlış parola/kurcalama/yol geçişi/bozuk veritabanı |

Ek elle yapılan: gerçek süreçte (`python -m ulgen`) 127.0.0.1'de HTTP, HTTPS dinleyici, CA indirme, belirteçli/belirteçsiz istek, geçersiz Host.

## Henüz yapılmayanlar (yeşil sayılmaz)

- Zamanlayıcı/ilaç yeniden başlatma, kota dolması ve kuyruk, çevrimdışı çalışma, uzun süreli çalışma → ilgili aşamalarda.
- **Mac ve iPhone üzerinde hiçbir test yapılmadı** (Anahtar Zinciri, `launchd`, Safari sertifika yükleme, Face ID, bildirim).

## Planlanan kabul senaryoları (Ek şartname §10) – simülasyon ve gerçek cihaz ayrı

| # | Senaryo | Simülasyon testi (Linux) | Gerçek cihaz testi (sizde) | Durum |
|---|---------|--------------------------|----------------------------|-------|
| 1 | Mac kapalıyken iPhone bildirimi | – (fiziksel olarak simüle edilemez) | gerekli | teknik engel |
| 2 | Mac yeniden açılınca görev geri yükleme | evet (süreç yeniden başlatma) | launchd ile gerekli | Aşama 4 |
| 3 | iPhone bağlantı kopması/yeniden bağlanma | evet (istemci betiği) | gerekli | Aşama 5 |
| 4–5 | İlaçların ayrı onayı, tek onay diğerini etkilemez | evet | arayüz kontrolü | Aşama 4 |
| 6 | Kota dolunca kalıcı kuyruk | evet (sahte sağlayıcı) | – | Aşama 3 |
| 7 | Ücretsiz sağlayıcılar kullanılamaz | evet | – | Aşama 3 |
| 8 | Yerel modele geçiş | evet | gerçek Ollama/llama.cpp | Aşama 3 |
| 9 | Hassas veri buluta gitmez | evet (istek içeriği denetimi) | – | Aşama 3 |
| 10 | Hafıza senkronizasyonu | evet | gerekli | Aşama 2 |
| 11 | F800/Joeme Fit aktarımı | örnek dosya ile ayrıştırma | gerçek cihaz/dışa aktarma | Aşama 7 (E) |
| 12 | Apple Health aktarımı | örnek export.xml ile | gerçek iPhone | Aşama 7 (E) |
| 13 | Çevrimdışı sesli kullanım | ses dosyasıyla STT | Mac mikrofonu, CPU/RAM ölçümü | Aşama 7 |
| 14 | Face ID geçersiz/süresi dolmuş | sunucu tarafı (sahte doğrulayıcı) | gerçek Face ID | Aşama 6 |
| 15 | Kasa yetkisi iptali | evet | – | Aşama 6 |
| 16 | Rapor doğruluğu | evet (bilinen veriyle) | – | Aşama 8 |

## Aşama 2 sonuçları (Linux benzetimi, gerçek Mac/iPhone değil)
76 test, tümü geçti: göç (eski v1 veritabanı dahil), işlem geri alma, bütünlük denetimi, bozuk veritabanından yedekle kurtarma, hafıza kaynak/güven/eskime/çelişki/düzeltme, duyarlı deponun buluta kapalılığı, disk şifrelemesi, bulutta kişisel araç engeli, hızlı hafıza komutları.
Denenmedi: Mac Anahtar Zinciri, uzun süreli (günler) çalışma, çok büyük veritabanında FTS başarımı.

## Aşama 3 sonuçları (benzetim: sahte sağlayıcı sunucuları)
97 test geçti. Kapsanan: gerçek/tahmini token ayrımı, dakikalık/günlük sınır, Pasifik günü, 429 sonrası sıradaki ücretsiz sağlayıcıya geçiş, sunucu hatasında kota harcamadan geçiş, ücretli modelin ağa çıkmadan reddi, kota doluyken kuyruk + hatırlatıcının çalışması, yeniden başlatmada kuyruğun korunması, kişisel mesajın buluta HİÇ gitmemesi, yerel beyin açılınca işlenmesi, süresi dolan istek bildirimi.
Denenmedi: gerçek Groq/Mistral/OpenRouter/Gemini uç noktaları (anahtarım yok; model adları ve başlık adları belgeden, doğrulanmadı), gerçek 429 davranışı, günler süren kullanım.

Kod penceresi: 14 birim testi (zaman aşımı, ortam, ad doğrulama, uzak kapı, tek çalıştırma) + Chromium uçtan uca deneme geçti.

## Aşama 4 sonuçları (benzetim + Chromium)
138 test geçti. Kabul senaryosu: A ilacı 08:00 ve 20:00, B ilacı 08:00; A-08 onayı A-20'yi, B-08'i ve ertesi günkü A-08'i değiştirmedi. Ayrıca: çıplak tamam, belirsiz "aldım", ilgisiz cümle ("marketten ekmek aldım"), çifte dokunuş, ertele, azami hatırlatma sonrası yanıtsız, yeniden başlatma (sayaç korunur), kapalıyken kaçan doz, yapay zekâ kapalıyken çalışma, model araçlarında ilaç yazma yokluğu, gerçek HTTP uç noktasında tek doz, geçersiz gövdeler, görev/randevu/rutin zamanlaması, genel hatırlatıcı toplu onay kusurunun giderildiği.
Chromium denemesi: iki doz bildirimi, "Aldım" yalnızca ilk dozu kapattı.
Denenmedi: gerçek iPhone'da bildirim (Safari/PWA kapalıyken yerel bildirim planlayamaz; Mac uykudayken/kapalıyken hiçbir hatırlatma çalışmaz — bkz. ROADMAP, bekleyen karar A/B/C), saat dilimi/yaz saati geçişi, günlerce süren çalışma.

## Aşama 5 (benzetim, Chromium 390 px)
Her sekme verilerle çizildi; ilaç ve görev düğmeleri gerçek arka uçta yalnızca ilgili kaydı değiştirdi; bağlantı koparılıp (istek engellenerek) geri verildi: uyarı çıktı ve kendiliğinden kapandı; sayfa hatası yok.
Denenmedi: gerçek iPhone/Safari, ana ekran uygulaması, uzun süreli bağlantı, ZeroTier ağı üzerinden.

## Takvim aktarımı (benzetim)
.ics, `icalendar` kütüphanesiyle ayrıştırıldı: olay sayısı, RRULE (günlük/hafta içi), alarmlar, 75 sekizli satır katlama, genel başlıklar, tek kullanımlık bağlantı, uzak sunucuda belirteç zorunluluğu. 150 test geçti.
DENENMEDİ (iPhone gerekir): Apple Takvim'in dosyayı içe aktarması, "Tüm Olayları Ekle", alarmın kilit ekranında çalması, Rahatsız Etme/Odak kipinde davranış, yinelenen olayların UID ile güncellenmesi.


## Ağır son sınav (2.7, Linux benzetimi, 2026-11-02)
- 199 birim sınavı 3 ardışık turda geçti; derleme ve stil temiz.
- `tests/agir/yuk_ve_saldiri.py`: 400 bulanık sohbet girdisi, bozuk/dev gövde, yol gezinme, kötü Host, 16 iş parçacığı × 50 istek: 5xx yok, 400/400 kayıt, bütünlük "ok". Yetkisiz yoğun deneme 429 (hız sınırı) ile kesildi (beklenen).
- `tests/agir/otuz_gun.py`: 43 200 dakikalık zaman benzetimi: 87 doz, her doza ayrı yanıt, sabah 30/akşam 30/haftalık 4 rapor, kopya yok.
- `tests/agir/yedek_donus.py`: silme→geri yükleme, yanlış parola ve bozuk yedek reddedildi, veritabanı düz sqlite ile okunamıyor.
- `tests/agir/ekran_tarama.py`: 12 sekme × 7 ekran boyutu: JS hatası yok. BULGU: iPhone yatay ve iPad yatayda yatay taşma → masaüstü düzeni 1240 px altında kapatıldı, düzeltildi.
- Gerçek cihazda yapılmayanlar: PROJECT_STATUS ve TEST_DEVICE'a bakın.
