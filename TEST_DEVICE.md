# Gerçek Cihaz Doğrulama Listesi

Önce Mac'te: `~/Ülgen/ortam/bin/python -m ulgen --tani` (sırsız rapor). Sonra aşağıyı işaretleyin, sonucu bana yazın.
"Cihazda doğrulandı" ancak buradaki madde işaretlenince PROJECT_STATUS.md'de yazılır.

## Mac
- [ ] Kurulum çift tıkla bitti; veri yedeği `~/ÜlgenVeri/yedekler/kurulum-*` oluştu
- [ ] Tanı: veritabanı ŞİFRELİ, anahtar Anahtar Zinciri'nde
- [ ] launchd görevi yüklü, yeniden başlatınca sunucu kalktı
- [ ] Launchpad > Ülgen tarayıcıda giriş yaptırıyor (belirteç sormadan)
- [ ] Aynı bağlantı ikinci kez açılınca reddediliyor
- [ ] ZeroTier adresi tanıda görünüyor

## iPhone
- [ ] Sertifika yüklendi ve güvenildi, https://<ZeroTier>:8443 açılıyor
- [ ] Sohbet, mikrofon, Ana Ekrana Ekle çalışıyor
- [ ] `--takvim-deneme` alarmı kilit ekranında çaldı (Mac kapalıyken de)
- [ ] İlaç takvimi aktarıldı, bir doz yanıtı yalnız o dozu etkiledi

## Eklenen cihaz denemeleri (2.7)
- [ ] `python -m ulgen --dene nvidia` → "ÇALIŞTI" görmeli (anahtar: `--sir-kaydet nvidia`).
- [ ] `pip install faster-whisper`, `brew install ffmpeg`, `python -m ulgen --ses-modeli-indir`; iPhone'da mikrofon düğmesi → Türkçe cümle; Wi-Fi kapalıyken de çalışmalı.
- [ ] Kestirme (SAGLIK_KESTIRME.md) → Sağlık sekmesinde değerler.
- [ ] Safari: Dynamic Island, klavye kayması, CSP hatası yok (Web Denetçisi).
- [ ] 07:30 / 21:00'de sabah/akşam raporu bildirimi geldi mi.
