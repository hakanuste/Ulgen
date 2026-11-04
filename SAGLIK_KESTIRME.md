# Sağlık verisini Ülgen'e aktarma (iPhone Kestirmeler)

Veri yalnızca ZeroTier ağında kendi Mac'inize gider; buluta çıkmaz.
Ülgen yalnızca gösterir; tıbbi öneri vermez.

Kaynak zinciri: Saat/F800/Joeme Fit → Apple Sağlık → Kestirme → Ülgen.
**Joeme Fit'in Apple Sağlık'a yazıp yazmadığı denenmedi.** Sağlık uygulaması >
Paylaşım > Uygulamalar'da Joeme Fit görünmüyorsa o veri gelmez; iPhone'un kendi
adım/nabız verisi yine gelir.

## 1. Kestirme için ayrı anahtar (Mac'te, bir kez)

```
cd ~/Ülgen && ortam/bin/python -m ulgen --cihaz-ekle iphone-kestirme
```

Çıkan uzun belirteci kopyalayıp iPhone'a (AirDrop / Notlar) gönderin. Başkasına
göstermeyin. İptal etmek için o cihazı Ülgen'den silmeniz yeter.

## 2. Önce elle deneme (Mac'te)

Aşağıdaki komut çalışırsa iPhone tarafı da çalışır. `BELİRTEÇ` yerine kendi
belirtecinizi yazın:

```
curl -sk -X POST https://10.28.199.147:8443/saglik/ozet \
  -H "Authorization: Bearer BELİRTEÇ" -H "Content-Type: application/json" \
  -d '{"adim": 1234, "nabiz": 70}'
```

Yanıt `{"eklenen": 2, "atlanan": 0}` olmalı; Ülgen'de Sağlık sayfasında 1234 adım
görünür.

## 3. Kestirme (iPhone, Kestirmeler uygulaması)

Yeni kestirme > adı **Ülgen Sağlık**. Eylemleri sırayla ekleyin:

1. **Sağlık Örneklerini Bul** — Tür: *Adım Sayısı*, Başlangıç Tarihi: *bugün*.
   **İstatistikleri Hesapla eylemi gerekmez**: örneklerin *Değer* listesini
   doğrudan gönderin, toplamı Ülgen yapar.
2. **Sağlık Örneklerini Bul** — Tür: *Kalp Atış Hızı*, Sırala: *Başlangıç Tarihi,
   en yeni önce*, Sınır: *1*. (Sonuç: son nabız değeri.)
3. İsteğe bağlı, **uyku**: **Sağlık Örneklerini Bul** — Tür: *Uyku Analizi*,
   Başlangıç Tarihi: *dün 18:00 sonrası*; **İstatistikleri Hesapla** — *Toplam*
   (Süre, dakika). Uyku bölümleri sürüme göre farklı görünebilir; sonuç mantıksız
   çıkarsa bu adımı atlayın (alan isteğe bağlıdır).
4. **URL İçeriğini Al**
   - URL: `https://10.28.199.147:8443/saglik/ozet`
   - Yöntem: **POST**
   - Başlıklar: `Authorization` = `Bearer ` + belirteciniz
   - İstek Gövdesi: **JSON**. Alanlar (tür *Sayı*):
     `adim` = adım örneklerinin *Değer* listesi (toplamı Ülgen yapar), `nabiz` = nabız değeri, `uyku_dk` = uyku toplamı
     (dakika; saat olarak göndermek isterseniz `uyku_saat`). Hepsi isteğe bağlıdır.
5. İsteğe bağlı: **Bildirim Göster** — "Sağlık verisi Ülgen'e gönderildi".

Kabul edilen alanlar: `adim`, `nabiz`, `uyku_dk`, `uyku_saat`, `aktif_dakika`,
`kalori`. Zaman Ülgen'de damgalanır. Adım, uyku, aktif dakika ve kalori günlük
toplamdır; aynı gün tekrar gönderilirse güncellenir (çift kayıt olmaz).

## 4. Otomatik çalıştırma

Kestirmeler > **Otomasyon** > Kişisel Otomasyon > **Günün Saati** (örn. 21:00,
bir de 07:30) > **Kestirmeyi Çalıştır: Ülgen Sağlık** > **Hemen Çalıştır** (soru
sormasın) .

Dürüst sınırlar:
- İstek, iPhone'da **ZeroTier VPN açıkken** Mac'e ulaşır. ZeroTier One'da
  *Enable On Demand (beta)* açık olsa bile ilk istekte bağlanma gecikebilir; olmazsa
  kestirme hata verir ve o gün gönderilmez (ertesi gün toplam yine gelir).
- Mac uykudaysa ya da Ülgen kapalıysa istek ulaşmaz.
- Başlık olarak `Authorization: Bearer …` yerine `X-Ulgen-Token` = belirteç de olur.
- Başlık hiç iletilmezse (günlükte "Authorization YOK"): JSON gövdesine metin alanı `belirtec` = belirteç ekleyin.
- Eski gelişme: `/saglik/veri` (tam ölçüm listesi, en çok 500 öğe) hâlâ çalışır.
- Gerçek iPhone'da denenmedi; alan adları ve eylem adları iOS sürümünüze göre
  küçük farklar gösterebilir.
