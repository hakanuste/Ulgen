"""Sağlayıcı kotası: sayaç, engel, gerçek/tahmini ayrımı, ücretsiz güvencesi.

Her bulut çağrısı ``kota_olay`` tablosuna yazılır. İki ayrı bilgi tutulur ve
ASLA karıştırılmaz:
  * GERÇEK  : sağlayıcının kendisinin bildirdiği değer (yanıt başlıkları,
              ``usage`` alanı, OpenRouter ``/key``).
  * TAHMİNİ : Ülgen'in kendi sayacı (istek sayısı kesindir; token sayısı
              sağlayıcı bildirmediyse karakterden hesaplanır ve "tahmini"
              diye işaretlenir).

Ücretli kullanım: ``UCRETLI_YASAK`` her zaman doğrudur; ayar dosyasında bunu
açan bir seçenek YOKTUR. Kota dolunca Ülgen başka ücretsiz beyne geçer, hepsi
doluysa isteği kuyruğa alır (bkz. kuyruk.py); ücretli servise asla geçmez.
"""

import json
import time
from datetime import datetime, timedelta, timezone

from . import ayar, veritabani
from .beyin import BeyinHatasi

UCRETLI_YASAK = True
MALIYET = 0.0           # her zaman 0: yalnızca ücretsiz katmanlar kullanılır

# Belgelerden alınan ücretsiz katman sınırları. None = belgede sayı yok / modele
# göre değişiyor; o zaman yalnızca sağlayıcının 429 yanıtı ve başlıkları
# kullanılır. ayar.json "kota_sinirlari" ile düzeltilebilir.
SINIRLAR = {
    "gemini": {"rpm": None, "rpd": None, "tpm": None, "tpd": None,
               "sifirlama": "pasifik",
               "kaynak": "ai.google.dev/gemini-api/docs/rate-limits: sınırlar "
                         "modele göre değişir, sayı AI Studio'da; günlük "
                         "kota gece yarısı (Pasifik saati) yenilenir"},
    "groq": {"rpm": 30, "rpd": None, "tpm": None, "tpd": None,
             "sifirlama": "utc",
             "kaynak": "console.groq.com/docs/rate-limits: çoğu metin modeli "
                       "30 RPM; kesin değerler hesabınızın Limits sayfasında"},
    "mistral": {"rpm": 60, "rpd": None, "tpm": 500000, "tpd": None,
                "tpay": 1000000000, "sifirlama": "utc",
                "kaynak": "help.mistral.ai: ücretsiz katman 1 istek/sn, "
                          "500 bin token/dk, 1 milyar token/ay"},
    "openrouter": {"rpm": 20, "rpd": 50, "tpm": None, "tpd": None,
                   "sifirlama": "utc",
                   "kaynak": "openrouter.ai/docs/limits: :free modeller 20 "
                             "istek/dk; 50 istek/gün (10 krediden azsa)"},
}
YEREL = ("ollama", "llamacpp")
ADLAR = {"gemini": "Gemini", "groq": "Groq", "mistral": "Mistral",
         "openrouter": "OpenRouter", "ollama": "Ollama (yerel)",
         "llamacpp": "llama.cpp (yerel)"}


# ------------------------------------------------------ ücretsiz güvencesi
def ucretsiz_mi(saglayici, model):
    """Model ücretsiz katmanda mı? (OpenRouter'da yalnızca ':free' ya da
    'openrouter/free'.) Diğer sağlayıcılarda ücretsizlik hesap düzeyindedir:
    anahtarınıza fatura kartı eklemeyin."""
    if saglayici == "openrouter":
        return model.endswith(":free") or model == "openrouter/free"
    return True


def ucretsiz_dogrula(saglayici, model):
    if UCRETLI_YASAK and not ucretsiz_mi(saglayici, model):
        raise BeyinHatasi(
            "'%s' ücretsiz değil; ücretli model kullanımı kapalıdır. "
            "Ayarda ':free' ile biten bir model seçin." % model)


# ------------------------------------------------------------ zaman ve sınır
def _sinirlar(saglayici):
    taban = dict(SINIRLAR.get(saglayici, {}))
    taban.update((ayar.yukle().get("kota_sinirlari") or {}).get(saglayici, {}))
    return taban


def gun_basi(saglayici, simdi=None):
    """Günlük kotanın başladığı an (epoch)."""
    simdi = time.time() if simdi is None else simdi
    if _sinirlar(saglayici).get("sifirlama") == "pasifik":
        try:
            from zoneinfo import ZoneInfo
            yerel = datetime.fromtimestamp(simdi, ZoneInfo(
                "America/Los_Angeles"))
        except Exception:
            yerel = datetime.fromtimestamp(
                simdi, timezone(timedelta(hours=-8)))
        return yerel.replace(hour=0, minute=0, second=0,
                             microsecond=0).timestamp()
    utc = datetime.fromtimestamp(simdi, timezone.utc)
    return utc.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def ay_basi(simdi=None):
    utc = datetime.fromtimestamp(time.time() if simdi is None else simdi,
                                 timezone.utc)
    return utc.replace(day=1, hour=0, minute=0, second=0,
                       microsecond=0).timestamp()


