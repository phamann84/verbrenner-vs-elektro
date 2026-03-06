from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any

from .api_clients import ApiUnavailableError, AwattarClient
from .cache import JsonTTLCache
from .models import ElectricityPriceSettings, PriceSnapshot


def _d(value: float | int | str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def eur_per_mwh_to_eur_per_kwh(value_eur_per_mwh: float) -> float:
    return float(_d(value_eur_per_mwh) / _d(1000))


def _default_cache_dir() -> Path:
    env = os.getenv("TCO_CACHE_DIR")
    if env:
        return Path(env)
    return Path(".cache") / "tco"


def build_price_snapshot(
    *,
    annual_home_kwh: float,
    electricity_settings: ElectricityPriceSettings,
    manual_fuel_price_eur_per_l: float | None,
    manual_home_price_eur_per_kwh: float | None,
    use_mock_data: bool,
) -> PriceSnapshot:
    cache = JsonTTLCache(_default_cache_dir(), default_ttl_seconds=1200)

    fuel_price, fuel_source, fuel_meta = _resolve_fuel_price(
        manual_fuel_price_eur_per_l=manual_fuel_price_eur_per_l,
    )

    home_price, awattar_next24h, awattar_last7d, electricity_source, elec_meta = (
        _resolve_home_price(
            cache=cache,
            annual_home_kwh=annual_home_kwh,
            settings=electricity_settings,
            manual_home_price_eur_per_kwh=manual_home_price_eur_per_kwh,
            use_mock_data=use_mock_data,
        )
    )

    metadata: dict[str, Any] = {
        "fuel": fuel_meta,
        "electricity": elec_meta,
    }

    return PriceSnapshot(
        fuel_price_eur_per_l=fuel_price,
        home_price_eur_per_kwh=home_price,
        awattar_avg_next24h_eur_per_kwh=awattar_next24h,
        awattar_avg_last7d_eur_per_kwh=awattar_last7d,
        fuel_source=fuel_source,
        electricity_source=electricity_source,
        metadata=metadata,
    )


def _resolve_fuel_price(
    *,
    manual_fuel_price_eur_per_l: float | None,
) -> tuple[float, str, dict[str, Any]]:
    if manual_fuel_price_eur_per_l is not None:
        return (
            manual_fuel_price_eur_per_l,
            "Manuell",
            {"mode": "manual"},
        )
    raise ValueError(
        "Bitte Spritpreis manuell angeben (EUR/l). Automatische Spritpreis-API ist deaktiviert."
    )


def _resolve_home_price(
    *,
    cache: JsonTTLCache,
    annual_home_kwh: float,
    settings: ElectricityPriceSettings,
    manual_home_price_eur_per_kwh: float | None,
    use_mock_data: bool,
) -> tuple[float, float | None, float | None, str, dict[str, Any]]:
    if settings.mode == "manual":
        if manual_home_price_eur_per_kwh is not None:
            return (
                manual_home_price_eur_per_kwh,
                None,
                None,
                "Manuell",
                {"mode": "manual"},
            )
        if use_mock_data:
            return 0.32, None, None, "Mock", {"mode": "mock"}
        raise ValueError(
            "Strommodus 'manual' gesetzt, aber kein manueller Heimpreis angegeben."
        )
    if use_mock_data:
        market = 0.11
        base_fee_component = 0.0
        if settings.base_fee_eur_per_month > 0 and annual_home_kwh > 0:
            base_fee_component = float(
                (_d(settings.base_fee_eur_per_month) * _d(12)) / _d(annual_home_kwh)
            )
        modeled = float(
            _d(market)
            + _d(settings.awattar_markup_eur_per_kwh)
            + _d(base_fee_component)
        )
        return (
            modeled,
            market,
            0.109,
            "Mock",
            {
                "mode": "mock",
                "forced": True,
                "markup_eur_per_kwh": settings.awattar_markup_eur_per_kwh,
                "base_fee_component_eur_per_kwh": round(base_fee_component, 5),
            },
        )

    client = AwattarClient(cache=cache)
    try:
        next24h, next24h_meta = client.get_average_next24h_eur_per_kwh(
            ttl_seconds=settings.cache_ttl_seconds
        )
        last7d, last7d_meta = client.get_average_last7d_eur_per_kwh(
            ttl_seconds=settings.cache_ttl_seconds
        )

        base_fee_component = 0.0
        if settings.base_fee_eur_per_month > 0 and annual_home_kwh > 0:
            base_fee_component = float(
                (_d(settings.base_fee_eur_per_month) * _d(12)) / _d(annual_home_kwh)
            )

        modeled = float(
            _d(next24h)
            + _d(settings.awattar_markup_eur_per_kwh)
            + _d(base_fee_component)
        )
        meta = {
            "mode": "awattar_model",
            "next24h": next24h_meta.details,
            "last7d": last7d_meta.details,
            "markup_eur_per_kwh": settings.awattar_markup_eur_per_kwh,
            "base_fee_component_eur_per_kwh": round(base_fee_component, 5),
        }
        source = f"aWATTar-Boersenpreis + Modell ({next24h_meta.cache_status})"
        return modeled, next24h, last7d, source, meta
    except ApiUnavailableError as exc:
        if manual_home_price_eur_per_kwh is not None:
            return (
                manual_home_price_eur_per_kwh,
                None,
                None,
                "Manuell (Fallback)",
                {"mode": "manual_fallback", "warning": str(exc)},
            )
        if use_mock_data:
            market = 0.11
            modeled = float(_d(market) + _d(settings.awattar_markup_eur_per_kwh))
            return (
                modeled,
                market,
                0.109,
                "Mock",
                {
                    "mode": "mock",
                    "warning": str(exc),
                    "markup_eur_per_kwh": settings.awattar_markup_eur_per_kwh,
                },
            )
        raise
