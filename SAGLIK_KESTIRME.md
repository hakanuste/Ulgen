# Sağlık verisini Ülgen'e aktarma (iPhone Kestirmeler)

Veri yalnızca ZeroTier ağında kendi Mac'inize gider; buluta çıkmaz.
Kaynak zinciri: F800 / Joeme Fit → Apple Sağlık → Kestirme → Ülgen.
**Joeme Fit'in Apple Sağlık'a yazıp yazmadığı denenmedi**; Sağlık uygulamasında
Kaynaklar bölümünde Joeme Fit görünmüyorsa bu zincir kurulamaz.

1. Kestirmeler → yeni kestirme "Ülgen Sağlık".
2. "Sağlık Örneklerini Bul": Adım Sayısı, bugün → "Hesapla: Toplam".
3. "Metin" eylemi (JSON): `{"olcumler":[{"tur":"adim","deger":<toplam>,"zaman":"<bugün>T12:00:00"}]}`
   (tür: adim, nabiz, uyku (dakika), aktif_dakika, kalori; en çok 500 öğe).
4. "URL İçeriğini Al": `https://<zerotier-adı>:8443/saglik/veri`, yöntem POST,
   başlık `Authorization: Bearer <cihaz belirteci>` ve `Content-Type: application/json`.
5. Otomasyon sekmesi: her gün 21:00 ve 07:00 bu kestirmeyi çalıştırın.
Belirteç: `python -m ulgen --cihaz-ekle iphone-kestirme`.
