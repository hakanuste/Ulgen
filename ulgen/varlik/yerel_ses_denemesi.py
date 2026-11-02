"""Yerel ses denemesi: XTTS-v2 ile sizin sesinizi Türkçe konuşturup hızını ölçer.

Ülgen'e dokunmaz; yalnız ~/ÜlgenVeri/ses_deneme/ klasörüne yazar.
Kullanım: python yerel_ses_denemesi.py <referans_ses.wav>
"""
import os
import sys
import time
import wave

CUMLELER = [
    ("kisa", "Günaydın Hakan. Bugün için üç görevin var."),
    ("orta", "Saat on beşte ilaç hatırlatman var. Şimdi suyunu içmeyi unutma."),
    ("uzun", "Aydın Koçarlı'daki zeytinlik için bu hafta budama yapılması uygun görünüyor. "
             "Budama artıklarını biyokömür üretmek için ayırabilirsin."),
]


def referansi_kirp(yol, sn=30):
    """Referans kaydı en çok 'sn' saniyeye kırpar (uzun kayıt işlemciyi boş yere yorar)."""
    with wave.open(yol, "rb") as k:
        p = k.getparams()
        veri = k.readframes(min(k.getnframes(), p.framerate * sn))
    cikis = yol + ".kirpik.wav"
    with wave.open(cikis, "wb") as y:
        y.setparams(p)
        y.writeframes(veri)
    return cikis


def main():
    if len(sys.argv) < 2:
        print("Referans ses dosyası verilmedi.")
        return 2
    ref = referansi_kirp(sys.argv[1])
    cikti = os.path.join(os.path.expanduser("~"), "ÜlgenVeri", "ses_deneme")
    os.makedirs(cikti, exist_ok=True)

    os.environ["COQUI_TOS_AGREED"] = "1"   # kişisel, ticari olmayan kullanım (CPML)
    t0 = time.time()
    from TTS.api import TTS
    print("Model yükleniyor (ilk seferde ~2 GB iner, sabırlı olun)...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
    print("Model hazır: %.1f sn" % (time.time() - t0))

    sonuc = []
    for ad, metin in CUMLELER:
        yol = os.path.join(cikti, "deneme_%s.wav" % ad)
        t = time.time()
        tts.tts_to_file(text=metin, speaker_wav=ref, language="tr", file_path=yol)
        gecen = time.time() - t
        with wave.open(yol, "rb") as w:
            sure = w.getnframes() / float(w.getframerate())
        sonuc.append((ad, len(metin), gecen, sure))
        print("%-5s %3d harf: üretim %.1f sn, ses %.1f sn (oran %.2f)" % (ad, len(metin), gecen, sure, gecen / sure))

    print("\nÖzet: oran 1'in altındaysa konuşma, üretimden uzundur (anlık okumaya yakın).")
    print("Dosyalar:", cikti)
    return 0


if __name__ == "__main__":
    sys.exit(main())