# ------------------------------------------------------------------- yazma
def kaydet(saglayici, model, giris, cikis, gercek, durum, gecikme_ms,
           hata=""):
    veritabani.sorgu(
        "INSERT INTO kota_olay (saglayici, model, zaman, giris_token, "
        "cikis_token, gercek, durum, gecikme_ms) VALUES (?,?,?,?,?,?,?,?)",
        (saglayici, model, time.time(), int(giris), int(cikis), int(gercek),
         durum, int(gecikme_ms)))
    if hata:
        _durum_yaz(saglayici, son_hata=hata)


def _durum_yaz(saglayici, **alanlar):
    veritabani.sorgu("INSERT OR IGNORE INTO kota_durum (saglayici) VALUES (?)",
                     (saglayici,))
    for ad, deger in alanlar.items():
        if ad not in ("engel_son", "engel_neden", "gercek", "gercek_zaman",
                      "son_hata"):
            raise ValueError(ad)
        veritabani.sorgu("UPDATE kota_durum SET %s=? WHERE saglayici=?" % ad,
                         (deger, saglayici))


def engel_koy(saglayici, saniye, neden):
    """Sağlayıcıyı ``saniye`` süre kullanma (429 sonrası)."""
    _durum_yaz(saglayici, engel_son=time.time() + max(1, saniye),
               engel_neden=neden, son_hata=neden)


def basliklari_isle(saglayici, basliklar):
    """Sağlayıcının bildirdiği GERÇEK kalan kotayı saklar (varsa)."""
    gercek = {}
    for ad, alan in (("x-ratelimit-remaining-requests", "kalan_istek"),
                     ("x-ratelimit-remaining-tokens", "kalan_token"),
                     ("x-ratelimit-limit-requests", "limit_istek"),
                     ("x-ratelimit-limit-tokens", "limit_token"),
                     ("x-ratelimit-reset-requests", "yenilenme_istek"),
                     ("x-ratelimit-reset-tokens", "yenilenme_token")):
        if ad in basliklar:
            gercek[alan] = basliklar[ad]
    if gercek:
        _durum_yaz(saglayici, gercek=json.dumps(gercek),
                   gercek_zaman=time.time())


def openrouter_gercek(anahtar):
    """OpenRouter /key uç noktasından GERÇEK günlük ücretsiz kullanımı alır."""
    from .beyin import OpenAIUyumluBeyin, _json_gonder
    veri = _json_gonder(OpenAIUyumluBeyin.TABANLAR["openrouter"] + "/key",
                        basliklar={"Authorization": "Bearer " + anahtar},
                        zaman_asimi=15)
    gunluk = (veri.get("data") or veri).get("free_model_daily_requests") or {}
    if gunluk:
        _durum_yaz("openrouter", gercek=json.dumps({
            "kalan_istek": gunluk.get("remaining"),
            "limit_istek": gunluk.get("limit"),
            "kullanilan_istek": gunluk.get("used")}),
            gercek_zaman=time.time())
    return gunluk


# ----------------------------------------------------------------- okuma
def _durum_oku(saglayici):
    satir = veritabani.sorgu("SELECT * FROM kota_durum WHERE saglayici=?",
                             (saglayici,), True)
    return satir[0] if satir else {
        "engel_son": 0, "engel_neden": "", "gercek": "{}",
        "gercek_zaman": 0, "son_hata": ""}


def kullanim(saglayici, simdi=None):
    """Kendi sayacımızdan (TAHMİNİ) kullanım özeti."""
    simdi = time.time() if simdi is None else simdi
    gun = gun_basi(saglayici, simdi)

    def topla(baslangic):
        s = veritabani.sorgu(
            "SELECT COUNT(*) AS n, COALESCE(SUM(giris_token+cikis_token),0) "
            "AS t, COALESCE(SUM(CASE WHEN gercek=0 THEN 1 ELSE 0 END),0) AS "
            "tahmin FROM kota_olay WHERE saglayici=? AND zaman>=? AND "
            "durum='ok'", (saglayici, baslangic), True)[0]
        return s["n"], s["t"], s["tahmin"]
    dakika = topla(simdi - 60)
    bugun = topla(gun)
    ay = topla(ay_basi(simdi))
    tum = veritabani.sorgu(
        "SELECT COUNT(*) AS n, COALESCE(SUM(CASE WHEN durum!='ok' THEN 1 "
        "ELSE 0 END),0) AS hata, COALESCE(AVG(CASE WHEN durum='ok' THEN "
        "gecikme_ms END),0) AS gecikme FROM kota_olay WHERE saglayici=? "
        "AND zaman>=?", (saglayici, simdi - 86400), True)[0]
    return {"istek_dk": dakika[0], "token_dk": dakika[1],
            "istek_gun": bugun[0], "token_gun": bugun[1],
            "tahmini_token_olay_gun": bugun[2],
            "token_ay": ay[1], "istek_24s": tum["n"],
            "hata_24s": tum["hata"], "gecikme_ms": int(tum["gecikme"])}


