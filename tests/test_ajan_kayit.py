import pytest

from ulgen import ajan_kayit


def test_sar_basarili_kayit_tutar():
    ajan_kayit.sifirla()
    f = ajan_kayit.sar("sabah", lambda: "Günaydın rapor")
    assert f() == "Günaydın rapor"
    k = [x for x in ajan_kayit.liste() if x["id"] == "sabah"][0]
    assert k["durum"] == "bosta" and k["sayac"] == 1
    assert "Günaydın" in k["ozet"] and k["son_calisma"]


def test_sar_hata_kaydeder_ve_firlatir():
    ajan_kayit.sifirla()

    def kotu():
        raise ValueError("bozuk")
    f = ajan_kayit.sar("saglik", kotu)
    with pytest.raises(ValueError):
        f()
    k = [x for x in ajan_kayit.liste() if x["id"] == "saglik"][0]
    assert k["durum"] == "hata" and "bozuk" in k["hata"]


def test_liste_tum_ajanlari_icerir():
    ajan_kayit.sifirla()
    assert {x["id"] for x in ajan_kayit.liste()} == {"arastirma", "saglik", "dosya", "sabah", "kitap"}
