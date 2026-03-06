from __future__ import annotations

import argparse
import sys

from .calculator import compare, ev_kwh_per_year
from .defaults import (
    DEFAULT_ACQUISITION_MODE,
    DEFAULT_ANNUAL_KM,
    DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH,
    DEFAULT_BASE_FEE_EUR_PER_MONTH,
    DEFAULT_EV_CONSUMPTION_KWH_PER_100KM,
    DEFAULT_EV_HOME_LOSS_PERCENT,
    DEFAULT_EV_HPC_PRICE_EUR_PER_KWH,
    DEFAULT_EV_HOME_SHARE,
    DEFAULT_EV_INSURANCE_PER_YEAR,
    DEFAULT_EV_LEASE_DOWN_PAYMENT,
    DEFAULT_EV_LEASE_MONTHLY_RATE,
    DEFAULT_EV_MAINTENANCE_PER_YEAR,
    DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH,
    DEFAULT_EV_PURCHASE_PRICE,
    DEFAULT_EV_RESIDUAL_PERCENT,
    DEFAULT_EV_TAX_PER_YEAR,
    DEFAULT_EV_HOME_SHARE,
    DEFAULT_ICE_CONSUMPTION_L_PER_100KM,
    DEFAULT_ICE_INSURANCE_PER_YEAR,
    DEFAULT_ICE_LEASE_DOWN_PAYMENT,
    DEFAULT_ICE_LEASE_MONTHLY_RATE,
    DEFAULT_ICE_MAINTENANCE_PER_YEAR,
    DEFAULT_ICE_PURCHASE_PRICE,
    DEFAULT_ICE_RESIDUAL_PERCENT,
    DEFAULT_ICE_TAX_PER_YEAR,
    DEFAULT_MANUAL_FUEL_PRICE_EUR_PER_L,
    DEFAULT_MANUAL_HOME_PRICE_EUR_PER_KWH,
    DEFAULT_YEARS,
)
from .models import (
    EVInputs,
    ElectricityPriceSettings,
    FinancingSettings,
    GeneralInputs,
    ICEInputs,
)
from .pricing import build_price_snapshot
from .reporting import render_cli_report, save_csv, save_json


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Wert muss >= 0 sein")
    return parsed


def _prompt_float(label: str, default: float) -> float:
    raw = input(f"{label} [{default}]: ").strip()
    if raw == "":
        return default
    return float(raw)


def _prompt_int(label: str, default: int) -> int:
    raw = input(f"{label} [{default}]: ").strip()
    if raw == "":
        return default
    return int(raw)


def _prompt_choice(label: str, default: str, choices: tuple[str, ...]) -> str:
    raw = input(f"{label} [{default}] ({'/'.join(choices)}): ").strip().lower()
    if raw == "":
        return default
    if raw not in choices:
        raise ValueError(f"Ungueltige Auswahl: {raw}")
    return raw


