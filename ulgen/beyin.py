"""Ülgen'in beyni: ücretsiz dil modeli ağ geçidi.

İki aile vardır:
  * Yerel beyin (veri cihazdan çıkmaz):
      - Ollama        (http://127.0.0.1:11434, /api/chat)
      - llama.cpp     (http://127.0.0.1:8080, OpenAI uyumlu /v1/chat/...)
  * Bulut beyin: Google Gemini (Google AI Studio ücretsiz katmanı)

Not: Ollama'nın güncel sürümü macOS 14 ve üstünü ister. Daha eski Mac'lerde
llama.cpp sunucusu ya da Gemini kullanılabilir.
"""

import json
import time
import urllib.error
import urllib.request

GEMINI_TABAN = "https://generativelanguage.googleapis.com/v1beta"


class BeyinHatasi(Exception):
    """Dil modeline ulaşılamadığında ya da yanıt alınamadığında fırlatılır."""


def _json_gonder(adres, govde=None, basliklar=None, zaman_asimi=120):
    """Adrese JSON gönderir (govde yoksa GET) ve JSON yanıtı döndürür."""
    veri = None if govde is None else json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(
        adres, data=veri, method="POST" if veri is not None else "GET")
    istek.add_header("Content-Type", "application/json")
    for ad, deger in (basliklar or {}).items():
        istek.add_header(ad, deger)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as yanit:
            return json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as hata:
        ayrinti = hata.read().decode("utf-8", errors="replace")[:300]
        raise BeyinHatasi("HTTP %d: %s" % (hata.code, ayrinti)) from hata
    except (urllib.error.URLError, OSError, ValueError) as hata:
        raise BeyinHatasi(str(hata)) from hata


class Beyin:
    """Tüm beyinlerin ortak arayüzü."""

    ad = "beyin"
    yerel = True
    sistem_butce = 3000   # sistem isteminin token bütçesi
    gecmis_butce = 1000   # konuşma geçmişinin token bütçesi

    def kullanilabilir_mi(self):
        """Beyin şu an yanıt verebilir durumda mı?"""
        raise NotImplementedError

    def yanitla(self, sistem, mesajlar, azami_token=700):
        """Sistem istemi ve mesaj listesiyle bir yanıt metni üretir."""
        raise NotImplementedError


class OllamaBeyin(Beyin):
    """Yerel Ollama sunucusu (Llama 3.x, Mistral vb.)."""

    ad = "Ollama (yerel)"

    def __init__(self, adres, model):
        self.adres = adres.rstrip("/")
        self.model = model

    def kullanilabilir_mi(self):
        try:
            _json_gonder(self.adres + "/api/tags", zaman_asimi=2)
            return True
        except BeyinHatasi:
            return False

    def yanitla(self, sistem, mesajlar, azami_token=700):
        govde = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": sistem}] + mesajlar,
            "options": {"num_ctx": 4096, "temperature": 0.6,
                        "num_predict": azami_token},
        }
        veri = _json_gonder(self.adres + "/api/chat", govde)
        try:
            return veri["message"]["content"]
        except (KeyError, TypeError) as hata:
            raise BeyinHatasi("Ollama beklenmeyen yanıt verdi.") from hata


