# ÜLGEN – GÜVENLİK RAPORU

Güncelleme: Aşama 1 sonu · Durum sütunu yalnızca **testle doğrulananı** "Düzeltildi" sayar.

## Aşama 1'de düzeltilenler

| # | Bulgu | Durum | Nasıl | Doğrulayan test |
|---|-------|-------|-------|-----------------|
| S1 | Komut kara listesi atlatılıyordu | **Düzeltildi** | Kara liste kaldırıldı; **izin listesi**: yalnızca salt okunur 23 komut onaysız. Listede olmayan her komut, birleşik/yönlendirmeli komut, mutlak yol ile verilen komut → ONAY. Gizli yollar (`~/ÜlgenVeri`, `.ssh`, `/etc`...) ve üst klasörde `grep -r` de ONAY ister | `test_guvenlik.KomutAnaliz`, `Enjeksiyon` |
| S2 | CSRF / DNS rebinding | **Düzeltildi** | Host yalnızca IP, `localhost` ya da `izinli_hostlar`; `Origin` aynı kaynak olmalı, `Sec-Fetch-Site: cross-site` ve `Origin: null` reddedilir; POST yalnızca `application/json` (415) | `test_sunucu.YerelSunucu` |
| S3 | `0.0.0.0` dinleme | **Düzeltildi** | Yalnızca `127.0.0.1` ve ZeroTier (`zt*`) adresleri; adres değişince dinleyiciler yenilenir | `test_loopback_dinleme` + gerçek süreç denemesi |
| S4 | Tek sabit anahtar, deneme sınırı yok | **Düzeltildi** | Cihaz başına 256 bit belirteç, veritabanında yalnızca SHA-256 özeti, iptal, isteğe bağlı süre; IP başına 5 yanlış denemede 5 dk engel (429) | `UzakSunucu`, `Belirtec` |
| S5 | HTTPS yok | **Düzeltildi (Linux'ta)** | Yerel CA + sunucu sertifikası (ECDSA P-256, 1 yıl, kendiliğinden yenilenir), TLS ≥ 1.2; iPhone'a CA bir kez yüklenir | `UzakSunucu`, `Sertifika` |
| S6 | Model/komut onaysız hafıza silebiliyordu | **Düzeltildi** | `hafiza_unut` ve `unut:` ONAY ister (kaç kayıt silineceği gösterilir) | `test_model_hafiza_silemez_onaysiz` |
| S7 | `veri.db` vb. terminalden okunabiliyordu | **Düzeltildi** | `~/ÜlgenVeri` kritik; yalnızca `dosyalar` ve `saglik` alt klasörleri açık | `test_gizli_veri_korunur` |
| S8 | API anahtarı `ayar.json`'da düz yazı | **Düzeltildi (Mac'te doğrulanmadı)** | Anahtar Zinciri; olmazsa şifreli `sirlar.bin`. Yedeğe girmez. Linux yedek yolu testli, Anahtar Zinciri yolu **Mac'te denenmedi** | `test_sirlar` |
| S9 | Fernet (AES-128) | **Düzeltildi** | AES-256-GCM (`ULGEN2:`), eski kayıt okunur ve yenilenir; kurcalama algılanır | `test_sifreleme.Sifreleme` |
| S10 | Bağlantı/zaman aşımı sınırı yok | **Düzeltildi** | En çok 32 eşzamanlı bağlantı, 15 sn soket zaman aşımı, 200 KB gövde sınırı | kod; yük testi Aşama 8 |
| V1 | Yedek yok | **Kısmen** | Parola + scrypt + AES-256-GCM şifreli yedek, doğrulama, yol geçişi ve bozuk veritabanı koruması, geri yüklemede eski dosyalar silinmez. Zamanlanmış yedek ve yönetim ekranı Aşama 2/5 | `test_sifreleme.Yedek` |
| S11 | CSP başlığı yok | **Düzeltildi** | CSP, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` | kod |

## Bilinen kalan riskler (dürüst liste)

1. **Mac'in kendi adresi (`127.0.0.1`) belirteçsiz güvenilir.** Aynı Mac'te çalışan başka bir süreç ya da kullanıcı Ülgen'e erişebilir. Tarayıcıdan gelen saldırılar S2 önlemleriyle kapalıdır; yerel kötü yazılıma karşı koruma yoktur. İstenirse yerel erişim de belirteçli yapılabilir (Aşama 5'te değerlendirilecek).
2. **ONAY verilen komut tam yetkiyle çalışır.** Kod kullanıcıya gösterilen komutu onaylar; kullanıcı metne dikkat etmezse zarar verebilir.
3. **Anahtar Zinciri'ne yazarken** (`security add-generic-password -w`) değer komut satırında kısa süre aynı kullanıcının süreçlerince görülebilir. macOS'ta betikten yazmanın başka yolu yok.
4. **CA özel anahtarı** Mac'te, ana anahtarla şifreli durur. Çalınırsa, CA'yı yüklemiş iPhone sahte sertifikalara güvenebilir. Ad kısıtlaması (NameConstraints) iOS'ta güvenilir desteklenmediği için kullanılmadı (**doğrulanmadı**). CA'yı iPhone'dan kaldırmak (Ayarlar → VPN ve Aygıt Yönetimi) riski bitirir.
5. **Bulut sağlayıcılar**: kişisel veri varsayılan olarak gitmez; ekran çözümleme açıkça izin ister. Sağlayıcı koşulları Aşama 3'te incelenecek.
6. **Şifreli olmayan**: `veri.db` (sohbet, not, hatırlatma) hâlâ düz SQLite. Yedekleri şifreli, ama canlı dosya değil. Aşama 2/6'da değerlendirilecek.
7. **Sistem yeniden başlatma, uzun süreli çalışma, yük** sınamaları Aşama 8'de.
8. Mac'e özgü kodlar (Anahtar Zinciri, ZeroTier arayüz bulma `ifconfig`, `launchd`) ve iPhone'da sertifika yükleme **denenmedi**.

## Değişiklik (geri uyumluluk)

- ZeroTier adresinden eski `http://<ip>:8765` artık **çalışmaz**. Yeni: `https://<ip>:8443` (önce `http://<ip>:8766` ile sertifikayı yükleyin).
- Eski `anahtar.txt` açılışta cihaz belirtecine çevrilir ve dosya silinir; iPhone'daki kayıtlı anahtar çalışmaya devam eder (ancak HTTPS'e geçmeniz gerekir).
