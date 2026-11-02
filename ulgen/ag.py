"""Ağ yardımcıları: macOS'ta python.org Python'u sistem sertifikalarını
bilmez ("CERTIFICATE_VERIFY_FAILED"). Bu yüzden certifi deposu kullanılır."""

import ssl

_BAGLAM = None


def baglam():
    """Doğrulamalı TLS bağlamı (certifi varsa onun CA deposuyla)."""
    global _BAGLAM
    if _BAGLAM is None:
        try:
            import certifi
            _BAGLAM = ssl.create_default_context(cafile=certifi.where())
        except (ImportError, OSError):
            _BAGLAM = ssl.create_default_context()
    return _BAGLAM
