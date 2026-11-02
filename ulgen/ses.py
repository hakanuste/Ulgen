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
