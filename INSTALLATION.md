# Kurulum

1. Zip'i açın, **Ülgen Kur.command** dosyasına çift tıklayın (ilk seferde sağ tık → Aç).
2. Mac'te: Launchpad → **Ülgen** (`http://127.0.0.1:8765`).
3. iPhone (bir kez):
   1. Mac'te: `~/Ülgen/ortam/bin/python -m ulgen --cihaz-ekle iPhone` → belirteci kopyalayın (bir kez gösterilir).
   2. iPhone Safari: `http://<Mac'in ZeroTier adresi>:8766` → sertifikayı indirin → Ayarlar → Genel → VPN ve Aygıt Yönetimi → Yükle → Ayarlar → Genel → Hakkında → Sertifika Güven Ayarları → açın.
   3. Safari: `https://<Mac'in ZeroTier adresi>:8443` → belirteci yapıştırın → Paylaş → Ana Ekrana Ekle.
4. Beyin: Ollama (macOS 14+), llama.cpp (`llama-server`, 8080) ya da Gemini anahtarı (kurulumda sorulur; Anahtar Zinciri'ne yazılır).

Yönetim: `--cihazlar`, `--cihaz-iptal N`, `--sir-kaydet gemini|groq|mistral|openrouter`, `--yedek-al DOSYA`, `--yedek-yukle DOSYA`.
Ayrıntılar: KURULUM.txt. **Sertifika adımları iPhone'da denenmedi.**
