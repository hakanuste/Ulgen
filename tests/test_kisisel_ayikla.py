from ulgen import guvenlik
from ulgen.araclar import KISISEL_ARACLAR


def test_duyarli_satir_atilir_gerisi_kalir():
    metin = ("Taş ev ölçüsü: 8 x 12 metre, duvar 50 cm\n"
             "Tansiyon ilacımı sabah alıyorum\n"
             "Çatı eğimi yüzde 30")
    sonuc = guvenlik.kisisel_ayikla(metin)
    assert "8 x 12" in sonuc and "Çatı eğimi" in sonuc
    assert "ilac" not in sonuc.lower() and "Tansiyon" not in sonuc


def test_kimlik_numaralari_ortulur():
    metin = ("Bana hakan@ornek.com ya da 0532 123 45 67 adresinden ulaşın, "
             "TC 12345678901, kart 1234 5678 9012 3456, "
             "TR12 0001 0002 0003 0004 0005 06")
    sonuc = guvenlik.kisisel_ayikla(metin)
    for gizli in ("hakan@ornek.com", "0532 123 45 67", "12345678901",
                  "1234 5678 9012 3456", "0004 0005"):
        assert gizli not in sonuc
    assert "[gizli]" in sonuc


def test_olculer_ortulmez():
    metin = "Temel 60 cm, duvar 4.5 m, 2025 Eylül, BIST 11842,83"
    assert guvenlik.kisisel_ayikla(metin) == metin


def test_kasa_ara_bulutta_ayiklanarak_calisir():
    assert "kasa_ara" not in KISISEL_ARACLAR
    assert "hafiza_ara" in KISISEL_ARACLAR


def test_kasa_alintilari_bulutta_ayiklar(monkeypatch):
    from ulgen import baglam
    monkeypatch.setattr(baglam, "_kasa_alintilari",
                        lambda m, s: "Ölçü 8x12\nŞifre: abc123")
    assert baglam.kasa_alintilari("x", bulut=True) == "Ölçü 8x12"
    assert "Şifre" in baglam.kasa_alintilari("x", bulut=False)