class LlamaCppBeyin(Beyin):
    """llama.cpp 'llama-server' (OpenAI uyumlu arayüz)."""

    ad = "llama.cpp (yerel)"

    def __init__(self, adres):
        self.adres = adres.rstrip("/")

    def kullanilabilir_mi(self):
        try:
            _json_gonder(self.adres + "/v1/models", zaman_asimi=2)
            return True
        except BeyinHatasi:
            return False

    def yanitla(self, sistem, mesajlar, azami_token=700):
        govde = {
            "messages": [{"role": "system", "content": sistem}] + mesajlar,
            "max_tokens": azami_token,
            "temperature": 0.6,
            "stream": False,
        }
        veri = _json_gonder(self.adres + "/v1/chat/completions", govde)
        try:
            return veri["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as hata:
            raise BeyinHatasi("llama.cpp beklenmeyen yanıt verdi.") from hata


class GeminiBeyin(Beyin):
    """Google Gemini (ücretsiz katman). Veri Google'a gider."""

    ad = "Gemini (bulut)"
    yerel = False
    sistem_butce = 6000
    gecmis_butce = 3000

    def __init__(self, anahtar, model):
        self.anahtar = anahtar
        self.model = model

    def kullanilabilir_mi(self):
        return bool(self.anahtar)

    def _basliklar(self):
        return {"x-goog-api-key": self.anahtar}

    def yanitla(self, sistem, mesajlar, azami_token=700):
        # Gemini, rollerin user/model olarak art arda değişmesini ister.
        icerik = []
        for mesaj in mesajlar:
            rol = "user" if mesaj["role"] == "user" else "model"
            if icerik and icerik[-1]["role"] == rol:
                icerik[-1]["parts"][0]["text"] += "\n\n" + mesaj["content"]
            else:
                icerik.append({"role": rol,
                               "parts": [{"text": mesaj["content"]}]})
        if not icerik or icerik[0]["role"] != "user":
            icerik.insert(0, {"role": "user", "parts": [{"text": "Merhaba."}]})
        govde = {
            "systemInstruction": {"parts": [{"text": sistem}]},
            "contents": icerik,
            "generationConfig": {"temperature": 0.7,
                                 "maxOutputTokens": max(azami_token, 1024)},
        }
        adres = "%s/models/%s:generateContent" % (GEMINI_TABAN, self.model)
        try:
            veri = _json_gonder(adres, govde, self._basliklar(), 60)
        except BeyinHatasi as hata:
            if "HTTP 429" in str(hata):
                raise BeyinHatasi(
                    "Gemini ücretsiz günlük kotası doldu. Yarın yeniden "
                    "deneyin ya da yerel beyni kullanın.") from hata
            raise
        adaylar = veri.get("candidates") or []
        if not adaylar:
            raise BeyinHatasi("Gemini yanıt vermedi (içerik engellenmiş "
                              "olabilir).")
        parcalar = adaylar[0].get("content", {}).get("parts", [])
        metin = "".join(p.get("text", "") for p in parcalar).strip()
        if not metin:
            raise BeyinHatasi("Gemini boş yanıt döndürdü.")
        return metin

    def gorselle_yanitla(self, istem, png, azami_token=700):
        """Bir görüntüyü (PNG baytları) inceleyip soruya yanıt verir."""
        import base64
        govde = {
            "contents": [{"role": "user", "parts": [
                {"text": istem},
                {"inlineData": {"mimeType": "image/png",
                                "data": base64.b64encode(png).decode()}}]}],
            "generationConfig": {"maxOutputTokens": max(azami_token, 1024)},
        }
        adres = "%s/models/%s:generateContent" % (GEMINI_TABAN, self.model)
        veri = _json_gonder(adres, govde, self._basliklar(), 90)
        adaylar = veri.get("candidates") or []
        parcalar = adaylar[0].get("content", {}).get("parts", []) \
            if adaylar else []
        metin = "".join(p.get("text", "") for p in parcalar).strip()
        if not metin:
            raise BeyinHatasi("Gemini görüntü için yanıt vermedi.")
        return metin

    def modelleri_listele(self):
        """Bu anahtarla kullanılabilen, metin üretebilen modelleri listeler."""
        veri = _json_gonder(GEMINI_TABAN + "/models?pageSize=200",
                            basliklar=self._basliklar(), zaman_asimi=20)
        return sorted(
            m["name"].split("/")[-1] for m in veri.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", []))


class BeyinYonlendirici:
    """Ayara göre kullanılabilir ilk beyni seçer.

    Seçim 20 saniye önbelleğe alınır; böylece kapalı bir yerel sunucu için
    her mesajda zaman aşımı beklenmez.
    """

    def __init__(self, ayar_oku):
        self._ayar_oku = ayar_oku
        self._onbellek = (0.0, None)

    def _adaylar(self, a):
        yerel = []
        tur = a.get("yerel_tur", "otomatik")
        if tur in ("otomatik", "ollama"):
            yerel.append(OllamaBeyin(a["ollama_adres"], a["ollama_model"]))
        if tur in ("otomatik", "llamacpp"):
            yerel.append(LlamaCppBeyin(a["llamacpp_adres"]))
        bulut = []
        if a.get("gemini_anahtar"):
            bulut.append(GeminiBeyin(a["gemini_anahtar"], a["gemini_model"]))
        mod = a.get("beyin", "otomatik")
        if mod == "yerel":
            return yerel
        if mod == "bulut":
            return bulut
        return yerel + bulut

    def sec(self):
        """Kullanılabilir beyni döndürür; hiçbiri yoksa None."""
        simdi = time.time()
        zaman, onbellekteki = self._onbellek
        if simdi - zaman < 20:
            return onbellekteki
        secilen = None
        for aday in self._adaylar(self._ayar_oku()):
            if aday.kullanilabilir_mi():
                secilen = aday
                break
        self._onbellek = (simdi, secilen)
        return secilen

    def sifirla(self):
        """Önbelleği temizler (ayar değişince çağrılır)."""
        self._onbellek = (0.0, None)

    def durum(self):
        """Arayüzde gösterilecek kısa beyin durumu."""
        beyin = self.sec()
        if beyin is None:
            return {"beyin": None, "yerel": None}
        return {"beyin": beyin.ad, "yerel": beyin.yerel}
