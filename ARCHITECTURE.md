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
