"""Yanıt metnini temizler.

Küçük yerel modeller bazen yanıtın içine Çince/Japonca/Korece harfler,
bozuk karakterler (�) ya da görünmez denetim karakterleri katar. Bunlar
Türkçe yanıtta hiç yer almadığı için atılır. Kiril, Arap ve Yunan harfleri
korunur (Orta Asya adları, Osmanlıca, bilimsel simgeler yerinde kalabilir).
"""

import re

YABANCI = re.compile(
    "[฀-๿"          # Tay
    "ᄀ-ᇿ"            # Hangul jamo
    "⺀-⿟"            # CJK kökleri
    "　-〿"            # CJK noktalama
    "぀-ヿ"            # Hiragana, Katakana
    "㄀-ㇿ"            # Bopomofo vb.
    "㐀-䶿"            # CJK ek A
    "一-鿿"            # CJK
    "가-힯"            # Hangul hece
    "-"            # özel kullanım
    "豈-﫿"            # CJK uyumluluk
    "＀-￯"            # tam genişlik biçimler
    "�"                   # bozuk karakter
    "​-‏⁠﻿"  # görünmez karakterler
    "\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def yabanci_harfleri_at(metin):
    if not metin:
        return metin
    temiz = YABANCI.sub("", metin)
    temiz = re.sub(r"[ \t]{2,}", " ", temiz)
    return re.sub(r" +([,.;:!?])", r"\1", temiz)
