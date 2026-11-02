"""Özel Kasa: AES-256-GCM ile şifreli, yapay zekânın AÇAMADIĞI gizli öğeler.

Anahtar yapısı
  K (32 bayt, rastgele) = kasa anahtarı; diskte YALNIZ sarılı hâlde durur:
    - parolayla  (scrypt)           -> her zaman çalışır
    - Face ID ile (WebAuthn PRF)    -> iPhone; parola unutulursa kurtarır
    - kurtarma koduyla (bir kez gösterilir)
  K hiçbir yerde saklanmaz; her işlemde açılır, iş bitince bellekten atılır.

Yapay zekâ sınırı
  Sohbet/araç katmanı yalnız ``istek_olustur`` çağırabilir (bekleyen istek,
  120 sn). İçerik ancak kullanıcının Face ID onayıyla, HTTP yanıtında
  arayüze döner; sohbete, günlüğe, hafızaya ya da yapay zekâya GİRMEZ.
  Her onay tek kullanımlık, kapsamlı (oku:<ad>) ve süreli.
"""

import base64
import os
import threading
import time

from . import ayar, gizli, veritabani, webauthn

OMUR_SN = 120
ILGILI = b"ULGEN-OZELKASA-1"
_DENEME = {"adet": 0, "bekle": 0.0}
_KILIT = threading.Lock()


class KasaHatasi(Exception):
    pass


def _hkdf(gizli_bayt, bilgi):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    return HKDF(hashes.SHA256(), 32, None, bilgi).derive(gizli_bayt)


def _scrypt(parola, tuz):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(tuz, 32, 2 ** 15, 8, 1).derive(parola.encode("utf-8"))


def _meta(ad):
    s = veritabani.sorgu("SELECT deger FROM kasa_meta WHERE ad=?", (ad,), True)
    return bytes(s[0]["deger"]) if s else None


def _meta_yaz(ad, deger):
    veritabani.sorgu("INSERT OR REPLACE INTO kasa_meta (ad, deger) VALUES "
                     "(?, ?)", (ad, deger))


def kurulu_mu():
    return _meta("sarmali_parola") is not None


def _hiz_siniri():
    with _KILIT:
        if _DENEME["bekle"] > time.time():
            raise KasaHatasi("çok fazla yanlış deneme; biraz bekleyin")


def _basarisiz():
    with _KILIT:
        _DENEME["adet"] += 1
        if _DENEME["adet"] >= 5:
            _DENEME["bekle"] = time.time() + 60
            _DENEME["adet"] = 0


def _basarili():
    with _KILIT:
        _DENEME["adet"] = 0


def _sar(anahtar, k):
    return gizli.aes_sifrele(anahtar, k, ILGILI)


def _ac_sarmali(anahtar, sarmali):
    try:
        return gizli.aes_coz(anahtar, sarmali, ILGILI)
    except gizli.AnahtarYok:
        _basarisiz()
        raise KasaHatasi("açılamadı (yanlış parola/anahtar)")


def kod_uret():
    ham = base64.b32encode(os.urandom(20)).decode("ascii")
    return "-".join(ham[i:i + 4] for i in range(0, len(ham), 4))


def _kod_anahtar(kod):
    temiz = "".join(c for c in kod.upper() if c.isalnum())
    return _hkdf(temiz.encode("ascii", "ignore"), b"ulgen-kurtarma-kodu")


def kur(parola):
    """Kasayı kurar. Kurtarma kodunu BİR KEZ döndürür (yazıp saklayın)."""
    if kurulu_mu():
        raise KasaHatasi("Özel Kasa zaten kurulu")
    if len(parola or "") < 8:
        raise KasaHatasi("parola en az 8 karakter olmalı")
    k = os.urandom(32)
    tuz = os.urandom(16)
    kod = kod_uret()
    with veritabani.islem():
        _meta_yaz("tuz", tuz)
        _meta_yaz("sarmali_parola", _sar(_scrypt(parola, tuz), k))
        _meta_yaz("sarmali_kurtarma", _sar(_kod_anahtar(kod), k))
    # Ana anahtarın (veritabanı) kurtarma paketi: kodla açılır, Mac'ten
    # bağımsız saklanabilir (iPhone Dosyalar, USB).
    paket = gizli.aes_sifrele(_kod_anahtar(kod), gizli.ana_anahtar(),
                              b"ULGEN-ANAHTAR-PAKETI")
    yol = os.path.join(ayar.KLASOR, "kurtarma.paket")
    with open(yol, "wb") as f:
        f.write(paket)
    os.chmod(yol, 0o600)
    return kod


