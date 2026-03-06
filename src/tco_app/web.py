from __future__ import annotations

import os

from flask import Flask, render_template_string, request

from .calculator import compare, ev_kwh_per_year
from .defaults import (
    DEFAULT_ACQUISITION_MODE,
    DEFAULT_ANNUAL_KM,
    DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH,
    DEFAULT_BASE_FEE_EUR_PER_MONTH,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_EV_CONSUMPTION_KWH_PER_100KM,
    DEFAULT_EV_HOME_LOSS_PERCENT,
    DEFAULT_EV_HOME_SHARE,
    DEFAULT_EV_HPC_PRICE_EUR_PER_KWH,
    DEFAULT_EV_INSURANCE_PER_YEAR,
    DEFAULT_EV_LEASE_DOWN_PAYMENT,
    DEFAULT_EV_LEASE_MONTHLY_RATE,
    DEFAULT_EV_MAINTENANCE_PER_YEAR,
    DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH,
    DEFAULT_EV_PURCHASE_PRICE,
    DEFAULT_EV_RESIDUAL_PERCENT,
    DEFAULT_EV_TAX_PER_YEAR,
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
    web_default_form,
)
from .models import (
    EVInputs,
    ElectricityPriceSettings,
    GeneralInputs,
    ICEInputs,
)
from .pricing import build_price_snapshot

app = Flask(__name__)


