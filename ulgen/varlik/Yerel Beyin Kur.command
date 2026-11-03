#!/bin/bash
# Yerel beyin kurulumu (Ollama gerekmez): llama.cpp + Gemma 3 4B (Türkçe iyi, ~2,5 GB).
# -ngl 0: yalnız işlemci. (Eski Intel Mac'lerde ekran kartı kullanımı belleği taşırıp çok yavaşlatıyor.)
# Yaptıkları: llama.cpp'yi Homebrew ile kurar, modeli ~/ÜlgenVeri/modeller/ klasörüne indirir
# (yarıda kesilirse kaldığı yerden sürer), arka planda 127.0.0.1:8080 adresinde çalıştırır.
# Hiçbir veri dışarı gitmez; yalnızca model dosyası Hugging Face'ten indirilir.
set -u
VERI="$HOME/ÜlgenVeri"
MODELLER="$VERI/modeller"
# Varsayılan: Gemma 3 4B (~2,5 GB, daha akıllı). Yavaş Mac için: ULGEN_MODEL=1b bash "Yerel Beyin Kur.command"
if [ "${ULGEN_MODEL:-4b}" = "1b" ]; then
  MODEL="$MODELLER/gemma-3-1b-it-Q4_K_M.gguf"
  ADRES="https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf"
  BOYUT_ALT=800000000           # ~806 MB beklenir
else
  MODEL="$MODELLER/gemma-3-4b-it-Q4_K_M.gguf"
  ADRES="https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf"
  BOYUT_ALT=2400000000          # ~2,49 GB beklenir
fi
AJAN="$HOME/Library/LaunchAgents/com.ulgen.yerelbeyin.plist"
adim() { printf '\n==> %s\n' "$1"; }
dur() { printf '\nHATA: %s\n' "$1"; read -r -p "Kapatmak için Enter'a basın." _; exit 1; }

adim "1/4  llama.cpp aranıyor"
BREW="$(command -v brew || ls /usr/local/bin/brew /opt/homebrew/bin/brew 2>/dev/null | head -1)"
SUNUCU="$(command -v llama-server || ls /usr/local/bin/llama-server /opt/homebrew/bin/llama-server 2>/dev/null | head -1)"
if [ -z "$SUNUCU" ]; then
  [ -n "$BREW" ] || dur "Homebrew bulunamadı. https://brew.sh adresindeki komutla kurup bunu yeniden çalıştırın."
  echo "llama.cpp kuruluyor (birkaç dakika sürebilir)..."
  "$BREW" install llama.cpp || dur "llama.cpp kurulamadı. Çıktıyı bana gönderin."
  SUNUCU="$(command -v llama-server || ls /usr/local/bin/llama-server /opt/homebrew/bin/llama-server 2>/dev/null | head -1)"
fi
[ -x "$SUNUCU" ] || dur "llama-server bulunamadı."
echo "llama-server: $SUNUCU"

adim "2/4  Model indiriliyor (~2,5 GB)"
mkdir -p "$MODELLER"
boyut() { stat -f%z "$MODEL" 2>/dev/null || echo 0; }
if [ "$(boyut)" -lt "$BOYUT_ALT" ]; then
  curl -L -C - --fail --progress-bar -o "$MODEL" "$ADRES" || dur "Model indirilemedi (internet?). Komutu yeniden çalıştırırsanız kaldığı yerden sürer."
fi
[ "$(boyut)" -ge "$BOYUT_ALT" ] || dur "Model eksik indi ($(boyut) bayt). Yeniden çalıştırın."

adim "3/4  Arka plan hizmeti kuruluyor"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$AJAN" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.ulgen.yerelbeyin</string>
  <key>ProgramArguments</key><array>
    <string>$SUNUCU</string><string>-m</string><string>$MODEL</string>
    <string>--host</string><string>127.0.0.1</string><string>--port</string><string>8080</string>
    <string>-ngl</string><string>0</string>
    <string>-c</string><string>4096</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$VERI/yerelbeyin.log</string>
  <key>StandardErrorPath</key><string>$VERI/yerelbeyin.log</string>
</dict></plist>
PLISTEOF
launchctl unload "$AJAN" 2>/dev/null
launchctl load "$AJAN" || dur "Hizmet başlatılamadı."

adim "4/4  Hazır olması bekleniyor (model belleğe yüklenir, 1-2 dk)"
for i in $(seq 1 60); do
  if curl -s -m 2 http://127.0.0.1:8080/v1/models | grep -q '"data"'; then
    echo "Yerel beyin çalışıyor."
    echo "Ülgen'de: Yapay Zekâ Modelleri > Yalnız yerel."
    read -r -p "Kapatmak için Enter'a basın." _; exit 0
  fi
  sleep 3
done
dur "Hizmet 3 dakikada hazır olmadı. $VERI/yerelbeyin.log dosyasının son satırlarını bana gönderin."
