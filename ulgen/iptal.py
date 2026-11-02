"""Çalışan bir sohbet/araştırma işini kullanıcı isteğiyle durdurma.

``ayarla()`` bayrağı kaldırır; uzun işler ara adımlarda ``denetle()`` çağırır
ve bayrak kalkmışsa ``Iptal`` fırlatılır. Sohbet işi başlarken bayrak
temizlenir; bu yüzden eski bir iptal yeni işi durdurmaz."""

import threading


class Iptal(Exception):
    """Kullanıcı çalışan işi durdurdu."""


_BAYRAK = threading.Event()


def ayarla():
    _BAYRAK.set()


def temizle():
    _BAYRAK.clear()


def istendi():
    return _BAYRAK.is_set()


def denetle():
    if _BAYRAK.is_set():
        raise Iptal()