def _format_de_number(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter("de_num")
def de_num_filter(value, decimals: int = 0) -> str:
    try:
        return _format_de_number(float(value), int(decimals))
    except (TypeError, ValueError):
        return str(value)


TEMPLATE = """
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Elektro vs Verbrenner Gesamtkosten</title>
  <style>
    :root {
      --bg: #f4f2ec;
      --card: #ffffff;
      --ink: #21252b;
      --muted: #5d6470;
      --accent: #0a7f5a;
      --accent2: #c46b29;
      --border: #d8d2c6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 10%, #ebe4d7 0%, transparent 35%),
        radial-gradient(circle at 90% 80%, #dcebe2 0%, transparent 30%),
        var(--bg);
    }
    .container {
      max-width: 1080px;
      margin: 24px auto;
      padding: 0 16px 24px;
    }
    h1 {
      font-family: "Bebas Neue", "Arial Narrow", sans-serif;
      letter-spacing: 0.03em;
      margin: 0 0 16px;
      font-size: 42px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      margin-bottom: 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.05);
      animation: fadeIn .35s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    label {
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    input, select {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 9px 10px;
      font-size: 14px;
      background: #fff;
      color: var(--ink);
    }
    button {
      border: 0;
      border-radius: 10px;
      background: linear-gradient(90deg, var(--accent), #14a674);
      color: white;
      padding: 11px 16px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }
    .kpi {
      border: 1px dashed var(--border);
      border-radius: 12px;
      padding: 10px;
      background: #fff;
    }
    .kpi .k {
      color: var(--muted);
      font-size: 12px;
    }
    .kpi .v {
      font-weight: 700;
      font-size: 18px;
      margin-top: 4px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      text-align: right;
      border-bottom: 1px solid #ece7dc;
      padding: 6px;
    }
    th:first-child, td:first-child { text-align: left; }
    .hint { color: var(--muted); font-size: 12px; }
    .pill {
      display: inline-block;
      font-size: 12px;
      border-radius: 999px;
      padding: 2px 8px;
      background: #f0f7f3;
      color: var(--accent);
      border: 1px solid #c8e5d7;
    }
    .hidden {
      display: none;
    }
    @media (max-width: 700px) {
      h1 { font-size: 34px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Elektro vs Verbrenner Gesamtkosten Rechner</h1>
    <div class="card">
      <form method="post">
        <div class="grid">
          <div><label>Jahre</label><input name="years" type="number" step="1" value="{{ form.years }}"></div>
          <div><label>km/Jahr</label><input name="annual_km" type="number" step="100" value="{{ form.annual_km }}"></div>
          <div><label>Kaufen/Leasen</label>
            <select name="acquisition_mode" id="acquisition_mode">
              <option value="buy" {% if form.acquisition_mode == 'buy' %}selected{% endif %}>Kaufen</option>
              <option value="lease" {% if form.acquisition_mode == 'lease' %}selected{% endif %}>Leasen</option>
            </select>
          </div>
          <div><label>Manueller Strompreis (EUR/kWh)</label><input name="manual_home_price" type="number" step="0.001" value="{{ form.manual_home_price }}"></div>
          <div><label>Spritpreis manuell (EUR/l)</label><input name="manual_fuel_price" type="number" step="0.001" value="{{ form.manual_fuel_price }}" required></div>
        </div>

        <h3>Elektro</h3>
        <div class="grid">
          <div class="buy-only" {% if form.acquisition_mode == 'lease' %}style="display:none"{% endif %}><label>Elektro Kaufpreis</label><input name="ev_purchase_price" type="number" step="100" value="{{ form.ev_purchase_price }}"></div>
          <div class="lease-only" {% if form.acquisition_mode != 'lease' %}style="display:none"{% endif %}><label>Elektro Leasingrate/Monat (EUR)</label><input name="ev_lease_monthly_rate" type="number" step="1" value="{{ form.ev_lease_monthly_rate }}"></div>
          <div class="lease-only" {% if form.acquisition_mode != 'lease' %}style="display:none"{% endif %}><label>Elektro Sonderzahlung (EUR)</label><input name="ev_lease_down_payment" type="number" step="100" value="{{ form.ev_lease_down_payment }}"></div>
          <div><label>Verbrauch (kWh/100km)</label><input name="ev_consumption_kwh" type="number" step="0.1" value="{{ form.ev_consumption_kwh }}"></div>
          <div><label>Wartung/Jahr</label><input name="ev_maintenance_year" type="number" step="10" value="{{ form.ev_maintenance_year }}"></div>
          <div><label>Versicherung/Jahr</label><input name="ev_insurance_year" type="number" step="10" value="{{ form.ev_insurance_year }}"></div>
          <div><label>Steuer/Jahr</label><input name="ev_tax_year" type="number" step="10" value="{{ form.ev_tax_year }}"></div>
          <div class="buy-only" {% if form.acquisition_mode == 'lease' %}style="display:none"{% endif %}><label>Restwert (%)</label><input name="ev_residual_percent" type="number" step="1" value="{{ form.ev_residual_percent }}"></div>
        </div>
        <h3>Verbrenner</h3>
        <div class="grid">
          <div class="buy-only" {% if form.acquisition_mode == 'lease' %}style="display:none"{% endif %}><label>Verbrenner Kaufpreis</label><input name="ice_purchase_price" type="number" step="100" value="{{ form.ice_purchase_price }}"></div>
          <div class="lease-only" {% if form.acquisition_mode != 'lease' %}style="display:none"{% endif %}><label>Verbrenner Leasingrate/Monat (EUR)</label><input name="ice_lease_monthly_rate" type="number" step="1" value="{{ form.ice_lease_monthly_rate }}"></div>
          <div class="lease-only" {% if form.acquisition_mode != 'lease' %}style="display:none"{% endif %}><label>Verbrenner Sonderzahlung (EUR)</label><input name="ice_lease_down_payment" type="number" step="100" value="{{ form.ice_lease_down_payment }}"></div>
          <div><label>Verbrauch (l/100km)</label><input name="ice_consumption_l" type="number" step="0.1" value="{{ form.ice_consumption_l }}"></div>
          <div><label>Wartung/Jahr</label><input name="ice_maintenance_year" type="number" step="10" value="{{ form.ice_maintenance_year }}"></div>
          <div><label>Versicherung/Jahr</label><input name="ice_insurance_year" type="number" step="10" value="{{ form.ice_insurance_year }}"></div>
          <div><label>Steuer/Jahr</label><input name="ice_tax_year" type="number" step="10" value="{{ form.ice_tax_year }}"></div>
          <div class="buy-only" {% if form.acquisition_mode == 'lease' %}style="display:none"{% endif %}><label>Restwert (%)</label><input name="ice_residual_percent" type="number" step="1" value="{{ form.ice_residual_percent }}"></div>
        </div>

        <div style="margin-top:12px"><button type="submit">Berechnen</button></div>
      </form>
    </div>

    {% if error %}
      <div class="card" style="border-color:#e3b0a8;background:#fff6f4;color:#9c2e1f">{{ error }}</div>
    {% endif %}

    {% if result %}
      <div class="card">
        <span class="pill">{{ result.prices.electricity_source }}</span>
        <span class="pill">{{ result.prices.fuel_source }}</span>
        <h3>Zusammenfassung</h3>
        <div class="summary">
          <div class="kpi"><div class="k">Gesamtkosten Elektro</div><div class="v">{{ ev_total|de_num(0) }} EUR</div></div>
          <div class="kpi"><div class="k">Gesamtkosten Verbrenner</div><div class="v">{{ ice_total|de_num(0) }} EUR</div></div>
          <div class="kpi"><div class="k">Kosten/km Elektro</div><div class="v">{{ result.ev.cost_per_km|de_num(3) }} EUR</div></div>
          <div class="kpi"><div class="k">Kosten/km Verbrenner</div><div class="v">{{ result.ice.cost_per_km|de_num(3) }} EUR</div></div>
        </div>
        <p><b>Empfehlung:</b> {{ result.recommendation }}</p>
      </div>

      <div class="card">
        <h3>Sensitivitaet</h3>
        <table>
          <thead><tr><th>Szenario</th><th>Elektro</th><th>Verbrenner</th><th>Delta (Elektro-Verbrenner)</th></tr></thead>
          <tbody>
          {% for s in result.sensitivity %}
            <tr>
              <td>{{ s.scenario }}</td>
              <td>{{ s.ev_total|de_num(0) }}</td>
              <td>{{ s.ice_total|de_num(0) }}</td>
              <td>{{ s.delta_ev_minus_ice|de_num(0) }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>

    {% endif %}
  </div>
  <script>
    (function () {
      function toggleLeaseFields() {
        var modeSelect = document.getElementById("acquisition_mode");
        if (!modeSelect) return;
        var isLease = modeSelect.value === "lease";
        var leaseFields = document.querySelectorAll(".lease-only");
        leaseFields.forEach(function (el) {
          el.style.display = isLease ? "" : "none";
          el.querySelectorAll("input, select, textarea").forEach(function (input) {
            input.disabled = !isLease;
          });
        });
        var buyFields = document.querySelectorAll(".buy-only");
        buyFields.forEach(function (el) {
          el.style.display = isLease ? "none" : "";
          el.querySelectorAll("input, select, textarea").forEach(function (input) {
            input.disabled = isLease;
          });
        });
      }

      document.addEventListener("DOMContentLoaded", function () {
        var modeSelect = document.getElementById("acquisition_mode");
        if (modeSelect) {
          modeSelect.addEventListener("change", toggleLeaseFields);
        }
        toggleLeaseFields();
      });
    })();
  </script>
</body>
</html>
"""


DEFAULT_FORM = web_default_form()


def _parse_float(
    raw: str,
    *,
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{label} muss eine Zahl sein.") from exc
    if min_value is not None and value < min_value:
        raise ValueError(f"{label} muss >= {min_value} sein.")
    if max_value is not None and value > max_value:
        raise ValueError(f"{label} muss <= {max_value} sein.")
    return value


def _required_float(
    data: dict[str, str],
    key: str,
    *,
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    raw = (data.get(key) or "").strip()
    if raw == "":
        raise ValueError(f"{label} ist erforderlich.")
    return _parse_float(raw, label=label, min_value=min_value, max_value=max_value)


def _optional_float(
    data: dict[str, str],
    key: str,
    *,
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
    default: float | None = None,
) -> float | None:
    raw = (data.get(key) or "").strip()
    if raw == "":
        return default
    return _parse_float(raw, label=label, min_value=min_value, max_value=max_value)


def _optional_int(
    data: dict[str, str],
    key: str,
    *,
    label: str,
    min_value: int | None = None,
    max_value: int | None = None,
    default: int,
) -> int:
    raw = (data.get(key) or "").strip()
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label} muss eine ganze Zahl sein.") from exc
    if min_value is not None and value < min_value:
        raise ValueError(f"{label} muss >= {min_value} sein.")
    if max_value is not None and value > max_value:
        raise ValueError(f"{label} muss <= {max_value} sein.")
    return value


def _build_and_run(form_data: dict[str, str]):
    acquisition_mode = (form_data.get("acquisition_mode") or DEFAULT_ACQUISITION_MODE).strip().lower()
    if acquisition_mode not in {"buy", "lease"}:
        raise ValueError("Kaufen/Leasen muss 'buy' oder 'lease' sein.")

    years = _optional_int(
        form_data,
        "years",
        label="Jahre",
        min_value=1,
        max_value=30,
        default=DEFAULT_YEARS,
    )
    annual_km = _required_float(
        form_data,
        "annual_km",
        label="km/Jahr",
        min_value=0,
        max_value=300000,
    )
    manual_fuel_price = _required_float(
        form_data,
        "manual_fuel_price",
        label="Spritpreis manuell",
        min_value=0.5,
        max_value=5.0,
    )
    manual_home_price = _optional_float(
        form_data,
        "manual_home_price",
        label="Manueller Strompreis",
        min_value=0.0,
        max_value=5.0,
        default=None,
    )

    ev_purchase_price = _optional_float(
        form_data,
        "ev_purchase_price",
        label="Elektro Kaufpreis",
        min_value=0.0,
        max_value=300000.0,
        default=DEFAULT_EV_PURCHASE_PRICE,
    ) or DEFAULT_EV_PURCHASE_PRICE
    ice_purchase_price = _optional_float(
        form_data,
        "ice_purchase_price",
        label="Verbrenner Kaufpreis",
        min_value=0.0,
        max_value=300000.0,
        default=DEFAULT_ICE_PURCHASE_PRICE,
    ) or DEFAULT_ICE_PURCHASE_PRICE
    if acquisition_mode == "lease":
        ev_purchase_price = 0.0
        ice_purchase_price = 0.0

    ev_lease_monthly_rate = _optional_float(
        form_data,
        "ev_lease_monthly_rate",
        label="Elektro Leasingrate/Monat",
        min_value=0.0,
        max_value=20000.0,
        default=DEFAULT_EV_LEASE_MONTHLY_RATE,
    ) or 0.0
    ev_lease_down_payment = _optional_float(
        form_data,
        "ev_lease_down_payment",
        label="Elektro Sonderzahlung",
        min_value=0.0,
        max_value=200000.0,
        default=DEFAULT_EV_LEASE_DOWN_PAYMENT,
    ) or 0.0
    ev_consumption = _required_float(
        form_data,
        "ev_consumption_kwh",
        label="Elektro Verbrauch",
        min_value=5.0,
        max_value=60.0,
    )
    ev_maintenance = _optional_float(
        form_data,
        "ev_maintenance_year",
        label="Elektro Wartung/Jahr",
        min_value=0.0,
        max_value=50000.0,
        default=DEFAULT_EV_MAINTENANCE_PER_YEAR,
    ) or 0.0
    ev_insurance = _optional_float(
        form_data,
        "ev_insurance_year",
        label="Elektro Versicherung/Jahr",
        min_value=0.0,
        max_value=50000.0,
        default=DEFAULT_EV_INSURANCE_PER_YEAR,
    ) or 0.0
    ev_tax = _optional_float(
        form_data,
        "ev_tax_year",
        label="Elektro Steuer/Jahr",
        min_value=0.0,
        max_value=5000.0,
        default=DEFAULT_EV_TAX_PER_YEAR,
    ) or 0.0
    ev_residual = _optional_float(
        form_data,
        "ev_residual_percent",
        label="Elektro Restwert (%)",
        min_value=0.0,
        max_value=100.0,
        default=DEFAULT_EV_RESIDUAL_PERCENT,
    )

    ice_lease_monthly_rate = _optional_float(
        form_data,
        "ice_lease_monthly_rate",
        label="Verbrenner Leasingrate/Monat",
        min_value=0.0,
        max_value=20000.0,
        default=DEFAULT_ICE_LEASE_MONTHLY_RATE,
    ) or 0.0
    ice_lease_down_payment = _optional_float(
        form_data,
        "ice_lease_down_payment",
        label="Verbrenner Sonderzahlung",
        min_value=0.0,
        max_value=200000.0,
        default=DEFAULT_ICE_LEASE_DOWN_PAYMENT,
    ) or 0.0
    ice_consumption = _required_float(
        form_data,
        "ice_consumption_l",
        label="Verbrenner Verbrauch",
        min_value=2.0,
        max_value=40.0,
    )
    ice_maintenance = _optional_float(
        form_data,
        "ice_maintenance_year",
        label="Verbrenner Wartung/Jahr",
        min_value=0.0,
        max_value=50000.0,
        default=DEFAULT_ICE_MAINTENANCE_PER_YEAR,
    ) or 0.0
    ice_insurance = _optional_float(
        form_data,
        "ice_insurance_year",
        label="Verbrenner Versicherung/Jahr",
        min_value=0.0,
        max_value=50000.0,
        default=DEFAULT_ICE_INSURANCE_PER_YEAR,
    ) or 0.0
    ice_tax = _optional_float(
        form_data,
        "ice_tax_year",
        label="Verbrenner Steuer/Jahr",
        min_value=0.0,
        max_value=5000.0,
        default=DEFAULT_ICE_TAX_PER_YEAR,
    ) or 0.0
    ice_residual = _optional_float(
        form_data,
        "ice_residual_percent",
        label="Verbrenner Restwert (%)",
        min_value=0.0,
        max_value=100.0,
        default=DEFAULT_ICE_RESIDUAL_PERCENT,
    )

    general = GeneralInputs(
        years=years,
        annual_km=annual_km,
        discount_rate=0.0,
        other_fixed_costs_per_year=0.0,
        tire_costs_per_year=0.0,
        financing=None,
    )

    ev = EVInputs(
        purchase_price=ev_purchase_price,
        consumption_kwh_per_100km=ev_consumption,
        acquisition_mode=acquisition_mode,
        lease_monthly_rate=ev_lease_monthly_rate,
        lease_down_payment=ev_lease_down_payment,
        home_loss_percent=DEFAULT_EV_HOME_LOSS_PERCENT,
        home_price_manual_eur_per_kwh=manual_home_price,
        public_price_eur_per_kwh=DEFAULT_EV_PUBLIC_PRICE_EUR_PER_KWH,
        hpc_price_eur_per_kwh=DEFAULT_EV_HPC_PRICE_EUR_PER_KWH,
        maintenance_per_year=ev_maintenance,
        insurance_per_year=ev_insurance,
        tax_per_year=ev_tax,
        residual_value_percent=ev_residual,
        residual_value_absolute=None,
    )

    ice = ICEInputs(
        purchase_price=ice_purchase_price,
        consumption_l_per_100km=ice_consumption,
        acquisition_mode=acquisition_mode,
        lease_monthly_rate=ice_lease_monthly_rate,
        lease_down_payment=ice_lease_down_payment,
        maintenance_per_year=ice_maintenance,
        insurance_per_year=ice_insurance,
        tax_per_year=ice_tax,
        residual_value_percent=ice_residual,
        residual_value_absolute=None,
    )

    electricity_settings = ElectricityPriceSettings(
        mode="manual" if manual_home_price is not None else "awattar_model",
        awattar_markup_eur_per_kwh=DEFAULT_AWATTAR_MARKUP_EUR_PER_KWH,
        base_fee_eur_per_month=DEFAULT_BASE_FEE_EUR_PER_MONTH,
        cache_ttl_seconds=DEFAULT_CACHE_TTL_SECONDS,
    )

    annual_home_kwh = (
        ev_kwh_per_year(general.annual_km, ev.consumption_kwh_per_100km)
        * (1.0 + ev.home_loss_percent / 100.0)
        * DEFAULT_EV_HOME_SHARE
    )

    prices = build_price_snapshot(
        annual_home_kwh=annual_home_kwh,
        electricity_settings=electricity_settings,
        manual_fuel_price_eur_per_l=manual_fuel_price,
        manual_home_price_eur_per_kwh=manual_home_price,
        use_mock_data=False,
    )

    return compare(general=general, ev_inputs=ev, ice_inputs=ice, prices=prices)


@app.route("/", methods=["GET", "POST"])
def index():
    form = dict(DEFAULT_FORM)
    result = None
    error = None

    if request.method == "POST":
        for key in DEFAULT_FORM.keys():
            form[key] = request.form.get(key, DEFAULT_FORM[key])
        try:
            result = _build_and_run(form)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

    ev_total = None
    ice_total = None
    if result is not None:
        if result.general.discount_rate > 0:
            ev_total = result.ev.total_discounted_cost
            ice_total = result.ice.total_discounted_cost
        else:
            ev_total = result.ev.total_cost
            ice_total = result.ice.total_cost

    return render_template_string(
        TEMPLATE,
        form=form,
        result=result,
        error=error,
        ev_total=ev_total,
        ice_total=ice_total,
    )


@app.route("/healthz", methods=["GET"])
def healthz():
    return {"status": "ok"}, 200


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    try:
        port = int(os.getenv("PORT", "8080"))
    except ValueError:
        port = 8080
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
