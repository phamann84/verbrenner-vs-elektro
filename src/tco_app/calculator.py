from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from .defaults import (
    DEFAULT_EV_HOME_SHARE,
    DEFAULT_EV_HPC_SHARE,
    DEFAULT_EV_PUBLIC_SHARE,
)
from .finance import annual_loan_cashflows
from .models import (
    ComparisonResult,
    EVInputs,
    GeneralInputs,
    ICEInputs,
    PriceSnapshot,
    SensitivityScenarioResult,
    VehicleResult,
    YearlyCostRow,
)

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")
TWELVE = Decimal("12")


def _d(value: float | int | str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _fmt_de(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ice_liters_per_year(annual_km: float, consumption_l_per_100km: float) -> float:
    return annual_km * (consumption_l_per_100km / 100.0)


def ev_kwh_per_year(annual_km: float, consumption_kwh_per_100km: float) -> float:
    return annual_km * (consumption_kwh_per_100km / 100.0)


def compute_ice_energy_cost_per_year(
    annual_km: float,
    consumption_l_per_100km: float,
    fuel_price_eur_per_l: float,
) -> float:
    liters = _d(annual_km) * (_d(consumption_l_per_100km) / HUNDRED)
    return float(liters * _d(fuel_price_eur_per_l))


def compute_ev_energy_cost_per_year(
    annual_km: float,
    consumption_kwh_per_100km: float,
    home_loss_percent: float,
    home_price_eur_per_kwh: float,
    public_price_eur_per_kwh: float,
    hpc_price_eur_per_kwh: float,
) -> float:
    kwh = _d(annual_km) * (_d(consumption_kwh_per_100km) / HUNDRED)
    kwh_effective = kwh * (ONE + (_d(home_loss_percent) / HUNDRED))
    weighted_price = (
        _d(DEFAULT_EV_HOME_SHARE) * _d(home_price_eur_per_kwh)
        + _d(DEFAULT_EV_PUBLIC_SHARE) * _d(public_price_eur_per_kwh)
        + _d(DEFAULT_EV_HPC_SHARE) * _d(hpc_price_eur_per_kwh)
    )
    return float(kwh_effective * weighted_price)


def _resolve_residual_value(
    net_purchase_price: float,
    residual_value_percent: float | None,
    residual_value_absolute: float | None,
    residual_multiplier: float,
) -> float:
    if residual_value_absolute is not None:
        base = _d(residual_value_absolute)
    elif residual_value_percent is not None:
        base = _d(net_purchase_price) * (_d(residual_value_percent) / HUNDRED)
    else:
        base = ZERO
    return float(max(ZERO, base * _d(residual_multiplier)))


def _vehicle_cashflow_rows(
    *,
    name: str,
    years: int,
    discount_rate: float,
    annual_energy_cost: float,
    annual_fixed_cost: float,
    acquisition_mode: str,
    net_purchase_price: float,
    residual_value: float,
    financing: tuple[float, float, int] | None,
    lease_monthly_rate: float,
    lease_down_payment: float,
) -> VehicleResult:
    financing_yearly = [ZERO for _ in range(years)]
    acquisition_yearly = [ZERO for _ in range(years)]
    remaining_balance = ZERO
    effective_residual = _d(residual_value)
    annual_energy_cost_dec = _d(annual_energy_cost)
    annual_fixed_cost_dec = _d(annual_fixed_cost)
    discount_rate_dec = _d(discount_rate)

    if acquisition_mode == "lease":
        acquisition_yearly[0] = _d(lease_down_payment)
        financing_yearly = [_d(lease_monthly_rate) * TWELVE for _ in range(years)]
        effective_residual = ZERO
    else:
        if financing is None:
            acquisition_yearly[0] = _d(net_purchase_price)
        else:
            annual_interest_rate, down_payment_pct, term_years = financing
            down_payment = _d(net_purchase_price) * _d(down_payment_pct)
            loan_principal = max(ZERO, _d(net_purchase_price) - down_payment)
            schedule = annual_loan_cashflows(
                principal=float(loan_principal),
                annual_interest_rate=annual_interest_rate,
                term_years=term_years,
                horizon_years=years,
            )
            acquisition_yearly[0] = down_payment
            financing_yearly = [_d(payment) for payment in schedule.annual_payments]
            remaining_balance = _d(schedule.remaining_balance_at_horizon)
            if remaining_balance > ZERO:
                financing_yearly[-1] += remaining_balance

    rows: list[YearlyCostRow] = []
    cum = ZERO
    cum_discounted = ZERO

    for year in range(1, years + 1):
        acquisition_cost = acquisition_yearly[year - 1]
        financing_cost = financing_yearly[year - 1]
        residual_credit = effective_residual if year == years else ZERO

        total = (
            annual_energy_cost_dec
            + annual_fixed_cost_dec
            + financing_cost
            + acquisition_cost
            - residual_credit
        )
        discount_factor = (ONE + discount_rate_dec) ** (year - 1)
        discounted_total = total / discount_factor

        cum += total
        cum_discounted += discounted_total

        rows.append(
            YearlyCostRow(
                year=year,
                energy_cost=float(annual_energy_cost_dec),
                fixed_cost=float(annual_fixed_cost_dec),
                financing_cost=float(financing_cost),
                acquisition_cost=float(acquisition_cost),
                residual_credit=float(residual_credit),
                total_cost=float(total),
                discounted_total_cost=float(discounted_total),
                cumulative_cost=float(cum),
                cumulative_discounted_cost=float(cum_discounted),
            )
        )

    total = float(cum)
    total_discounted = float(cum_discounted)
    components = {
        "Energie": float(annual_energy_cost_dec * _d(years)),
        "Fixkosten": float(annual_fixed_cost_dec * _d(years)),
        "Finanzierung": float(sum(financing_yearly, ZERO)),
        "Anschaffung": float(sum(acquisition_yearly, ZERO)),
        "Restwert": float(effective_residual),
        "Restschuld": float(remaining_balance),
    }

    return VehicleResult(
        name=name,
        yearly_rows=rows,
        total_cost=total,
        total_discounted_cost=total_discounted,
        cost_per_km=0.0,
        components_total=components,
    )


def _cost_drivers(ev: VehicleResult, ice: VehicleResult) -> list[tuple[str, float]]:
    ev_effective = {
        "Anschaffung": ev.components_total["Anschaffung"],
        "Energie": ev.components_total["Energie"],
        "Fixkosten": ev.components_total["Fixkosten"],
        "Finanzierung": ev.components_total["Finanzierung"],
        "Restwert": -ev.components_total["Restwert"],
    }
    ice_effective = {
        "Anschaffung": ice.components_total["Anschaffung"],
        "Energie": ice.components_total["Energie"],
        "Fixkosten": ice.components_total["Fixkosten"],
        "Finanzierung": ice.components_total["Finanzierung"],
        "Restwert": -ice.components_total["Restwert"],
    }

    deltas = {
        key: ev_effective[key] - ice_effective[key]
        for key in ev_effective.keys()
    }

    return sorted(deltas.items(), key=lambda item: abs(item[1]), reverse=True)[:3]


def _recommendation(
    general: GeneralInputs,
    ev: VehicleResult,
    ice: VehicleResult,
) -> str:
    use_discounted = general.discount_rate > 0
    ev_total = ev.total_discounted_cost if use_discounted else ev.total_cost
    ice_total = ice.total_discounted_cost if use_discounted else ice.total_cost

    if ev_total < ice_total:
        saving = ice_total - ev_total
        return (
            f"Empfehlung: Elektro ist ueber {general.years} Jahre voraussichtlich guenstiger "
            f"(Vorteil ca. {_fmt_de(saving, 0)} EUR)."
        )

    extra = ev_total - ice_total
    return (
        f"Empfehlung: Verbrenner ist ueber {general.years} Jahre derzeit guenstiger "
        f"(Vorteil ca. {_fmt_de(extra, 0)} EUR)."
    )


def _evaluate_once(
    *,
    general: GeneralInputs,
    ev_inputs: EVInputs,
    ice_inputs: ICEInputs,
    prices: PriceSnapshot,
    ev_energy_multiplier: float,
    ice_energy_multiplier: float,
    km_multiplier: float,
    residual_multiplier: float,
) -> tuple[VehicleResult, VehicleResult]:
    effective_annual_km = general.annual_km * km_multiplier

    ev_energy = compute_ev_energy_cost_per_year(
        annual_km=effective_annual_km,
        consumption_kwh_per_100km=ev_inputs.consumption_kwh_per_100km,
        home_loss_percent=ev_inputs.home_loss_percent,
        home_price_eur_per_kwh=prices.home_price_eur_per_kwh * ev_energy_multiplier,
        public_price_eur_per_kwh=ev_inputs.public_price_eur_per_kwh * ev_energy_multiplier,
        hpc_price_eur_per_kwh=ev_inputs.hpc_price_eur_per_kwh * ev_energy_multiplier,
    )

    ice_energy = compute_ice_energy_cost_per_year(
        annual_km=effective_annual_km,
        consumption_l_per_100km=ice_inputs.consumption_l_per_100km,
        fuel_price_eur_per_l=prices.fuel_price_eur_per_l * ice_energy_multiplier,
    )

    ev_fixed = (
        ev_inputs.maintenance_per_year
        + ev_inputs.insurance_per_year
        + ev_inputs.tax_per_year
        + general.tire_costs_per_year
        + general.other_fixed_costs_per_year
    )
    ice_fixed = (
        ice_inputs.maintenance_per_year
        + ice_inputs.insurance_per_year
        + ice_inputs.tax_per_year
        + general.tire_costs_per_year
        + general.other_fixed_costs_per_year
    )

    ev_net_purchase = max(0.0, ev_inputs.purchase_price)
    ice_net_purchase = max(0.0, ice_inputs.purchase_price)

    ev_residual = 0.0
    if ev_inputs.acquisition_mode == "buy":
        ev_residual = _resolve_residual_value(
            net_purchase_price=ev_net_purchase,
            residual_value_percent=ev_inputs.residual_value_percent,
            residual_value_absolute=ev_inputs.residual_value_absolute,
            residual_multiplier=residual_multiplier,
        )

    ice_residual = 0.0
    if ice_inputs.acquisition_mode == "buy":
        ice_residual = _resolve_residual_value(
            net_purchase_price=ice_net_purchase,
            residual_value_percent=ice_inputs.residual_value_percent,
            residual_value_absolute=ice_inputs.residual_value_absolute,
            residual_multiplier=residual_multiplier,
        )

    financing_tuple: tuple[float, float, int] | None = None
    if general.financing is not None:
        financing_tuple = (
            general.financing.annual_interest_rate,
            general.financing.down_payment_pct,
            general.financing.term_years,
        )

    ev_result = _vehicle_cashflow_rows(
        name="Elektro",
        years=general.years,
        discount_rate=general.discount_rate,
        annual_energy_cost=ev_energy,
        annual_fixed_cost=ev_fixed,
        acquisition_mode=ev_inputs.acquisition_mode,
        net_purchase_price=ev_net_purchase,
        residual_value=ev_residual,
        financing=financing_tuple,
        lease_monthly_rate=ev_inputs.lease_monthly_rate,
        lease_down_payment=ev_inputs.lease_down_payment,
    )
    ice_result = _vehicle_cashflow_rows(
        name="Verbrenner",
        years=general.years,
        discount_rate=general.discount_rate,
        annual_energy_cost=ice_energy,
        annual_fixed_cost=ice_fixed,
        acquisition_mode=ice_inputs.acquisition_mode,
        net_purchase_price=ice_net_purchase,
        residual_value=ice_residual,
        financing=financing_tuple,
        lease_monthly_rate=ice_inputs.lease_monthly_rate,
        lease_down_payment=ice_inputs.lease_down_payment,
    )

    total_km = _d(effective_annual_km) * _d(general.years)
    if total_km > ZERO:
        ev_result.cost_per_km = float(_d(ev_result.total_cost) / total_km)
        ice_result.cost_per_km = float(_d(ice_result.total_cost) / total_km)
    else:
        ev_result.cost_per_km = 0.0
        ice_result.cost_per_km = 0.0

    return ev_result, ice_result


def run_sensitivity(
    *,
    general: GeneralInputs,
    ev_inputs: EVInputs,
    ice_inputs: ICEInputs,
    prices: PriceSnapshot,
) -> list[SensitivityScenarioResult]:
    scenarios = [
        ("Strom-Preis +20%", 1.2, 1.0, 1.0),
        ("Strom-Preis -20%", 0.8, 1.0, 1.0),
        ("Sprit-Preis +20%", 1.0, 1.2, 1.0),
        ("Sprit-Preis -20%", 1.0, 0.8, 1.0),
        ("km/Jahr +20%", 1.0, 1.0, 1.2),
        ("km/Jahr -20%", 1.0, 1.0, 0.8),
    ]

    results: list[SensitivityScenarioResult] = []
    for label, ev_energy_multiplier, ice_energy_multiplier, km_multiplier in scenarios:
        ev_res, ice_res = _evaluate_once(
            general=general,
            ev_inputs=ev_inputs,
            ice_inputs=ice_inputs,
            prices=prices,
            ev_energy_multiplier=ev_energy_multiplier,
            ice_energy_multiplier=ice_energy_multiplier,
            km_multiplier=km_multiplier,
            residual_multiplier=1.0,
        )

        base_ev_total = (
            ev_res.total_discounted_cost
            if general.discount_rate > 0
            else ev_res.total_cost
        )
        base_ice_total = (
            ice_res.total_discounted_cost
            if general.discount_rate > 0
            else ice_res.total_cost
        )

        results.append(
            SensitivityScenarioResult(
                scenario=label,
                ev_total=base_ev_total,
                ice_total=base_ice_total,
                delta_ev_minus_ice=base_ev_total - base_ice_total,
            )
        )

    return results


def compare(
    *,
    general: GeneralInputs,
    ev_inputs: EVInputs,
    ice_inputs: ICEInputs,
    prices: PriceSnapshot,
) -> ComparisonResult:
    ev_inputs.validate()
    ice_inputs.validate()

    ev_result, ice_result = _evaluate_once(
        general=general,
        ev_inputs=ev_inputs,
        ice_inputs=ice_inputs,
        prices=prices,
        ev_energy_multiplier=1.0,
        ice_energy_multiplier=1.0,
        km_multiplier=1.0,
        residual_multiplier=1.0,
    )

    sensitivity = run_sensitivity(
        general=general,
        ev_inputs=ev_inputs,
        ice_inputs=ice_inputs,
        prices=prices,
    )

    recommendation = _recommendation(
        general=general,
        ev=ev_result,
        ice=ice_result,
    )
    top_cost_drivers = _cost_drivers(ev_result, ice_result)

    return ComparisonResult(
        general=replace(general),
        ev=ev_result,
        ice=ice_result,
        prices=prices,
        recommendation=recommendation,
        top_cost_drivers=top_cost_drivers,
        sensitivity=sensitivity,
    )
