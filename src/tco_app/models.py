from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .defaults import (
    DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH,
    DEFAULT_BASE_FEE_EUR_PER_MONTH,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_EV_HOME_LOSS_PERCENT,
    DEFAULT_EV_HPC_PRICE_EUR_PER_KWH,
    DEFAULT_EV_INSURANCE_PER_YEAR,
    DEFAULT_EV_MAINTENANCE_PER_YEAR,
    DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH,
    DEFAULT_EV_RESIDUAL_PERCENT,
    DEFAULT_EV_TAX_PER_YEAR,
    DEFAULT_ICE_INSURANCE_PER_YEAR,
    DEFAULT_ICE_MAINTENANCE_PER_YEAR,
    DEFAULT_ICE_RESIDUAL_PERCENT,
    DEFAULT_ICE_TAX_PER_YEAR,
)

ElectricityMode = Literal["awattar_model", "manual"]
AcquisitionMode = Literal["buy", "lease"]


@dataclass
class ElectricityPriceSettings:
    mode: ElectricityMode = "awattar_model"
    awattar_markup_eur_per_kwh: float = DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH
    base_fee_eur_per_month: float = DEFAULT_BASE_FEE_EUR_PER_MONTH
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS


@dataclass
class FinancingSettings:
    annual_interest_rate: float
    down_payment_pct: float
    term_years: int


@dataclass
class GeneralInputs:
    years: int
    annual_km: float
    discount_rate: float = 0.0
    other_fixed_costs_per_year: float = 0.0
    tire_costs_per_year: float = 0.0
    financing: FinancingSettings | None = None


@dataclass
class EVInputs:
    purchase_price: float
    consumption_kwh_per_100km: float
    acquisition_mode: AcquisitionMode = "buy"
    lease_monthly_rate: float = 0.0
    lease_down_payment: float = 0.0
    home_loss_percent: float = DEFAULT_EV_HOME_LOSS_PERCENT
    home_price_manual_eur_per_kwh: float | None = None
    public_price_eur_per_kwh: float = DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH
    hpc_price_eur_per_kwh: float = DEFAULT_EV_HPC_PRICE_EUR_PER_KWH
    maintenance_per_year: float = DEFAULT_EV_MAINTENANCE_PER_YEAR
    insurance_per_year: float = DEFAULT_EV_INSURANCE_PER_YEAR
    tax_per_year: float = DEFAULT_EV_TAX_PER_YEAR
    residual_value_percent: float | None = DEFAULT_EV_RESIDUAL_PERCENT
    residual_value_absolute: float | None = None

    def validate(self) -> None:
        if self.acquisition_mode not in {"buy", "lease"}:
            raise ValueError("Elektro acquisition_mode muss 'buy' oder 'lease' sein.")
        if self.lease_monthly_rate < 0 or self.lease_down_payment < 0:
            raise ValueError("Elektro-Leasingwerte duerfen nicht negativ sein.")


@dataclass
class ICEInputs:
    purchase_price: float
    consumption_l_per_100km: float
    acquisition_mode: AcquisitionMode = "buy"
    lease_monthly_rate: float = 0.0
    lease_down_payment: float = 0.0
    maintenance_per_year: float = DEFAULT_ICE_MAINTENANCE_PER_YEAR
    insurance_per_year: float = DEFAULT_ICE_INSURANCE_PER_YEAR
    tax_per_year: float = DEFAULT_ICE_TAX_PER_YEAR
    residual_value_percent: float | None = DEFAULT_ICE_RESIDUAL_PERCENT
    residual_value_absolute: float | None = None

    def validate(self) -> None:
        if self.acquisition_mode not in {"buy", "lease"}:
            raise ValueError("Verbrenner acquisition_mode muss 'buy' oder 'lease' sein.")
        if self.lease_monthly_rate < 0 or self.lease_down_payment < 0:
            raise ValueError("Verbrenner-Leasingwerte duerfen nicht negativ sein.")


@dataclass
class PriceSnapshot:
    fuel_price_eur_per_l: float
    home_price_eur_per_kwh: float
    awattar_avg_next24h_eur_per_kwh: float | None = None
    awattar_avg_last7d_eur_per_kwh: float | None = None
    fuel_source: str = ""
    electricity_source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class YearlyCostRow:
    year: int
    energy_cost: float
    fixed_cost: float
    financing_cost: float
    acquisition_cost: float
    residual_credit: float
    total_cost: float
    discounted_total_cost: float
    cumulative_cost: float
    cumulative_discounted_cost: float


@dataclass
class VehicleResult:
    name: str
    yearly_rows: list[YearlyCostRow]
    total_cost: float
    total_discounted_cost: float
    cost_per_km: float
    components_total: dict[str, float]


@dataclass
class SensitivityScenarioResult:
    scenario: str
    ev_total: float
    ice_total: float
    delta_ev_minus_ice: float


@dataclass
class ComparisonResult:
    general: GeneralInputs
    ev: VehicleResult
    ice: VehicleResult
    prices: PriceSnapshot
    recommendation: str
    top_cost_drivers: list[tuple[str, float]]
    sensitivity: list[SensitivityScenarioResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
