"""Tek ve bütünleşik kullanıcı hafızası.

Her öğenin kimliği, kategorisi, projesi, KAYNAĞI, güveni, tarihi ve durumu
vardır:

  kaynak  : ``kullanici`` (kullanıcının kendi söylediği / girdiği) ya da
            ``cikarim`` (yapay zekânın çıkardığı). İkisi ASLA karıştırılmaz.
  guven   : 0-1. Kullanıcı bilgisi 1.0 (kalıp çıkarımı 0.9); model çıkarımı
            0.5; kullanıcı teyit ederse 1.0.
  durum   : ``gecerli`` · ``eskimis`` (yerine yenisi geldi, geçmiş olarak
            korunur) · ``celiski`` (bir çıkarım, kullanıcı bilgisiyle
            çelişiyor; kullanıcı teyit edene kadar kullanılmaz).

Duyarlı öğeler (sağlık, kimlik, finans, parola...) AYRI şifreli dosyada
(memory_hassas.json) tutulur; sistem istemine ve buluta kendiliğinden girmez.
Dosyalar AES-256-GCM ile şifrelidir (gizli.py). Bilgiler yalnızca kullanıcı
isteğiyle silinir; düzeltme eski kaydı silmez, "eskimiş" yapar.
"""

import json
import os
import re
import threading
from datetime import date, datetime

from . import ayar, gizli, veritabani
from .beyin import BeyinHatasi
from .guvenlik import duyarli_mi

KATEGORILER = ("profil", "tercih", "karar", "proje", "teknik", "gorev",
               "rutin", "ogrenilmis", "saglik", "bilgi")

# Kullanıcının verdiği örnek projeler (boş bağlam olarak açılır)
VARSAYILAN_PROJELER = {
    "ÜLGEN": ["ülgen", "ulgen"],
    "ÖTÜKEN": ["ötüken", "otuken"],
    "UMAY": ["umay"],
    "DOOMSDAY AMFİBİ OVERLAND": ["doomsday", "amfibi", "amfibİ", "overland"],
    "TILSIM": ["tılsım", "tilsim", "tılsim"],
    "Permakültür ve arazi": ["permakültür", "permakultur", "arazi",
                             "cincin", "zeytinlik"],
}

IPUCLARI = re.compile(
    r"\b(ben|benim|bana|hat[ıi]rla|unutma|karar|tercih|severim|sevmem|"
    r"istiyorum|kullan[ıi]yorum|al[ıi]yorum|al[ıi]şkanl[ıi]k)\b",
    re.IGNORECASE)

SEZGISEL_KALIPLAR = [
    (re.compile(r"\bbenim ad[ıi]m\s+([\wçğıöşüÇĞİÖŞÜ]+)", re.IGNORECASE),
     "profil", "Adı: {0}"),
    (re.compile(r"\bben\s+(.{2,40}?)\s+(severim|seviyorum)\b", re.IGNORECASE),
     "tercih", "{0} sever"),
    (re.compile(r"\bben\s+(.{2,40}?)\s+(sevmem|istemem)\b", re.IGNORECASE),
     "tercih", "{0} sevmez/istemez"),
    (re.compile(r"\bkarar verdim[:,]?\s*(.{3,160})", re.IGNORECASE),
     "karar", "{0}"),
    (re.compile(r"\b(?:hat[ıi]rla|unutma)[:,]\s*(.{3,200})", re.IGNORECASE),
     "bilgi", "{0}"),
]

ESIK_ESKIME = 0.6      # benzerlik eşiği: aynı konuda yeni bilgi
_TR = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s",
                     "Ğ": "g", "ğ": "g", "Ü": "u", "ü": "u", "Ö": "o",
                     "ö": "o", "Ç": "c", "ç": "c"})


def _norm(metin):
    return metin.translate(_TR).lower()


def _govde(metin):
    """Karşılaştırma için sözcük köklerini (ilk 5 harf) çıkarır."""
    return {k[:5] for k in re.findall(r"\w{3,}", _norm(metin))}


