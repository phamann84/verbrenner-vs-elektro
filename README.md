# Elektro vs Verbrenner Gesamtkosten (CLI + Web)

## Architekturentscheidung (CLI-first)
Die Anwendung ist **CLI-first** aufgebaut: Kernlogik und API-Anbindung liegen in wiederverwendbaren Python-Modulen (`calculator`, `pricing`, `api_clients`).
Darauf setzen zwei dünne Frontends auf:
- CLI (`tco-cli`) fuer reproduzierbare Szenarien und Exporte (JSON/CSV)
- Web-UI (`tco-web`) als schnelle interaktive Eingabemaske

So bleibt die TCO-Berechnung an einer Stelle und Ergebnisse sind zwischen CLI und Web konsistent.

## Features
- TCO-Vergleich Elektro vs Verbrenner fuer frei waehlbaren Zeitraum (z.B. 3/5/8 Jahre)
- Anschaffungsswitch **Kaufen vs Leasen** (global fuer beide Fahrzeuge)
- Ausgabe von:
  - Gesamtkosten
  - Kosten pro km
  - Sensitivitaetsanalyse (Energiepreise, km/Jahr)
  - kurze Empfehlung
- API-Integration:
  - aWATTar Marketdata fuer Strom-Boersenpreis
- Spritpreis immer manuell als Feld (EUR/l)
- Transparente Preisquelle:
  - Boersenpreis + Modell (`Aufschlag + optionale Grundgebuehr/kWh`)
  - oder manueller Heimtarif
- Robustheit:
  - TTL-Cache (10-30 Minuten, konfigurierbar)
  - Retry bei API-Fehlern/Rate-Limits
  - Fallback auf stale Cache oder manuelle Werte
- Exporte nach JSON und CSV

## Projektstruktur
```text
.
├── .github/workflows/ci.yml
├── .dockerignore
├── Dockerfile
├── Procfile
├── pyproject.toml
├── README.md
├── render.yaml
├── requirements.txt
├── src
│   └── tco_app
│       ├── __init__.py
│       ├── api_clients.py
│       ├── cache.py
│       ├── calculator.py
│       ├── cli.py
│       ├── finance.py
│       ├── models.py
│       ├── pricing.py
│       ├── reporting.py
│       ├── web.py
│       └── wsgi.py
└── tests
    ├── test_global_acquisition.py
    ├── test_leasing.py
    ├── test_conversion.py
    └── test_energy.py
```

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[test]'
```

Optionales Cache-Verzeichnis:
```bash
export TCO_CACHE_DIR=".cache/tco"
```

## CLI Verwendung
### Schneller Lauf mit Mock-Daten
```bash
tco-cli --years 5 --annual-km 18000 --use-mock-data
```

### Lauf mit manuellem Spritpreis + aWATTar Modellstrom
```bash
tco-cli \
  --years 8 \
  --annual-km 20000 \
  --manual-fuel-price 1.86 \
  --base-fee-monthly 8 \
  --output-json outputs/result.json \
  --output-csv outputs/result.csv
```

### Manuelle Fallback-Preise
```bash
tco-cli \
  --years 5 \
  --annual-km 15000 \
  --manual-fuel-price 1.82 \
  --manual-home-price 0.31
```

### Leasing-Szenario (global: beide leasen)
```bash
tco-cli \
  --years 4 \
  --annual-km 15000 \
  --use-mock-data \
  --acquisition-mode lease \
  --ev-lease-monthly-rate 499 \
  --ev-lease-down-payment 2000 \
  --ice-lease-monthly-rate 399 \
  --ice-lease-down-payment 1500
```

### Interaktiver Wizard
```bash
tco-cli --wizard --use-mock-data
```

## Web-UI
```bash
tco-web
```
Dann im Browser oeffnen: [http://127.0.0.1:8080](http://127.0.0.1:8080)

## Statische GitHub Pages UI
- Datei: `docs/index.html`
- Oeffentliche URL (nach Aktivierung): [https://phamann84.github.io/verbrenner-vs-elektro/](https://phamann84.github.io/verbrenner-vs-elektro/)

Optional (expliziter Host/Port):
```bash
HOST=127.0.0.1 PORT=8080 tco-web
```

Healthcheck:
```bash
curl http://127.0.0.1:8080/healthz
```

## GitHub + extern erreichbar (Render)
### 1) Git lokal initialisieren (falls noch nicht vorhanden)
```bash
git init
git add .
git commit -m "Initial commit: Elektro vs Verbrenner Rechner"
```

### 2) Repo im Account `phamann84` anlegen und pushen
```bash
gh auth login
gh repo create phamann84/verbrenner-vs-elektro --public --source=. --remote=origin --push
```

### 3) Auf Render deployen
1. Auf [https://render.com](https://render.com) einloggen.
2. `New +` -> `Web Service` -> GitHub Repo `phamann84/verbrenner-vs-elektro` waehlen.
3. Optional: `render.yaml` im Repo direkt uebernehmen (Blueprint Deploy).
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `PYTHONPATH=src gunicorn -w 2 -b 0.0.0.0:$PORT tco_app.wsgi:app`
5. Deploy starten.
6. Nach dem Deploy die Render-URL oeffnen (z.B. `https://verbrenner-vs-elektro.onrender.com`).

