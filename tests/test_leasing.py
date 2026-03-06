from tco_app.calculator import compare
from tco_app.models import EVInputs, GeneralInputs, ICEInputs, PriceSnapshot


def test_leasing_uses_monthly_rate_and_no_residual_credit():
    general = GeneralInputs(years=4, annual_km=12000, discount_rate=0.0)

    ev = EVInputs(
        purchase_price=50000,
        consumption_kwh_per_100km=18.0,
        acquisition_mode="lease",
        lease_monthly_rate=450.0,
        lease_down_payment=2000.0,
        maintenance_per_year=300.0,
        insurance_per_year=800.0,
        tax_per_year=0.0,
    )

    ice = ICEInputs(
        purchase_price=32000,
        consumption_l_per_100km=6.0,
        maintenance_per_year=600.0,
        insurance_per_year=800.0,
        tax_per_year=200.0,
    )

    prices = PriceSnapshot(
        fuel_price_eur_per_l=1.8,
        home_price_eur_per_kwh=0.3,
        fuel_source="test",
        electricity_source="test",
    )

    result = compare(general=general, ev_inputs=ev, ice_inputs=ice, prices=prices)
    ev_rows = result.ev.yearly_rows

    assert ev_rows[0].acquisition_cost == 2000.0
    assert ev_rows[0].financing_cost == 5400.0
    assert ev_rows[1].financing_cost == 5400.0
    assert ev_rows[-1].residual_credit == 0.0
    assert result.ev.components_total["Restwert"] == 0.0
