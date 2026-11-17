"""Kullanıcının kendi eklediği yapay zekâ sağlayıcıları.

OpenAI uyumlu (``/chat/completions``) her servis eklenebilir: DeepSeek,
Together, Anthropic (Claude, OpenAI uyumlu uç), kendi Mac'inizdeki LM Studio
vb. Tanım ayar.json'a (anahtarsız), anahtar Anahtar Zinciri'ne yazılır.

Kurallar:
- Adres https olmalı; yalnızca bu Mac'teki sunucu (127.0.0.1/localhost)
  için http olabilir. Yerel adres yerel beyin sayılır (veri Mac'ten çıkmaz).
- "Ücretsiz" işaretlenmeyen sağlayıcıya Ülgen kendiliğinden geçmez; tanım
  durur ama kullanılmaz (ücretli servise otomatik geçiş yok).
"""

import re
from urllib.parse import urlparse

from . import ayar, gizli
from .beyin import BeyinHatasi, OzelBeyin, ozel_yerel_mi

ONEK = "ozel_"
ORNEKLER = [
    {"baslik": "DeepSeek", "taban": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"baslik": "Claude (Anthropic)", "taban": "https://api.anthropic.com/v1",
     "model": "claude-sonnet-5-5"},
    {"baslik": "LM Studio (bu Mac)", "taban": "http://127.0.0.1:1234/v1", "model": "yerel-model"},
]


class SaglayiciHatasi(Exception):
    pass


def liste():
    a = ayar.yukle()
    sonuc = []
    for t in a.get("ozel_saglayicilar") or []:
        if not isinstance(t, dict) or not t.get("ad"):
            continue
        yer, son4 = gizli.sir_durumu(t["ad"])
        uzmanlari = [u for u, s in (a.get("uzman_saglayici") or {}).items() if s == t["ad"]]
        one = t["ad"] in (a.get("one_alinanlar") or [])
        sonuc.append(dict(t, anahtar_var=yer is not None, son4=son4 or "", uzmanlar=uzmanlari,
                          one=one,
                          yerel=ozel_yerel_mi(t.get("taban", "")),
                          acik=t["ad"] not in set(a.get("kapali_beyinler") or [])))
    return sonuc


def dogrula(veri):
    baslik = " ".join(str(veri.get("baslik", "")).split())[:40]
    if not baslik:
        raise SaglayiciHatasi("Bir ad yazın (örn. DeepSeek).")
    taban = str(veri.get("taban", "")).strip().rstrip("/")
    u = urlparse(taban)
    if u.scheme not in ("https", "http") or not u.hostname:
        raise SaglayiciHatasi("Adres https:// ile başlamalı (örn. https://api.deepseek.com/v1).")
    if u.scheme == "http" and not ozel_yerel_mi(taban):
        raise SaglayiciHatasi("Dışarıdaki bir servis için yalnızca https kabul edilir.")
    if u.username or u.password or u.query or u.fragment:
        raise SaglayiciHatasi("Adreste kullanıcı adı, parola ya da ? bulunmamalı.")
    if taban.endswith("/chat/completions"):
        taban = taban[:-len("/chat/completions")]
    model = str(veri.get("model", "")).strip()
    if not re.fullmatch(r"[\w.:/@+-]{1,120}", model):
        raise SaglayiciHatasi("Model adını sağlayıcının yazdığı gibi girin (örn. deepseek-chat).")
    kok = re.sub(r"[^a-z0-9]+", "_", baslik.lower().translate(
        str.maketrans("çğıöşüâî", "cgiosuai"))).strip("_")[:20] or "saglayici"
    return {"ad": ONEK + kok, "baslik": baslik, "taban": taban, "model": model,
            "ucretsiz": bool(veri.get("ucretsiz"))}


def ekle(veri):
    """Ekler ya da aynı adlıyı günceller. Anahtar verildiyse Anahtar Zinciri'ne."""
    t = dogrula(veri)
    anahtar = str(veri.get("anahtar") or "").strip()
    if anahtar:
        if not 8 <= len(anahtar) <= 400 or re.search(r"\s", anahtar) or not anahtar.isprintable():
            raise SaglayiciHatasi("Anahtar geçersiz görünüyor.")
    elif not ozel_yerel_mi(t["taban"]) and gizli.sir_durumu(t["ad"])[0] is None:
        raise SaglayiciHatasi("Bu servis için API anahtarı gerekli.")
    a = ayar.yukle()
    mevcut = [x for x in (a.get("ozel_saglayicilar") or [])
              if isinstance(x, dict) and x.get("ad") != t["ad"]]
    if len(mevcut) >= 10:
        raise SaglayiciHatasi("En çok 10 özel sağlayıcı eklenebilir.")
    if anahtar:
        gizli.sir_yaz(t["ad"], anahtar)
    ayar.guncelle("ozel_saglayicilar", mevcut + [t])
    return t