## Eingaben (aktuelle Web-UI)
### Allgemein
- `Jahre`
- `km/Jahr`
- `Kaufen/Leasen` (global fuer beide Fahrzeuge)
- `Manueller Strompreis (EUR/kWh)`
- `Spritpreis manuell (EUR/l)`

### Elektro
- Bei `Kaufen`: `Elektro Kaufpreis`, `Restwert (%)`
- Bei `Leasen`: `Elektro Leasingrate/Monat`, `Elektro Sonderzahlung`
- Immer: `Verbrauch (kWh/100km)`, `Wartung/Jahr`, `Versicherung/Jahr`, `Steuer/Jahr`

### Verbrenner
- Bei `Kaufen`: `Verbrenner Kaufpreis`, `Restwert (%)`
- Bei `Leasen`: `Verbrenner Leasingrate/Monat`, `Verbrenner Sonderzahlung`
- Immer: `Verbrauch (l/100km)`, `Wartung/Jahr`, `Versicherung/Jahr`, `Steuer/Jahr`

## Berechnungslogik
### Einheiten
- **aWATTar** liefert `EUR/MWh`
- Umrechnung: `EUR/kWh = (EUR/MWh) / 1000`

### Energiekosten
- Verbrenner:
  - `liter_jahr = km_jahr * (l/100km) / 100`
  - `kosten = liter_jahr * spritpreis`
- Elektro:
  - `kwh_jahr = km_jahr * (kWh/100km) / 100`
  - `kwh_effektiv = kwh_jahr * (1 + ladeverluste)`
  - `kosten = kwh_effektiv * gewichteter_strompreis`

### Gesamtkosten
`Gesamtkosten = Anschaffung - Restwert + Energie + Wartung + Versicherung + Steuer`

Bei Leasing (`acquisition_mode=lease`) gilt:
- Anschaffung = einmalige Sonderzahlung im Jahr 1
- Leasingkosten = Monatsrate * 12 pro Jahr
- Restwertansatz = 0 (kein Eigentum)

## Sensitivitaetsanalyse
Automatisch enthalten:
- Strom-Preis `+20%` und `-20%`
- Sprit-Preis `+20%` und `-20%`
- Jahresfahrleistung `+20%` und `-20%`

## Tests
```bash
PYTHONPATH=src python3 -m pytest
```
Getestet werden:
- Umrechnungen (EUR/MWh -> EUR/kWh)
- Energiekostenformeln (Elektro/Verbrenner)
- Leasingberechnung und globaler Kaufen/Leasen-Switch

## CI
- GitHub Actions Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- Trigger: Push auf `main` und Pull Requests
- Fuehrt `python -m pytest` automatisch aus

## Docker
Build:
```bash
docker build -t ev-ice-tco .
```

Run:
```bash
docker run --rm -p 8080:8080 ev-ice-tco
```

Dann im Browser oeffnen: [http://127.0.0.1:8080](http://127.0.0.1:8080)

## Datenquellen
- aWATTar Marketdata: https://api.awattar.at/v1/marketdata

## Beispielausgabe (Mock)
Nach `tco-cli --years 5 --annual-km 18000 --use-mock-data` erscheint u.a.:
- Gesamtkosten Elektro vs Verbrenner
- Kosten pro km
- Top 3 Kostentreiber
- Sensitivitaetstabelle
- Jahreswertetabelle fuer Elektro und Verbrenner

Beispiel (Auszug):
```text
=== Elektro vs Verbrenner TCO Vergleich ===
Zeitraum: 5 Jahre | Fahrleistung: 18.000,00 km/Jahr
Spritpreis (Verbrenner): 1,82 EUR/l [Manuell]
Heimstrompreis (Elektro): 0,23 EUR/kWh [Mock]

Gesamtkosten Elektro: 37.379,56 EUR
Gesamtkosten Verbrenner: 40.497,00 EUR
Kosten pro km Elektro: 0,42 EUR/km
Kosten pro km Verbrenner: 0,45 EUR/km
```
