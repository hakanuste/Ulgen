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
