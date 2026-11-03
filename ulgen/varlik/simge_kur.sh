#!/bin/bash
# Launchpad'deki "Ülgen" uygulamasını (yeniden) oluşturur. Veriye dokunmaz.
# Kullanım: bash ~/Ülgen/ulgen/varlik/simge_kur.sh
HEDEF="${HEDEF:-$HOME/Ülgen}"
AJAN="${AJAN:-$HOME/Library/LaunchAgents/com.ulgen.sunucu.plist}"
ESKI="${ESKI:-$HEDEF/eski}"
ZAMAN="$(date +%Y%m%d-%H%M%S)"
UYGULAMA_KLASORU="/Applications"
[ -w "$UYGULAMA_KLASORU" ] || { UYGULAMA_KLASORU="$HOME/Applications"; mkdir -p "$UYGULAMA_KLASORU"; }
UYGULAMA="$UYGULAMA_KLASORU/Ülgen.app"
YENIUYG="$HEDEF/.yeni-Ülgen-$ZAMAN.app"
TMPAS="$(mktemp -t ulgen).applescript"
mkdir -p "$ESKI"
# NOT: "python -m ulgen" paketi çalışma klasöründe arar; bu yüzden önce klasöre girilir.
cat > "$TMPAS" <<ASEOF
-- Uygulama açık kalır (Dock'ta görünür); Dock simgesine yeniden tıklanınca Ülgen tekrar açılır.
on run
  my baslat()
end run

on reopen
  my baslat()
end reopen

on idle
  return 3600
end idle

on baslat()
  try
    do shell script "/usr/bin/curl -s -m 2 http://127.0.0.1:8765/saglik"
  on error
    do shell script "/bin/launchctl load $AJAN >/dev/null 2>&1 || true"
    delay 4
  end try
  -- Tek kullanımlık giriş bağlantısı üretip tarayıcıyı açar
  try
    do shell script "cd '$HEDEF' && '$HEDEF/ortam/bin/python' -m ulgen --ac >> '$HOME/ÜlgenVeri/simge.log' 2>&1 &"
  on error mesaj
    display dialog "Ülgen açılamadı: " & mesaj buttons {"Tamam"} default button 1
  end try
end baslat
ASEOF
if osacompile -s -o "$YENIUYG" "$TMPAS"; then
  [ -e "$UYGULAMA" ] && mv "$UYGULAMA" "$ESKI/Ülgen.app-$ZAMAN"
  if [ -f "$HEDEF/ulgen/varlik/ulgen.icns" ]; then
    cp "$HEDEF/ulgen/varlik/ulgen.icns" "$YENIUYG/Contents/Resources/applet.icns" 2>/dev/null
    touch "$YENIUYG"
  fi
  /usr/bin/codesign --force --deep --sign - "$YENIUYG" >/dev/null 2>&1 || true
  /usr/bin/xattr -cr "$YENIUYG" 2>/dev/null || true
  mv "$YENIUYG" "$UYGULAMA" && echo "Uygulama: $UYGULAMA" \
    || { [ -e "$ESKI/Ülgen.app-$ZAMAN" ] && mv "$ESKI/Ülgen.app-$ZAMAN" "$UYGULAMA"; echo "Uyarı: uygulama yerleştirilemedi, eskisi geri konuldu."; }
else
  echo "Uyarı: uygulama oluşturulamadı; eskisi (varsa) yerinde."
fi
rm -f "$TMPAS"
