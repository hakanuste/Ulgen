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
import re
import time
import urllib.error
import urllib.request

from . import ag, ayar, veritabani

GEMINI_TABAN = "https://generativelanguage.googleapis.com/v1beta"


class BeyinHatasi(Exception):
    """Dil modeline ulaşılamadığında ya da yanıt alınamadığında fırlatılır."""


class KotaHatasi(BeyinHatasi):
    """Sağlayıcının ücretsiz kotası ya da hız sınırı doldu (HTTP 429 vb.)."""

    def __init__(self, mesaj, bekle_sn=60, baslik=None):
        super().__init__(mesaj)
        self.bekle_sn = bekle_sn
        self.baslik = baslik or {}


def _json_gonder(adres, govde=None, basliklar=None, zaman_asimi=120,
                 baslik_don=False):
    """Adrese JSON gönderir (govde yoksa GET) ve JSON yanıtı döndürür.

    ``baslik_don`` açıksa (yanıt, küçük_harfli_başlıklar) döner. HTTP 429
    ``KotaHatasi`` olarak fırlatılır (Retry-After okunur)."""
    veri = None if govde is None else json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(
        adres, data=veri, method="POST" if veri is not None else "GET")
    istek.add_header("Content-Type", "application/json")
    for ad, deger in (basliklar or {}).items():
        istek.add_header(ad, deger)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi,
                                    context=ag.baglam()) as yanit:
            veri_ = json.loads(yanit.read().decode("utf-8"))
            if baslik_don:
                return veri_, {k.lower(): v for k, v in yanit.headers.items()}
            return veri_
    except urllib.error.HTTPError as hata:
        ayrinti = hata.read().decode("utf-8", errors="replace")[:300]
        basliklar_ = {k.lower(): v for k, v in hata.headers.items()}
        if hata.code == 429:
            try:
                bekle = int(float(basliklar_.get("retry-after", "60")))
            except ValueError:
                bekle = 60
            raise KotaHatasi("HTTP 429: %s" % ayrinti, max(bekle, 1),
                             basliklar_) from hata
        raise BeyinHatasi("HTTP %d: %s" % (hata.code, ayrinti)) from hata
    except (urllib.error.URLError, OSError, ValueError) as hata:
        raise BeyinHatasi(str(hata)) from hata


class Beyin:
    """Tüm beyinlerin ortak arayüzü."""

    ad = "beyin"
    yerel = True
    saglayici = None      # kota sayacındaki ad (yerel beyinlerde de tutulur)
    model = ""
    son_kullanim = None   # {"giris", "cikis", "gercek"} son çağrıdan
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
    saglayici = "gemini"
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

    TERCIH = ("flash-lite", "flash", "pro")
    ELE = ("embed", "image", "vision", "tts", "audio", "live", "robotics",
           "aqa", "imagen", "veo", "gemma", "learnlm", "computer-use",
           "thinking", "preview", "exp")

    def _yeni_model(self, eski):
        adaylar = [m for m in self.modelleri_listele() if m != eski
                   and not any(e in m.lower() for e in self.ELE)]
        for tercih in self.TERCIH:
            sirali = sorted((m for m in adaylar if tercih in m.lower()),
                            reverse=True)         # en yeni sürüm önce
            if sirali:
                return sirali[0]
        return None

    def yanitla(self, sistem, mesajlar, azami_token=700):
        try:
            return self._yanitla(sistem, mesajlar, azami_token)
        except BeyinHatasi as hata:
            if not re.match(r"HTTP (404|410)\b", str(hata)):
                raise
            try:
                yeni = self._yeni_model(self.model)
            except BeyinHatasi:
                yeni = None
            if not yeni:
                raise
            eski, self.model = self.model, yeni
            try:
                yanit = self._yanitla(sistem, mesajlar, azami_token)
            except BeyinHatasi:
                self.model = eski
                raise
            try:
                ayar.guncelle("gemini_model", yeni)
                veritabani.gunluge_yaz("bilgi", "model", "gemini modeli %s -> %s"
                                       % (eski, yeni))
            except Exception:
                pass
            return yanit

    def _yanitla(self, sistem, mesajlar, azami_token=700):
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
        veri = _json_gonder(adres, govde, self._basliklar(), 60)
        kul = veri.get("usageMetadata") or {}
        if "promptTokenCount" in kul:
            self.son_kullanim = {
                "giris": int(kul.get("promptTokenCount", 0)),
                "cikis": int(kul.get("candidatesTokenCount", 0)),
                "gercek": True}
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


