"""Alan uzmanları: tek yönlendirici + konu profilleri.

Her uzman ayrı bir ajan değil, sistem istemine eklenen bir PROFİL'dir:
kuralları, güvenilir kaynak türleri ve Obsidian'daki bakılacak klasör.
Yönlendirici sorudaki sözcüklere göre en uygun uzmanı seçer.
"""

import os
import re

from . import ayar, obsidyen, obsidyen_yaz

ORTAK = (
    "For facts, FIRST call the tool guvenilir_ara(sorgu, uzman) with your "
    "expert name: it searches only that expert's trusted sites. Base the "
    "answer on what it returns; if it finds nothing, say so. "
    "Cite where each claim comes from (source name or site). When a fact is "
    "not in a source you have, say 'bilinmiyor' - never guess numbers, "
    "names or dates. Label what is traditional/anecdotal versus verified. "
    "Answer in Turkish, plainly, with native Turkish words where possible.")

UZMANLAR = {
    "OTACI": {
        "kaynaklar": [
            "who.int", "ema.europa.eu", "nccih.nih.gov", "pubmed.ncbi.nlm.nih.gov",
            "islamansiklopedisi.org.tr"],
        "alan": "bitkiler, geleneksel şifa bilgisi, ilk yardım kaynakları",
        "anahtar": r"\b(bitki\w*|biberiye|kantaron|nane|lavanta|kekik|"
                   r"papatya|adaçay\w*|ada çay\w*|ıhlamur|çay\w* (iyi|neye)|"
                   r"vitamin\w*|mineral\w*|merhem|tentür|esansiyel|"
                   r"şifalı|ibn[- ]?i? ?sina|ibni sina|el-?kanun|"
                   r"neye iyi|bitkisel)\b",
        "talimat": (
            "You are OTACI, a herbal-knowledge reference. You MAY explain "
            "what a plant is traditionally used for (naming sources such as "
            "Ibn Sina's al-Qanun, Dioscorides, modern monographs), which "
            "vitamins/minerals/active compounds it contains when a source "
            "says so, and HOW it is traditionally prepared and used "
            "(infusion, oil, tincture, topical) as written in those "
            "sources. Always add: safety cautions (toxic look-alikes, drug "
            "interactions, pregnancy/breastfeeding, allergy) and the "
            "modern evidence level (strong / limited / none). Do NOT "
            "diagnose, do NOT replace a doctor's medicine, do NOT give "
            "personal dosing instructions. For serious symptoms (high "
            "fever, bleeding, loss of consciousness, poisoning, breathing "
            "trouble) give first-aid steps and say to call 112 or reach a "
            "doctor. Use the tool bitki_bilgisi to look a plant up and "
            "save the note instead of relying on memory."),
        "klasor": "Bitkiler",
    },
    "TULGA": {
        "kaynaklar": [
            "tr.wikipedia.org", "en.wikipedia.org", "mercedes-benz.com"],
        "alan": "otomotiv ve araç mühendisliği",
        "anahtar": r"\b(musso|m104|ara[cç]\w*|şanzıman\w*|motor\w*|4wd|"
                   r"biyodizel|enjeksiyon|lastik\w*|süspansiyon|fren\w*|"
                   r"overland)\b",
        "talimat": (
            "You are TULGA, vehicle engineering. The user's car is a 1998 "
            "Daewoo Musso 3.2 (Mercedes M104 3.2L inline-6, Mercedes "
            "4-speed auto, BorgWarner part-time 4WD). Prefer manufacturer "
            "and workshop-manual facts; give torque/fluid specs only when "
            "a source states them."),
        "klasor": "Araç",
    },
    "YER-SU": {
        "kaynaklar": [
            "mgm.gov.tr", "tarimorman.gov.tr", "fao.org"],
        "alan": "permakültür, tarım, toprak, su",
        "anahtar": r"\b(permak\w*|toprak\w*|kompost\w*|solucan\w*|zeytin\w*|"
                   r"tohum\w*|sarnıç\w*|sera\w*|gıda ormanı|biyokömür|"
                   r"sulama|tavuk\w*|kaz\w*|gölet\w*)\b",
        "talimat": (
            "You are YER-SU, permaculture and land. The plot is 1509 m2 "
            "olive grove in Koçarlı, Aydın; no chemical inputs, close "
            "input-output loops. Prefer local climate facts."),
        "klasor": "Arsa",
    },
    "KÜN": {
        "kaynaklar": [
            "re.jrc.ec.europa.eu", "nrel.gov", "energy.gov"],
        "alan": "güneş enerjisi ve solar dizgeler",
        "anahtar": r"\b(solar|güneş enerji\w*|panel\w*|inverter|invertör|"
                   r"lifepo4|batarya\w*|akü\w*|mppt|şarj kontrol\w*|"
                   r"kilovat|kwh?)\b",
        "talimat": (
            "You are KÜN, off-grid solar. The plan is ~6 kW off-grid with "
            "LiFePO4 batteries, panels on a separate pergola/garage roof. "
            "Show your arithmetic; flag electrical-safety risks (DC "
            "voltage, fusing)."),
        "klasor": "Enerji",
    },
    "DEMİR": {
        "kaynaklar": [
            "raspberrypi.com", "orangepi.org", "ti.com", "st.com"],
        "alan": "elektronik, kart, donanım",
        "anahtar": r"\b(elektronik|orange ?pi|raspberry|arduino|devre\w*|"
                   r"sensör\w*|radar\w*|kamera\w*|lora|telsiz\w*|3d "
                   r"yazıcı\w*|lehim\w*)\b",
        "talimat": (
            "You are DEMİR, electronics and hardware (Orange Pi / "
            "Raspberry Pi, sensors, low-power off-grid builds). Quote "
            "datasheet values only from a source; warn about voltage and "
            "current limits."),
        "klasor": "Donanım",
    },
    "BALBAL": {
        "kaynaklar": [
            "csb.gov.tr", "tse.org.tr", "tr.wikipedia.org"],
        "alan": "inşaat, taş ev, kerpiç, mimari",
        "anahtar": r"\b(kerpiç\w*|horasan\w*|taş ev|duvar\w*|sıva\w*|"
                   r"yapı\w*|inşaat\w*|temel\w*|mimari|saman\w*|ahşap)\b",
        "talimat": (
            "You are BALBAL, natural building: stone, timber, clay, straw, "
            "Horasan mortar; NO reinforced concrete or cement. For "
            "structural safety, state that a site engineer should confirm."),
        "klasor": "Yapı",
    },
    "AKÇA": {
        "kaynaklar": [
            "tcmb.gov.tr", "borsaistanbul.com", "tuik.gov.tr", "spk.gov.tr"],
        "alan": "akçe, borsa, kripto, makroekonomi",
        "anahtar": r"\b(borsa\w*|bist\w*|kripto\w*|bitcoin\w*|btc|eth\w*|"
                   r"hisse\w*|enflasyon\w*|faiz\w*|dolar\w*|usd|euro\w*|"
                   r"altın\w*|gümüş\w*|gram altın\w*|ons|döviz\w*|kuru|kurlar\w*|"
                   r"ekonomi\w*|yatırım\w*|tahvil\w*|merkez bankası|"
                   r"tl|lira\w*|piyasa\w*|endeks\w*|coin\w*)\b",
        "talimat": (
            "You are AKÇA, finance and economics. Give facts, definitions "
            "and sourced data only. Do NOT tell the user to buy or sell "
            "anything and never predict prices; say that you are not a "
            "financial advisor. For any current price, rate or "
            "index you MUST call the tool piyasa_verisi first (exchange "
            "rates, BIST 100, gold, crypto, oil) and report the value with "
            "its source and time exactly as returned; use internette_ara "
            "only for news. Never quote a price from memory or from "
            "scraped pages. If the tool fails, say you could not fetch it."),
        "klasor": "Akçe",
    },
    "YARGU": {
        "kaynaklar": [
            "mevzuat.gov.tr", "resmigazete.gov.tr", "anayasa.gov.tr", "yargitay.gov.tr"],
        "alan": "hukuk ve mevzuat",
        "anahtar": r"\b(kanun\w*|yasa\w*|mevzuat|dava\w*|sözleşme\w*|"
                   r"tapu\w*|imar|ruhsat\w*|fsek|telif|hukuk\w*|"
                   r"yönetmelik\w*|mahkeme\w*)\b",
        "talimat": (
            "You are YARGU, law and legislation (Turkey). Quote the law "
            "name and article number from a source (mevzuat.gov.tr or "
            "similar); say when a rule may have changed. This is "
            "information, not legal advice - say a lawyer should confirm "
            "for any real dispute or contract."),
        "klasor": "Hukuk",
    },
    "ALPAGU": {
        "kaynaklar": [
            "nist.gov", "cisa.gov", "enisa.europa.eu", "btk.gov.tr", "ogm.gov.tr"],
        "alan": "kendi mülkünü ve verini koruma: güvenlik, yangın, siber",
        "anahtar": r"\b(güvenlik|alarm\w*|çit\w*|siber|güvenlik duvarı|"
                   r"air-?gap\w*|yangın\w*|hırsız\w*|koruma|savunma|"
                   r"şifre\w*|vpn|lan)\b",
        "talimat": (
            "You are ALPAGU, protection of the user's own land, home, "
            "vehicle and data: cameras, fences, alarms, fire defence, "
            "network and cyber hygiene, air-gapped backups. Defensive "
            "only: refuse to design weapons or attacks on others; for "
            "electric fences, follow local law and keep them non-lethal."),
        "klasor": "Güvenlik",
    },
    "KOPUZ": {
        "kaynaklar": [
            "kulturportali.gov.tr", "islamansiklopedisi.org.tr", "tr.wikipedia.org"],
        "alan": "müzik ve beste",
        "anahtar": r"\b(müzik\w*|beste\w*|bağlama|saz\w*|kopuz\w*|makam\w*|"
                   r"nota\w*|türkü\w*|akort\w*|ezgi\w*|söz yaz\w*)\b",
        "talimat": (
            "You are KOPUZ, music and composition: Turkish folk and "
            "classical modes (makam), saz/bağlama/kopuz, tunings, rhythm "
            "(usul), songwriting. Describe scales and intervals precisely; "
            "never reproduce copyrighted lyrics or scores."),
        "klasor": "Müzik",
    },
    "OYUN": {
        "kaynaklar": [
            "kulturportali.gov.tr", "islamansiklopedisi.org.tr", "tr.wikipedia.org"],
        "alan": "dans ve koreografi",
        "anahtar": r"\b(dans\w*|koreografi\w*|halay\w*|semah\w*|horon\w*|"
                   r"zeybek\w*|figür\w*|sahne\w*|ders planı)\b",
        "talimat": (
            "You are OYUN, dance and choreography (the user is a dance "
            "instructor). Help with lesson plans, counts, figures, warm-up "
            "and injury-safe progressions, folk-dance history. For pain or "
            "injury, say a physiotherapist or doctor should see it."),
        "klasor": "Dans",
    },
    "YAZIT": {
        "kaynaklar": [
            "help.obsidian.md", "obsidian.md"],
        "alan": "bilgi arşivi ve belge yönetimi",
        "anahtar": r"\b(arşiv\w*|belge\w*|obsidyen\w*|obsidian|kaynakça|"
                   r"etiket\w*|ocr|kütüphane\w*|not düzeni|dizin\w*)\b",
        "talimat": (
            "You are YAZIT, knowledge archive and document management: "
            "folder and tag schemes for the Obsidian vault, source lists, "
            "OCR'd books, citation style. Never suggest deleting or "
            "overwriting the user's own notes."),
        "klasor": "Arşiv",
    },
}


