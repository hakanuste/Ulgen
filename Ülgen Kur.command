#!/bin/bash
# Ülgen kurulumu: bu dosyaya çift tıklamanız yeterlidir.
# Yaptıkları: ~/Ülgen klasörüne kurar, sanal ortam (venv) açar, gereken
# ücretsiz kütüphaneleri yükler, açılışta kendiliğinden başlatır ve
# Launchpad'e "Ülgen" uygulamasını koyar.
set -u
KAYNAK="$(cd "$(dirname "$0")" && pwd)"
HEDEF="$HOME/Ülgen"
VERI="$HOME/ÜlgenVeri"
AJAN="$HOME/Library/LaunchAgents/com.ulgen.sunucu.plist"
MAC=0; [ "$(uname)" = "Darwin" ] && MAC=1
[ "${ULGEN_DRY:-0}" = "1" ] && MAC=0

adim() { printf '\n==> %s\n' "$1"; }
dur() { printf '\nHATA: %s\n' "$1"; read -r -p "Kapatmak için Enter'a basın." _; exit 1; }

adim "1/6  Python aranıyor"
PY=""
for aday in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 "$(command -v python3 || true)"; do
  if [ -n "$aday" ] && [ -x "$aday" ] && "$aday" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
    PY="$aday"; break
  fi
done
[ -n "$PY" ] || dur "Python 3.8 ya da üstü bulunamadı. Terminal'de 'brew install python' yazıp kurulumu yeniden çalıştırın."
echo "Python: $PY ($("$PY" -V 2>&1))"

adim "2/6  Dosyalar kopyalanıyor ($HEDEF)"
mkdir -p "$HEDEF" "$VERI" || dur "Klasörler oluşturulamadı."
chmod 700 "$VERI"
rm -rf "$HEDEF/ulgen"
cp -R "$KAYNAK/ulgen" "$HEDEF/ulgen" || dur "Dosyalar kopyalanamadı."
cp "$KAYNAK/requirements.txt" "$KAYNAK/requirements-ses.txt" "$HEDEF/" 2>/dev/null
find "$HEDEF/ulgen" -name '__pycache__' -type d -prune -exec rm -rf {} +

adim "3/6  Sanal ortam ve kütüphaneler (birkaç dakika sürebilir)"
if [ ! -x "$HEDEF/ortam/bin/python" ]; then
  "$PY" -m venv "$HEDEF/ortam" || dur "Sanal ortam oluşturulamadı."
fi
"$HEDEF/ortam/bin/python" -m pip install --quiet --upgrade pip
"$HEDEF/ortam/bin/python" -m pip install --quiet -r "$HEDEF/requirements.txt" \
  || dur "Kütüphaneler yüklenemedi. İnternet bağlantınızı denetleyip yeniden çalıştırın."
"$HEDEF/ortam/bin/python" -c 'import sys; sys.path.insert(0, "'"$HEDEF"'"); import ulgen.cekirdek' \
  || dur "Ülgen yüklenemedi."
"$HEDEF/ortam/bin/python" -m ulgen --anahtar >/dev/null

adim "4/6  Beyin (ücretsiz)"
if [ "$MAC" = "1" ]; then
  ANAHTAR="$(osascript -e 'text returned of (display dialog "İsteğe bağlı: ücretsiz Gemini anahtarınız varsa yapıştırın (aistudio.google.com). Yoksa boş bırakıp Tamam deyin.\n\nNot: ücretsiz katmanda gönderilen metinler Google tarafından ürün geliştirmede kullanılabilir. Ülgen kişisel verilerinizi (hafıza, sağlık, notlar) bulutta VARSAYILAN olarak göndermez." default answer "" with title "Ülgen")' 2>/dev/null || true)"
  if [ -n "$ANAHTAR" ]; then
    ULGEN_ANAHTAR="$ANAHTAR" "$HEDEF/ortam/bin/python" - <<'PYEOF'
import json, os, sys
sys.path.insert(0, os.path.expanduser("~/Ülgen"))
from ulgen import ayar
ayar.sablon_olustur()
with open(ayar.AYAR_DOSYASI, encoding="utf-8") as f:
    a = json.load(f)
