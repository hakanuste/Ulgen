"""İlaç takibi: ilaç -> plan saati -> DOZ ÖRNEĞİ (her birinin kendi kimliği).

Kurallar (kullanıcı kararı, kodla zorunlu):
  * Bir yanıt YALNIZCA bir doz örneğini değiştirir (``UPDATE ... WHERE id=?``).
    Aynı ilacın başka saati, başka ilaç, yarınki doz ve genel hatırlatmalar
    etkilenmez.
  * Çıplak "tamam" hiçbir dozu onaylamaz; Ülgen "hangisi?" diye sorar.
  * İlaçları ve dozlarını YALNIZCA kullanıcı kendi yazdığı komutla ekler.
    Yapay zekâ modelinin bu tabloya yazan aracı yoktur; Ülgen doz değiştirmez,
    tıbbi öneri vermez, yalnızca hatırlatır ve yanıtı kaydeder.
  * Yapay zekâ/kota/ağ durumundan bağımsızdır; durum SQLite'tadır, yeniden
    başlatmada kalınan yerden sürer.
  * Sessizce vazgeçmez: azami hatırlatmadan sonra doz "yanıtsız" olur ve
    kullanıcıya bildirilir. "Yanıtsız" = alındı mı alınmadı mı BİLİNMİYOR.
"""

import re
import time
from datetime import datetime, timedelta

from . import ayar, veritabani

ACIK = ("bekliyor", "ertelendi")
SONUCLAR = {"alindi": "alındı", "almadi": "almadı", "atlandi": "atlandı",
            "tamamlandi": "tamamlandı"}
GUN_ADLARI = ("pazartesi", "salı", "çarşamba", "perşembe", "cuma",
              "cumartesi", "pazar")
SAAT = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
BICIM = "%Y-%m-%d %H:%M"


def _norm(m):
    return (m or "").lower().replace("İ", "i").replace("ı", "i") \
        .replace("ş", "s").replace("ğ", "g").replace("ü", "u") \
        .replace("ö", "o").replace("ç", "c")


