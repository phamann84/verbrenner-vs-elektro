from __future__ import annotations

# Gemeinsame Berechnungs- und Preisannahmen
DEFAULT_CACHE_TTL_SECONDS = 1200
DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH = 0.12
DEFAULT_BASE_FEE_EUR_PER_MONTH = 0.0

DEFAULT_EV_HOME_SHARE = 0.7
DEFAULT_EV_PUBLIC_SHARE = 0.2
DEFAULT_EV_HPC_SHARE = 0.1

DEFAULT_EV_HOME_LOSS_PERCENT = 10.0
DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH = 0.59
DEFAULT_EV_HPC_PRICE_EUR_PER_KWH = 0.79

# Einheitliche UI-Defaults (CLI + Web)
DEFAULT_YEARS = 3
DEFAULT_ANNUAL_KM = 10000.0
DEFAULT_ACQUISITION_MODE = "lease"

DEFAULT_MANUAL_HOME_PRICE_EUR_PER_KWH = 0.70
DEFAULT_MANUAL_FUEL_PRICE_EUR_PER_L = 1.82

DEFAULT_EV_PURCHASE_PRICE = 45000.0
DEFAULT_EV_LEASE_MONTHLY_RATE = 700.0
DEFAULT_EV_LEASE_DOWN_PAYMENT = 0.0
DEFAULT_EV_CONSUMPTION_KWH_PER_100KM = 18.0
DEFAULT_EV_MAINTENANCE_PER_YEAR = 350.0
DEFAULT_EV_INSURANCE_PER_YEAR = 1100.0
DEFAULT_EV_TAX_PER_YEAR = 0.0
DEFAULT_EV_RESIDUAL_PERCENT = 45.0

DEFAULT_ICE_PURCHASE_PRICE = 35000.0
DEFAULT_ICE_LEASE_MONTHLY_RATE = 700.0
DEFAULT_ICE_LEASE_DOWN_PAYMENT = 0.0
DEFAULT_ICE_CONSUMPTION_L_PER_100KM = 9.0
DEFAULT_ICE_MAINTENANCE_PER_YEAR = 650.0
DEFAULT_ICE_INSURANCE_PER_YEAR = 1100.0
DEFAULT_ICE_TAX_PER_YEAR = 420.0
DEFAULT_ICE_RESIDUAL_PERCENT = 40.0


def web_default_form() -> dict[str, str]:
    return {
        "years": str(DEFAULT_YEARS),
        "annual_km": str(int(DEFAULT_ANNUAL_KM)),
        "acquisition_mode": DEFAULT_ACQUISITION_MODE,
        "manual_home_price": f"{DEFAULT_MANUAL_HOME_PRICE_EUR_PER_KWH:.2f}",
        "manual_fuel_price": f"{DEFAULT_MANUAL_FUEL_PRICE_EUR_PER_L:.2f}",
        "ev_purchase_price": str(int(DEFAULT_EV_PURCHASE_PRICE)),
        "ev_lease_monthly_rate": str(int(DEFAULT_EV_LEASE_MONTHLY_RATE)),
        "ev_lease_down_payment": str(int(DEFAULT_EV_LEASE_DOWN_PAYMENT)),
        "ev_consumption_kwh": f"{DEFAULT_EV_CONSUMPTION_KWH_PER_100KM:.1f}",
        "ev_maintenance_year": str(int(DEFAULT_EV_MAINTENANCE_PER_YEAR)),
        "ev_insurance_year": str(int(DEFAULT_EV_INSURANCE_PER_YEAR)),
        "ev_tax_year": str(int(DEFAULT_EV_TAX_PER_YEAR)),
        "ev_residual_percent": str(int(DEFAULT_EV_RESIDUAL_PERCENT)),
        "ice_purchase_price": str(int(DEFAULT_ICE_PURCHASE_PRICE)),
        "ice_lease_monthly_rate": str(int(DEFAULT_ICE_LEASE_MONTHLY_RATE)),
        "ice_lease_down_payment": str(int(DEFAULT_ICE_LEASE_DOWN_PAYMENT)),
        "ice_consumption_l": f"{DEFAULT_ICE_CONSUMPTION_L_PER_100KM:.1f}",
        "ice_maintenance_year": str(int(DEFAULT_ICE_MAINTENANCE_PER_YEAR)),
        "ice_insurance_year": str(int(DEFAULT_ICE_INSURANCE_PER_YEAR)),
        "ice_tax_year": str(int(DEFAULT_ICE_TAX_PER_YEAR)),
        "ice_residual_percent": str(int(DEFAULT_ICE_RESIDUAL_PERCENT)),
    }

