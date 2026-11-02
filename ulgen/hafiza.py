"""Uzun süreli kişisel hafıza.

Kalıcı bilgiler ``memory.json`` dosyasında tutulur. Ülgen konuşmaları
gözlemleyip kalıcı bilgileri (ad, tercih, karar, sağlık özeti...) kendisi
ayıklar:
  * Sezgisel kalıplar (her zaman, modelsiz).
  * Yerel beyin varsa ek olarak model destekli ayıklama.

Her yeni sohbette bu dosya sistem istemine bağlam olarak eklenir. Bulut
beyinde bu ekleme yalnızca kullanıcı ``bulut_kisisel_veri`` ayarını açtıysa
yapılır (bkz. cekirdek.py).
"""

import json
import os
import re
import threading
from datetime import date

from . import ayar, gizli
from .beyin import BeyinHatasi

KATEGORILER = ("profil", "tercih", "karar", "saglik", "bilgi")

# Model destekli ayıklamayı tetikleyen ipuçları (gereksiz model çağrısını önler)
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


class HafizaYoneticisi:
    """memory.json dosyasını okuyan, yazan ve kendiliğinden dolduran sınıf."""

    AZAMI_OGE = 300

    def __init__(self, beyin_sec):
        self._beyin_sec = beyin_sec
        self._kilit = threading.RLock()

    # ------------------------------------------------------------ dosya
    def _oku(self):
        try:
            with open(ayar.HAFIZA_DOSYASI, "rb") as dosya:
                ham = dosya.read()
        except OSError:
            return {"surum": 1, "ogeler": [], "saglik": {}}
        try:
            veri = json.loads(gizli.coz(ham).decode("utf-8"))
        except (gizli.AnahtarYok, ValueError):
            # Çözülemeyen dosya ezilmesin: yedeklenip boş başlanır
            os.replace(ayar.HAFIZA_DOSYASI, ayar.HAFIZA_DOSYASI + ".bozuk")
            return {"surum": 1, "ogeler": [], "saglik": {}}
        if isinstance(veri, dict):
            veri.setdefault("ogeler", [])
            veri.setdefault("saglik", {})
            if not gizli.sifreli_mi(ham) and gizli.kullanilabilir_mi():
                self._yaz(veri)  # eski düz yazı dosyayı şifrele
            return veri
        return {"surum": 1, "ogeler": [], "saglik": {}}

    def _yaz(self, veri):
        ayar.klasor_hazirla()
        gecici = ayar.HAFIZA_DOSYASI + ".tmp"
        ham = json.dumps(veri, ensure_ascii=False, indent=2).encode("utf-8")
        with open(gecici, "wb") as dosya:
            dosya.write(gizli.sifrele(ham))
        os.chmod(gecici, 0o600)
        os.replace(gecici, ayar.HAFIZA_DOSYASI)

    # ----------------------------------------------------------- işlemler
    def ekle(self, kategori, metin, kaynak="otomatik"):
        """Yeni bir bilgi ekler. Aynı bilgi varsa eklemez; eklenirse True."""
        kategori = kategori if kategori in KATEGORILER else "bilgi"
        metin = re.sub(r"\s+", " ", metin).strip()
        if len(metin) < 3:
            return False
        with self._kilit:
            veri = self._oku()
            for oge in veri["ogeler"]:
                if oge["metin"].lower() == metin.lower():
                    return False
            veri["ogeler"].append({
                "kategori": kategori, "metin": metin[:300],
                "tarih": date.today().isoformat(), "kaynak": kaynak})
            veri["ogeler"] = veri["ogeler"][-self.AZAMI_OGE:]
            self._yaz(veri)
        return True

    def eslesen_sayisi(self, anahtar):
        """İçinde anahtar geçen kayıt sayısını verir (silmeden)."""
        anahtar = anahtar.strip().lower()
        if len(anahtar) < 3:
            return 0
        with self._kilit:
            return sum(1 for o in self._oku()["ogeler"]
                       if anahtar in o["metin"].lower())

    def unut(self, anahtar):
        """İçinde anahtar geçen bilgileri siler; silinen sayısını döndürür."""
        anahtar = anahtar.strip().lower()
        if len(anahtar) < 3:
            return 0
        with self._kilit:
            veri = self._oku()
            kalan = [o for o in veri["ogeler"]
                     if anahtar not in o["metin"].lower()]
            silinen = len(veri["ogeler"]) - len(kalan)
            if silinen:
                veri["ogeler"] = kalan
                self._yaz(veri)
        return silinen

    def saglik_guncelle(self, ozet, icgoruler):
        """Sağlık ajanının özetini ve içgörülerini hafızaya senkronize eder."""
        with self._kilit:
            veri = self._oku()
            veri["saglik"] = {
                "guncelleme": date.today().isoformat(),
                "ozet": ozet, "icgoruler": icgoruler}
            self._yaz(veri)

    def metne_cevir(self, azami_karakter=1500, saglik_dahil=True):
        """Hafızayı sistem istemine eklenecek kısa bir metne çevirir."""
        veri = self._oku()
        satirlar = []
        for oge in veri["ogeler"][-60:]:
            satirlar.append("- (%s) %s" % (oge["kategori"], oge["metin"]))
        if saglik_dahil and veri["saglik"].get("icgoruler"):
            satirlar.append("- (saglik, %s) %s" % (
                veri["saglik"].get("guncelleme", ""),
                " ".join(veri["saglik"]["icgoruler"])))
        metin = "\n".join(satirlar)
        return metin[-azami_karakter:] if metin else ""

    # ------------------------------------------------------ gözlemleme
    def sezgisel_ayikla(self, metin):
        """Kalıplarla (modelsiz) kalıcı bilgileri bulur: [(kategori, metin)]."""
        bulunanlar = []
        for desen, kategori, sablon in SEZGISEL_KALIPLAR:
            for eslesme in desen.finditer(metin):
                bulunanlar.append(
                    (kategori, sablon.format(*eslesme.groups()).strip()))
        return bulunanlar

    def _model_ile_ayikla(self, metin):
        """Yerel beyne sorup kalıcı bilgileri JSON olarak alır."""
        beyin = self._beyin_sec()
        if beyin is None or not beyin.yerel or not IPUCLARI.search(metin):
            return []
        istem = (
            "Aşağıdaki kullanıcı mesajında, kullanıcı hakkında KALICI olarak "
            "hatırlanmaya değer bir bilgi (ad, tercih, karar, alışkanlık, "
            "sağlık bilgisi) var mı? Varsa yalnızca JSON dizi döndür: "
            '[{"kategori":"profil|tercih|karar|saglik|bilgi",'
            '"metin":"kısa Türkçe cümle"}]. Yoksa [] döndür.\n\nMESAJ:\n'
            + metin[:800])
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
        """Bir konuşma çiftini inceleyip kalıcı bilgileri kaydeder."""
        bulunanlar = self.sezgisel_ayikla(kullanici_metni)
        if not bulunanlar:
            bulunanlar = self._model_ile_ayikla(kullanici_metni)
        for kategori, metin in bulunanlar:
            self.ekle(kategori, metin)
        return len(bulunanlar)