def _k_ac(acma):
    """acma: {"parola":..} | {"prf": bayt} | {"kod":..} -> K."""
    _hiz_siniri()
    if "parola" in acma:
        tuz = _meta("tuz")
        k = _ac_sarmali(_scrypt(acma["parola"], tuz),
                        _meta("sarmali_parola"))
    elif "kod" in acma:
        k = _ac_sarmali(_kod_anahtar(acma["kod"]), _meta("sarmali_kurtarma"))
    elif "prf" in acma:
        s = veritabani.sorgu("SELECT sarmali FROM kasa_anahtar WHERE "
                             "kimlik=?", (acma["cred"],), True)
        if not s or not s[0]["sarmali"]:
            raise KasaHatasi("bu Face ID anahtarı kasaya bağlı değil")
        k = _ac_sarmali(_hkdf(acma["prf"], b"ulgen-kasa-prf"),
                        bytes(s[0]["sarmali"]))
    else:
        raise KasaHatasi("açma yöntemi yok")
    _basarili()
    return k


# ----------------------------------------------------------------- öğeler
def adlar():
    """Yalnız ADLAR (içerik değil). Adlar şifresiz saklanır; gizli bilgiyi
    ada yazmayın."""
    return [s["ad"] for s in veritabani.sorgu(
        "SELECT ad FROM kasa_oge ORDER BY ad", (), True)]


def oge_ekle(ad, icerik, acma):
    ad = (ad or "").strip()
    if not ad or len(ad) > 80 or len(icerik or "") > 100000:
        raise KasaHatasi("ad (≤80) ve içerik (≤100 KB) gerekli")
    k = _k_ac(acma)
    veritabani.sorgu(
        "INSERT OR REPLACE INTO kasa_oge (ad, veri, olusturma) VALUES "
        "(?, ?, ?)", (ad, gizli.aes_sifrele(k, icerik.encode("utf-8"),
                                            ad.encode("utf-8")), time.time()))


def _coz(ad, k):
    s = veritabani.sorgu("SELECT veri FROM kasa_oge WHERE ad=?", (ad,), True)
    if not s:
        raise KasaHatasi("öğe yok")
    return gizli.aes_coz(k, bytes(s[0]["veri"]),
                         ad.encode("utf-8")).decode("utf-8")


def oge_oku(ad, acma):
    return _coz(ad, _k_ac(acma))


def oge_sil(ad, acma):
    _k_ac(acma)
    return veritabani.sorgu("DELETE FROM kasa_oge WHERE ad=?", (ad,),
                            sayi=True)


def parola_degistir(acma, yeni):
    if len(yeni or "") < 8:
        raise KasaHatasi("parola en az 8 karakter olmalı")
    k = _k_ac(acma)
    tuz = os.urandom(16)
    with veritabani.islem():
        _meta_yaz("tuz", tuz)
        _meta_yaz("sarmali_parola", _sar(_scrypt(yeni, tuz), k))


# ------------------------------------------------------------ yapay zekâ
def istek_olustur(ad):
    """Yapay zekâ/sohbet YALNIZ bunu çağırabilir. İçerik döndürmez."""
    if ad not in adlar():
        return "Özel Kasa'da '%s' adlı öğe yok." % ad
    veritabani.sorgu("DELETE FROM kasa_istek WHERE bitis < ?", (time.time(),))
    kimlik = veritabani.sorgu(
        "INSERT INTO kasa_istek (kapsam, bitis, durum) VALUES (?, ?, "
        "'bekliyor')", ("oku:" + ad, time.time() + OMUR_SN))
    return ("'%s' için Özel Kasa isteği #%d açıldı. İçeriği ben göremem; "
            "iPhone'unuzda Ülgen > Özel Kasa'dan Face ID ile onaylayın "
            "(%d sn geçerli, tek kullanımlık)." % (ad, kimlik, OMUR_SN))


def bekleyen_istekler():
    return veritabani.sorgu(
        "SELECT id, kapsam FROM kasa_istek WHERE durum='bekliyor' AND "
        "bitis>=? ORDER BY id", (time.time(),), True)


def istek_tuket(kimlik, ad):
    """İsteği YAKAR (bir kez); geçerliyse True."""
    return bool(veritabani.sorgu(
        "UPDATE kasa_istek SET durum='kullanildi' WHERE id=? AND "
        "kapsam=? AND durum='bekliyor' AND bitis>=?",
        (kimlik, "oku:" + ad, time.time()), sayi=True))