GENEL = [
    ("BİLGE", "bilgi bulma ve öğüt", "ana sohbet"),
    ("ARAŞTIRMACI", "planlı, kaynaklı araştırma", "Araştırma ajanı"),
    ("ÇEVİRMEN", "dil çevirisi", "ana sohbet"),
    ("YAZMAN", "bitig ve bellek işleri", "ana sohbet + Obsidian yazma"),
    ("GÖZCÜ", "yanıt ve dizge yoklaması", "Doğrulayıcı"),
    ("ONARICI", "aksaklık bulma ve onarım önerisi", "Tanı (Sistem sekmesi)"),
]


def liste():
    """Sayfadaki kart için: genel görev türleri + alan uzmanları."""
    return {"genel": [{"ad": a, "is": i, "yer": y} for a, i, y in GENEL],
            "uzmanlar": [{"ad": ad, "alan": u["alan"]}
                         for ad, u in UZMANLAR.items()]}


def guvenilir_kaynaklar(ad):
    """Uzmanın güvenilir alan adları; ayar.json'daki "guvenilir_kaynaklar"
    anahtarı (örn. {"OTACI": ["who.int"]}) varsa onu kullanır."""
    ozel = ayar.yukle().get("guvenilir_kaynaklar") or {}
    liste = ozel.get(ad) if isinstance(ozel, dict) else None
    if isinstance(liste, list) and liste:
        return [str(d) for d in liste][:8]
    return list(UZMANLAR.get(ad, {}).get("kaynaklar", []))