class OpenAIUyumluBeyin(Beyin):
    """Groq, Mistral ve OpenRouter: OpenAI uyumlu sohbet arayüzü (bulut).

    Yalnızca ücretsiz katman: OpenRouter'da ``:free`` olmayan model
    ``ucretsiz_dogrula`` tarafından ağa çıkmadan reddedilir."""

    yerel = False
    sistem_butce = 6000
    gecmis_butce = 3000
    TABANLAR = {"groq": "https://api.groq.com/openai/v1",
                "nvidia": "https://integrate.api.nvidia.com/v1",
                "mistral": "https://api.mistral.ai/v1",
                "openrouter": "https://openrouter.ai/api/v1"}
    ADLAR = {"groq": "Groq", "nvidia": "NVIDIA", "mistral": "Mistral",
             "openrouter": "OpenRouter"}

    def __init__(self, saglayici, anahtar, model):
        self.saglayici = saglayici
        self.anahtar = anahtar
        self.model = model
        self.ad = "%s (bulut)" % self.ADLAR[saglayici]

    def kullanilabilir_mi(self):
        from . import kota
        return bool(self.anahtar) and kota.ucretsiz_mi(self.saglayici,
                                                       self.model)

    def _basliklar(self):
        return {"Authorization": "Bearer " + self.anahtar}

    # Model emekli olduysa (HTTP 404/410) liste sorulup yeni model seçilir.
    TERCIH = ("llama-3.3-70b", "llama-3.1-70b", "lightning", "nemotron",
              "llama-3.1-8b", "qwen", "mistral", "gemma")
    ELE = ("embed", "rerank", "vision", "-vl", "vlm", "guard", "safety",
           "reward", "parse", "clip", "retriev", "nv-", "audio", "speech",
           "tts", "asr", "diffusion", "image", "code-", "translate")

    def _yeni_model(self, eski):
        adaylar = [m for m in self.modelleri_listele()
                   if m != eski and not any(e in m.lower() for e in self.ELE)]
        for tercih in self.TERCIH:
            for m in adaylar:
                if tercih in m.lower():
                    return m
        return None

    def yanitla(self, sistem, mesajlar, azami_token=700):
        try:
            return self._yanitla(sistem, mesajlar, azami_token)
        except BeyinHatasi as hata:
            if not re.match(r"HTTP (404|410)\b", str(hata)):
                raise
            try:
                yeni = self._yeni_model(self.model)
            except BeyinHatasi:
                yeni = None
            if not yeni:
                raise
            eski, self.model = self.model, yeni
            try:
                yanit = self._yanitla(sistem, mesajlar, azami_token)
            except BeyinHatasi:
                self.model = eski
                raise
            try:                                   # kalıcı olsun
                ayar.guncelle(self.saglayici + "_model", yeni)
                veritabani.gunluge_yaz("bilgi", "model", "%s modeli %s -> %s" % (
                    self.saglayici, eski, yeni))
            except Exception:
                pass
            return yanit

    def _yanitla(self, sistem, mesajlar, azami_token=700):
        from . import kota
        kota.ucretsiz_dogrula(self.saglayici, self.model)
        govde = {"model": self.model, "temperature": 0.6, "stream": False,
                 "max_tokens": azami_token,
                 "messages": [{"role": "system", "content": sistem}]
                 + mesajlar}
        veri, basliklar = _json_gonder(
            self.TABANLAR[self.saglayici] + "/chat/completions", govde,
            self._basliklar(), 60, baslik_don=True)
        kota.basliklari_isle(self.saglayici, basliklar)
        kul = veri.get("usage") or {}
        if "prompt_tokens" in kul:
            self.son_kullanim = {"giris": int(kul["prompt_tokens"]),
                                 "cikis": int(kul.get("completion_tokens", 0)),
                                 "gercek": True}
        try:
            metin = (veri["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as hata:
            raise BeyinHatasi("%s beklenmeyen yanıt verdi." % self.ad) from hata
        if not metin:
            raise BeyinHatasi("%s boş yanıt döndürdü." % self.ad)
        return metin

    def modelleri_listele(self):
        veri = _json_gonder(self.TABANLAR[self.saglayici] + "/models",
                            basliklar=self._basliklar(), zaman_asimi=20)
        sonuc = []
        for m in veri.get("data", []):
            kimlik = m.get("id", "")
            if self.saglayici == "openrouter":
                fiyat = m.get("pricing") or {}
                if not (kimlik.endswith(":free") or (
                        str(fiyat.get("prompt")) in ("0", "0.0")
                        and str(fiyat.get("completion")) in ("0", "0.0"))):
                    continue
            sonuc.append(kimlik)
        return sorted(sonuc)


class KotaliBeyin(Beyin):
    """Bir beyni sarar: kotayı denetler, her çağrıyı sayar ve süresini ölçer."""

    def __init__(self, ic, ad_kisa):
        self.ic = ic
        self.ad = ic.ad
        self.yerel = ic.yerel
        self.sistem_butce = ic.sistem_butce
        self.gecmis_butce = ic.gecmis_butce
        self.saglayici = ad_kisa
        self.model = getattr(ic, "model", "")

    def kullanilabilir_mi(self):
        return self.ic.kullanilabilir_mi()

    def yanitla(self, sistem, mesajlar, azami_token=700):
        from . import kota
        engelli, neden, bekle = kota.engel(self.saglayici)
        if engelli:
            raise KotaHatasi("%s kullanılamaz: %s" % (self.ad, neden),
                             bekle or 60)
        self.ic.son_kullanim = None
        basla = time.time()
        giris = sum(len(m["content"]) for m in mesajlar) + len(sistem)
        try:
            yanit = self.ic.yanitla(sistem, mesajlar, azami_token)
        except KotaHatasi as hata:
            kota.kaydet(self.saglayici, self.model, 0, 0, False, "kota",
                        int((time.time() - basla) * 1000))
            kota.engel_koy(self.saglayici, hata.bekle_sn, str(hata)[:160])
            raise
        except BeyinHatasi as hata:
            kota.kaydet(self.saglayici, self.model, 0, 0, False, "hata",
                        int((time.time() - basla) * 1000), str(hata)[:160])
            raise
        kul = self.ic.son_kullanim
        if kul:
            g, c, gercek = kul["giris"], kul["cikis"], True
        else:       # sağlayıcı sayı vermediyse TAHMİN (≈3,5 karakter/token)
            g, c, gercek = int(giris / 3.5), int(len(yanit) / 3.5), False
        kota.kaydet(self.saglayici, self.model, g, c, gercek, "ok",
                    int((time.time() - basla) * 1000))
        return yanit

    def __getattr__(self, ad):
        return getattr(self.ic, ad)


class BeyinYonlendirici:
    """Ayara göre kullanılabilir beyinleri sıralar (önce yerel).

    Yerel sunucunun ulaşılabilirliği 20 saniye önbelleğe alınır; kota
    denetimi her seferinde yeniden yapılır."""

    def __init__(self, ayar_oku):
        self._ayar_oku = ayar_oku
        self._yerel_onbellek = (0.0, [])

    def _yerel(self, a):
        yerel = []
        tur = a.get("yerel_tur", "otomatik")
        if tur in ("otomatik", "ollama"):
            b = OllamaBeyin(a["ollama_adres"], a["ollama_model"])
            b.saglayici = "ollama"
            yerel.append(b)
        if tur in ("otomatik", "llamacpp"):
            b = LlamaCppBeyin(a["llamacpp_adres"])
            b.saglayici = "llamacpp"
            yerel.append(b)
        return [KotaliBeyin(b, b.saglayici) for b in yerel]

    def _bulut(self, a):
        bulut = []
        for ad in a.get("bulut_sirasi", []):
            anahtar = a.get(ad + "_anahtar")
            if not anahtar:
                continue
            if ad == "gemini":
                ic = GeminiBeyin(anahtar, a["gemini_model"])
            elif ad in OpenAIUyumluBeyin.TABANLAR:
                ic = OpenAIUyumluBeyin(ad, anahtar, a[ad + "_model"])
            else:
                continue
            bulut.append(KotaliBeyin(ic, ad))
        return bulut

    def _adaylar(self, a):
        mod = a.get("beyin", "otomatik")
        if mod == "yerel":
            return self._yerel(a)
        if mod == "bulut":
            return self._bulut(a)
        return self._yerel(a) + self._bulut(a)

    def _ulasilabilir(self, aday):
        if not aday.yerel:
            return aday.kullanilabilir_mi()
        zaman, kayit = self._yerel_onbellek
        if time.time() - zaman >= 20:
            kayit = {}
            self._yerel_onbellek = (time.time(), kayit)
        if aday.saglayici not in kayit:
            kayit[aday.saglayici] = aday.kullanilabilir_mi()
        return kayit[aday.saglayici]

    def kullanilabilirler(self):
        """Şu an yanıt verebilecek beyinler (sıralı)."""
        from . import kota
        sonuc = []
        for aday in self._adaylar(self._ayar_oku()):
            if not self._ulasilabilir(aday):
                continue
            if not aday.yerel and kota.engel(aday.saglayici)[0]:
                continue
            sonuc.append(aday)
        return sonuc

    def engelliler(self):
        """Anahtarı olup kotası dolu/bekleyen bulut beyinler: (ad, neden, bekle)."""
        from . import kota
        sonuc = []
        for aday in self._adaylar(self._ayar_oku()):
            if aday.yerel or not aday.kullanilabilir_mi():
                continue
            engelli, neden, bekle = kota.engel(aday.saglayici)
            if engelli:
                sonuc.append((aday.ad, neden, bekle))
        return sonuc

    def sec(self):
        """İlk kullanılabilir beyni döndürür; hiçbiri yoksa None."""
        liste = self.kullanilabilirler()
        return liste[0] if liste else None

    def sifirla(self):
        """Önbelleği temizler (ayar değişince çağrılır)."""
        self._yerel_onbellek = (0.0, [])

    def durum(self):
        """Arayüzde gösterilecek kısa beyin durumu."""
        beyin = self.sec()
        if beyin is None:
            return {"beyin": None, "yerel": None}
        return {"beyin": beyin.ad, "yerel": beyin.yerel}
