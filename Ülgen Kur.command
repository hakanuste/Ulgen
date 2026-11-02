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

adim "2/6  Yedek alınıyor, dosyalar güvenle değiştiriliyor ($HEDEF)"
ZAMAN="$(date +%Y%m%d-%H%M%S)"
ESKI="$HEDEF/eski"                      # eski sürümler SİLİNMEZ, buraya taşınır
mkdir -p "$HEDEF" "$VERI" "$ESKI" || dur "Klasörler oluşturulamadı."
chmod 700 "$VERI"

# 2a) Kurulumdan ÖNCE verinin yedeği (hiçbir şey silinmez, yalnız kopyalanır)
YEDEK="$VERI/yedekler/kurulum-$ZAMAN"
mkdir -p "$YEDEK" && chmod 700 "$VERI/yedekler" "$YEDEK" 2>/dev/null
for f in "$VERI"/veri.db* "$VERI"/*.json "$VERI"/*.anahtar "$VERI"/*.key "$VERI"/*.sifreli; do
  [ -f "$f" ] && cp -p "$f" "$YEDEK/" 2>/dev/null
done
[ -d "$VERI/kod" ] && cp -Rp "$VERI/kod" "$YEDEK/kod" 2>/dev/null
echo "Veri yedeği: $YEDEK"
if [ -f "$VERI/veri.db" ] && [ ! -f "$YEDEK/veri.db" ]; then
  dur "Veritabanı yedeklenemedi; kurulum DURDURULDU, hiçbir şey değişmedi."
fi

# 2b) Yeni sürüm önce GEÇİCİ klasöre hazırlanır
YENI="$HEDEF/.yeni-$ZAMAN"
mkdir -p "$YENI" || dur "Geçici klasör oluşturulamadı."
cp -R "$KAYNAK/ulgen" "$YENI/ulgen" || { rmdir "$YENI" 2>/dev/null; dur "Dosyalar kopyalanamadı; mevcut kurulum değişmedi."; }
cp "$KAYNAK/requirements.txt" "$KAYNAK/requirements-ses.txt" "$YENI/" 2>/dev/null
find "$YENI/ulgen" -name '*.pyc' -delete 2>/dev/null

# 2c) Eski sürüm taşınır (silinmez), yeni sürüm yerine konur
ESKI_SURUM=""
if [ -d "$HEDEF/ulgen" ]; then
  ESKI_SURUM="$ESKI/ulgen-$ZAMAN"
  mv "$HEDEF/ulgen" "$ESKI_SURUM" || dur "Eski sürüm taşınamadı; mevcut kurulum değişmedi."
fi
if ! mv "$YENI/ulgen" "$HEDEF/ulgen"; then
  [ -n "$ESKI_SURUM" ] && mv "$ESKI_SURUM" "$HEDEF/ulgen"
  dur "Yeni sürüm yerleştirilemedi; eski sürüm geri konuldu."
fi
cp "$YENI/requirements.txt" "$YENI/requirements-ses.txt" "$HEDEF/" 2>/dev/null
rmdir "$YENI" 2>/dev/null

# Başarısızlıkta eski sürümü geri koyar (veri yedeği de yukarıda duruyor)
geri_al() {
  printf '\nGERİ ALINIYOR...\n'
  if [ -n "$ESKI_SURUM" ] && [ -d "$ESKI_SURUM" ]; then
    mv "$HEDEF/ulgen" "$ESKI/basarisiz-$ZAMAN" 2>/dev/null
    mv "$ESKI_SURUM" "$HEDEF/ulgen" && echo "Eski sürüm geri konuldu."
  else
    echo "Önceki sürüm yoktu; yarım kurulum $HEDEF/ulgen altında duruyor."
  fi
  if [ "$MAC" = "1" ] && [ -f "$AJAN" ]; then
    launchctl unload "$AJAN" 2>/dev/null; launchctl load "$AJAN" 2>/dev/null
  fi
  echo "Verileriniz değişmedi; yedek: $YEDEK"
}

adim "3/6  Sanal ortam ve kütüphaneler (birkaç dakika sürebilir)"
if [ ! -x "$HEDEF/ortam/bin/python" ]; then
  "$PY" -m venv "$HEDEF/ortam" || dur "Sanal ortam oluşturulamadı."
fi
"$HEDEF/ortam/bin/python" -m pip install --quiet --upgrade pip
"$HEDEF/ortam/bin/python" -m pip install --quiet -r "$HEDEF/requirements.txt" \
  || { geri_al; dur "Kütüphaneler yüklenemedi. İnternet bağlantınızı denetleyip yeniden çalıştırın."; }
"$HEDEF/ortam/bin/python" -c 'import sys; sys.path.insert(0, "'"$HEDEF"'"); import ulgen.cekirdek' \
  || { geri_al; dur "Ülgen yüklenemedi."; }
# Veritabanı şifrelemesi (SQLCipher). Yüklenemezse kurulum sürer ama veritabanı
# diskte ŞİFRESİZ kalır; bu açıkça söylenir ve tanı raporunda HATA görünür.
if ! "$HEDEF/ortam/bin/python" -m pip install --quiet sqlcipher3-wheels; then
  printf '\n!!! UYARI: sqlcipher3-wheels yüklenemedi. Veritabanınız diskte ŞİFRESİZ kalacak.\n'
  echo "    Sonra deneyin: $HEDEF/ortam/bin/python -m pip install sqlcipher3-wheels"
  echo "    ve '$HEDEF/ortam/bin/python -m ulgen --tani' ile denetleyin."
fi
"$HEDEF/ortam/bin/python" -m ulgen --anahtar >/dev/null

adim "4/6  Beyin (ücretsiz)"
if [ "$MAC" = "1" ]; then
  ANAHTAR="$(osascript -e 'text returned of (display dialog "İsteğe bağlı: ücretsiz Gemini anahtarınız varsa yapıştırın (aistudio.google.com). Yoksa boş bırakıp Tamam deyin.\n\nNot: ücretsiz katmanda gönderilen metinler Google tarafından ürün geliştirmede kullanılabilir. Ülgen kişisel verilerinizi (hafıza, sağlık, notlar) bulutta VARSAYILAN olarak göndermez." default answer "" with title "Ülgen")' 2>/dev/null || true)"
  if [ -n "$ANAHTAR" ]; then
    printf '%s' "$ANAHTAR" | "$HEDEF/ortam/bin/python" -m ulgen --sir-kaydet gemini \
      || echo "Uyarı: Gemini anahtarı kaydedilemedi."
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
  YENIUYG="$HEDEF/.yeni-Ülgen-$ZAMAN.app"
  TMPAS="$(mktemp -t ulgen).applescript"
  cat > "$TMPAS" <<ASEOF
on run
  try
    do shell script "/usr/bin/curl -s -m 2 http://127.0.0.1:8765/saglik"
  on error
    do shell script "/bin/launchctl load $AJAN >/dev/null 2>&1 || true"
    delay 4
  end try
  -- Tek kullanımlık giriş bağlantısı üretip tarayıcıyı açar
  do shell script "'$HEDEF/ortam/bin/python' -m ulgen --ac >/dev/null 2>&1 &"
end run
ASEOF
  if osacompile -o "$YENIUYG" "$TMPAS"; then
    [ -e "$UYGULAMA" ] && mv "$UYGULAMA" "$ESKI/Ülgen.app-$ZAMAN"
    mv "$YENIUYG" "$UYGULAMA" && echo "Uygulama: $UYGULAMA" \
      || { [ -e "$ESKI/Ülgen.app-$ZAMAN" ] && mv "$ESKI/Ülgen.app-$ZAMAN" "$UYGULAMA"; echo "Uyarı: uygulama yerleştirilemedi, eskisi geri konuldu."; }
  else
    echo "Uyarı: uygulama oluşturulamadı; eskisi (varsa) yerinde."
  fi
  rm -f "$TMPAS"
  sleep 3
  if curl -s -m 3 http://127.0.0.1:8765/saglik | grep -q tamam; then
    echo "Ülgen çalışıyor."
    "$HEDEF/ortam/bin/python" -m ulgen --ac >/dev/null 2>&1 || true
  else
    echo "Sunucu yanıt vermedi; sağlık denetimi başarısız."
    geri_al
    echo "Günlük: $VERI/ulgen.log"
  fi
else
  echo "(Mac dışı ortam: uygulama atlandı)"
fi

printf '\n==================================================\n'
echo "Kurulum tamam."
echo "Mac'te: Launchpad > Ülgen   (tek kullanımlık giriş bağlantısıyla açar)
echo "Eski sürümler silinmedi: $ESKI   |   Veri yedeği: $YEDEK"
echo "Durum denetimi: $HEDEF/ortam/bin/python -m ulgen --tani""
echo
echo "iPhone için (bir kez):"
echo "  1. Cihaz belirteci üretin:"
echo "     $HEDEF/ortam/bin/python -m ulgen --cihaz-ekle iPhone"
echo "     (belirteç yalnızca bir kez gösterilir; iPhone'da isteyince yapıştırın)"
echo "  2. iPhone Safari: http://<Mac'in ZeroTier adresi>:8766  > sertifikayı yükleyin"
echo "  3. Sonra: https://<Mac'in ZeroTier adresi>:8443"
echo "Adresi görmek için günlük: $VERI/ulgen.log"
echo "=================================================="
read -r -p "Kapatmak için Enter'a basın." _
