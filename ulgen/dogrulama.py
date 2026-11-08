"""Yanıt doğrulayıcı: Ülgen'in verdiği gerçek bilgileri web kaynaklarıyla
karşılaştırır ve işi bitince kullanıcıya KISA bir sonuç bildirir.

Akış: yanıt verilir -> arka planda somut iddialar ayıklanır (sayı, özel ad
içeren cümleler) -> her biri için arama yapılır -> iddianın anahtar
sözcükleri (sayılar, özel adlar) kaynak sayfalarında aranır -> sonuç
bildirilir. Kullanıcı sessiz kalırsa doğru sayılır; ``yanlış: <doğrusu>``
yazarsa düzeltme hafızaya kullanıcı bilgisi olarak kaydedilir.

Gizlilik: yalnız kişisel/duyarlı veri içermeyen konuşmalar doğrulanır; web'e
yalnızca iddia cümlesi gider. Sağlıkla ilgili konular hiç doğrulanmaz.
"""

import re
import threading

from . import ayar, guvenlik, obsidyen

AZAMI_IDDIA = 4
AZAMI_UZUNLUK = 220
AZ_UZUNLUK = 25
EN_AZ_YANIT = 150
DESTEK = 0.75
KISMI = 0.4
YANLIS_DESENI = re.compile(r"^\s*yanl[ıi]ş\s*[:\-–]\s*(.{3,300})$",
                           re.IGNORECASE | re.DOTALL)
OZEL_AD = re.compile(r"\b[A-ZÇĞİÖŞÜ][\w'’-]{2,}")
SAYI = re.compile(r"\d[\d.,]*")
SAGLIK = re.compile(
    r"\b(ilaç|ilac|hap|doz|tedavi|hastal\w*|ağrı|agri|tansiyon|şeker|seker|"
    r"belirti|semptom|tanı|teşhis|yara|enfeksiyon|antibiyotik)\b",
    re.IGNORECASE)


def acik_mi():
    return bool(ayar.yukle().get("dogrulama", True))


def uygun_mu(soru, yanit, kisisel_kullanildi=False):
    """Bu konuşma doğrulanabilir mi? (kişisel/sağlık/kısa yanıtlar değil)"""
    if not acik_mi() or kisisel_kullanildi:
        return False
    if len(yanit or "") < EN_AZ_YANIT:
        return False
    if guvenlik.duyarli_mi(soru) or guvenlik.duyarli_mi(yanit):
        return False
    return not (SAGLIK.search(soru or "") or SAGLIK.search(yanit or ""))


def iddialar_ayikla(yanit):
    """Somut iddia taşıyan cümleler: sayı ya da cümle içinde özel ad."""
    temiz = re.sub(r"[*_`#>]+", " ", yanit)
    cumleler = re.split(r"(?<=[.!?])\s+|\n+", temiz)
    sonuc = []
    for c in cumleler:
        c = re.sub(r"^[\-•\d.)\s]+", "", c).strip()
        if not (AZ_UZUNLUK <= len(c) <= AZAMI_UZUNLUK) or c.endswith("?"):
            continue
        ozel = OZEL_AD.findall(c[1:]) if c else []
        if SAYI.search(c) or ozel:
            sonuc.append(c)
        if len(sonuc) >= AZAMI_IDDIA:
            break
    return sonuc


def anahtarlar(iddia):
    """Sayılar ve özel adlar (normalize); doğrulamanın dayanağı."""
    sayilar = [s.strip(".,") for s in SAYI.findall(iddia)]
    adlar = OZEL_AD.findall(iddia[1:])
    return sorted({obsidyen.normal(k) for k in sayilar + adlar if k})


def puanla(iddia, metin):
    """Anahtarların kaynak metinde bulunma oranı (0..1) ve bulunmayanlar."""
    ks = anahtarlar(iddia)
    if not ks:
        return 0.0, []
    kucuk = obsidyen.normal(metin)
    eksik = [k for k in ks if k not in kucuk]
    return (len(ks) - len(eksik)) / len(ks), eksik


def durum_adi(oran):
    if oran >= DESTEK:
        return "destekleniyor"
    if oran >= KISMI:
        return "kısmen"
    return "bulunamadı"


def tek_dogrula(iddia, arastirma):
    """-> {"iddia", "durum", "oran", "kaynak"}; ağ hatası "bulunamadı"."""
    en_iyi, kaynak = 0.0, ""
    try:
        sonuclar = arastirma.ara(iddia, adet=5)
    except Exception:
        return {"iddia": iddia, "durum": "bakılamadı", "oran": 0.0,
                "kaynak": ""}
    okunan = 0
    for s in sonuclar:
        metin = s.get("baslik", "") + " " + s.get("ozet", "")
        oran, _ = puanla(iddia, metin)
        if oran < DESTEK and okunan < 2:
            try:
                metin += " " + arastirma.sayfa_metni(s["adres"], 6000)
                okunan += 1
                oran, _ = puanla(iddia, metin)
            except Exception:
                pass
        if oran > en_iyi:
            en_iyi, kaynak = oran, s.get("adres", "")
    return {"iddia": iddia, "durum": durum_adi(en_iyi), "oran": en_iyi,
            "kaynak": kaynak}


def ozet_metni(sonuclar):
    toplam = len(sonuclar)
    iyi = [s for s in sonuclar if s["durum"] == "destekleniyor"]
    sorunlu = [s for s in sonuclar if s["durum"] in ("kısmen", "bulunamadı")]
    satir = ["Doğrulama bitti: %d iddiadan %d'i kaynaklarda destekleniyor."
             % (toplam, len(iyi))]
    for s in sorunlu:
        satir.append("• Kaynaklarda net bulamadım: «%s»" % s["iddia"][:140])
    if iyi and iyi[0]["kaynak"]:
        satir.append("Örnek kaynak: %s" % iyi[0]["kaynak"])
    satir.append("Doğruysa bir şey demeyin. Yanlış gördüğünüz varsa "
                 "'yanlış: <doğrusu>' yazın, öğrenip kaydedeyim.")
    return "\n".join(satir)


def calistir(yanit, arastirma, bildir, kaydet=None):
    """Eşzamanlı çalışır (testte kolay); sonucu bildirir ve döndürür."""
    iddialar = iddialar_ayikla(yanit)
    if not iddialar:
        return []
    sonuclar = [tek_dogrula(i, arastirma) for i in iddialar]
    if all(s["durum"] == "bakılamadı" for s in sonuclar):
        return sonuclar            # ağ yok: gürültü yapma
    sonuclar = [s for s in sonuclar if s["durum"] != "bakılamadı"]
    if kaydet:
        kaydet(sonuclar)
    bildir(ozet_metni(sonuclar))
    return sonuclar


def arka_planda(yanit, arastirma, bildir, kaydet=None):
    def kos():
        try:
            calistir(yanit, arastirma, bildir, kaydet)
        except Exception:
            pass
    t = threading.Thread(target=kos, daemon=True)
    t.start()
    return t


def duzeltme_mi(metin):
    """'yanlış: ...' ise doğrusunu döndürür, değilse None."""
    e = YANLIS_DESENI.match(metin or "")
    return e.group(1).strip() if e else None