def _wizard_defaults(args: argparse.Namespace) -> argparse.Namespace:
    print("Interaktiver Wizard (Enter = Default)")
    args.years = _prompt_int("Betrachtungsdauer (Jahre)", args.years)
    args.annual_km = _prompt_float("Jahresfahrleistung (km)", args.annual_km)
    args.acquisition_mode = _prompt_choice(
        "Kaufen/Leasen", args.acquisition_mode, ("buy", "lease")
    )
    args.manual_fuel_price = _prompt_float(
        "Spritpreis manuell (EUR/l)", args.manual_fuel_price
    )
    if args.acquisition_mode == "buy":
        args.ev_purchase_price = _prompt_float(
            "Elektro Kaufpreis (EUR)", args.ev_purchase_price
        )
        args.ice_purchase_price = _prompt_float(
            "Verbrenner Kaufpreis (EUR)", args.ice_purchase_price
        )
    args.ev_consumption_kwh = _prompt_float(
        "Elektro Verbrauch (kWh/100km)", args.ev_consumption_kwh
    )
    args.ice_consumption_l = _prompt_float(
        "Verbrenner Verbrauch (l/100km)", args.ice_consumption_l
    )
    return args


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tco-cli",
        description="Gesamtkostenvergleich Elektroauto vs Verbrenner",
    )

    parser.add_argument("--wizard", action="store_true", help="Interaktive Eingabe")

    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--annual-km", type=_positive_float, default=DEFAULT_ANNUAL_KM)
    parser.add_argument("--other-fixed-costs-year", type=_positive_float, default=0.0)
    parser.add_argument("--tire-costs-year", type=_positive_float, default=0.0)
    parser.add_argument(
        "--acquisition-mode",
        choices=["buy", "lease"],
        default=DEFAULT_ACQUISITION_MODE,
        help="Globaler Modus fuer beide Fahrzeuge",
    )

    parser.add_argument(
        "--manual-fuel-price",
        type=float,
        default=DEFAULT_MANUAL_FUEL_PRICE_EUR_PER_L,
        help="Manueller Spritpreis in EUR/l (automatische Spritpreisabfrage ist deaktiviert)",
    )

    parser.add_argument("--manual-home-price", type=float, default=DEFAULT_MANUAL_HOME_PRICE_EUR_PER_KWH)
    parser.add_argument("--base-fee-monthly", type=float, default=DEFAULT_BASE_FEE_EUR_PER_MONTH)

    parser.add_argument("--cache-ttl-minutes", type=int, default=20)
    parser.add_argument("--use-mock-data", action="store_true")

    parser.add_argument("--ev-purchase-price", type=_positive_float, default=DEFAULT_EV_PURCHASE_PRICE)
    parser.add_argument("--ev-lease-monthly-rate", type=_positive_float, default=DEFAULT_EV_LEASE_MONTHLY_RATE)
    parser.add_argument("--ev-lease-down-payment", type=_positive_float, default=DEFAULT_EV_LEASE_DOWN_PAYMENT)
    parser.add_argument("--ev-consumption-kwh", type=_positive_float, default=DEFAULT_EV_CONSUMPTION_KWH_PER_100KM)
    parser.add_argument("--ev-home-loss-percent", type=float, default=DEFAULT_EV_HOME_LOSS_PERCENT)
    parser.add_argument("--ev-public-price", type=_positive_float, default=DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH)
    parser.add_argument("--ev-hpc-price", type=_positive_float, default=DEFAULT_EV_HPC_PRICE_EUR_PER_KWH)
    parser.add_argument("--ev-maintenance-year", type=_positive_float, default=DEFAULT_EV_MAINTENANCE_PER_YEAR)
    parser.add_argument("--ev-insurance-year", type=_positive_float, default=DEFAULT_EV_INSURANCE_PER_YEAR)
    parser.add_argument("--ev-tax-year", type=_positive_float, default=DEFAULT_EV_TAX_PER_YEAR)
    parser.add_argument("--ev-residual-percent", type=float, default=DEFAULT_EV_RESIDUAL_PERCENT)
    parser.add_argument("--ev-residual-absolute", type=float, default=None)

    parser.add_argument("--ice-purchase-price", type=_positive_float, default=DEFAULT_ICE_PURCHASE_PRICE)
    parser.add_argument("--ice-lease-monthly-rate", type=_positive_float, default=DEFAULT_ICE_LEASE_MONTHLY_RATE)
    parser.add_argument("--ice-lease-down-payment", type=_positive_float, default=DEFAULT_ICE_LEASE_DOWN_PAYMENT)
    parser.add_argument("--ice-consumption-l", type=_positive_float, default=DEFAULT_ICE_CONSUMPTION_L_PER_100KM)
    parser.add_argument("--ice-maintenance-year", type=_positive_float, default=DEFAULT_ICE_MAINTENANCE_PER_YEAR)
    parser.add_argument("--ice-insurance-year", type=_positive_float, default=DEFAULT_ICE_INSURANCE_PER_YEAR)
    parser.add_argument("--ice-tax-year", type=_positive_float, default=DEFAULT_ICE_TAX_PER_YEAR)
    parser.add_argument("--ice-residual-percent", type=float, default=DEFAULT_ICE_RESIDUAL_PERCENT)
    parser.add_argument("--ice-residual-absolute", type=float, default=None)

    parser.add_argument(
        "--financing-rate",
        type=float,
        default=None,
        help="Optional in Prozent p.a.",
    )
    parser.add_argument("--financing-down-payment-pct", type=float, default=20.0)
    parser.add_argument("--financing-term-years", type=int, default=5)

    parser.add_argument("--output-json", type=str, default=None)
    parser.add_argument("--output-csv", type=str, default=None)

    args = parser.parse_args(argv)
    if args.wizard:
        args = _wizard_defaults(args)
    return args