def benzerlik(a, b):
    """İki metnin Jaccard benzerliği (0-1), Türkçe ek farkına dayanıklı."""
    x, y = _govde(a), _govde(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


class _Depo:
    """Şifreli JSON dosyası + öğe kimliği üretimi."""

    def __init__(self, yol, onek=""):
        self.yol = yol
        self.onek = onek

    def _bos(self):
        return {"surum": 2, "sayac": 0, "projeler": {}, "ogeler": [],
                "saglik": {}}

    def oku(self):
        try:
            with open(self.yol, "rb") as dosya:
                ham = dosya.read()
        except OSError:
            return self._bos()
        try:
            veri = json.loads(gizli.coz(ham).decode("utf-8"))
        except (gizli.AnahtarYok, ValueError):
            os.replace(self.yol, self.yol + ".bozuk")
            return self._bos()
        if not isinstance(veri, dict):
            return self._bos()
        degisti = self._goc(veri)
        if degisti or (not gizli.sifreli_mi(ham) and gizli.kullanilabilir_mi()):
            self.yaz(veri)
        return veri

    def _goc(self, veri):
        """Eski (v1) kayıtları yeni şemaya taşır. Değiştiyse True."""
        degisti = False
        for anahtar, varsayilan in (("ogeler", []), ("saglik", {}),
                                    ("projeler", {}), ("sayac", 0)):
            if anahtar not in veri:
                veri[anahtar] = varsayilan
                degisti = True
        for oge in veri["ogeler"]:
            if "id" not in oge:
                veri["sayac"] += 1
                oge["id"] = "%s%d" % (self.onek, veri["sayac"])
                kaynak = oge.get("kaynak", "otomatik")
                oge["kaynak"] = ("kullanici" if kaynak == "kullanici"
                                 else "cikarim")
                oge["guven"] = 1.0 if kaynak == "kullanici" else 0.6
                oge["proje"] = oge.get("proje")
                oge["teyitli"] = False
                oge["guncelleme"] = oge.get("tarih", "")
                oge["durum"] = "gecerli"
                oge["yerine"] = None
                oge["kanit"] = "eski kayıt (v2.0'dan taşındı)"
                degisti = True
        if veri.get("surum", 1) < 2:
            veri["surum"] = 2
            degisti = True
        return degisti

    def yaz(self, veri):
        ayar.klasor_hazirla()
        gecici = self.yol + ".tmp"
        ham = json.dumps(veri, ensure_ascii=False, indent=2).encode("utf-8")
        with open(gecici, "wb") as dosya:
            dosya.write(gizli.sifrele(ham))
        os.chmod(gecici, 0o600)
        os.replace(gecici, self.yol)

    def yeni_id(self, veri):
        veri["sayac"] += 1
        return "%s%d" % (self.onek, veri["sayac"])


class HafizaYoneticisi:
    """Hafıza öğelerini ekler, düzeltir, arar ve istem metnine çevirir."""

    AZAMI_OGE = 1000

    def __init__(self, beyin_sec):
        self._beyin_sec = beyin_sec
        self._kilit = threading.RLock()
        self._ana = _Depo(ayar.HAFIZA_DOSYASI)
        self._hassas = _Depo(ayar.HASSAS_DOSYASI, "h")

    # -------------------------------------------------------- yardımcılar
    def _depo_id(self, kimlik):
        return self._hassas if str(kimlik).startswith("h") else self._ana

    def _projeleri_hazirla(self, veri):
        for ad, anahtarlar in VARSAYILAN_PROJELER.items():
            if ad not in veri["projeler"]:
                veri["projeler"][ad] = {
                    "anahtarlar": anahtarlar, "aciklama": "",
                    "olusturma": date.today().isoformat(),
                    "kaynak": "kullanici"}

    def projeler(self):
        with self._kilit:
            veri = self._ana.oku()
            self._projeleri_hazirla(veri)
            return {ad: p for ad, p in veri["projeler"].items()}

    def proje_ekle(self, ad, anahtarlar=None):
        ad = ad.strip()[:60]
        if len(ad) < 2:
            return False
        with self._kilit:
            veri = self._ana.oku()
            self._projeleri_hazirla(veri)
            if ad in veri["projeler"]:
                return False
            veri["projeler"][ad] = {
                "anahtarlar": [a.lower() for a in (anahtarlar or [ad])],
                "aciklama": "", "olusturma": date.today().isoformat(),
                "kaynak": "kullanici"}
            self._ana.yaz(veri)
            return True

    def projeleri_bul(self, metin):
        """Metinde geçen projelerin adlarını verir."""
        kucuk = _norm(metin)
        bulunan = []
        for ad, p in self.projeler().items():
            if any(_norm(a) in kucuk for a in p["anahtarlar"] + [ad]):
                bulunan.append(ad)
        return bulunan

    # --------------------------------------------------------------- ekle
    def ekle(self, kategori, metin, kaynak="kullanici", proje=None,
             guven=None, kanit="", duyarli=None):
        """Bilgi ekler. Yeni öğenin kimliğini döndürür; zaten biliniyorsa None.

        Aynı konuda eski bir bilgi varsa:
          * yeni bilgi kullanıcıdan ise eskisi "eskimis" olur (silinmez);
          * yeni bilgi çıkarım, eskisi kullanıcı bilgisi ise çıkarım
            "celiski" durumunda bekler, eskisinin yerine GEÇMEZ;
          * ikisi de çıkarımsa yenisi eskisinin yerine geçer.
        """
        kategori = kategori if kategori in KATEGORILER else "bilgi"
        kaynak = "kullanici" if kaynak == "kullanici" else "cikarim"
        metin = re.sub(r"\s+", " ", metin).strip()[:300]
        if len(metin) < 3:
            return None
        if duyarli is None:
            duyarli = duyarli_mi(metin) or kategori == "saglik"
        if guven is None:
            guven = 1.0 if kaynak == "kullanici" else 0.5
        depo = self._hassas if duyarli else self._ana
        with self._kilit:
            veri = depo.oku()
            for oge in veri["ogeler"]:
                if oge["durum"] == "gecerli" \
                        and _norm(oge["metin"]) == _norm(metin) \
                        and oge.get("proje") == proje:
                    if kaynak == "kullanici" and oge["kaynak"] == "cikarim":
                        oge.update(kaynak="kullanici", guven=1.0,
                                   teyitli=True, guncelleme=self._simdi())
                        depo.yaz(veri)
                    return None
            kimlik = depo.yeni_id(veri)
            yeni = {"id": kimlik, "kategori": kategori, "proje": proje,
                    "metin": metin, "kaynak": kaynak,
                    "guven": round(float(guven), 2), "teyitli": False,
                    "tarih": self._simdi(), "guncelleme": self._simdi(),
                    "durum": "gecerli", "yerine": None,
                    "kanit": kanit[:160]}
            self._cakisma_coz(veri, yeni)
            veri["ogeler"].append(yeni)
            veri["ogeler"] = veri["ogeler"][-self.AZAMI_OGE:]
            depo.yaz(veri)
        return kimlik

    @staticmethod
    def _simdi():
        return datetime.now().isoformat(timespec="seconds")

    def _cakisma_coz(self, veri, yeni):
        for eski in veri["ogeler"]:
            if eski["durum"] != "gecerli" or eski["kategori"] != yeni["kategori"] \
                    or eski.get("proje") != yeni["proje"]:
                continue
            if benzerlik(eski["metin"], yeni["metin"]) < ESIK_ESKIME:
                continue
            if yeni["kaynak"] == "cikarim" and (
                    eski["kaynak"] == "kullanici" or eski["teyitli"]):
                yeni["durum"] = "celiski"
                yeni["celiski"] = eski["id"]
                yeni["guven"] = min(yeni["guven"], 0.3)
            else:
                eski["durum"] = "eskimis"
                eski["yerine"] = yeni["id"]
                eski["guncelleme"] = self._simdi()
                yeni["oncekiler"] = yeni.get("oncekiler", []) + [eski["id"]]

    # ----------------------------------------------- düzeltme, teyit, silme
    def _bul(self, veri, kimlik):
        for oge in veri["ogeler"]:
            if oge["id"] == str(kimlik):
                return oge
        return None

    def duzelt(self, kimlik, yeni_metin, neden=""):
        """Yanlış bilgiyi düzeltir: eskisi "eskimis" kalır, yenisi kullanıcı
        bilgisi olarak eklenir. Yeni kimliği döndürür (bulunamazsa None)."""
        depo = self._depo_id(kimlik)
        yeni_metin = re.sub(r"\s+", " ", yeni_metin).strip()[:300]
        if len(yeni_metin) < 3:
            return None
        with self._kilit:
            veri = depo.oku()
            eski = self._bul(veri, kimlik)
            if eski is None:
                return None
            yeni_id = depo.yeni_id(veri)
            eski["durum"] = "eskimis"
            eski["yerine"] = yeni_id
            eski["guncelleme"] = self._simdi()
            veri["ogeler"].append({
                "id": yeni_id, "kategori": eski["kategori"],
                "proje": eski.get("proje"), "metin": yeni_metin,
                "kaynak": "kullanici", "guven": 1.0, "teyitli": False,
                "tarih": self._simdi(), "guncelleme": self._simdi(),
                "durum": "gecerli", "yerine": None, "oncekiler": [eski["id"]],
                "kanit": ("düzeltme: " + neden)[:160]})
            depo.yaz(veri)
            return yeni_id

    def teyit(self, kimlik):
        """Kullanıcı bir çıkarımı doğrular. Çelişkideyse eskisinin yerine geçer."""
        depo = self._depo_id(kimlik)
        with self._kilit:
            veri = depo.oku()
            oge = self._bul(veri, kimlik)
            if oge is None or oge["durum"] == "eskimis":
                return False
            if oge["durum"] == "celiski":
                eski = self._bul(veri, oge.get("celiski", ""))
                if eski is not None:
                    eski["durum"] = "eskimis"
                    eski["yerine"] = oge["id"]
                oge["durum"] = "gecerli"
            oge.update(teyitli=True, guven=1.0, guncelleme=self._simdi())
            depo.yaz(veri)
            return True

    def eslesen_sayisi(self, anahtar):
        """İçinde anahtar geçen kayıt sayısı (silmeden)."""
        anahtar = anahtar.strip().lower()
        if len(anahtar) < 3:
            return 0
        with self._kilit:
            return sum(1 for d in (self._ana, self._hassas)
                       for o in d.oku()["ogeler"]
                       if anahtar in o["metin"].lower())

    def unut(self, anahtar):
        """İçinde anahtar geçen kayıtları (geçmiş sürümler dahil) siler."""
        anahtar = anahtar.strip().lower()
        if len(anahtar) < 3:
            return 0
        silinen = 0
        with self._kilit:
            for depo in (self._ana, self._hassas):
                veri = depo.oku()
                kalan = [o for o in veri["ogeler"]
                         if anahtar not in o["metin"].lower()]
                if len(kalan) != len(veri["ogeler"]):
                    silinen += len(veri["ogeler"]) - len(kalan)
                    veri["ogeler"] = kalan
                    depo.yaz(veri)
        return silinen

    def saglik_guncelle(self, ozet, icgoruler):
        """Sağlık ajanının özetini ayrı (duyarlı) depoya senkronize eder."""
        with self._kilit:
            veri = self._hassas.oku()
            veri["saglik"] = {
                "guncelleme": date.today().isoformat(),
                "ozet": ozet, "icgoruler": icgoruler}
            self._hassas.yaz(veri)

    # ------------------------------------------------------ listeleme
    def goster(self, kimlik):
        """Bir öğenin tüm ayrıntısını (kaynak, tarih, güven, geçmiş) verir."""
        with self._kilit:
            return self._bul(self._depo_id(kimlik).oku(), kimlik)

    def liste(self, proje=None, kategori=None, duyarli=False, durum="gecerli"):
        with self._kilit:
            depo = self._hassas if duyarli else self._ana
            return [o for o in depo.oku()["ogeler"]
                    if (durum is None or o["durum"] == durum)
                    and (proje is None or o.get("proje") == proje)
                    and (kategori is None or o["kategori"] == kategori)]

    def celiskiler(self):
        return (self.liste(durum="celiski")
                + self.liste(durum="celiski", duyarli=True))

    def eskimis_adaylar(self, gun=180):
        """Doğrulanmamış ve eski çıkarımları (güncelliği şüpheli) listeler."""
        bugun = datetime.now()
        sonuc = []
        for duyarli in (False, True):
            for o in self.liste(duyarli=duyarli):
                if o["kaynak"] != "cikarim" or o["teyitli"]:
                    continue
                try:
                    yas = (bugun - datetime.fromisoformat(o["tarih"])).days
                except ValueError:
                    yas = gun + 1
                if yas >= gun:
                    sonuc.append(dict(o, yas_gun=yas))
        return sonuc

    @staticmethod
    def etiket(oge):
        """Öğenin kaynağını ve güvenini insan okuyabilir yazıya çevirir."""
        if oge["kaynak"] == "kullanici":
            kaynak = "kullanıcı söyledi" if oge["guven"] >= 1 else \
                "kullanıcı sözünden, %%%d güven" % int(oge["guven"] * 100)
        elif oge["teyitli"]:
            kaynak = "çıkarım, kullanıcı teyit etti"
        else:
            kaynak = "ÇIKARIM, doğrulanmadı, %%%d güven" % int(
                oge["guven"] * 100)
        return "%s, %s" % (kaynak, oge["tarih"][:10])

    def metne_cevir(self, azami_karakter=1500, saglik_dahil=True,
                    metin_ipucu="", duyarli_dahil=False):
        """Hafızayı sistem istemine eklenecek kısa metne çevirir.

        Duyarlı depo yalnızca ``duyarli_dahil`` ile (yerel beyin) eklenir.
        Mesajda geçen projelerin bilgileri öne alınır. Her satırda kaynak
        ve güven belirtilir; çıkarımlar kullanıcı bilgisinden ayrı görünür.
        """
        oncelik = set(self.projeleri_bul(metin_ipucu)) if metin_ipucu else set()
        ogeler = self.liste()
        if duyarli_dahil:
            ogeler += self.liste(duyarli=True)
        ogeler.sort(key=lambda o: (o.get("proje") not in oncelik,
                                   o["kaynak"] != "kullanici", o["tarih"]),
                    reverse=False)
        satirlar = ["- (%s%s) %s [%s]" % (
            o["kategori"], "/" + o["proje"] if o.get("proje") else "",
            o["metin"], self.etiket(o)) for o in ogeler[:80]]
        if saglik_dahil and duyarli_dahil:
            saglik = self._hassas.oku()["saglik"]
            if saglik.get("icgoruler"):
                satirlar.append("- (saglik, %s, ölçüm özeti) %s" % (
                    saglik.get("guncelleme", ""), " ".join(saglik["icgoruler"])))
        metin = "\n".join(satirlar)
        return metin[:azami_karakter] if metin else ""

    # ------------------------------------------------------------- arama
    def ara(self, sorgu, proje=None, adet=8, duyarli_dahil=False,
            sohbette=True):
        """Hafızada ve geçmiş konuşmalarda arar.

        [{tur, id, metin, ayrinti, proje}] döndürür; ``tur`` "hafiza" ya da
        "sohbet". Duyarlı öğeler yalnızca ``duyarli_dahil`` ile aranır.
        """
        kelimeler = {k[:5] for k in re.findall(r"\w{3,}", _norm(sorgu))}
        sonuc = []
        if kelimeler:
            havuz = self.liste(proje=proje, durum=None)
            if duyarli_dahil:
                havuz += self.liste(proje=proje, durum=None, duyarli=True)
            puanli = []
            for o in havuz:
                puan = len(kelimeler & _govde(o["metin"]))
                if puan:
                    # geçerli olan, eskimişten önce gelir
                    puanli.append((puan, o["durum"] == "gecerli", o))
            puanli.sort(key=lambda p: (-p[0], not p[1]))
            for _, _, o in puanli[:adet]:
                sonuc.append({
                    "tur": "hafiza", "id": o["id"], "metin": o["metin"],
                    "ayrinti": "%s; %s; durum: %s" % (
                        o["kategori"], self.etiket(o), o["durum"]),
                    "proje": o.get("proje")})
        if sohbette:
            for s in veritabani.sohbet_ara(sorgu, adet):
                if s.get("duyarli") and not duyarli_dahil:
                    continue
                sonuc.append({
                    "tur": "sohbet", "id": "s%d" % s["id"],
                    "metin": s["metin"][:240],
                    "ayrinti": "%s, %s" % (
                        "kullanıcı" if s["rol"] == "kullanici" else "Ülgen",
                        s["zaman"][:16]),
                    "proje": None})
        return sonuc

    # ------------------------------------------------------ gözlemleme
    def sezgisel_ayikla(self, metin):
        """Kalıplarla (modelsiz) kullanıcının söylediği kalıcı bilgileri bulur."""
        bulunanlar = []
        for desen, kategori, sablon in SEZGISEL_KALIPLAR:
            for eslesme in desen.finditer(metin):
                bulunanlar.append(
                    (kategori, sablon.format(*eslesme.groups()).strip()))
        return bulunanlar

    def _model_ile_ayikla(self, metin):
        """Yerel beyne sorup kalıcı bilgi ÇIKARIMLARINI JSON olarak alır."""
        beyin = self._beyin_sec()
        if beyin is None or not beyin.yerel or not IPUCLARI.search(metin):
            return []
        istem = (
            "Aşağıdaki kullanıcı mesajında, kullanıcı hakkında KALICI olarak "
            "hatırlanmaya değer bir bilgi (ad, tercih, karar, alışkanlık) "
            "var mı? Yalnızca mesajda AÇIKÇA yazılanı al, tahmin yürütme. "
            'Varsa yalnızca JSON dizi döndür: [{"kategori":'
            '"profil|tercih|karar|bilgi","metin":"kısa Türkçe cümle"}]. '
            "Yoksa [] döndür.\n\nMESAJ:\n" + metin[:800])
        try:
            ham = beyin.yanitla("Yalnızca geçerli JSON döndürürsün.",
                                [{"role": "user", "content": istem}], 300)
        except BeyinHatasi:
            return []
        baslangic = ham.find("[")
        if baslangic < 0:
            return []
        try:
            dizi, _ = json.JSONDecoder().raw_decode(ham[baslangic:])
        except ValueError:
            return []
        sonuc = []
        for oge in dizi if isinstance(dizi, list) else []:
            if isinstance(oge, dict) and oge.get("metin"):
                sonuc.append((str(oge.get("kategori", "bilgi")),
                              str(oge["metin"])))
        return sonuc[:3]

    def gozlemle(self, kullanici_metni, yanit=""):
        """Konuşmadan kalıcı bilgileri ayıklar. Eklenen sayısını verir.

        Kalıp eşleşmesi = kullanıcının kendi sözü (güven 0.9, kaynak
        kullanıcı). Model çıkarımı = kaynak "cikarim" (güven 0.5).
        """
        projeler = self.projeleri_bul(kullanici_metni)
        proje = projeler[0] if len(projeler) == 1 else None
        kanit = kullanici_metni[:120]
        eklenen = 0
        bulunanlar = [(k, m, "kullanici", 0.9)
                      for k, m in self.sezgisel_ayikla(kullanici_metni)]
        if not bulunanlar:
            bulunanlar = [(k, m, "cikarim", 0.5) for k, m
                          in self._model_ile_ayikla(kullanici_metni)]
        for kategori, metin, kaynak, guven in bulunanlar:
            if self.ekle(kategori, metin, kaynak, proje, guven, kanit):
                eklenen += 1
        return eklenen
