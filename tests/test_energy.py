from tco_app.calculator import compute_ev_energy_cost_per_year, compute_ice_energy_cost_per_year


def test_ice_energy_cost_formula():
    # 15.000 km * 6 l/100 km = 900 l, bei 1.80 EUR/l => 1.620 EUR
    cost = compute_ice_energy_cost_per_year(
        annual_km=15000,
        consumption_l_per_100km=6.0,
        fuel_price_eur_per_l=1.8,
    )
    assert round(cost, 2) == 1620.00


def test_ev_energy_cost_formula_with_losses_and_weighted_mix():
    # 15.000 km * 18 kWh/100 = 2.700 kWh
    # +10% Verluste => 2.970 kWh
    # gewichteter Preis: 70%*0.30 + 20%*0.60 + 10%*0.80 = 0.41
    # Kosten => 2.970 * 0.41 = 1.217,70
    cost = compute_ev_energy_cost_per_year(
        annual_km=15000,
        consumption_kwh_per_100km=18.0,
        home_loss_percent=10.0,
        home_price_eur_per_kwh=0.30,
        public_price_eur_per_kwh=0.60,
        hpc_price_eur_per_kwh=0.80,
    )
    assert round(cost, 2) == 1217.70
