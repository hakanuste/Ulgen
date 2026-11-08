"""Kurum görüşü derlemesi: aracı kurumların analist tavsiyeleri ve model portföyleri.

Kaynak: kullanıcının giriş yaptığı Fintables (oturumlu okuyucu, salt okuma).
Her kurumun "Analist tavsiyeleri" tablosu (hisse, öneri, tarih, hedef fiyat,
son fiyat, potansiyel getiri, model portföyde mi) okunur; hisse başına kaç
kurumun ne dediği hesaplanır. Bu bir DERLEME'dir: kurumların görüşünü özetler,
kendi yatırım tavsiyemiz değildir.
"""

import re
import statistics
import time
from datetime import date

from . import obsidyen_yaz, oturum, piyasa

TABAN = "https://fintables.com"
LISTE_ADRESI = TABAN + "/araci-kurumlar"
KOMUT_DESENI = re.compile(r"^\s*portf[öo]y\s*[:\-]\s*(\d{0,2})\s*$", re.IGNORECASE)
AY = {"oca": 1, "şub": 2, "mar": 3, "nis": 4, "may": 5, "haz": 6,
      "tem": 7, "ağu": 8, "eyl": 9, "eki": 10, "kas": 11, "ara": 12}
POZITIF = {"al", "güçlü al", "endeks üstü", "endeks üzeri", "piyasa üstü",
           "artır", "fazla ağırlık", "outperform", "overweight"}
NEGATIF = {"sat", "güçlü sat", "endeks altı", "piyasa altı", "azalt",
           "düşük ağırlık", "underperform", "underweight"}
TARIH = re.compile(r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]{3,})\.?\s+(\d{4})")
KOD = re.compile(r"^[A-ZÇĞİÖŞÜ]{3,6}$")
ESKI_GUN = 180


def sayi(metin):
    """'% -45,42' / 'G331,75' / '1.234,50' -> float; olmazsa None."""
    t = re.sub(r"[%\sG]", "", str(metin or ""))
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def tarih(metin):
    e = TARIH.search(str(metin or ""))
    if not e:
        return None
    ay = AY.get(e.group(2).lower()[:3])
    if not ay:
        return None
    try:
        return date(int(e.group(3)), ay, int(e.group(1)))
    except ValueError:
        return None


def yon(oneri):
    k = str(oneri or "").strip().lower()
    if k in POZITIF:
        return "olumlu"
    if k in NEGATIF:
        return "olumsuz"
    return "nötr"


def satir_coz(hucreler):
    """DOM hücrelerinden ({t, s}) bir tavsiye kaydı; olmazsa None."""
    kod = oneri = tr = None
    sayilar, simge = [], ""
    for h in hucreler:
        t = (h.get("t") or "").strip()
        ilk = t.split("\n")[0].strip() if t else ""
        if kod is None and KOD.match(ilk) and not tarih(t):
            kod = ilk
        elif tarih(t) and tr is None:
            tr = tarih(t)
        elif t and kod and oneri is None and not re.search(r"\d", t):
            oneri = t
        elif t and re.search(r"\d", t) and "," in t:      # sıra no. (1,2..) değil
            v = sayi(t)
            if v is not None:
                sayilar.append(v)
        elif not t and h.get("s"):
            simge = h["s"]
    if not (kod and oneri and tr and len(sayilar) >= 3):
        return None
    return {"kod": kod, "oneri": oneri, "tarih": tr, "hedef": sayilar[0],
            "son": sayilar[1], "getiri": sayilar[2], "simge": simge}


def metinden_coz(metin):
    """Düz metin yedeği: 'ASELS Al 1 Eki 2026 575,00 331,75 73,32' kalıbı."""
    duz = " ".join(str(metin).split())
    kayitlar = []
    kalip = re.compile(
        r"([A-ZÇĞİÖŞÜ]{3,6})\s+((?:Endeks|Piyasa)\s+\S+|[A-Za-zÇĞİÖŞÜçğıöşü]+)\s+"
        r"(\d{1,2}\s+[A-Za-zÇĞİÖŞÜçğıöşü]{3,}\.?\s+\d{4})\s+"
        r"([\d.]+,\d+)\s+G?\s*([\d.]+,\d+)\s+%?\s*(-?[\d.]+,\d+)")
    for m in kalip.finditer(duz):
        kayitlar.append({"kod": m.group(1), "oneri": m.group(2),
                         "tarih": tarih(m.group(3)), "hedef": sayi(m.group(4)),
                         "son": sayi(m.group(5)), "getiri": sayi(m.group(6)),
                         "simge": ""})
    return [k for k in kayitlar if k["tarih"]]


