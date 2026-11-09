# Değişiklik Günlüğü

## 2.7.84
- **Uzmanlar ayrı ajan:** 12 alan uzmanı Ajanlar sekmesinde, "Alan uzmanları" başlığı altında kendi kartlarıyla görünür (durum, son çalışma, özet, görev kutusu, "Şimdi çalıştır"). Sonuç sohbette yayınlanır.
- **Araştırma ajanı görevi devreder:** Kısa bir araştırma görevi bir uzmanın alanına giriyorsa (örn. kur → AKÇA, bitki → OTACI, kerpiç → BALBAL, Musso → TULGA) Araştırma ajanı işi o uzmana verir. Uzman önce resmî veriye (AKÇA için TCMB/piyasa), sonra kendi güvenilir sitelerine bakar; orada bulgu yoksa genel arama yapılır ve "doğrulanmamış" diye etiketlenir. Yanıtın başında hangi uzmana devredildiği yazar. Uzun, çok maddeli görevler planlı araştırmada kalır.
- **Önce kütüphane, yoksa araştırma:** Sohbete yazılan bir bilgi sorusu önce Obsidian kütüphanesinde aranır; soruyu karşılayan not yoksa Araştırma ajanı hemen çalışır ve yanıt bulunan kaynaklara dayanır (kaynaklar yanıtın sonunda). Kişisel, duyarlı ve sağlık durumu içeren sorular dışarıda aranmaz. Ayar: `otomatik_arastirma` (açık).
- Kodlandı ve test edildi (404 test); Mac'te gerçek sorularla denenecek.

## 2.7.83
- **Kurum görüşü derlemesi (`portfoy: 20`):** Fintables'taki aracı kurumların "Analist tavsiyeleri" tablolarını (hisse, öneri, tarih, hedef fiyat, son fiyat, potansiyel getiri, model portföy simgesi) sizin girişinizle, salt okuma ve kurum başına birkaç saniye bekleyerek gezer (ilk N kurum, pazar payı sırasıyla; varsayılan 20). Hisse başına hesaplar: kaç kurum kapsıyor (%), olumlu/nötr/olumsuz sayısı, model portföyde kaç kurum, hedef fiyat (en düşük–ortanca–en yüksek), ortanca potansiyel getiri. 180 günden eski tavsiyeler sayılmaz. Sonuç sohbette yayınlanır ve `Ülgen/Akçe/` altına not olur. Kurumların görüşünün derlemesidir; kendi tavsiyemiz değildir, raporda sürü etkisi ve az kurum uyarısı vardır. Model portföy bilgisi tablodaki ✓/✕ simgesinden ÇIKARILIR (en sık simge = portföyde değil); rapor bunu belirtir.
- Oturumlu okuyucu tek oturumda çok sayfa gezebilir (`Okuyucu`), kaydırdıkça yüklenen tabloları da toplar. Gerçek tarayıcıyla sahte Fintables sayfalarına karşı uçtan uca sınandı; gerçek Fintables ve Mac'te test bekliyor.

## 2.7.82
- **Ajan görev penceresi:** Sohbet sayfasındaki "Ajan Görevi" düğmesi tam ekran bir pencere açar: ajanı seçin (Araştırma ajanı ya da 12 alan uzmanından biri), görevi yazın (araştırmada 60 000 karaktere dek), gönderin. Görev arka planda yürür (sayfayı kapatabilirsiniz); bitince sonuç sohbet sayfasında bir ajan yanıtı olarak yayınlanır ve sohbet geçmişine yazılır (sesli okunmaz). Uzmana verilen görev, uzmanın kurallarıyla ve güvenilir kaynaklarıyla yürür; Araştırma ajanı uzun görevlerde Obsidian'a not da yazar. Görevler sırayla çalışır. Kodlandı ve sunucu ucu test edildi; sayfa görünümü Mac'te denenecek.