def engel(saglayici, simdi=None):
    """(engelli_mi, neden, kalan_saniye). Yerel beyinler hiç engellenmez."""
    if saglayici in YEREL:
        return False, "", 0
    simdi = time.time() if simdi is None else simdi
    d = _durum_oku(saglayici)
    if d["engel_son"] > simdi:
        return True, d["engel_neden"] or "sağlayıcı bekletiyor", \
            int(d["engel_son"] - simdi) + 1
    sinir = _sinirlar(saglayici)
    k = kullanim(saglayici, simdi)
    if sinir.get("rpm") and k["istek_dk"] >= sinir["rpm"]:
        return True, "dakikalık istek sınırı (%d)" % sinir["rpm"], 30
    if sinir.get("tpm") and k["token_dk"] >= sinir["tpm"]:
        return True, "dakikalık token sınırı (%d)" % sinir["tpm"], 30
    if sinir.get("rpd") and k["istek_gun"] >= sinir["rpd"]:
        return True, "günlük istek sınırı (%d)" % sinir["rpd"], \
            int(gun_basi(saglayici, simdi) + 86400 - simdi)
    if sinir.get("tpd") and k["token_gun"] >= sinir["tpd"]:
        return True, "günlük token sınırı", \
            int(gun_basi(saglayici, simdi) + 86400 - simdi)
    if sinir.get("tpay") and k["token_ay"] >= sinir["tpay"]:
        return True, "aylık token sınırı", 3600
    return False, "", 0


def tablo(simdi=None):
    """Panel için sağlayıcı başına durum listesi."""
    simdi = time.time() if simdi is None else simdi
    a = ayar.yukle()
    sonuc = []
    for ad in YEREL + ("gemini", "groq", "mistral", "openrouter"):
        if ad in ayar.SIRLAR and not a.get(ad + "_anahtar"):
            continue
        k = kullanim(ad, simdi)
        engelli, neden, bekle = engel(ad, simdi)
        sinir = _sinirlar(ad)
        d = _durum_oku(ad)
        gercek = json.loads(d["gercek"] or "{}")
        yas = int(simdi - d["gercek_zaman"]) if d["gercek_zaman"] else None
        kalan_tahmini = None
        if sinir.get("rpd"):
            kalan_tahmini = max(sinir["rpd"] - k["istek_gun"], 0)
        sonuc.append({
            "saglayici": ad, "ad": ADLAR[ad], "yerel": ad in YEREL,
            "engelli": engelli, "neden": neden, "bekle_sn": bekle,
            "sinir": {x: sinir.get(x) for x in
                      ("rpm", "rpd", "tpm", "tpd", "tpay")},
            "sinir_kaynagi": sinir.get("kaynak", ""),
            "tahmini": {"kalan_istek_gun": kalan_tahmini, **k},
            "gercek": gercek or None, "gercek_yas_sn": yas,
            "hata_orani": (k["hata_24s"] / k["istek_24s"]
                           if k["istek_24s"] else 0.0),
            "son_hata": d["son_hata"], "maliyet": MALIYET})
    return sonuc


def metin(simdi=None):
    """İnsan okuyabilir kota raporu (gerçek ve tahmini ayrı satırlarda)."""
    satirlar = []
    for t in tablo(simdi):
        durum = ("ENGELLİ: %s (~%d sn)" % (t["neden"], t["bekle_sn"])
                 if t["engelli"] else "kullanılabilir")
        e = t["tahmini"]
        satirlar.append("• %s — %s" % (t["ad"], durum))
        satirlar.append(
            "   Tahmini (kendi sayacım): bugün %d istek, ~%d token; son "
            "dakika %d istek; gecikme ~%d ms; hata oranı %%%d; maliyet 0 ₺"
            % (e["istek_gun"], e["token_gun"], e["istek_dk"],
               e["gecikme_ms"], round(t["hata_orani"] * 100)))
        if e["kalan_istek_gun"] is not None:
            satirlar.append("   Tahmini kalan günlük istek: %d (sınır belge/"
                            "ayardan)" % e["kalan_istek_gun"])
        if t["gercek"]:
            satirlar.append("   GERÇEK (sağlayıcı bildirdi, %d sn önce): %s"
                            % (t["gercek_yas_sn"] or 0, ", ".join(
                                "%s=%s" % kv for kv in t["gercek"].items())))
        elif not t["yerel"]:
            satirlar.append("   Gerçek kalan kota: sağlayıcı bildirmedi.")
    return "\n".join(satirlar) or "Tanımlı sağlayıcı yok."