def guvenilir_ara(sorgu, uzman, arastirma, alan_basina=2, sayfa=2):
    """Yalnızca uzmanın güvenilir sitelerinde arar; kaynaklı metin döndürür.

    Hiçbirinde bulunamazsa bunu açıkça söyler (tahmin etmez)."""
    istenen = obsidyen.normal((uzman or "").strip())
    uzman = next((a for a in UZMANLAR if obsidyen.normal(a) == istenen), "")
    if not uzman:
        return "Bilinmeyen uzman. Seçenekler: %s" % ", ".join(UZMANLAR)
    parcalar, okunan = [], 0
    for alan in guvenilir_kaynaklar(uzman)[:5]:
        try:
            sonuclar = arastirma.ara("%s site:%s" % (sorgu, alan),
                                     adet=alan_basina)
        except Exception:
            continue
        for sn in sonuclar:
            if alan not in sn.get("adres", ""):
                continue
            govde = sn.get("ozet", "")
            if okunan < sayfa:
                try:
                    govde = arastirma.sayfa_metni(sn["adres"], 1500)
                    okunan += 1
                except Exception:
                    pass
            parcalar.append("KAYNAK (%s): %s (%s)\n%s" % (
                alan, sn.get("baslik", ""), sn["adres"], govde))
    if not parcalar:
        return ("Güvenilir kaynak listesinde (%s) bu konuda bir şey "
                "bulamadım. Tahmin yürütmüyorum."
                % ", ".join(guvenilir_kaynaklar(uzman)))
    return "\n\n".join(parcalar)