# ---------------------------------------------------------------- passkey
def rp_onerisi(host):
    """WebAuthn rpId bir alan adı olmalıdır. IP ise sslip.io adı önerilir
    (ör. 10.147.17.5 -> 10-147-17-5.sslip.io); sertifikaya da eklenmelidir."""
    ana = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    if ana.replace(".", "").isdigit():
        return ana.replace(".", "-") + ".sslip.io"
    return ana


def passkey_sayisi():
    return veritabani.sorgu("SELECT COUNT(*) AS n FROM kasa_anahtar", (),
                            True)[0]["n"]


def kayit_baslat():
    kimlik, ch = webauthn.challenge_uret("kayit")
    return {"kimlik": kimlik, "challenge": ch}


def kayit_bitir(kimlik, veri, rp_id, origin, ad="iPhone"):
    cred, x, y, sayac = webauthn.kayit_bitir(kimlik, veri, rp_id, origin)
    veritabani.sorgu(
        "INSERT OR REPLACE INTO kasa_anahtar (kimlik, ad, x, y, rp, sayac, "
        "olusturma) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (webauthn.b64(cred), ad, x, y, rp_id, sayac, time.time()))
    return webauthn.b64(cred)


def prf_bagla(cred, prf, acma):
    """Face ID'nin PRF çıktısını kasa anahtarına bağlar (parolayla bir kez)."""
    k = _k_ac(acma)
    veritabani.sorgu("UPDATE kasa_anahtar SET sarmali=? WHERE kimlik=?",
                     (_sar(_hkdf(prf, b"ulgen-kasa-prf"), k), cred))


def giris_baslat(kapsam):
    kimlik, ch = webauthn.challenge_uret("giris", kapsam)
    return {"kimlik": kimlik, "challenge": ch, "izinli": [
        s["kimlik"] for s in veritabani.sorgu(
            "SELECT kimlik FROM kasa_anahtar", (), True)]}


def passkey_dogrula(kimlik, veri, rp_id, origin, beklenen_kapsam):
    """Face ID imzasını doğrular, kapsamı eşleştirir; kimlik döndürür."""
    cred = veri.get("id", "")
    s = veritabani.sorgu("SELECT * FROM kasa_anahtar WHERE kimlik=?",
                         (cred,), True)
    if not s or s[0]["rp"] != rp_id:
        raise KasaHatasi("tanınmayan Face ID anahtarı")
    if webauthn.kapsam_bak(kimlik) != beklenen_kapsam:
        try:
            webauthn._tuket(kimlik, "giris")
        except webauthn.Hata:
            pass
        raise KasaHatasi("onay bu işlem için verilmemiş")
    try:
        _, sayac = webauthn.giris_bitir(kimlik, veri, rp_id, origin,
                                        bytes(s[0]["x"]), bytes(s[0]["y"]),
                                        s[0]["sayac"])
    except webauthn.Hata as hata:
        raise KasaHatasi("Face ID doğrulanamadı: %s" % hata)
    veritabani.sorgu("UPDATE kasa_anahtar SET sayac=? WHERE kimlik=?",
                     (sayac, cred))
    return cred


def ana_anahtar_kurtar(dosya, kod):
    """kurtarma.paket + kod -> ana anahtar (yeni Mac'te). Var olan anahtarın
    üzerine YAZMAZ."""
    with open(dosya, "rb") as f:
        paket = f.read()
    try:
        ham = gizli.aes_coz(_kod_anahtar(kod), paket, b"ULGEN-ANAHTAR-PAKETI")
    except gizli.AnahtarYok:
        raise KasaHatasi("kod yanlış ya da paket bozuk")
    try:
        gizli.ana_anahtar(olustur=False)
    except gizli.AnahtarYok:
        pass
    else:
        raise KasaHatasi("bu Mac'te zaten bir ana anahtar var; üzerine "
                         "yazılmadı")
    metin = base64.urlsafe_b64encode(ham).decode("ascii")
    if not gizli._zincire_yaz(gizli.HIZMET, metin):
        ayar.klasor_hazirla()
        with open(gizli._anahtar_dosyasi(), "w", encoding="ascii") as f:
            f.write(metin)
        os.chmod(gizli._anahtar_dosyasi(), 0o600)
    return True
