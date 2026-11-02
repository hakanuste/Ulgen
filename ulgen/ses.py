"""Ses katmanı: konuşma sentezi (TTS) ve konuşma tanıma (STT).

Mac'te sunucu tarafı ses isteğe bağlıdır; telefon ve tarayıcı arayüzü kendi
sesini (Web Speech API) kullanır. Bu modüldeki sınıflar terminal/ses
kipinde (``python -m ulgen --ses``) kullanılır. Kütüphaneler yoksa
modül hata vermez, yalnızca özelliği kapalı bildirir.
"""

import os
import re
import shutil
import subprocess
import tempfile
import threading

from . import ayar


def sesli_metin(metin):
    """Okunacak metni temizler (biçim imleri, bağlantılar atılır)."""
    metin = re.sub(r"https?://\S+", " bağlantı ", metin)
    metin = re.sub(r"[*_`#>]+", " ", metin)
    return re.sub(r"\s+", " ", metin).strip()


class Konusmaci:
    """Metni sesli okur: macOS ``say`` > pyttsx3 > gTTS (internet gerekir)."""

    def __init__(self):
        self._kilit = threading.Lock()
        self._surec = None

    def motor(self):
        secim = ayar.yukle().get("tts_motor", "otomatik")
        if secim in ("otomatik", "say") and shutil.which("say"):
            return "say"
        if secim in ("otomatik", "pyttsx3"):
            try:
                import pyttsx3  # noqa: F401
                return "pyttsx3"
            except ImportError:
                pass
        if secim in ("otomatik", "gtts"):
            try:
                import gtts  # noqa: F401
                return "gtts"
            except ImportError:
                pass
        return None

    def sustur(self):
        with self._kilit:
            if self._surec and self._surec.poll() is None:
                self._surec.terminate()

    def konus(self, metin):
        """Metni okur; kullanılan motoru ya da None döndürür."""
        metin = sesli_metin(metin)
        if not metin:
            return None
        motor = self.motor()
        if motor == "say":
            ses = ayar.yukle().get("ses", "Yelda")
            with self._kilit:
                self._surec = subprocess.Popen(["say", "-v", ses, metin])
            self._surec.wait()
        elif motor == "pyttsx3":
            import pyttsx3
            sesci = pyttsx3.init()
            sesci.say(metin)
            sesci.runAndWait()
        elif motor == "gtts":
            self._gtts_oku(metin)
        return motor

    @staticmethod
    def _gtts_oku(metin):
        from gtts import gTTS
        dosya = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        dosya.close()
        try:
            gTTS(text=metin, lang="tr").save(dosya.name)
            oynatici = shutil.which("afplay") or shutil.which("mpg123")
            if oynatici:
                subprocess.run([oynatici, dosya.name], check=False)
        finally:
            os.unlink(dosya.name)


class Dinleyici:
    """Mikrofonu dinler; 'Ülgen' uyandırma sözcüğünden sonra komutu alır."""

    def __init__(self):
        self._durdur = threading.Event()

    @staticmethod
    def kullanilabilir_mi():
        try:
            import speech_recognition  # noqa: F401
            import pyaudio  # noqa: F401
            return True
        except ImportError:
            return False

    def _tani(self, tanima, mikrofon, sure):
        """Bir cümle dinleyip metne çevirir (başarısızsa boş metin)."""
        import speech_recognition as sr
        try:
            ses = tanima.listen(mikrofon, timeout=sure, phrase_time_limit=15)
            return tanima.recognize_google(ses, language="tr-TR")
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except sr.RequestError:
            return ""

    @staticmethod
    def uyandirma_ayikla(metin):
        """Metin uyandırma sözcüğüyle başlıyorsa komutu döndürür, yoksa None."""
        sozcukler = ayar.yukle().get("uyandirma_sozcukleri", ["ülgen"])
        kucuk = metin.lower().strip()
        for sozcuk in sozcukler:
            if kucuk == sozcuk:
                return ""
            if kucuk.startswith(sozcuk + " ") or kucuk.startswith(
                    sozcuk + ","):
                return metin[len(sozcuk):].strip(" ,.")
        return None

    def dinle(self, komut_isle, konusmaci):
        """Sürekli dinler. ``komut_isle(metin) -> yanıt`` her komutta çağrılır."""
        import speech_recognition as sr
        tanima = sr.Recognizer()
        tanima.dynamic_energy_threshold = True
        with sr.Microphone() as mikrofon:
            tanima.adjust_for_ambient_noise(mikrofon, duration=1)
            print("Ülgen dinliyor. 'Ülgen' deyip komutunuzu söyleyin.")
            while not self._durdur.is_set():
                metin = self._tani(tanima, mikrofon, 5)
                if not metin:
                    continue
                komut = self.uyandirma_ayikla(metin)
                if komut is None:
                    continue
                if not komut:
                    konusmaci.konus("Buyurun, dinliyorum.")
                    komut = self._tani(tanima, mikrofon, 8)
                    if not komut:
                        continue
                print("Siz:", komut)
                yanit = komut_isle(komut)
                print("Ülgen:", yanit)
                konusmaci.konus(yanit)

    def durdur(self):
        self._durdur.set()