def sec(metin):
    """Soruya en uygun uzmanın adını döndürür; yoksa None.

    Uzmanın adı geçiyorsa ("Akça: ..." gibi) o seçilir."""
    kucuk = obsidyen.normal(metin or "")
    for ad in UZMANLAR:
        if re.search(r"\b%s\b" % re.escape(obsidyen.normal(ad)), kucuk):
            return ad
    en_iyi, puan = None, 0
    for ad, u in UZMANLAR.items():
        p = len(re.findall(u["anahtar"], metin or "", re.IGNORECASE))
        if p > puan:
            en_iyi, puan = ad, p
    return en_iyi


def istem(metin):
    """Sistem istemine eklenecek uzman metni ('' = uzman yok)."""
    ad = sec(metin)
    if not ad:
        return ""
    u = UZMANLAR[ad]
    return "# EXPERT MODE: %s (%s)\n%s\n%s" % (
        ad, u["alan"], u["talimat"], ORTAK)


def bitki_notu(ad, arastirma):
    """Bitki için kaynaklı araştırma yapar, Obsidian'a not yazar.

    Dönen metin kullanıcıya/modele gider; kaynaklar not içinde de durur."""
    ad = " ".join(str(ad).split())[:60]
    if not ad:
        raise ValueError("Bitki adı gerekli")
    sorgu = ("%s bitkisi geleneksel kullanımı içerdiği vitaminler mineraller "
             "etken maddeler nasıl kullanılır yan etkiler uyarılar" % ad)
    bulgu = arastirma.arastir(sorgu)
    icerik = (obsidyen_yaz.onbilgi(tur="bitki", bitki=ad)
              + "# %s\n\n> Kaynaklı derleme; tanı/tedavi değildir. Ciddi "
                "belirtilerde hekime başvurun, acilde 112.\n\n%s\n"
              % (ad, bulgu))
    try:
        yol = obsidyen_yaz.yaz(UZMANLAR["OTACI"]["klasor"], ad, icerik)
        konum = "Not: %s" % yol
    except obsidyen_yaz.YazmaHatasi as hata:
        konum = "Not yazılamadı: %s" % hata
    return ("%s\n\n%s\n(Tanı/tedavi değildir; ciddi belirtilerde hekime "
            "başvurun, acilde 112.)" % (bulgu[:3500], konum))


def kasa_klasoru(ad):
    """Uzmanın Obsidian klasörü (varsa) - arama ipucu için."""
    u = UZMANLAR.get(ad)
    if not u:
        return None
    kasa = obsidyen.kasa_yolu()
    yol = os.path.join(kasa, "Ülgen", u["klasor"])
    return yol if os.path.isdir(yol) else None