class Ilac:

    def __init__(self, bildir):
        self._bildir = bildir      # bildir(metin, eylem=None)

    # ------------------------------------------------------------ ayarlar
    @staticmethod
    def _aralik():
        return int(ayar.yukle().get("ilac_tekrar_dk", 5)) * 60

    @staticmethod
    def _azami_tekrar():
        return int(ayar.yukle().get("ilac_azami_tekrar", 24))

    @staticmethod
    def _gec_sinir():
        return int(ayar.yukle().get("ilac_gec_saat", 4)) * 3600

    # ------------------------------------------------- ilaç ekleme (kullanıcı)
    def ekle(self, metin):
        """'Metformin 08:00 20:00 1 tablet' [+ 'hafta içi'] biçimini ekler."""
        metin = metin.strip()
        saatler = [(int(a), int(b)) for a, b in SAAT.findall(metin)]
        ilk = SAAT.search(metin)
        if not ilk or not metin[:ilk.start()].strip():
            return ("Biçim: ilaç ekle: AD SAAT [SAAT...] [not]. Örnek: "
                    "ilaç ekle: Metformin 08:00 20:00 yemekten sonra")
        ad = metin[:ilk.start()].strip(" ,:-")[:60]
        son = list(SAAT.finditer(metin))[-1]
        kalan = metin[son.end():].strip(" ,;-")
        gunler = "0,1,2,3,4,5,6"
        k = _norm(kalan)
        if "hafta ici" in k:
            gunler = "0,1,2,3,4"
            kalan = re.sub(r"hafta i[çc]i", "", kalan,
                           flags=re.I).strip(" ,;-")
        elif "hafta sonu" in k:
            gunler = "5,6"
            kalan = re.sub(r"hafta sonu", "", kalan,
                           flags=re.I).strip(" ,;-")
        simdi = time.time()
        with veritabani.islem():
            kimlik = veritabani.sorgu(
                "INSERT INTO ilac (ad, doz_notu, olusturma) VALUES (?,?,?)",
                (ad, kalan[:120], simdi))
            for sa, dk in sorted(set(saatler)):
                veritabani.sorgu(
                    "INSERT INTO ilac_plan (ilac_id, saat, gunler, olusturma)"
                    " VALUES (?,?,?,?)",
                    (kimlik, "%02d:%02d" % (sa, dk), gunler, simdi))
        veritabani.gunluge_yaz("bilgi", "ilac", "ilaç eklendi: #%d" % kimlik)
        return ("Kaydettim: %s%s — saatler: %s. Dozu ben değiştirmem; "
                "yalnızca hatırlatır ve yanıtınızı kaydederim."
                % (ad, " (%s)" % kalan if kalan else "",
                   ", ".join("%02d:%02d" % s for s in sorted(set(saatler)))))

    def durdur(self, ad):
        """İlacın planını durdurur (geçmiş silinmez). Bugünkü açık dozlara
        dokunmaz."""
        satirlar = [i for i in veritabani.sorgu(
            "SELECT * FROM ilac WHERE aktif=1", (), True)
            if _norm(ad) in _norm(i["ad"])]
        if len(satirlar) != 1:
            return ("Bu adla tam bir aktif ilaç bulamadım." if not satirlar
                    else "Birden çok ilaç eşleşti; tam adı yazın.")
        veritabani.sorgu("UPDATE ilac SET aktif=0 WHERE id=?",
                         (satirlar[0]["id"],))
        veritabani.sorgu("UPDATE ilac_plan SET aktif=0 WHERE ilac_id=?",
                         (satirlar[0]["id"],))
        return ("%s planını durdurdum; kayıtlar duruyor. (Doz değişikliğini "
                "hekiminizle yapın.)" % satirlar[0]["ad"])

    def listele(self):
        satirlar = veritabani.sorgu(
            "SELECT i.ad, i.doz_notu, GROUP_CONCAT(p.saat, ' ') AS saatler "
            "FROM ilac i JOIN ilac_plan p ON p.ilac_id=i.id AND p.aktif=1 "
            "WHERE i.aktif=1 GROUP BY i.id ORDER BY i.ad", (), True)
        if not satirlar:
            return "Kayıtlı aktif ilaç yok. Örnek: ilaç ekle: Ad 08:00 20:00"
        return "\n".join("• %s%s: %s" % (
            s["ad"], " (%s)" % s["doz_notu"] if s["doz_notu"] else "",
            s["saatler"]) for s in satirlar)

    # ---------------------------------------------------------- doz üretimi
    def doz_uret(self, su_an):
        """Planlardan doz örnekleri oluşturur (bugün + son 24 saat).

        Plandan ÖNCE kalan saatler için doz üretilmez. Uygulama kapalıyken
        kaçan doz, ``ilac_gec_saat`` içindeyse geç hatırlatılır; değilse
        "yanıtsız" kaydedilir (alınıp alınmadığı bilinmez)."""
        planlar = veritabani.sorgu(
            "SELECT p.*, i.ad, i.doz_notu FROM ilac_plan p JOIN ilac i ON "
            "i.id=p.ilac_id WHERE p.aktif=1 AND i.aktif=1", (), True)
        for p in planlar:
            gunler = {int(g) for g in p["gunler"].split(",")}
            for gun_farki in (-1, 0):
                gun = (su_an + timedelta(days=gun_farki)).date()
                if gun.weekday() not in gunler:
                    continue
                sa, dk = (int(x) for x in p["saat"].split(":"))
                planli = datetime(gun.year, gun.month, gun.day, sa, dk)
                if planli > su_an or planli < su_an - timedelta(hours=24):
                    continue
                if planli.timestamp() < p["olusturma"]:
                    continue
                var = veritabani.sorgu(
                    "SELECT 1 FROM doz WHERE plan_id=? AND planli=?",
                    (p["id"], planli.strftime(BICIM)), True)
                if var:
                    continue
                gec = su_an.timestamp() - planli.timestamp()
                durum = "bekliyor" if gec <= self._gec_sinir() else "yanitsiz"
                kimlik = veritabani.sorgu(
                    "INSERT INTO doz (ilac_id, plan_id, ilac_ad, doz_notu, "
                    "planli, durum, sonraki) VALUES (?,?,?,?,?,?,?)",
                    (p["ilac_id"], p["id"], p["ad"], p["doz_notu"],
                     planli.strftime(BICIM), durum, planli.timestamp()))
                if durum == "yanitsiz":
                    self._gecmis(kimlik, "kapali_kaldi",
                                 "Ülgen kapalıydı; hatırlatılamadı")
                    self._bildir("%s %s dozu için hatırlatma yapamadım "
                                 "(Ülgen kapalıydı). Kayıt: yanıtsız — "
                                 "alınıp alınmadığını bilmiyorum. [D%d]"
                                 % (p["ad"], p["saat"], kimlik),
                                 {"tur": "doz_bilgi", "doz": kimlik})

    @staticmethod
    def _gecmis(doz_id, olay, ayrinti=""):
        veritabani.sorgu(
            "INSERT INTO doz_gecmis (doz_id, zaman, olay, ayrinti) "
            "VALUES (?,?,?,?)", (doz_id, time.time(), olay, ayrinti))

    # --------------------------------------------------------------- adım
    def adim(self, su_an):
        """Zamanı gelen dozları bildirir (ertelenenleri uyandırır)."""
        self.doz_uret(su_an)
        simdi = su_an.timestamp()
        for d in veritabani.sorgu(
                "SELECT * FROM doz WHERE durum IN ('bekliyor','ertelendi') "
                "AND sonraki<=? ORDER BY planli, id", (simdi,), True):
            sayi = d["bildirim_sayisi"] + 1
            if sayi > self._azami_tekrar():
                self._yanitsiz(d)
                continue
            veritabani.sorgu(
                "UPDATE doz SET durum='bekliyor', bildirim_sayisi=?, "
                "sonraki=? WHERE id=? AND durum IN ('bekliyor','ertelendi')",
                (sayi, simdi + self._aralik(), d["id"]))
            self._gecmis(d["id"], "bildirim", "#%d" % sayi)
            self._bildir(self._bildirim_metni(d, sayi),
                         {"tur": "doz", "doz": d["id"],
                          "secenekler": ["alindi", "ertele", "almadi",
                                         "atlandi"]})

    @staticmethod
    def _bildirim_metni(d, sayi):
        saat = d["planli"][11:]
        not_ = " (%s)" % d["doz_notu"] if d["doz_notu"] else ""
        bas = "İlaç zamanı" if sayi == 1 else "Tekrar hatırlatıyorum"
        return ("%s: %s%s, %s [D%d]. Yanıt: 'aldım D%d', 'ertele 15 D%d', "
                "'almadım D%d' ya da 'atla D%d'." % (
                    bas, d["ilac_ad"], not_, saat, d["id"], d["id"],
                    d["id"], d["id"], d["id"]))

    def _yanitsiz(self, d):
        adet = veritabani.sorgu(
            "UPDATE doz SET durum='yanitsiz' WHERE id=? AND durum IN "
            "('bekliyor','ertelendi')", (d["id"],), sayi=True)
        if adet:
            self._gecmis(d["id"], "yanitsiz", "azami hatırlatma doldu")
            self._bildir("%s %s dozu için yanıt alamadım; %d kez hatırlattım. "
                         "Kayıt: YANITSIZ (alınıp alınmadığını bilmiyorum). "
                         "Durumu değiştirmek için 'düzelt D%d aldım' yazın."
                         % (d["ilac_ad"], d["planli"][11:],
                            self._azami_tekrar(), d["id"]),
                         {"tur": "doz_bilgi", "doz": d["id"]})

    # ------------------------------------------------------------ yanıtlar
    def yanit(self, doz_id, yanit, dk=15, kaynak="kullanici", simdi=None):
        """TEK bir doz örneğine yanıt: alindi | almadi | atlandi |
        tamamlandi | ertele. Başka hiçbir satıra dokunmaz."""
        doz_id = int(doz_id)
        d = veritabani.sorgu("SELECT * FROM doz WHERE id=?", (doz_id,), True)
        if not d:
            return "D%d numaralı bir doz yok." % doz_id
        d = d[0]
        ad = "%s %s [D%d]" % (d["ilac_ad"], d["planli"][11:], doz_id)
        if d["durum"] not in ACIK:
            return ("%s zaten '%s' olarak kayıtlı; değiştirmedim. Yanlışsa: "
                    "'düzelt D%d aldım'." % (ad, d["durum"], doz_id))
        simdi = time.time() if simdi is None else simdi
        if yanit == "ertele":
            dk = max(1, min(int(dk), 240))
            adet = veritabani.sorgu(
                "UPDATE doz SET durum='ertelendi', sonraki=?, kaynak=? "
                "WHERE id=? AND durum IN ('bekliyor','ertelendi')",
                (simdi + dk * 60, kaynak, doz_id), sayi=True)
            self._gecmis(doz_id, "ertelendi", "%d dk" % dk)
            return "%s dozunu %d dakika erteledim." % (ad, dk) if adet \
                else "Değişmedi."
        if yanit not in SONUCLAR:
            return "Geçersiz yanıt."
        adet = veritabani.sorgu(
            "UPDATE doz SET durum=?, yanit_zaman=?, kaynak=? WHERE id=? AND "
            "durum IN ('bekliyor','ertelendi')",
            (yanit, simdi, kaynak, doz_id), sayi=True)
        if not adet:
            return "Değişmedi."
        self._gecmis(doz_id, yanit, kaynak)
        return "%s: %s olarak kaydettim. Diğer dozlara dokunmadım." % (
            ad, SONUCLAR[yanit])

    def duzelt(self, doz_id, yanit):
        """Kapanmış bir dozun kaydını (kullanıcı isteğiyle) düzeltir; eski
        durum geçmişte kalır."""
        d = veritabani.sorgu("SELECT * FROM doz WHERE id=?", (int(doz_id),),
                             True)
        if not d or yanit not in SONUCLAR:
            return "Doz bulunamadı ya da yanıt geçersiz."
        veritabani.sorgu(
            "UPDATE doz SET durum=?, yanit_zaman=?, kaynak='duzeltme' "
            "WHERE id=?", (yanit, time.time(), int(doz_id)))
        self._gecmis(int(doz_id), "duzeltme",
                     "%s -> %s" % (d[0]["durum"], yanit))
        return "D%s kaydını '%s' olarak düzelttim (eski: %s)." % (
            doz_id, SONUCLAR[yanit], d[0]["durum"])

    def acik_dozlar(self, su_an=None):
        """Zamanı gelmiş ve yanıt bekleyen dozlar."""
        simdi = (su_an or datetime.now()).strftime(BICIM)
        return veritabani.sorgu(
            "SELECT * FROM doz WHERE durum IN ('bekliyor','ertelendi') AND "
            "planli<=? AND bildirim_sayisi>0 ORDER BY planli, id",
            (simdi,), True)

    def _liste_metni(self, dozlar):
        return "; ".join("D%d %s %s" % (d["id"], d["ilac_ad"], d["planli"][11:])
                         for d in dozlar)

    def metinden_yanit(self, m, su_an=None):
        """Kullanıcı cümlesini yanıta çevirir. Hiç ilgisi yoksa None.

        Kısa ve açık cümleler kabul edilir; "market'ten ekmek aldım" gibi
        ilgisiz cümleler bir dozu ETKİLEMEZ."""
        k = _norm(m).strip(" .!")
        acik = self.acik_dozlar(su_an)
        if re.fullmatch(r"(tamam|tamamdir|olur|goruldu|onayliyorum)", k):
            if acik:
                return ("%d ilaç dozu yanıt bekliyor: %s. 'Tamam' bir dozu "
                        "onaylamaz; hangisini aldıysanız 'aldım D%d' gibi "
                        "yazın." % (len(acik), self._liste_metni(acik),
                                    acik[0]["id"]))
            return None
        e = re.search(r"\b(duzelt)\s+d(\d+)\s+(aldim|almadim|atla)", k)
        if e:
            return self.duzelt(e.group(2), {
                "aldim": "alindi", "almadim": "almadi",
                "atla": "atlandi"}[e.group(3)])
        yanit = dk = None
        if re.search(r"\b(aldim|ictim)\b", k):
            yanit = "alindi"
        elif re.search(r"\b(almadim|alamadim|icmedim|icemedim)\b", k):
            yanit = "almadi"
        elif re.search(r"\b(atla|atliyorum|atladim)\b", k):
            yanit = "atlandi"
        elif re.search(r"\bertele", k):
            yanit = "ertele"
            e = re.search(r"\bertele\w*\s+(\d{1,3})", k) or re.search(
                r"\b(\d{1,3})\s*(?:dk|dakika)", k)
            dk = int(e.group(1)) if e else 15
        if yanit is None or len(k) > 60 or not acik:
            return None
        hedef = self._hedef(k, acik)
        if hedef is None:
            return None                  # ilgisiz cümle
        if hedef == []:
            return ("Hangi doz? %s. Örnek: '%s D%d'." % (
                self._liste_metni(acik),
                {"alindi": "aldım", "almadi": "almadım", "atlandi": "atla",
                 "ertele": "ertele 15"}[yanit], acik[0]["id"]))
        return self.yanit(hedef["id"], yanit, dk or 15, "kullanici",
                          su_an.timestamp() if su_an else None)

    @staticmethod
    def _hedef(k, acik):
        """Cümleden tek doz seçer: dict | [] (belirsiz) | None (ilgisiz)."""
        e = re.search(r"\bd(\d+)\b", k)
        if e:
            for d in acik:
                if d["id"] == int(e.group(1)):
                    return d
            return None
        kalan = re.sub(r"\b(aldim|ictim|almadim|alamadim|icmedim|icemedim|"
                       r"atla\w*|ertele\w*|dk|dakika|\d{1,3})\b", " ", k)
        saat = SAAT.search(k)
        kalan = SAAT.sub(" ", kalan)
        adaylar = acik
        sozcukler = [s for s in re.findall(r"[a-z]{2,}", kalan)]
        if sozcukler:
            adaylar = [d for d in acik if all(
                s in _norm(d["ilac_ad"]) for s in sozcukler)]
            if not adaylar:
                return None
        if saat:
            hh = "%02d:%s" % (int(saat.group(1)), saat.group(2))
            adaylar = [d for d in adaylar if d["planli"][11:] == hh]
            if not adaylar:
                return None
        if len(adaylar) == 1 and (sozcukler or saat or len(acik) == 1):
            return adaylar[0]
        return [] if len(k.split()) <= 6 else None

    # ------------------------------------------------------------- raporlar
    def bugun(self, su_an=None):
        su_an = su_an or datetime.now()
        gun = su_an.strftime("%Y-%m-%d")
        satirlar = veritabani.sorgu(
            "SELECT * FROM doz WHERE planli>=? ORDER BY planli, id",
            (gun,), True)
        if not satirlar:
            return "Bugün için ilaç dozu kaydı yok."
        etiket = {"bekliyor": "bekliyor", "ertelendi": "ertelendi",
                  "alindi": "alındı", "almadi": "almadı", "atlandi": "atlandı",
                  "tamamlandi": "tamamlandı", "yanitsiz": "YANITSIZ"}
        return "\n".join("D%d  %s  %s  → %s" % (
            d["id"], d["planli"][11:], d["ilac_ad"], etiket[d["durum"]])
            for d in satirlar)

    def bugun_json(self, su_an=None):
        gun = (su_an or datetime.now()).strftime("%Y-%m-%d")
        return veritabani.sorgu(
            "SELECT id, ilac_ad, doz_notu, planli, durum, bildirim_sayisi "
            "FROM doz WHERE planli>=? ORDER BY planli, id", (gun,), True)

    def gecmis_metni(self, adet=15):
        satirlar = veritabani.sorgu(
            "SELECT g.zaman, g.doz_id, g.olay, g.ayrinti, d.ilac_ad, "
            "d.planli FROM doz_gecmis g JOIN doz d ON d.id=g.doz_id "
            "WHERE g.olay!='bildirim' ORDER BY g.id DESC LIMIT ?", (adet,),
            True)
        return "\n".join("%s  D%d %s %s: %s %s" % (
            datetime.fromtimestamp(s["zaman"]).strftime("%d.%m %H:%M"),
            s["doz_id"], s["ilac_ad"], s["planli"][11:], s["olay"],
            s["ayrinti"]) for s in satirlar) or "Henüz kayıt yok."