def kurum_kodlari(baglantilar):
    """Liste sayfasındaki bağlantılardan kurum kodları (sırasını korur)."""
    kodlar = []
    for b in baglantilar:
        e = re.search(r"/araci-kurumlar/([A-Za-z0-9]{2,8})(?:[/?#]|$)", b or "")
        if e and e.group(1).upper() not in kodlar:
            kodlar.append(e.group(1).upper())
    return kodlar


def model_simgesi_belirle(tum_simgeler):
    """En sık görülen simge 'portföyde değil' (✕) sayılır; diğerleri 'portföyde'.

    Simgeler yalnız görüntü olduğundan bu bir ÇIKARIM'dır; rapor bunu yazar."""
    sayac = {}
    for s in tum_simgeler:
        if s:
            sayac[s] = sayac.get(s, 0) + 1
    if len(sayac) < 2:
        return None
    return max(sayac, key=sayac.get)


def topla(kurumlar, bugun=None):
    """kurumlar: {kod: [kayıt,...]} -> hisse başına derleme (güncel kayıtlar)."""
    bugun = bugun or date.today()
    tum = [k["simge"] for liste in kurumlar.values() for k in liste]
    yok_simgesi = model_simgesi_belirle(tum)
    hisseler = {}
    for kurum, liste in kurumlar.items():
        for k in liste:
            if (bugun - k["tarih"]).days > ESKI_GUN:
                continue
            h = hisseler.setdefault(k["kod"], {"kurumlar": {}, "model": 0})
            h["kurumlar"][kurum] = k
            if yok_simgesi and k["simge"] and k["simge"] != yok_simgesi:
                h["model"] += 1
    return hisseler, yok_simgesi


def ozet(hisseler, kurum_sayisi):
    satirlar = []
    for kod, h in hisseler.items():
        ks = list(h["kurumlar"].values())
        hedefler = [k["hedef"] for k in ks if k["hedef"]]
        getiriler = [k["getiri"] for k in ks if k["getiri"] is not None]
        yonler = [yon(k["oneri"]) for k in ks]
        satirlar.append({
            "kod": kod, "kurum": len(ks),
            "kapsam": 100.0 * len(ks) / max(kurum_sayisi, 1),
            "olumlu": yonler.count("olumlu"), "notr": yonler.count("nötr"),
            "olumsuz": yonler.count("olumsuz"), "model": h["model"],
            "hedef_min": min(hedefler) if hedefler else None,
            "hedef_ort": statistics.median(hedefler) if hedefler else None,
            "hedef_max": max(hedefler) if hedefler else None,
            "getiri_ort": statistics.median(getiriler) if getiriler else None,
        })
    satirlar.sort(key=lambda r: (-r["kurum"], -r["olumlu"], r["kod"]))
    return satirlar


def _f(x, b=2):
    return "—" if x is None else piyasa.tr_sayi(x, b)


def rapor(kurumlar, atlananlar, bugun=None, en_cok=25):
    bugun = bugun or date.today()
    veri_olan = {k: v for k, v in kurumlar.items() if v}
    hisseler, yok = topla(veri_olan, bugun)
    satir = ozet(hisseler, len(veri_olan))
    kisa = ["# Kurum görüşü derlemesi (%s)" % bugun.strftime("%d.%m.%Y"), "",
            "Kaynak: Fintables analist tavsiyeleri; %d kurum okundu (tavsiyesi "
            "olan), %d kurum okunamadı/boş. %d günden eski tavsiyeler "
            "sayılmadı." % (len(veri_olan), len(atlananlar), ESKI_GUN), "",
            "| Hisse | Kurum | Kapsam | Olumlu/Nötr/Olumsuz | Model portföy | "
            "Hedef (en düşük–ortanca–en yüksek) | Ort. potansiyel |",
            "|---|---|---|---|---|---|---|"]
    for r in satir[:en_cok]:
        kisa.append("| %s | %d | %%%s | %d/%d/%d | %s | %s – %s – %s | %%%s |" % (
            r["kod"], r["kurum"], _f(r["kapsam"], 0), r["olumlu"], r["notr"],
            r["olumsuz"], r["model"] if yok else "?",
            _f(r["hedef_min"]), _f(r["hedef_ort"]), _f(r["hedef_max"]),
            _f(r["getiri_ort"], 0)))
    kisa += ["", "## Nasıl okunur",
             "- **Kapsam:** hisse için güncel tavsiyesi olan kurumların, "
             "taranan kurumlara oranı.",
             "- **Olumlu:** Al / endeks üstü; **olumsuz:** Sat / endeks altı; "
             "gerisi nötr (Tut vb.).",
             "- **Hedef:** kurumların 12 aylık hedef fiyatları; ortanca "
             "aşırı uçlardan etkilenmez."]
    if yok:
        kisa.append("- **Model portföy:** tablodaki simgeden ÇIKARILDI (en "
                    "sık görülen simge 'portföyde değil' sayıldı). Birkaç "
                    "hisseyi Fintables'ta elle denetleyin.")
    else:
        kisa.append("- **Model portföy:** simgeler ayırt edilemedi; sütun "
                    "'?' bırakıldı.")
    kisa += ["", "## Dikkat",
             "- Bu, kurumların görüşlerinin derlemesidir; bizim önerimiz "
             "değildir. Kurumlar aynı hisseyi öneriyorsa bu doğru olduğunu "
             "göstermez (sürü etkisi, çıkar çatışması olabilir).",
             "- Kurum sayısı azsa yüzdeler yanıltıcıdır.",
             "- Yatırım tavsiyesi değildir; karar sizindir."]
    if atlananlar:
        kisa += ["", "Okunamayan/boş kurumlar: " + ", ".join(atlananlar[:40])]
    return "\n".join(kisa)


