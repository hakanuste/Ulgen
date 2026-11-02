"""WebAuthn (Face ID / Touch ID geçiş anahtarı) doğrulaması.

Kapsam: kayıt (attestation "none") ve giriş (assertion), ES256 (P-256).
Kullanıcı doğrulaması (UV = Face ID) ZORUNLUDUR. Her challenge TEK
KULLANIMLIKTIR, 120 sn ömürlüdür ve bir kapsama (ör. "oku:banka") bağlıdır;
bir kapsam için alınan onay başka kapsamda geçmez.

Sınır: tarayıcılar rpId olarak IP adresine İZİN VERMEZ; bir alan adı gerekir
(bkz. ozelkasa.rp_onerisi). Gerçek iPhone'da denenmedi.
"""

import base64
import hashlib
import json
import secrets
import threading
import time

from . import cbor

OMUR_SN = 120
_KILIT = threading.Lock()
_BEKLEYEN = {}


class Hata(Exception):
    pass


def b64(ham):
    return base64.urlsafe_b64encode(ham).rstrip(b"=").decode("ascii")


def b64coz(metin):
    return base64.urlsafe_b64decode(metin + "=" * (-len(metin) % 4))


def challenge_uret(tur, kapsam=""):
    """(kimlik, challenge_b64) döndürür; 120 sn içinde bir kez kullanılır."""
    kimlik = secrets.token_urlsafe(16)
    ch = secrets.token_bytes(32)
    simdi = time.time()
    with _KILIT:
        for k in [k for k, v in _BEKLEYEN.items() if v[2] < simdi]:
            del _BEKLEYEN[k]
        _BEKLEYEN[kimlik] = (ch, tur + "|" + kapsam, simdi + OMUR_SN)
    return kimlik, b64(ch)


def _tuket(kimlik, tur):
    with _KILIT:
        kayit = _BEKLEYEN.pop(kimlik, None)
    if not kayit or kayit[2] < time.time():
        raise Hata("challenge geçersiz ya da süresi dolmuş")
    t, _, kapsam = kayit[1].partition("|")
    if t != tur:
        raise Hata("challenge türü uyuşmuyor")
    return kayit[0], kapsam


def kapsam_bak(kimlik):
    with _KILIT:
        k = _BEKLEYEN.get(kimlik)
    return k[1].partition("|")[2] if k else None


def _istemci_verisi(ham_b64, tur, challenge, origin):
    ham = b64coz(ham_b64)
    try:
        veri = json.loads(ham.decode("utf-8"))
    except ValueError as hata:
        raise Hata("clientDataJSON bozuk") from hata
    if veri.get("type") != tur:
        raise Hata("işlem türü uyuşmuyor")
    if not secrets.compare_digest(veri.get("challenge", ""), b64(challenge)):
        raise Hata("challenge uyuşmuyor")
    if veri.get("origin") != origin:
        raise Hata("köken (origin) uyuşmuyor")
    return ham


def _yetki_verisi(auth, rp_id, kayit):
    if len(auth) < 37:
        raise Hata("authenticatorData kısa")
    if auth[:32] != hashlib.sha256(rp_id.encode("utf-8")).digest():
        raise Hata("rpId uyuşmuyor")
    bayrak = auth[32]
    if not bayrak & 0x01:
        raise Hata("kullanıcı varlığı (UP) yok")
    if not bayrak & 0x04:
        raise Hata("kullanıcı doğrulaması (Face ID) yapılmamış")
    if kayit and not bayrak & 0x40:
        raise Hata("kimlik verisi yok")
    return int.from_bytes(auth[33:37], "big")


def kayit_bitir(kimlik, veri, rp_id, origin):
    """Yeni geçiş anahtarını doğrular; (cred_id, x, y, sayac) döndürür."""
    ch, _ = _tuket(kimlik, "kayit")
    _istemci_verisi(veri["clientDataJSON"], "webauthn.create", ch, origin)
    try:
        nesne, _ = cbor.coz(b64coz(veri["attestationObject"]))
        auth = nesne["authData"]
    except (ValueError, KeyError, TypeError) as hata:
        raise Hata("attestationObject bozuk") from hata
    sayac = _yetki_verisi(auth, rp_id, True)
    try:
        uzun = int.from_bytes(auth[53:55], "big")
        cred = bytes(auth[55:55 + uzun])
        anahtar, _ = cbor.coz(auth[55 + uzun:])
        if anahtar[1] != 2 or anahtar[3] != -7 or anahtar[-1] != 1:
            raise Hata("yalnız ES256/P-256 desteklenir")
        x, y = anahtar[-2], anahtar[-3]
    except (ValueError, KeyError, IndexError, TypeError) as hata:
        raise Hata("açık anahtar okunamadı") from hata
    if len(x) != 32 or len(y) != 32 or not cred:
        raise Hata("açık anahtar geçersiz")
    return cred, x, y, sayac


def giris_bitir(kimlik, veri, rp_id, origin, x, y, eski_sayac):
    """Assertion'ı doğrular; yeni sayaç döndürür. Kapsamı (kapsam, sayac)."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    ch, kapsam = _tuket(kimlik, "giris")
    ham = _istemci_verisi(veri["clientDataJSON"], "webauthn.get", ch, origin)
    auth = b64coz(veri["authenticatorData"])
    sayac = _yetki_verisi(auth, rp_id, False)
    if (sayac or eski_sayac) and sayac <= eski_sayac:
        raise Hata("sayaç geriledi (kopyalanmış anahtar olabilir)")
    anahtar = ec.EllipticCurvePublicNumbers(
        int.from_bytes(x, "big"), int.from_bytes(y, "big"),
        ec.SECP256R1()).public_key()
    try:
        anahtar.verify(b64coz(veri["signature"]),
                       auth + hashlib.sha256(ham).digest(),
                       ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as hata:
        raise Hata("imza geçersiz") from hata
    return kapsam, sayac
