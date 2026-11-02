#!/bin/bash
# Yerel ses denemesi (XTTS-v2): sizin sesinizi ücretsiz, bu bilgisayarda üretir ve hızını ölçer.
# Ülgen'e dokunmaz; ayrı bir ortam kurar: ~/ÜlgenVeri/xtts_ortam
# Önce ~/ÜlgenVeri/ klasörüne 20-30 sn'lik temiz kaydınızı "referans_ses.*" adıyla koyun
# (wav, mp3, m4a, mp4 olabilir).
set -u
BU="$(cd "$(dirname "$0")" && pwd)"
VERI="$HOME/ÜlgenVeri"
ORTAM="$VERI/xtts_ortam"
dur() { printf '\nHATA: %s\n' "$1"; read -r -p "Kapatmak için Enter'a basın." _; exit 1; }

REF=""
for u in wav mp3 m4a mp4 aac; do [ -f "$VERI/referans_ses.$u" ] && REF="$VERI/referans_ses.$u" && break; done
[ -n "$REF" ] || dur "$VERI içinde 'referans_ses' dosyası yok (örn. referans_ses.mp3)."

# Coqui TTS için Python 3.10-3.12 gerekir.
PY=""
for a in python3.11 python3.10 python3.12 python3; do
  p="$(command -v $a 2>/dev/null || true)"
  [ -n "$p" ] && "$p" -c 'import sys; sys.exit(not ((3,10) <= sys.version_info[:2] <= (3,12)))' 2>/dev/null && PY="$p" && break
done
[ -n "$PY" ] || dur "Python 3.10-3.12 bulunamadı. Terminal'de: brew install python@3.11"

mkdir -p "$VERI/ses_deneme"
WAV="$VERI/ses_deneme/referans.wav"
if [ "${REF##*.}" = "wav" ]; then cp "$REF" "$WAV"; else
  afconvert -f WAVE -d LEI16@22050 -c 1 "$REF" "$WAV" || dur "Kayıt dönüştürülemedi."
fi

if [ ! -x "$ORTAM/bin/python" ]; then
  echo "==> Ortam kuruluyor (birkaç GB iner, 10-20 dk sürebilir)"
  "$PY" -m venv "$ORTAM" || dur "Ortam açılamadı."
  "$ORTAM/bin/pip" install --upgrade pip || dur "pip güncellenemedi."
  # Intel Mac için son torch sürümü 2.2.2'dir.
  "$ORTAM/bin/pip" install "torch==2.2.2" "torchaudio==2.2.2" "numpy<2" || dur "torch kurulamadı."
  "$ORTAM/bin/pip" install coqui-tts "transformers<4.50" || dur "coqui-tts kurulamadı."
fi

"$ORTAM/bin/python" "$BU/yerel_ses_denemesi.py" "$WAV" 2>&1 | tee "$VERI/ses_deneme/sonuc.txt"
open "$VERI/ses_deneme" 2>/dev/null
echo; read -r -p "Bitti. sonuc.txt dosyasını bana gönderin. Kapatmak için Enter." _
