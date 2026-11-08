"""Mac Takvim ve Hatırlatıcılar → Ülgen eşitlemesi; Ülgen → Mac bildirimi.

Okuma yalnızca Mac'in kendi uygulamalarından (AppleScript) yapılır; veri
Mac'ten dışarı çıkmaz. Ülgen bu uygulamalara YAZMAZ.

Sınırlar (dürüst):
  * Tekrarlayan takvim olaylarının yalnızca ilk kaydı gelir (AppleScript
    tekrarları açmaz). Tek seferlik randevular tam gelir.
  * Tüm gün süren olaylar (doğum günü, tatil) alınmaz.
  * İlk çalışmada macOS "Otomasyon" izni sorar (Takvim ve Hatırlatıcılar).
  * Uygulama kapalıysa kısa süre açılır, okunur, yeniden kapatılır.
  * Ülgen kapalıyken eşitleme ve Mac bildirimi çalışmaz.
"""

import platform
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta

from . import ayar, veritabani

BICIM = "%Y-%m-%d %H:%M"
KAYNAK = "mac"
PENCERE_GUN = 14
AZAMI_KAYIT = 300
ZAMAN_ASIMI = 120

_DURUM = {"calisiyor": False, "son": 0.0, "sayilar": {}, "hata": []}
_KILIT = threading.Lock()


class MacSenkHatasi(Exception):
    pass


ORTAK = '''
on pad(n)
  return text -2 thru -1 of ("0" & n)
end pad
on fmt(d)
  set t1 to (year of d as string) & "-" & pad(month of d as integer)
  set t2 to "-" & pad(day of d) & " " & pad(hours of d)
  return t1 & t2 & ":" & pad(minutes of d)
end fmt
on clean(t)
  try
    if t is missing value then return ""
    set t to t as string
    set AppleScript's text item delimiters to {tab, linefeed, return}
    set p to text items of t
    set AppleScript's text item delimiters to " "
    set t to p as string
    set AppleScript's text item delimiters to ""
    return t
  on error
    set AppleScript's text item delimiters to ""
    return ""
  end try
end clean
'''

TAKVIM_BETIGI = ORTAK + '''
set wasRunning to application "Calendar" is running
set d1 to (current date)
set time of d1 to 0
set d2 to d1 + (%d * days)
set out to ""
tell application "Calendar"
  repeat with c in calendars
    try
      set evs to (every event of c whose start date >= d1 and start date < d2)
      if (count of evs) > 0 then
        set us to uid of evs
        set ss to summary of evs
        set ds to start date of evs
        set al to allday event of evs
        repeat with i from 1 to count of evs
          if not (item i of al) then
            set nm to my clean(item i of ss)
            set out to out & (item i of us) & tab & nm & tab & my fmt(item i of ds) & linefeed
          end if
        end repeat
      end if
    end try
  end repeat
end tell
if not wasRunning then
  try
    tell application "Calendar" to quit
  end try
end if
return out
''' % PENCERE_GUN

HATIRLATICI_BETIGI = ORTAK + '''
set wasRunning to application "Reminders" is running
set out to ""
tell application "Reminders"
  repeat with l in lists
    try
      set rs to (reminders of l whose completed is false)
      if (count of rs) > 0 then
        set ids to id of rs
        set ns to name of rs
        set dues to due date of rs
        repeat with i from 1 to count of rs
          set dd to item i of dues
          set ds to ""
          if dd is not missing value then set ds to my fmt(dd)
          set out to out & (item i of ids) & tab & my clean(item i of ns) & tab & ds & linefeed
        end repeat
      end if
    end try
  end repeat
end tell
if not wasRunning then
  try
    tell application "Reminders" to quit
  end try
end if
return out
'''


def mac_mi():
    return platform.system() == "Darwin"


def gizli_ac(betik):
    """Betiğin kullanacağı uygulama kapalıysa onu gizli ve arka planda açar.

    Böylece eşitleme sırasında Takvim/Anımsıtıcı penceresi öne gelmez."""
    for uygulama in ("Calendar", "Reminders"):
        if 'application "%s"' % uygulama in betik:
            try:
                subprocess.run(["open", "-g", "-j", "-a", uygulama],
                               timeout=20, capture_output=True)
            except Exception:
                pass