def calistir(ilk_n=20, ilerleme=None, bekleme_sn=3.0):
    """Fintables'ta ilk N kurumu (pazar payına göre) gezer; rapor metni döndürür."""
    sorun = oturum.hazirlik_hatasi(LISTE_ADRESI)
    if sorun:
        return sorun
    kurumlar, atlanan = {}, []
    with oturum.Okuyucu(bekleme_sn) as o:
        o.ac(LISTE_ADRESI)
        kodlar = kurum_kodlari(o.baglantilar())[:max(1, ilk_n)]
        if not kodlar:
            return ("Kurum listesi okunamadı. Giriş süresi dolmuş olabilir: "
                    "'giris: fintables.com' ile yeniden giriş yapın.")
        for i, kod in enumerate(kodlar, 1):
            if ilerleme:
                ilerleme("Kurum %d/%d: %s" % (i, len(kodlar), kod))
            try:
                o.ac("%s/%s/analist-tavsiyeleri" % (LISTE_ADRESI, kod))
                kayitlar = [k for k in (satir_coz(r)
                                        for r in o.kaydir_ve_satirlar()) if k]
                if not kayitlar:
                    kayitlar = metinden_coz(o.metin())
            except Exception:
                kayitlar = []
            if kayitlar:
                kurumlar[kod] = kayitlar
            else:
                atlanan.append(kod)
            time.sleep(bekleme_sn)
    if not kurumlar:
        return ("Hiçbir kurumdan tavsiye okunamadı. Giriş süresi dolmuş ya da "
                "sayfa düzeni değişmiş olabilir.")
    return rapor(kurumlar, atlanan)


def komut_kaydet(rapor_metni):
    try:
        yol = obsidyen_yaz.yaz(
            "Akçe", "Kurum görüşü derlemesi " + date.today().isoformat(),
            obsidyen_yaz.onbilgi(tur="kurum-derlemesi") + rapor_metni)
        return "\n\n(Not kaydedildi: %s)" % yol
    except Exception:
        return ""


def komut(metin, ulgen):
    """'portfoy: 20' -> arka planda çalıştırır; sonuç sohbette yayınlanır."""
    e = KOMUT_DESENI.match(metin or "")
    if not e:
        return None
    n = int(e.group(1) or 20)
    sorun = oturum.hazirlik_hatasi(LISTE_ADRESI)
    if sorun:
        return sorun
    import threading

    def kos():
        try:
            r = calistir(n)
            r += komut_kaydet(r)
        except BaseException as hata:
            r = "Derleme tamamlanamadı: %s" % str(hata)[:200]
        ulgen.bildir("🤖 AKÇA – kurum görüşü derlemesi\n\n" + r[:12000],
                     {"tur": "ajan_sonuc", "ajan": "AKÇA"})
    threading.Thread(target=kos, daemon=True).start()
    return ("İlk %d kurumun analist tavsiyeleri okunuyor (kurum başına birkaç "
            "saniye; yaklaşık %d dakika). Bitince sonuç burada yayınlanır."
            % (n, max(1, n // 6)))
