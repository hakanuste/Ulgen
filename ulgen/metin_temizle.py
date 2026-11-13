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


def latex_temizle(metin):
    """Bulut modelleri bazen ölçüleri LaTeX yazar ($6,5\\text{ m}$); sohbette
    ve seste düz metin olsun: 6,5 m × 6,5 m."""
    t = re.sub(r"\\(?:text|mathbf|mathrm|textbf)\{([^{}]*)\}", r"\1", metin)
    t = (t.replace("\\times", "×").replace("\\cdot", "·").replace("\\approx", "≈")
         .replace("\\le", "≤").replace("\\ge", "≥").replace("\\%", "%"))
    t = re.sub(r"\\[()\[\]]", "", t)
    t = re.sub(r"\$\$?([^$\n]{1,120}?)\$\$?", r"\1", t)
    t = re.sub(r"\^\{?2\}?", "²", t)
    t = re.sub(r"\^\{?3\}?", "³", t)
    return t.replace("\\ ", " ")


def yuzde_turkce(metin):
    """İngilizce yüzde yazımı Türkçeye: '13.3%' -> '%13,3', '-2.3 %' -> '%-2,3'."""
    return re.sub(r"(?<![\w.,%])([+\-−]?)(\d+)(?:\.(\d+))?\s?%(?!\w)",
                  lambda e: "%" + e.group(1) + e.group(2)
                  + ("," + e.group(3) if e.group(3) else ""), metin)


def yabanci_harfleri_at(metin):
    if not metin:
        return metin
    temiz = YABANCI.sub("", yuzde_turkce(latex_temizle(metin)))
    temiz = re.sub(r"[ \t]{2,}", " ", temiz)
    return re.sub(r" +([,.;:!?])", r"\1", temiz)
