from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import ComparisonResult, VehicleResult


def _fmt_eur(value: float) -> str:
    return f"{value:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_num(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _vehicle_yearly_table(vehicle: VehicleResult, discounted: bool) -> str:
    lines = [
        f"\n{vehicle.name} - Jahresuebersicht",
        "Jahr | Energie | Fixkosten | Finanzierung/Leasing | Anschaffung | Restwert | Jahr Summe | Kumuliert",
        "-----|---------|-----------|-------------|-------------|----------|------------|----------",
    ]

    for row in vehicle.yearly_rows:
        year_sum = row.discounted_total_cost if discounted else row.total_cost
        cumulative = (
            row.cumulative_discounted_cost if discounted else row.cumulative_cost
        )
        lines.append(
            " | ".join(
                [
                    str(row.year),
                    _fmt_eur(row.energy_cost),
                    _fmt_eur(row.fixed_cost),
                    _fmt_eur(row.financing_cost),
                    _fmt_eur(row.acquisition_cost),
                    _fmt_eur(row.residual_credit),
                    _fmt_eur(year_sum),
                    _fmt_eur(cumulative),
                ]
            )
        )

    return "\n".join(lines)


def render_cli_report(result: ComparisonResult) -> str:
    discounted = result.general.discount_rate > 0
    ev_total = result.ev.total_discounted_cost if discounted else result.ev.total_cost
    ice_total = result.ice.total_discounted_cost if discounted else result.ice.total_cost

    lines = [
        "=== Elektro vs Verbrenner TCO Vergleich ===",
        f"Zeitraum: {result.general.years} Jahre | Fahrleistung: {_fmt_num(result.general.annual_km)} km/Jahr",
        f"Spritpreis ({result.ice.name}): {_fmt_num(result.prices.fuel_price_eur_per_l)} EUR/l [{result.prices.fuel_source}]",
        (
            "Heimstrompreis (Elektro): "
            f"{_fmt_num(result.prices.home_price_eur_per_kwh)} EUR/kWh [{result.prices.electricity_source}]"
        ),
    ]

    if result.prices.awattar_avg_next24h_eur_per_kwh is not None:
        lines.append(
            "aWATTar Avg naechste 24h: "
            f"{_fmt_num(result.prices.awattar_avg_next24h_eur_per_kwh)} EUR/kWh"
        )
    if result.prices.awattar_avg_last7d_eur_per_kwh is not None:
        lines.append(
            "aWATTar Avg letzte 7 Tage: "
            f"{_fmt_num(result.prices.awattar_avg_last7d_eur_per_kwh)} EUR/kWh"
        )

    lines.extend(
        [
            "",
            f"Gesamtkosten Elektro: {_fmt_eur(ev_total)}",
            f"Gesamtkosten Verbrenner: {_fmt_eur(ice_total)}",
            f"Kosten pro km Elektro: {_fmt_num(result.ev.cost_per_km)} EUR/km",
            f"Kosten pro km Verbrenner: {_fmt_num(result.ice.cost_per_km)} EUR/km",
        ]
    )

    lines.append("\nTop 3 Kostentreiber (Delta Elektro minus Verbrenner):")
    for label, delta in result.top_cost_drivers:
        sign = "+" if delta >= 0 else "-"
        lines.append(f"- {label}: {sign}{_fmt_eur(abs(delta))}")

    lines.append("\nSensitivitaetsanalyse:")
    lines.append("Szenario | Elektro total | Verbrenner total | Delta (Elektro-Verbrenner)")
    lines.append("---------|----------|-----------|----------------")
    for s in result.sensitivity:
        lines.append(
            " | ".join(
                [
                    s.scenario,
                    _fmt_eur(s.ev_total),
                    _fmt_eur(s.ice_total),
                    _fmt_eur(s.delta_ev_minus_ice),
                ]
            )
        )

    lines.append("")
    lines.append(result.recommendation)

    lines.append(_vehicle_yearly_table(result.ev, discounted=discounted))
    lines.append(_vehicle_yearly_table(result.ice, discounted=discounted))

    return "\n".join(lines)


def save_json(result: ComparisonResult, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def save_csv(result: ComparisonResult, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "fahrzeug",
                "jahr",
                "energy_cost",
                "fixed_cost",
                "financing_cost",
                "acquisition_cost",
                "residual_credit",
                "total_cost",
                "discounted_total_cost",
                "cumulative_cost",
                "cumulative_discounted_cost",
            ]
        )

        for vehicle in [result.ev, result.ice]:
            for row in vehicle.yearly_rows:
                writer.writerow(
                    [
                        vehicle.name,
                        row.year,
                        f"{row.energy_cost:.6f}",
                        f"{row.fixed_cost:.6f}",
                        f"{row.financing_cost:.6f}",
                        f"{row.acquisition_cost:.6f}",
                        f"{row.residual_credit:.6f}",
                        f"{row.total_cost:.6f}",
                        f"{row.discounted_total_cost:.6f}",
                        f"{row.cumulative_cost:.6f}",
                        f"{row.cumulative_discounted_cost:.6f}",
                    ]
                )
