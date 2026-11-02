#!/bin/bash
# Launchpad'de çoğalan "Ülgen" simgelerini temizler.
# Yalnız Launchpad'in kayıt defterinden (LaunchServices) eski/yinelenen kayıtları siler.
# Dosyalara, veriye ve yedeğe DOKUNMAZ. Geçerli uygulama: $1 (varsayılan /Applications/Ülgen.app)
LS=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
[ -x "$LS" ] || { echo "(Mac dışı ortam: atlandı)"; exit 0; }
GECERLI="${1:-/Applications/Ülgen.app}"
[ -d "$GECERLI" ] || GECERLI="$HOME/Applications/Ülgen.app"
# Adlardaki Ü, macOS'ta iki biçimde yazılabildiğinden "*lgen*" ile aranır.
adaylar() {
  { /usr/bin/mdfind "kMDItemContentType == 'com.apple.application-bundle' && kMDItemFSName == '*lgen*'" 2>/dev/null
    find /Applications "$HOME/Applications" "$HOME/Ülgen" "$HOME/ÜlgenVeri" "$HOME/Desktop" "$HOME/Downloads" \
      -maxdepth 4 \( -name '*lgen*.app' -o -name '.yeni-*lgen*' -o -name '*lgen.app-*' \) 2>/dev/null
  } | sort -u
}
gecerli_gercek="$(cd "$GECERLI" 2>/dev/null && pwd -P)"
n=0
while IFS= read -r yol; do
  [ -n "$yol" ] || continue
  gercek="$(cd "$yol" 2>/dev/null && pwd -P)"
  [ -n "$gecerli_gercek" ] && [ "$gercek" = "$gecerli_gercek" ] && continue
  "$LS" -u "$yol" >/dev/null 2>&1 && n=$((n + 1))
done < <(adaylar)
"$LS" -f "$GECERLI" >/dev/null 2>&1
echo "Launchpad: $n eski/yinelenen Ülgen kaydı silindi."
/usr/bin/killall Dock 2>/dev/null || true       # Launchpad'i yeniler (düzeniniz bozulmaz)
