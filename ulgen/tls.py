"""Yerel sertifika yetkilisi (CA) ve sunucu sertifikası.

ZeroTier adreslerine herkese açık bir sertifika verilemez. Bu yüzden Ülgen
kendi CA'sını üretir; iPhone'a bu CA'nın GENEL sertifikası bir kez
yüklenir. CA'nın özel anahtarı Mac'ten çıkmaz ve ana anahtarla şifreli
saklanır. Sunucu sertifikası ZeroTier adreslerini kapsar, 1 yıl geçerlidir
ve adres değişince ya da süresi dolmadan önce kendiliğinden yenilenir.
"""

import ipaddress
import os
import socket
import ssl
from datetime import datetime, timedelta, timezone

from . import ayar, gizli


def klasor():
    yol = os.path.join(ayar.KLASOR, "tls")
    os.makedirs(yol, mode=0o700, exist_ok=True)
    return yol


def yollar():
    k = klasor()
    return {"ca_sert": os.path.join(k, "ca.crt"),
            "ca_anahtar": os.path.join(k, "ca.key.sifreli"),
            "sert": os.path.join(k, "sunucu.crt"),
            "anahtar": os.path.join(k, "sunucu.key")}


def _x509():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    return (x509, hashes, serialization, ec, ExtendedKeyUsageOID, NameOID)


def _yaz(yol, veri, mod=0o600):
    gecici = yol + ".tmp"
    with open(gecici, "wb") as dosya:
        dosya.write(veri)
    os.chmod(gecici, mod)
    os.replace(gecici, yol)


def ca_hazirla():
    """CA yoksa üretir. CA sertifikasının (genel) yolunu döndürür."""
    x509, hashes, serialization, ec, _, NameOID = _x509()
    y = yollar()
    if os.path.exists(y["ca_sert"]) and os.path.exists(y["ca_anahtar"]):
        return y["ca_sert"]
    anahtar = ec.generate_private_key(ec.SECP256R1())
    ad = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,
                                       "Ülgen Yerel CA (%s)" % socket.gethostname())])
    simdi = datetime.now(timezone.utc) - timedelta(minutes=5)
    sert = (x509.CertificateBuilder()
            .subject_name(ad).issuer_name(ad)
            .public_key(anahtar.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(simdi)
            .not_valid_after(simdi + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0),
                           critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(
                anahtar.public_key()), critical=False)
            .add_extension(x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False), critical=True)
            .sign(anahtar, hashes.SHA256()))
    pem = anahtar.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    _yaz(y["ca_anahtar"], gizli.sifrele(pem))
    _yaz(y["ca_sert"], sert.public_bytes(serialization.Encoding.PEM), 0o644)
    return y["ca_sert"]


def _ca_yukle():
    x509, _, serialization, _, _, _ = _x509()
    y = yollar()
    with open(y["ca_sert"], "rb") as f:
        sert = x509.load_pem_x509_certificate(f.read())
    with open(y["ca_anahtar"], "rb") as f:
        anahtar = serialization.load_pem_private_key(gizli.coz(f.read()), None)
    return sert, anahtar


def _san_listesi(adresler):
    x509 = _x509()[0]
    san = [x509.DNSName("localhost")]
    for adres in sorted(set(adresler) | {"127.0.0.1", "::1"}):
        san.append(x509.IPAddress(ipaddress.ip_address(adres)))
    # WebAuthn (Face ID) alan adı ister: 10.1.2.3 -> 10-1-2-3.sslip.io
    for adres in sorted(set(adresler)):
        if ":" not in adres:
            san.append(x509.DNSName(adres.replace(".", "-") + ".sslip.io"))
    return san


def sunucu_sertifikasi(adresler):
    """Adresleri kapsayan geçerli bir sunucu sertifikası sağlar.

    (sertifika_yolu, anahtar_yolu) döndürür.
    """
    x509, hashes, serialization, ec, EKU, NameOID = _x509()
    ca_hazirla()
    y = yollar()
    istenen = {str(ipaddress.ip_address(a)) for a in adresler}
    if os.path.exists(y["sert"]) and os.path.exists(y["anahtar"]):
        with open(y["sert"], "rb") as f:
            mevcut = x509.load_pem_x509_certificate(f.read())
        try:
            ips = {str(ip) for ip in mevcut.extensions.get_extension_for_class(
                x509.SubjectAlternativeName).value.get_values_for_type(
                    x509.IPAddress)}
        except x509.ExtensionNotFound:
            ips = set()
        kalan = mevcut.not_valid_after_utc - datetime.now(timezone.utc)
        if (istenen | {"127.0.0.1", "::1"}) <= ips and kalan > timedelta(days=30):
            return y["sert"], y["anahtar"]
    ca_sert, ca_anahtar = _ca_yukle()
    anahtar = ec.generate_private_key(ec.SECP256R1())
    simdi = datetime.now(timezone.utc) - timedelta(minutes=5)
    sert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(
                NameOID.COMMON_NAME, "Ülgen")]))
            .issuer_name(ca_sert.subject)
            .public_key(anahtar.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(simdi)
            .not_valid_after(simdi + timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName(_san_listesi(istenen)),
                           critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None),
                           critical=True)
            .add_extension(x509.ExtendedKeyUsage([EKU.SERVER_AUTH]),
                           critical=False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(
                anahtar.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(
                ca_anahtar.public_key()), critical=False)
            .sign(ca_anahtar, hashes.SHA256()))
    _yaz(y["anahtar"], anahtar.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    _yaz(y["sert"], sert.public_bytes(serialization.Encoding.PEM)
         + ca_sert.public_bytes(serialization.Encoding.PEM), 0o644)
    return y["sert"], y["anahtar"]


def ssl_baglami(adresler):
    """Sunucu için TLS 1.2+ bağlamı kurar."""
    sert, anahtar = sunucu_sertifikasi(adresler)
    baglam = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    baglam.minimum_version = ssl.TLSVersion.TLSv1_2
    baglam.load_cert_chain(sert, anahtar)
    return baglam


def ca_der():
    """iPhone'a yüklenecek CA sertifikası (DER biçimi)."""
    x509, _, serialization, _, _, _ = _x509()
    with open(ca_hazirla(), "rb") as f:
        sert = x509.load_pem_x509_certificate(f.read())
    return sert.public_bytes(serialization.Encoding.DER)