def sil(ad):
    a = ayar.yukle()
    kalan = [x for x in (a.get("ozel_saglayicilar") or [])
             if isinstance(x, dict) and x.get("ad") != ad]
    if len(kalan) == len(a.get("ozel_saglayicilar") or []):
        raise SaglayiciHatasi("Böyle bir sağlayıcı yok.")
    ayar.guncelle("ozel_saglayicilar", kalan)
    gizli.sir_sil(ad)
    kapali = [k for k in (a.get("kapali_beyinler") or []) if k != ad]
    ayar.guncelle("kapali_beyinler", kapali)
    ayar.guncelle("one_alinanlar", [x for x in (a.get("one_alinanlar") or []) if x != ad])
    ayar.guncelle("uzman_saglayici", {u: x for u, x in
                                      (a.get("uzman_saglayici") or {}).items() if x != ad})


def dene(ad):
    """Gerçek, kısa bir istek (özel veri yok)."""
    t = next((x for x in liste() if x["ad"] == ad), None)
    if not t:
        raise SaglayiciHatasi("Böyle bir sağlayıcı yok.")
    b = OzelBeyin(t, gizli.sir_oku(ad))
    if not b.kullanilabilir_mi():
        return {"calisti": False, "cikti": "Anahtar ya da model eksik."}
    try:
        yanit = b.yanitla("Kısa yanıt ver.", [{"role": "user",
                                               "content": "Yalnızca 'merhaba' yaz."}], 20)
        return {"calisti": True, "cikti": "%s yanıt verdi: %s" % (t["baslik"], yanit[:80])}
    except BeyinHatasi as hata:
        cikti = str(hata)[:240]
        # 401/404 ama anahtar doğru olabilir: model (AnythingLLM'de çalışma alanı
        # kısa adı) yanlışsa da böyle döner. Geçerli adları sorup yaz.
        if re.match(r"HTTP (401|404)", cikti):
            try:
                adlar = b.modelleri_listele()
            except Exception:
                adlar = []
            if adlar and t["model"] not in adlar:
                cikti += ("\nModel adı '%s' bu serviste yok. Geçerli adlar: %s"
                          % (t["model"], ", ".join(adlar[:15])))
            elif not adlar:
                cikti += ("\nAnahtar ya da model adı (AnythingLLM'de çalışma alanının "
                          "kısa adı) yanlış olabilir.")
        return {"calisti": False, "cikti": cikti}


def uzmana_bagla(ad, uzman):
    """Sağlayıcıyı bir uzmanın öncelikli beyni yapar; uzman boşsa bağı kaldırır."""
    from . import uzmanlar
    if ad not in [t["ad"] for t in liste()]:
        raise SaglayiciHatasi("Böyle bir sağlayıcı yok.")
    baglar = {k: v for k, v in (ayar.yukle().get("uzman_saglayici") or {}).items()
              if v != ad}
    if uzman:
        if uzman not in uzmanlar.UZMANLAR:
            raise SaglayiciHatasi("Böyle bir uzman yok.")
        baglar[uzman] = ad
    ayar.guncelle("uzman_saglayici", baglar)
    return baglar


def one_al(ad, one=True):
    """Sağlayıcıyı beyin sırasında en başa alır (one=False: normal sırasına döner)."""
    if ad not in [t["ad"] for t in liste()]:
        raise SaglayiciHatasi("Böyle bir sağlayıcı yok.")
    liste_ = [x for x in (ayar.yukle().get("one_alinanlar") or []) if x != ad]
    if one:
        liste_.append(ad)
    ayar.guncelle("one_alinanlar", liste_)
    return liste_


def anahtar_degistir(ad, anahtar):
    """Yalnızca anahtarı değiştirir (Anahtar Zinciri); tanım aynı kalır."""
    if ad not in [t["ad"] for t in liste()]:
        raise SaglayiciHatasi("Böyle bir sağlayıcı yok.")
    anahtar = str(anahtar or "").strip()
    if not 8 <= len(anahtar) <= 400 or re.search(r"\s", anahtar) or not anahtar.isprintable():
        raise SaglayiciHatasi("Anahtar geçersiz görünüyor.")
    gizli.sir_yaz(ad, anahtar)
    return anahtar[-4:]