def _build_inputs(args: argparse.Namespace) -> tuple[GeneralInputs, EVInputs, ICEInputs, ElectricityPriceSettings]:
    financing = None
    if args.financing_rate is not None:
        financing = FinancingSettings(
            annual_interest_rate=args.financing_rate / 100.0,
            down_payment_pct=args.financing_down_payment_pct / 100.0,
            term_years=args.financing_term_years,
        )

    general = GeneralInputs(
        years=args.years,
        annual_km=args.annual_km,
        discount_rate=0.0,
        other_fixed_costs_per_year=args.other_fixed_costs_year,
        tire_costs_per_year=args.tire_costs_year,
        financing=financing,
    )

    ev_purchase_price = args.ev_purchase_price if args.acquisition_mode == "buy" else 0.0
    ice_purchase_price = args.ice_purchase_price if args.acquisition_mode == "buy" else 0.0

    ev = EVInputs(
        purchase_price=ev_purchase_price,
        consumption_kwh_per_100km=args.ev_consumption_kwh,
        acquisition_mode=args.acquisition_mode,
        lease_monthly_rate=args.ev_lease_monthly_rate,
        lease_down_payment=args.ev_lease_down_payment,
        home_loss_percent=args.ev_home_loss_percent,
        home_price_manual_eur_per_kwh=args.manual_home_price,
        public_price_eur_per_kwh=args.ev_public_price,
        hpc_price_eur_per_kwh=args.ev_hpc_price,
        maintenance_per_year=args.ev_maintenance_year,
        insurance_per_year=args.ev_insurance_year,
        tax_per_year=args.ev_tax_year,
        residual_value_percent=args.ev_residual_percent,
        residual_value_absolute=args.ev_residual_absolute,
    )

    ice = ICEInputs(
        purchase_price=ice_purchase_price,
        consumption_l_per_100km=args.ice_consumption_l,
        acquisition_mode=args.acquisition_mode,
        lease_monthly_rate=args.ice_lease_monthly_rate,
        lease_down_payment=args.ice_lease_down_payment,
        maintenance_per_year=args.ice_maintenance_year,
        insurance_per_year=args.ice_insurance_year,
        tax_per_year=args.ice_tax_year,
        residual_value_percent=args.ice_residual_percent,
        residual_value_absolute=args.ice_residual_absolute,
    )

    ttl_seconds = max(600, min(1800, args.cache_ttl_minutes * 60))

    electricity_settings = ElectricityPriceSettings(
        mode="manual" if args.manual_home_price is not None else "awattar_model",
        awattar_markup_eur_per_kwh=DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH,
        base_fee_eur_per_month=args.base_fee_monthly,
        cache_ttl_seconds=ttl_seconds,
    )

    return general, ev, ice, electricity_settings


def _annual_home_kwh(general: GeneralInputs, ev: EVInputs) -> float:
    total_ev_kwh = ev_kwh_per_year(general.annual_km, ev.consumption_kwh_per_100km)
    kwh_effective = total_ev_kwh * (1.0 + ev.home_loss_percent / 100.0)
    return kwh_effective * DEFAULT_EV_HOME_SHARE


def run(args: argparse.Namespace) -> int:
    general, ev, ice, electricity_settings = _build_inputs(args)
    annual_home_kwh = _annual_home_kwh(general, ev)

    prices = build_price_snapshot(
        annual_home_kwh=annual_home_kwh,
        electricity_settings=electricity_settings,
        manual_fuel_price_eur_per_l=args.manual_fuel_price,
        manual_home_price_eur_per_kwh=args.manual_home_price,
        use_mock_data=args.use_mock_data,
    )

    result = compare(general=general, ev_inputs=ev, ice_inputs=ice, prices=prices)
    print(render_cli_report(result))

    if args.output_json:
        save_json(result, args.output_json)
        print(f"\nJSON gespeichert: {args.output_json}")
    if args.output_csv:
        save_csv(result, args.output_csv)
        print(f"CSV gespeichert: {args.output_csv}")

    return 0


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        code = run(args)
    except Exception as exc:  # noqa: BLE001
        print(f"Fehler: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