## 2.7.81
- **Oturumlu okuyucu (giriş gerektiren siteler):** `giris: fintables.com` -> ayrı bir tarayıcı penceresi açılır, siteye KENDİNİZ giriş yaparsınız (şifre Ülgen'e hiç girmez, saklanmaz), pencereyi kapatırsınız. Sonra `oturumlu oku: <adres>` (ya da `oturumlu_oku` aracı) aynı oturumla sayfanın metnini okur. Salt okuma: tıklama, form gönderme, indirme yok. Yalnızca `kaynak ekle` ile eklediğiniz alan adları okunur; yerel/özel adresler engelli. Oturum çerezleri yalnız Mac'te `~/ÜlgenVeri/tarayici` (0700) altında durur; sonuçlar kişisel veri sayılır ve bulut beyne gitmez. İsteğe bağlı bileşen: `pip install playwright && playwright install chromium` (yoksa komut bunu söyler). Gerçek tarayıcıyla çerez kalıcılığı sınandı (Linux); Mac ve gerçek siteler için test bekliyor.
- Düzeltme: alan adı eşleştirmesi `ornek.com/yol` gibi şemasız adreslerde yolu da alan sanıyordu.

## 2.7.80
- **Kendi kaynağınızı ekleyin:** `kaynak ekle: AKÇA https://www.isyatirim.com.tr/...` (herhangi bir uzman için) — o sayfa uzmanın güvenilir listesine girer ve `guvenilir_ara` onu doğrudan okur. `kaynak sil: AKÇA isyatirim.com.tr`, `kaynaklar: AKÇA` ile çıkarma/listeleme. Hazır listeler korunur; eklenenler `ayar.json`da `kullanici_kaynaklari` altında durur. Yerel/özel ağ adresleri eklenemez.
- **Varlık analizi:** `analiz: THYAO` (BIST hisse kodu), `analiz: ons altın`, `gümüş`, `brent`, `bitcoin`, `bist 100`. Son 1 yılın günlük kapanışlarından kodda hesaplanır: getiri (1 ay/3 ay/1 yıl), 20/50/200 günlük ortalama, RSI(14), yıllık oynaklık, tepe/dip, en büyük düşüş; durum tespiti ve ±1σ ölçek aralığı. Kesin al/sat emri ya da fiyat tahmini vermez; her raporda "finansal danışmanlık değildir" yazar. Rapor `Ülgen/Akçe/` altına not olur. Mali tablo, çarpan, KAP ve haber bu sürümde YOK (rapor bunu açıkça belirtir); İş Yatırım/KAP sayfasını `kaynak ekle` ile ekleyip AKÇA'ya sorabilirsiniz. Kodlandı, gerçek ağda test bekliyor.

## 2.7.79
- **Güvenilir kaynak listeleri:** Her alan uzmanının kendi güvenilir site listesi var (örn. OTACI: WHO, EMA, NCCIH, PubMed, TDV İslâm Ansiklopedisi; YARGU: mevzuat.gov.tr, Resmî Gazete; AKÇA: TCMB, Borsa İstanbul, TÜİK, SPK; KÜN: PVGIS/JRC, NREL; YER-SU: MGM, Tarım Bakanlığı, FAO; ALPAGU: NIST, CISA, ENISA, BTK). Yeni araç `guvenilir_ara(sorgu, uzman)` yalnız bu sitelerde arar ve kaynaklı metin verir; listede bir şey bulunamazsa "bulamadım, tahmin yürütmüyorum" der. Uzmanlar olgu için önce bu aracı çağırır. Listeler `ayar.json` içinde `"guvenilir_kaynaklar": {"OTACI": ["who.int", ...]}` ile değiştirilebilir. Alan adları ilk taslaktır; Mac'te denenip düzeltilecek.

## 2.7.78
- **Piyasa verisi (AKÇA):** Borsa siteleri kazınınca Cloudflare engeli ve JavaScript yüzünden güncel değer alınamıyordu. Yeni araç `piyasa_verisi`: döviz için **TCMB günlük kurları** (resmî, anahtarsız), BIST 100 / ons altın / gümüş / Brent / Bitcoin / Ethereum için Yahoo Finance'in herkese açık ucu; yanıt değeri kaynak ve zamanla verir. Gram altın, ons x TCMB dolar / 31,1035 olarak HESAPLANIR ve öyle etiketlenir. Yalnızca bu iki alan adına bağlanılır; ücretli servis yok. AKÇA güncel değer için bu aracı önce çağırır.
- **Araştırma:** Cloudflare/"Lütfen bekleyiniz" gibi engel sayfaları artık sonuca ham metin olarak girmez; arama özeti kalır.
- Kodlandı, birim testleri sahte yanıtlarla geçti; gerçek ağda (Mac) test bekliyor.

## 2.7.77
- **AKÇA düzeltmesi:** "altının", "euro", "bitcoin fiyatı", "kuru" gibi ekli/kısa sözcükler uzmanı tetiklemiyordu. Anahtar sözcükler genişletildi; uzmanın adı geçince ("Akça: ...") her zaman o uzman seçilir (tüm uzmanlar için). AKÇA artık güncel fiyat/kur sorulunca `internette_ara` aracını önce çağırır, değeri kaynak ve tarihle verir, bellekten fiyat söylemez.

## 2.7.76
- **Tüm alan uzmanları:** AKÇA (akçe; alım-satım önerisi yok), YARGU (mevzuat; hukuk görüşü değil), ALPAGU (kendi mülk ve veri güvenliği; yalnız savunma), KOPUZ (müzik), OYUN (dans), YAZIT (arşiv) eklendi; toplam 12 uzman.
- **Sayfa:** Ana sayfadaki "Sağlık Durumu" kartı kaldırıldı; yerine 6 genel görev türü ve 12 uzmanı gösteren "Ajanlar ve Uzmanlar" kartı kondu (`/uzmanlar`). Üstteki şeritteki küçük "Sağlık" kartı ve Sağlık sekmesi yerinde duruyor.

## 2.7.75
- **Alan uzmanları (yönlendirici + profil):** Soruda konuya özgü sözcükler geçince ilgili uzmanın kuralları sistem istemine eklenir: **OTACI** (bitkiler, geleneksel şifa bilgisi), **TULGA** (Musso/otomotiv), **YER-SU** (permakültür, arsa), **KÜN** (güneş enerjisi), **DEMİR** (elektronik), **BALBAL** (kerpiç/taş yapı). Hepsi için ortak kural: her bilginin kaynağı söylenir, bilinmeyen "bilinmiyor" denir, geleneksel bilgi ile doğrulanmış bilgi ayrı belirtilir.
- **OTACI ve bitki kütüphanesi:** "Biberiye neye iyi gelir / hangi vitamini içerir / nasıl kullanılır" gibi sorulara geleneksel kullanım (İbn Sînâ, Dioskorides vb. kaynaklarıyla), içerik, hazırlama biçimi ve uyarılarla yanıt verir. Tanı koymaz, kişiye doz vermez, ağır belirtilerde ilk yardım ve 112'ye yönlendirir. Yeni araç `bitki_bilgisi(ad)`: kaynaklı araştırma yapar ve `Ülgen/Bitkiler/<ad>.md` notunu yazar. Kodlandı, gerçek cihaz testi bekliyor.

## 2.7.74
- **Yanıt doğrulayıcı:** Ülgen gerçek bilgi içeren (sayı/özel ad geçen) bir yanıt verdikten sonra, arka planda iddiaları web kaynaklarıyla karşılaştırır ve işi bitince KISA bir bildirim yollar: kaç iddia kaynaklarda destekleniyor, hangilerini net bulamadı, örnek kaynak. Doğruysa bir şey demenize gerek yok; yanlış gördüğünüzü `yanlış: <doğrusu>` diye yazarsanız düzeltme hafızaya kullanıcı bilgisi olarak kaydedilir. Kişisel/duyarlı/sağlıkla ilgili konuşmalar ve kısa yanıtlar hiç doğrulanmaz; web'e yalnızca iddia cümlesi gider. Ayar: `dogrulama` (varsayılan açık). Kurallı karşılaştırmadır (anahtar sayı ve özel adların kaynakta bulunması); sayfanın kendisi yanlışsa anlayamaz. Kodlandı, gerçek cihaz testi bekliyor.

## 2.7.73
- **Araç çağrısı ayrıştırma:** Bazı modeller aracı JSON yerine `<arac>ad</arac><parametreler>{...}` etiketleriyle çağırıyordu; bu çağrı çalışmayıp sohbette ham metin olarak görünüyordu (örn. Obsidian araması hiç yapılmıyordu). Etiketli biçim artık tanınır ve araç çalışır.
- **Obsidian araması ek alan sözcükleri bulur:** "aracım" gibi ekli bir sözcük, notlardaki "araç" kökünü de arar (kök eşleşmesi).

## 2.7.72
- **Takvim/Anımsıtıcı artık sürekli öne gelmez:** Mac eşitlemesi uygulamaları gizli ve arka planda (`open -g -j`) açar, işi bitince yine kapatır (zaten açıksa dokunmaz). Eşitleme aralığı varsayılan 10 dakikadan 30 dakikaya çıkarıldı (`mac_senk_dk`; ayarlardan değiştirilebilir, elle "şimdi eşitle" aynen çalışır). Kodlandı, gerçek cihaz testi bekliyor.

## 2.7.71
- **Hap/ilaç ve hatırlatmalar bilgisayarda sesli:** Mac'te bir doz ya da hatırlatma zamanı gelince önce kısa bir uyarı sesi çalar, sonra metin sesli okunur (kimlik imleri ve yanıt yönergeleri okunmaz). Sayfa kapalı olsa da çalışır; aynı Mac'teki sayfa ikinci kez okumaz. Ayar: `hatirlatma_sesi` (varsayılan açık). Kodlandı, gerçek cihaz testi bekliyor.

## 2.7.70
- **Uzun araştırma:** Araştırma Ajanı artık uzunluğu ne olursa olsun (60 000 karaktere dek) görev alır. Görev maddelere ayrılır (örn. "Ad (eser, eser)" listesi → her ad bir madde), her madde için ayrı aramalar yapılıp sayfalar okunur, bulgular kaynak bağlantılarıyla Obsidian'da `Ülgen/Araştırmalar/<görev>/` altında not olur, sonda `00 Dizin` yazılır. Her madde sonrası denetim noktası: iptal/kapanma sonrası aynı görev verilince kalan maddelerden sürer. Telifli kitapların tam metni indirilmez; PDF bağlantıları notta listelenir.
- **Obsidian'a yazma (kullanıcı onaylı):** Yalnız kasadaki `Ülgen/` klasörüne, yeni not olarak; sizin notlarınızın üzerine yazılmaz, hiçbir şey silinmez, yol kaçışı engelli. Ayar: `obsidyen_yazma`, `obsidyen_yazma_klasoru`. Kasa yoksa notlar `~/ÜlgenVeri/notlar/` altına yazılır.
- **Kitap Okuyucu (yerel OCR):** Ajanlar sekmesinden PDF/resim yükleyin (ya da `~/ÜlgenVeri/gelen`); sayfalar tesseract ile yerelde okunur, `Ülgen/Kitaplar/` altına not olur (uzun kitaplar 40 sayfalık bölümlere ve bir dizin notuna ayrılır). Gömülü metni olan PDF sayfaları OCR'sız alınır. Sayfa sayfa denetim noktası. Kurulum: `brew install tesseract tesseract-lang poppler`. Kodlandı ve Linux'ta gerçek tesseract ile test edildi; Mac'te gerçek cihaz testi bekliyor.

## 2.7.69
- `/saglik/ozet` yanıtında atlanma nedeni kısa `neden` alanı olarak ilk satırda ve değerin türüyle birlikte gelir (Kestirme sonuç önizlemesi kesiyor).

## 2.7.68
- `/saglik/ozet` yanıtı atlanan alanın nedenini söyler (`atlanan_nedenler`: sayı okunamadı / sınır dışı).

## 2.7.67
- Sağlık özeti birimli değerleri de okur ("72 count/min", "1.234 adım" → ilk sayı); Kestirme'den gelen birim eki artık "atlanan" sayılmaz.

## 2.7.66
- Kestirmeler özel başlığı iletmediğinde: `/saglik/ozet` belirteci JSON gövdesindeki `belirtec` alanından da kabul eder (yalnız bu yolda). Günlük de gövdede belirteç olup olmadığını yazar.

## 2.7.65
- "Hiç değer yok" hatası artık Kestirme'nin gönderdiği alanları ve değerlerini gösterir (boş değişken teşhisi için).

## 2.7.64
- Kestirme'de "İstatistikleri Hesapla" eylemi artık gerekmez: `adim`, `uyku_dk`, `aktif_dakika`, `kalori` alanlarına örneklerin değer listesi (satır satır) gönderilebilir, toplamı Ülgen yapar; `nabiz` listesinde ilk (en yeni) değer alınır.

## 2.7.63
- Cihaz belirteci okuma toleranslı: Kestirmeler/Notlar'dan yapıştırmada gelen bölünmez boşluk, satır sonu gibi görünmez karakterler artık "yetkisiz"e yol açmaz. Yeni, daha kolay başlık: `X-Ulgen-Token: <belirteç>` ("Bearer" ve boşluk gerekmez).
- Yetkisiz uzak istekler Sistem Durumu günlüğüne (kaynak "yetki") yazılır: başlık geldi mi, kaç karakter, Bearer ile mi başlıyor (belirtecin kendisi yazılmaz).

## 2.7.62
- Sağlık ajanı artık iPhone Kestirmesi'nin gönderdiği ölçümleri de okur (`saglik_olcum`); eskiden yalnız dışa aktarılan dosyaya (export.xml/csv/json) bakıyordu ve Kestirme verisini "bulunamadı" diye görmüyordu. Dosya ve Kestirme verisi birleşir, aynı gün için Kestirme geçerli olur.

## 2.7.61
- iPhone alarm tekrarı ayarlanabilir: Ayarlar > "iPhone alarmı: tekrar" (tekrar sayısı 1/2/3/6, aralık 5/10/15/30/60 dk). iPhone takvimi "aldım" yanıtını bilemediği için eskiden her ilaç saatinde 6 alarm çalıyordu. Değişince dosyayı yeniden aktarmak gerekir. Gerçek iPhone testi bekliyor.

## 2.7.60
- iPhone takvim aktarımına sohbetten kurulan hatırlatıcılar da eklendi (zamanı gelmemiş, onaysız olanlar; kalıcı olanlar ilaç gibi 6 tekrar alarmıyla). Başlık varsayılan olarak genel ("Ülgen: hatırlatma"). Yeni hatırlatıcı kurulunca ya da silinince dosyayı yeniden aktarmak gerekir. Gerçek iPhone testi bekliyor.

## 2.7.59
- iPhone takvim aktarımı: olay saatleri artık "Europe/Istanbul" diliminde AÇIKÇA (sabit +03:00, VTIMEZONE) yazılır; eskiden "yüzen" saat yazılıyor, iPhone'un saat dilimi/geçersiz kılma ayarına göre alarm 1 saat kayabiliyordu. Ayar: `takvim_saat_dilimi` (boş = eski davranış). Kök neden iPhone'da henüz doğrulanmadı: dosyayı yeniden aktarıp denemek gerekiyor.

## 2.7.58
- `Ülgen/eski` klasörü her güncellemeden sonra budanır: güncelleme yedeklerinden en yeni 3, eski uygulama simgesi ve eski kod kopyasından en yeni 1 kalır. Geri alma (Ayarlar > Güncelleme) en yeni yedekle çalışmaya devam eder.

## 2.7.57
- Yedek klasörü kendiliğinden temizlenir: `kurulum-…`, `bozuk-…`, `onceki-…` kopyalarının her türünden yalnız en yeni 3 tanesi kalır (açılışta ve günlük yedekte). Otomatik yedekler (7 tane) ve diğer dosyalar değişmedi.

## 2.7.56
- Yerel ses klonlama denemesi (XTTS-v2) kaldırıldı: ses benzedi ama bu Mac'te her 1 sn konuşma için ~6 sn üretim gerekiyor (anlık kullanım için yavaş). Betikler depodan silindi; ölçüm sonuçları yukarıdaki 2.7.5x notlarında.

## 2.7.55
- Yerel ses denemesi: eski torch'un `weights_only` reddi aşıldı (yalnız deneme sürecinde, resmi Coqui modeli). Kurulum notu: Intel Mac'te `llvmlite==0.43.0 numba==0.60.0`, `transformers==4.46.2`, `click==8.1.8 typer==0.12.5` gerekti. Gerçek cihaz testi sürüyor.

## 2.7.54
- Sağlık kestirmesi kolaylaştı: `/saglik/ozet` ({"adim", "nabiz", "uyku_dk"/"uyku_saat", "aktif_dakika", "kalori"}; hepsi isteğe bağlı, zamanı Ülgen damgalar, "8.421" gibi Türkçe sayılar okunur). `SAGLIK_KESTIRME.md` adım adım yeniden yazıldı (elle `curl` sınaması dahil). Gerçek iPhone/Kestirmeler testi bekliyor.

## 2.7.53
- Mac Takvim randevuları ve Hatırlatıcılar Ülgen'e kendiliğinden gelir (10 dakikada bir, yalnız okunur; `ulgen/macsenk.py`). Ülgen'de bitirilen/silinen kayıt geri gelmez; Mac'te silinen/tamamlanan kapanır. Geçmiş tarihli hatırlatıcılar için bildirim yağmuru yok.
- Ülgen hatırlatmaları (ilaç, randevu, rutin, görev) Mac'in kendi bildirimi olarak da çıkar (Ayarlar'dan kapatılabilir).
- Ayarlar: "Mac Takvim ve Hatırlatıcılar ⇄ Ülgen" bölümü (Şimdi eşitle, kendiliğinden eşitle, Mac bildirimi). Veritabanı göçü 10 (`gorev.kaynak`, `gorev.dis_kimlik`).
- Sınırlar: tekrarlayan olayların yalnız ilk kaydı gelir, tüm gün olayları alınmaz, Ülgen kapalıyken çalışmaz. Gerçek cihaz testi (macOS izinleri, AppleScript) bekliyor.