a["gemini_anahtar"] = os.environ["ULGEN_ANAHTAR"].strip()
with open(ayar.AYAR_DOSYASI, "w", encoding="utf-8") as f:
    json.dump(a, f, ensure_ascii=False, indent=2)
os.chmod(ayar.AYAR_DOSYASI, 0o600)
print("Gemini anahtarı kaydedildi.")
PYEOF
  fi
fi
if command -v ollama >/dev/null 2>&1; then
  echo "Ollama bulundu; llama3.2:3b modeli indiriliyor (ilk seferde birkaç GB)."
  ollama pull llama3.2:3b || echo "Model indirilemedi; sonra 'ollama pull llama3.2:3b' deneyin."
elif command -v llama-server >/dev/null 2>&1; then
  echo "llama.cpp bulundu. Sunucuyu 8080 kapısında başlatırsanız Ülgen onu kullanır."
else
  echo "Yerel beyin (Ollama ya da llama.cpp) bulunamadı. Gemini anahtarı girdiyseniz"
  echo "Ülgen onunla çalışır; yerel beyin için KURULUM.txt dosyasındaki 5. bölüme bakın."
fi

adim "5/6  Açılışta kendiliğinden başlatma"
if [ "$MAC" = "1" ]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$AJAN" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.ulgen.sunucu</string>
  <key>ProgramArguments</key><array>
    <string>$HEDEF/ortam/bin/python</string><string>-m</string><string>ulgen</string>
  </array>
  <key>WorkingDirectory</key><string>$HEDEF</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$VERI/ulgen.log</string>
  <key>StandardErrorPath</key><string>$VERI/ulgen.log</string>
</dict></plist>
PLISTEOF
  launchctl unload "$AJAN" 2>/dev/null
  launchctl load "$AJAN" || echo "Uyarı: otomatik başlatma yüklenemedi."
else
  echo "(Mac dışı ortam: otomatik başlatma atlandı)"
fi

adim "6/6  Launchpad uygulaması"
if [ "$MAC" = "1" ]; then
  UYGULAMA_KLASORU="/Applications"
  [ -w "$UYGULAMA_KLASORU" ] || { UYGULAMA_KLASORU="$HOME/Applications"; mkdir -p "$UYGULAMA_KLASORU"; }
  UYGULAMA="$UYGULAMA_KLASORU/Ülgen.app"
  rm -rf "$UYGULAMA"
  TMPAS="$(mktemp -t ulgen).applescript"
  cat > "$TMPAS" <<ASEOF
on run
  try
    do shell script "/usr/bin/curl -s -m 2 http://127.0.0.1:8765/saglik"
  on error
    do shell script "/bin/launchctl load $AJAN >/dev/null 2>&1 || true"
    delay 4
  end try
  open location "http://127.0.0.1:8765"
end run
ASEOF
  osacompile -o "$UYGULAMA" "$TMPAS" && echo "Uygulama: $UYGULAMA" || echo "Uyarı: uygulama oluşturulamadı."
  rm -f "$TMPAS"
  sleep 3
  if curl -s -m 3 http://127.0.0.1:8765/saglik | grep -q tamam; then
    echo "Ülgen çalışıyor."
    open "http://127.0.0.1:8765"
  else
    echo "Sunucu henüz yanıt vermedi; günlük: $VERI/ulgen.log"
  fi
else
  echo "(Mac dışı ortam: uygulama atlandı)"
fi

IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
printf '\n==================================================\n'
echo "Kurulum tamam."
echo "Mac'te: Launchpad > Ülgen   (ya da http://127.0.0.1:8765)"
echo "iPhone: Safari'de http://<ZeroTier-IP>:8765 ; anahtar için Mac'te:"
echo "  $HEDEF/ortam/bin/python -m ulgen --anahtar"
[ -n "$IP" ] && echo "(Bu Mac'in yerel ağ adresi: $IP)"
echo "=================================================="
read -r -p "Kapatmak için Enter'a basın." _