def osascript_calistir(betik):
    """Betiği osascript'e standart girişten verir; çıktıyı döndürür."""
    gizli_ac(betik)
    try:
        s = subprocess.run(["osascript", "-"], input=betik,
                           capture_output=True, text=True,
                           timeout=ZAMAN_ASIMI)
    except FileNotFoundError:
        raise MacSenkHatasi("osascript bulunamadı (yalnız macOS'ta çalışır)")
    except subprocess.TimeoutExpired:
        raise MacSenkHatasi("Uygulama zamanında yanıt vermedi")
    if s.returncode != 0:
        hata = (s.stderr or "").strip()
        if "-1743" in hata or "not authorized" in hata.lower():
            raise MacSenkHatasi(
                "İzin verilmemiş: Sistem Ayarları > Gizlilik ve Güvenlik > "
                "Otomasyon içinde Takvim ve Hatırlatıcılar'a izin verin")
        raise MacSenkHatasi(hata[-160:] or "bilinmeyen hata")
    return s.stdout


def ayikla(cikti):
    """'kimlik<TAB>ad<TAB>YYYY-AA-GG SS:DD' satırlarını ayıklar."""
    sonuc = []
    for satir in str(cikti).splitlines():
        parca = satir.split("\t")
        if len(parca) < 3:
            continue
        kimlik, ad, zaman = parca[0].strip(), parca[1].strip(), parca[2].strip()
        if not kimlik or not ad:
            continue
        if zaman:
            try:
                datetime.strptime(zaman, BICIM)
            except ValueError:
                continue
        sonuc.append({"kimlik": kimlik, "baslik": ad[:200],
                      "zaman": zaman or None})
        if len(sonuc) >= AZAMI_KAYIT:
            break
    return sonuc


def _yaz(tur, dis, baslik, zaman, su_an):
    """Tek kaydı ekler ya da (hâlâ açıksa) günceller."""
    var = veritabani.sorgu(
        "SELECT * FROM gorev WHERE kaynak=? AND dis_kimlik=?",
        (KAYNAK, dis), True)
    gecti = bool(zaman) and zaman <= su_an.strftime(BICIM)
    if not var:
        veritabani.sorgu(
            "INSERT INTO gorev (tur, baslik, zaman, tekrar, onceden_dk, "
            "asama, olusturma, kaynak, dis_kimlik) "
            "VALUES (?, ?, ?, '', ?, ?, ?, ?, ?)",
            (tur, baslik, zaman,
             int(ayar.yukle().get("randevu_oncesi_dk", 60))
             if tur == "randevu" else 0,
             2 if gecti else 0, su_an.timestamp(), KAYNAK, dis))
        return "yeni"
    g = var[0]
    if g["durum"] != "acik":
        return "ayni"            # Ülgen'de bitirilmiş ya da iptal edilmiş
    if g["baslik"] == baslik and g["zaman"] == zaman:
        return "ayni"
    veritabani.sorgu(
        "UPDATE gorev SET baslik=?, zaman=?, asama=?, son_bildirim='' "
        "WHERE id=?", (baslik, zaman, 2 if gecti else 0, g["id"]))
    return "guncel"


def esitle(su_an=None, calistir=None):
    """Mac Takvim + Hatırlatıcılar → Ülgen. Sayıları döndürür."""
    su_an = su_an or datetime.now()
    calistir = calistir or osascript_calistir
    simdi = su_an.strftime(BICIM)
    sayi = {"yeni": 0, "guncel": 0, "kapandi": 0}
    hatalar = []
    for ad, betik, tur, on in (
            ("Takvim", TAKVIM_BETIGI, "randevu", "t:"),
            ("Hatırlatıcılar", HATIRLATICI_BETIGI, "gorev", "h:")):
        try:
            kayitlar = ayikla(calistir(betik))
        except MacSenkHatasi as hata:
            hatalar.append("%s: %s" % (ad, hata))
            continue
        gorulen = set()
        for k in kayitlar:
            if tur == "randevu":
                if not k["zaman"]:
                    continue
                dis = "%s%s|%s" % (on, k["kimlik"], k["zaman"])
            else:
                dis = on + k["kimlik"]
            gorulen.add(dis)
            sonuc = _yaz(tur, dis, k["baslik"], k["zaman"], su_an)
            if sonuc in sayi:
                sayi[sonuc] += 1
        # Kaynaktan kalkanlar: takvimde gelecekteki silinmiş olay → iptal;
        # tamamlanmış/silinmiş hatırlatıcı → tamam.
        for g in veritabani.sorgu(
                "SELECT id, dis_kimlik, zaman FROM gorev WHERE kaynak=? AND "
                "durum='acik' AND tur=? AND dis_kimlik LIKE ?",
                (KAYNAK, tur, on + "%"), True):
            if g["dis_kimlik"] in gorulen:
                continue
            if tur == "randevu" and not (g["zaman"] and g["zaman"] > simdi):
                continue
            veritabani.sorgu("UPDATE gorev SET durum=? WHERE id=?",
                             ("iptal" if tur == "randevu" else "tamam",
                              g["id"]))
            sayi["kapandi"] += 1
    with _KILIT:
        _DURUM["son"] = time.time()
        _DURUM["sayilar"] = sayi
        _DURUM["hata"] = hatalar
    return {"sayilar": sayi, "hata": hatalar}


