# Ülgen'in sesi: internetsiz, sizin sesinizle

Ülgen yanıtları **Piper** ile Mac'te sese çevirir. Metin hiçbir yere
gönderilmez, internet gerekmez; kişisel yanıtlar da okunur.

## 1. Hazır Türkçe sesle başlayın (bir kez internet gerekir)

1. Ülgen > **Ayarlar** > **Ülgen'in kendi sesi (Piper, internetsiz)**.
2. **Piper'ı kur** (~40 MB, birkaç dakika).
3. **Türkçe sesi indir** (~63 MB, "tr_TR-dfki-medium").
4. **Bu sesle oku: açık**, sonra **Dene**.

Bundan sonra internet gerekmez.

## 2. Kendi sesinizi kaydedin

1. Aynı bölümde **Kendi sesimi kaydet**.
2. Sessiz bir oda, mikrofona yakın, doğal ses. Ekrandaki cümleyi okuyun:
   **● Kaydı başlat** → okuyun → **■ Bitir** → **Dinle** → **Kaydet ve sonraki**.
3. Yanlış okursanız **Son kaydı sil**; okuyamadığınız cümlede **Atla**.
4. Hedef **45 dakika** (~500 cümle). Birkaç oturuma bölebilirsiniz; kaldığınız
   yerden sürer. Hazır cümleler bitince kasadaki kitaplarınızdan cümle gelir.
5. Kayıtlar Mac'te `~/ÜlgenVeri/ses_kaydi/` içinde durur.

## 3. Modeli eğitin (Google Colab, ücretsiz GPU, birkaç saat)

1. **Eğitim paketini indir** → `ses_veri.zip`.
2. `docs/piper_egitim.ipynb` dosyasını Google Colab'da açın
   (colab.research.google.com > Yükle).
3. *Çalışma zamanı türü: T4 GPU* seçin, hücreleri sırayla çalıştırın.
   4. adımda `ses_veri.zip`'i yükleyin.
4. Eğitim bitince deneme sesini dinleyin, iki dosyayı indirin:
   `tr_TR-hakan-medium.onnx` ve `tr_TR-hakan-medium.onnx.json`.

Eğitim yalnızca bu aşamada, sizin Google hesabınızda yapılır; kayıtlarınızı
eğitimden sonra Drive'daki `ulgen_ses` klasöründen silebilirsiniz.

## 4. Ülgen'e koyun

İki dosyayı Mac'te `~/ÜlgenVeri/sesler/` klasörüne kopyalayın. Ülgen >
Ayarlar > Ülgen'in kendi sesi listesinde **"(kendi sesiniz)"** olarak
görünür; seçip **Bu sesle oku: açık**.

Aynı iki dosya Raspberry Pi'de de çalışır.
