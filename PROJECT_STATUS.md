# Proje Durumu

Son güncelleme: Aşama 1 sonu + ek şartname birleştirmesi (2026-11-02).
Durum sözlüğü ve tüm özellik matrisi: **ROADMAP.md** (tek ana plan).

| Aşama | Durum |
|-------|-------|
| 0 Denetim | tamamlandı |
| 1 Kritik güvenlik | tamamlandı, 49 test yeşil; Mac/iPhone adımları gerçek cihaz testi bekliyor |
| 2 Veritabanı + gelişmiş hafıza | geliştirilmedi (sırada) |
| 3 Sağlayıcılar, kota, kuyruk | geliştirilmedi |
| 4 Görev + doz başına ilaç takibi | geliştirilmedi — **ilaç onayı hâlâ toplu (bilinen hata)** |
| 5 iPhone arayüzü + yönetim paneli | kısmen (yalnızca sohbet) |
| 6 Özel Kasa + Face ID | geliştirilmedi; Face ID için teknik engel (PWA/native) |
| 7 Ses + sağlık köprüsü | kısmen (elle dışa aktarılan sağlık verisi okunuyor; çevrimdışı STT yok) |
| 8 Raporlar + bütünleşik test | kısmen (yalnızca sabah haber+sağlık özeti) |

Bekleyen kararlar: ROADMAP.md sonu.

## Aşama 2 durumu
Tamamlandı ve test edildi (benzetim): veritabanı göç/işlem/bütünlük/yedek-kurtarma, hafıza modeli, duyarlı depo ayrımı.
Kısmen: iPhone arayüzünde geçmiş/hafıza sayfaları geliştirilmedi (Aşama 5); `veri.db` diskte şifresiz (yedekleri şifreli).

## Aşama 3 durumu
Kodlandı, benzetimde test edildi: sağlayıcı yöneticisi, kota sayacı, kuyruk. Gerçek hesaplarla denenmedi (anahtar gerekir).
Kısmen: iPhone arayüzünde kota paneli yok (yalnızca `kota` komutu ve `/kota` JSON; panel Aşama 5).
Not: Groq/Mistral/Gemini'de "ücretsiz" hesap düzeyindedir; anahtarınıza fatura kartı eklemeyin. Ülgen bunu ağdan doğrulayamaz.

Kod penceresi: tamamlandı ve test edildi (benzetim + Chromium ekran denemesi). iPhone'da denenmedi; telefon klavyesinde uzun kod yazımı rahat olmayabilir.
