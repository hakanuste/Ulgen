# Mimari

```
iPhone (Safari/PWA) ──HTTPS 8443──┐        Mac tarayıcı ──HTTP 127.0.0.1:8765──┐
 (ZeroTier, cihaz belirteci)      │                                            │
                                  ▼                                            ▼
                         sunucu.py (Host/Origin/Content-Type, hız sınırı, TLS)
                                  │
                           cekirdek.Ulgen ── ONAY / hızlı komut / araç döngüsü
        ┌──────────┬─────────────┼──────────────┬───────────────┐
     beyin.py   baglam.py     hafiza.py     araclar.py      zamanlayici.py
   (Ollama,     (bütçe,      (memory.json,  (dosya, sistem,  (SQLite)
   llama.cpp,    özet,        AES-256-GCM)   terminal)
   Gemini)       kasa)                           │
                                          guvenlik.py (izin listesi, ONAY)
                                          ajanlar.py (araştırma, sağlık, sabah, dosya)
   veritabani.py (SQLite)  gizli.py (şifreleme, Anahtar Zinciri)  tls.py (CA)
   cihazlar.py (belirteçler)  yedek.py (şifreli yedek)  ses.py  arayuz.py
```

Veri klasörü `~/ÜlgenVeri` (izin 700): `veri.db`, `memory.json` (şifreli), `ayar.json`, `tls/`, `sirlar.bin` (Mac dışı), `bellek.anahtar` (Anahtar Zinciri yoksa), `dosyalar/`, `saglik/`, `yedekler/`.

İlkeler: yerel öncelik; kişisel veri varsayılan buluta gitmez; tehlikeli işlem ancak kullanıcının kendi ONAY'ıyla; web/dosya içeriği "güvenilmez veri".

## Değişmez mimari kararlar (kullanıcı kararı, 2026-11-02)

1. MacBook Air ana merkezdir; iPhone 14 Plus mobil istemcidir.
2. Yerel ve internetli çalışma birlikte bulunur; internet kesilince yerel işlevler sürer.
3. AI kotası dolsa bile zamanlayıcı durmaz (zamanlayıcı modelden bağımsızdır).
4. Ücretli servise otomatik geçilmez; ücretli kullanım kodla kapalıdır.
5. Hassas veriler (sağlık, ilaç, hafıza, kasa) buluta gönderilmez.
6. Kullanıcı onayı olmadan önemli değişiklik yapılmaz.
7. **İlaç dozlarını Ülgen değiştirmez.** İlaç/doz kayıtlarını yalnızca kullanıcı (arayüz/CLI, ONAY ile) ekler ve düzenler; model araçlarının ilaç tablosuna yazma yetkisi yoktur. Ülgen yalnızca hatırlatır ve alındı/ertelendi/alınamadı yanıtını kaydeder.

## İlaç onay modeli (kullanıcı kuralı, 2026-11-02)

Üç katman: **ilaç** (ad, doz bilgisi — yalnızca kullanıcı girer) → **plan saati** (08:00, 14:00, 20:00...) → **doz örneği** (o gün, o saat için oluşan kayıt; kendi kimliği ve durumu vardır: bekliyor / alındı / almadı / ertelendi / atlandı / tamamlandı).
Bir onay **yalnızca bir doz örneğini** değiştirir. Aynı ilacın başka saatini, başka bir ilacı, ertesi günün aynı saatini ve genel hatırlatmaları etkilemez. Birden fazla doz bekliyorsa "tamam" onay vermez; Ülgen hangisini sorar. Kabul testi: A ilacı 08:00 ve 20:00, B ilacı 08:00 → A-08:00 onayı A-20:00, B-08:00 ve yarınki A-08:00'ı değiştirmemeli.
