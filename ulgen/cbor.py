"""WebAuthn için yeterli en küçük CBOR çözücü (yalnız okuma)."""

import struct


def coz(veri):
    deger, son = _oku(veri, 0)
    return deger, son


def _oku(v, i, derinlik=0):
    if derinlik > 8 or i >= len(v):
        raise ValueError("CBOR bozuk")
    ilk = v[i]
    tur, ek = ilk >> 5, ilk & 31
    i += 1
    if ek < 24:
        n = ek
    elif ek in (24, 25, 26, 27):
        boy = {24: 1, 25: 2, 26: 4, 27: 8}[ek]
        if i + boy > len(v):
            raise ValueError("CBOR kısa")
        n = int.from_bytes(v[i:i + boy], "big")
        i += boy
    elif tur == 7 and ek in (20, 21, 22):
        return {20: False, 21: True, 22: None}[ek], i
    else:
        raise ValueError("CBOR desteklenmiyor")
    if tur == 0:
        return n, i
    if tur == 1:
        return -1 - n, i
    if tur in (2, 3):
        if i + n > len(v):
            raise ValueError("CBOR kısa")
        ham = bytes(v[i:i + n])
        return (ham if tur == 2 else ham.decode("utf-8")), i + n
    if tur == 4:
        liste = []
        for _ in range(n):
            e, i = _oku(v, i, derinlik + 1)
            liste.append(e)
        return liste, i
    if tur == 5:
        sozluk = {}
        for _ in range(n):
            k, i = _oku(v, i, derinlik + 1)
            e, i = _oku(v, i, derinlik + 1)
            sozluk[k] = e
        return sozluk, i
    raise ValueError("CBOR desteklenmiyor")


def kodla_deneme(nesne):
    """Yalnız testler için basit kodlayıcı."""
    def baslik(tur, n):
        if n < 24:
            return bytes([tur << 5 | n])
        if n < 256:
            return bytes([tur << 5 | 24, n])
        if n < 65536:
            return bytes([tur << 5 | 25]) + struct.pack(">H", n)
        return bytes([tur << 5 | 26]) + struct.pack(">I", n)
    if isinstance(nesne, bool) or nesne is None:
        return bytes([{False: 0xf4, True: 0xf5, None: 0xf6}[nesne]])
    if isinstance(nesne, int):
        return baslik(0, nesne) if nesne >= 0 else baslik(1, -1 - nesne)
    if isinstance(nesne, bytes):
        return baslik(2, len(nesne)) + nesne
    if isinstance(nesne, str):
        b = nesne.encode("utf-8")
        return baslik(3, len(b)) + b
    if isinstance(nesne, list):
        return baslik(4, len(nesne)) + b"".join(map(kodla_deneme, nesne))
    if isinstance(nesne, dict):
        return baslik(5, len(nesne)) + b"".join(
            kodla_deneme(k) + kodla_deneme(e) for k, e in nesne.items())
    raise TypeError(type(nesne))