class CevrimdisiTanima:
    """İnternetsiz Türkçe konuşma tanıma (faster-whisper, yerel model).

    Ses hiçbir yere gönderilmez. Gerekenler (bir kez, Mac'te):
      pip install faster-whisper  ve  brew install ffmpeg
      python -m ulgen --ses-modeli-indir      (tek internet adımı)
    Model ``~/Ülgen/modeller`` altında durur; sonrası tümüyle çevrimdışı."""

    AZAMI_BAYT = 8 * 1024 * 1024
    _model = None
    _kilit = threading.Lock()

    @staticmethod
    def model_dizini():
        return os.path.join(os.path.expanduser("~"), "Ülgen", "modeller")

    @classmethod
    def eksikler(cls):
        eksik = []
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            eksik.append("faster-whisper (pip install faster-whisper)")
        if not shutil.which("ffmpeg"):
            eksik.append("ffmpeg (brew install ffmpeg)")
        return eksik

    @classmethod
    def model_adi(cls):
        return ayar.yukle().get("stt_model", "small")

    @classmethod
    def hazir_mi(cls):
        if cls.eksikler():
            return False
        return os.path.isdir(os.path.join(cls.model_dizini(),
                                          "yuklendi-" + cls.model_adi()))

    @classmethod
    def indir(cls):
        """Modeli bir kez indirir (tek internet gerektiren adım)."""
        from faster_whisper import WhisperModel
        os.makedirs(cls.model_dizini(), exist_ok=True)
        WhisperModel(cls.model_adi(), device="cpu", compute_type="int8",
                     download_root=cls.model_dizini())
        os.makedirs(os.path.join(cls.model_dizini(),
                                 "yuklendi-" + cls.model_adi()),
                    exist_ok=True)

    @classmethod
    def _yukle(cls):
        with cls._kilit:
            if cls._model is None:
                from faster_whisper import WhisperModel
                cls._model = WhisperModel(
                    cls.model_adi(), device="cpu", compute_type="int8",
                    download_root=cls.model_dizini(), local_files_only=True)
            return cls._model

    @classmethod
    def yaz(cls, ses_baytlari):
        """Herhangi bir ses biçimini (webm/mp4/wav) Türkçe metne çevirir."""
        if not ses_baytlari or len(ses_baytlari) > cls.AZAMI_BAYT:
            raise ValueError("Ses boş ya da çok büyük (en çok 8 MB).")
        if not cls.hazir_mi():
            raise RuntimeError("Çevrimdışı ses tanıma kurulu değil: "
                               + "; ".join(cls.eksikler() or
                                           ["model indirilmemiş"]))
        with tempfile.TemporaryDirectory() as klasor:
            ham = os.path.join(klasor, "ham")
            wav = os.path.join(klasor, "ses.wav")
            with open(ham, "wb") as f:
                f.write(ses_baytlari)
            sonuc = subprocess.run(
                ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", ham,
                 "-ac", "1", "-ar", "16000", wav],
                capture_output=True, timeout=60, check=False)
            if sonuc.returncode != 0:
                raise ValueError("Ses biçimi çözülemedi.")
            parcalar, _ = cls._yukle().transcribe(
                wav, language="tr", vad_filter=True, beam_size=1)
            return " ".join(p.text.strip() for p in parcalar).strip()