## 2.7.52
- iPhone (ana ekran simgesi): üst şerit durum çubuğu payını da kapsıyor; menü ve "‹ Ana Sayfa" düğmeleri artık kesilmiyor. Gerçek cihaz testi bekliyor.

## 2.7.51
- iPhone: bölüm sayfalarında görünür "‹ Ana Sayfa" düğmesi; kenardan kaydırarak geri gitme (tarayıcı geçmişi) artık bölümler arasında çalışır. Gerçek cihaz testi bekliyor.

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

## 2.7.38
- **Kendi Mac'inden kilitlenme düzeltildi:** yalnız 127.0.0.1'e açık sunucuda "çok fazla yanlış deneme" kilidi kaldırıldı (eski bir sekmenin geçersiz belirteci 5 denemede giriş bağlantısını da engelliyordu; Launchpad simgesi ve Güncelleme açılamıyordu). Uzak (iPhone) sunucuda kilit sürer.

## 2.7.39
- Launchpad uygulaması açık kalır (Dock'ta görünür): "stay open" uygulama olarak yeniden oluşturulur; Dock simgesine tekrar tıklayınca Ülgen yeniden açılır. Mac'te denenmedi.

## 2.7.40
- Ayarlar > "Kendi ses dosyalarınız": çıplak dosya kutusu yerine **Dosya seç (mp3)** düğmesi; 4 MB üstü dosya yüklenmeden önce açık iletiyle bildirilir; yükleme hatası artık sessiz kalmaz, nedeni yazılır.

## 2.7.41
- Kılavuz aktarımı içeriğe bakar: adı .pdf olan Word/zip dosyaları artık tanınır (Word dosyaları Obsidian notuna çevrilir), okunamayan dosya bir kez bildirilip değişene dek atlanır; .docx uzantısı da desteklenir.
- `simge_kur.sh` sonunda `simge_temizle.sh` çalıştırır: yeniden kurulumdan sonra Launchpad'de çift Ülgen simgesi kalmaz.

## 2.7.42
- Kılavuz aktarıcısı **HTML** dosyalarını da alır (.html/.htm): ChatGPT dışa aktarımındaki `chat.html` konuşma başına bir Obsidian notuna (`Yapay Zekâ Konuşmaları/ChatGPT/`), diğer HTML dosyaları (Gemini vb.) okunur Markdown'a çevrilir (`Yapay Zekâ Konuşmaları/<dosya adı>/`).

## 2.7.43
- Kılavuz aktarıcısı **Google Earth KML/KMZ** dosyalarını okur: her arazi için alan (m² ve dönüm), çevre, merkez noktası, harita bağlantısı ve köşe koordinatlarıyla `Arazi/<dosya adı>.md` notu yazar (ölçüm yerel düzlem yaklaşımıyla; küçük parsellerde hata binde birin altındadır).

## 2.7.44
- Arazi, tapu, parsel, adres ve konum soruları duyarlı sayılır: bulut beyne (Gemini vb.) gönderilmez, yerel beyin yoksa kuyruğa alınır.
- Kişilik yönergesine eklendi: model "mutlak gizlilik protokolü" gibi kural uydurmaz; kullanıcının arazi/ev/proje bilgilerini yerelde tutabilir, gizlilik gerekçesiyle bilgi almayı reddetmez.

## 2.7.45
- `ulgen/varlik/Yerel Beyin Kur.command`: Ollama olmadan yerel beyin kurulumu (llama.cpp + Gemma 3 4B Q4_K_M, ~2,5 GB, 127.0.0.1:8080, açılışta kendiliğinden). Mac'te denenmedi.

## 2.7.46
- Güncelleme sonrası `.command` ve `.sh` dosyalarına çalıştırma izni verilir (zip açılırken izin kayboluyor, "yetkiniz yok" hatası çıkıyordu).

## 2.7.47
- Yapay Zekâ Modelleri: **Beyinleri aç / kapat** bölümü. Yerel (llama.cpp, Ollama) ve bulut (Gemini, NVIDIA, Groq, Mistral, OpenRouter) beyinlerin her biri ayrı ayrı kapatılıp açılabilir; kapalı beyin hiç denenmez (`kapali_beyinler` ayarı, `/yz/saglayici`).

## 2.7.48
- Yerel beyin hızlandırma (log: istem işleme saniyede ~11 token; her yanıt ~2 dk sürüyordu): llama-server yalnız işlemciyle çalışır (`-ngl 0`, eski Intel Mac'te ekran kartı belleği taşırıyor); yerel beynin istemi kısaltıldı (sistem 2200, geçmiş 700 token); zaman aşımı 300 sn; yavaş Mac için `ULGEN_MODEL=1b` ile Gemma 3 1B seçeneği.

## 2.7.49
- Yeni beyin kipi **Hızlı**: sıradan sorular önce buluta (Gemini vb., hızlı) gider; arazi, sağlık, kimlik gibi özel sorular buluta GİTMEZ, yalnızca yerel beyinde yanıtlanır (yerel yoksa kuyruğa alınır). Yerel beyin yavaş olan Mac için önerilir.

## 2.7.50
- **iPhone adresi açılmıyordu:** ZeroTier macOS'ta ağ arayüzünü `zt...` değil `feth...` adıyla açar; Ülgen yalnız `zt` aradığı için HTTPS (8443) ve sertifika (8766) dinleyicileri hiç başlamıyordu. Artık `feth` arayüzleri de bulunur (bağlantı-yerel 169.254 adresler atlanır).
