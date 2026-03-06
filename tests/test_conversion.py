from tco_app.pricing import eur_per_mwh_to_eur_per_kwh


def test_eur_per_mwh_to_eur_per_kwh():
    assert eur_per_mwh_to_eur_per_kwh(120.0) == 0.12
    assert eur_per_mwh_to_eur_per_kwh(0.0) == 0.0