def arka_planda_esitle():
    with _KILIT:
        if _DURUM["calisiyor"]:
            return False
        _DURUM["calisiyor"] = True

    def kos():
        try:
            esitle()
        except Exception as hata:
            with _KILIT:
                _DURUM["hata"] = [str(hata)[:160]]
        finally:
            with _KILIT:
                _DURUM["calisiyor"] = False
    threading.Thread(target=kos, daemon=True).start()
    return True


def otomatik_dongu(durdur):
    """Ayar açıksa belirli aralıkla eşitler (yalnız macOS)."""
    if not mac_mi():
        return
    if durdur.wait(30):
        return
    while True:
        try:
            a = ayar.yukle()
            if a.get("mac_senk", True):
                arka_planda_esitle()
            aralik = max(5, int(a.get("mac_senk_dk", 10))) * 60
        except Exception:
            aralik = 600
        if durdur.wait(aralik):
            return


def durum():
    a = ayar.yukle()
    with _KILIT:
        d = dict(_DURUM)
    d.update({"mac": mac_mi(), "senk": bool(a.get("mac_senk", True)),
              "bildirim": bool(a.get("mac_bildirim", True)),
              "aralik_dk": int(a.get("mac_senk_dk", 10))})
    return d


# ------------------------------------------------------------ Mac bildirimi
BILDIRIM_BETIGI = ['on run argv',
                   'display notification (item 1 of argv) with title '
                   '(item 2 of argv) sound name "Glass"',
                   'end run']


def bildirim_komutu(metin, baslik="Ülgen"):
    metin = " ".join(str(metin).split())[:220]
    komut = ["osascript"]
    for satir in BILDIRIM_BETIGI:
        komut += ["-e", satir]
    return komut + [metin, baslik]


def bildirim_goster(metin, baslik="Ülgen"):
    """Mac'in kendi bildirimini gösterir (yalnız macOS, ayar açıksa)."""
    if not mac_mi() or not ayar.yukle().get("mac_bildirim", True):
        return False

    def kos():
        try:
            subprocess.run(bildirim_komutu(metin, baslik), timeout=15,
                           capture_output=True)
        except Exception:
            pass
    threading.Thread(target=kos, daemon=True).start()
    return True


_SES_KILIDI = threading.Lock()
SESLI_BASLAR = re.compile(
    r"^(İlaç zamanı|Tekrar hatırlatıyorum|Hatırlatma zamanı)", re.IGNORECASE)


def sesli_metin_yap(metin):
    """Okunacak cümle: kimlik imleri ve yanıt yönergeleri atılır."""
    metin = str(metin).split("Yanıt:")[0].split("deyin.")[0]
    metin = re.sub(r"\[[#D]?\d+\]", " ", metin)
    metin = re.sub(r"https?://\S+", " ", metin)
    return " ".join(metin.split())[:300]


def sesli_komutlar(metin, ses="Yelda"):
    """Önce kısa uyarı sesi, sonra cümlenin okunması."""
    return [["afplay", "/System/Library/Sounds/Glass.aiff"],
            ["say", "-v", ses, sesli_metin_yap(metin)]]


def sesli_hatirlat(metin):
    """Mac'te hatırlatmayı sesli okur (yalnız macOS, ayar açıksa)."""
    if not mac_mi() or not ayar.yukle().get("hatirlatma_sesi", True):
        return False

    def kos():
        with _SES_KILIDI:
            for komut in sesli_komutlar(
                    metin, ayar.yukle().get("ses", "Yelda")):
                try:
                    subprocess.run(komut, timeout=60, capture_output=True)
                except Exception:
                    pass
    threading.Thread(target=kos, daemon=True).start()
    return True
