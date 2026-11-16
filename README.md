# Weather Dashboard CLI

A command-line weather dashboard that fetches **live weather data for any city** from a public REST API and presents it in a clean, readable format — with proper handling for invalid cities, timeouts, and failed requests.

> Elevvo Internship — Python Programming & AI Track · **Task 5: Weather Dashboard Using a Public REST API** (Module 6: APIs & Applied Testing)

## What it does

Type a city name and get its current weather: condition, temperature (and what it feels like), humidity, pressure, and wind — in metric or imperial units.

The tool supports two public providers:

| Provider | When it's used | Key needed? |
|---|---|---|
| **OpenWeatherMap** | Whenever `OPENWEATHER_API_KEY` is set | Yes — free key |
| **Open-Meteo** | Automatic fallback when no key is set | No |

## Features

- Live data from a public REST API (`requests`), parsed from JSON into a typed `WeatherReport` dataclass
- API key handled the safe way: environment variable loaded from a local `.env` file with **python-dotenv** — never hard-coded, never committed
- Specific, friendly error handling for every failure mode in the brief:
  - **Invalid city** → "City … was not found. Check the spelling and try again."
  - **Timeout** → dedicated `WeatherTimeoutError` with the timeout value
  - **Failed request / bad key / server error** → dedicated exception types, clean message, non-zero exit code
- Clean, aligned CLI dashboard output
- **Bonus:** a full pytest suite with **mocked API responses** (no test touches the network)

## Tech stack

- Python 3.10+
- `requests` — HTTP calls
- `python-dotenv` — loading the API key from `.env`
- `pytest` + `unittest.mock` — tests with mocked responses

## Setup

```bash
git clone https://github.com/MaryammMalik/weather-dashboard-cli.git
cd weather-dashboard-cli
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Optional: add an OpenWeatherMap key

The dashboard works with **no setup at all** (via Open-Meteo). To use OpenWeatherMap instead:

1. Get a free key at [openweathermap.org/api](https://openweathermap.org/api)
2. Copy `.env.example` to `.env` and paste your key:

```bash
cp .env.example .env
# OPENWEATHER_API_KEY=your_openweathermap_api_key_here
```

## How to run

```bash
python -m weather "Faisalabad"
python -m weather "New York" --units imperial
python -m weather "London" --timeout 5
```

## Example output

Real output from a live run:

```text
====================================================
  Weather Dashboard — Faisalabad, PK
====================================================
  Condition     : Clear sky
  Temperature   : 17.0 °C (feels like 15.9 °C)
  Humidity      : 65 %
  Pressure      : 1013 hPa
  Wind          : 2.3 m/s
  Source        : Open-Meteo
====================================================
```

An invalid city fails gracefully (exit code 1, no traceback):

```text
$ python -m weather "Notarealcity123"
Error: City 'Notarealcity123' was not found. Check the spelling and try again.
```

## How to run the tests

```bash
pip install -r requirements-dev.txt
pytest
```

All 12 tests mock the HTTP layer (success, 404 invalid city, 401 bad key, timeout, connection error, server error, and CLI behaviour), so the suite passes offline in under a second.

## Project structure

```text
weather-dashboard-cli/
├── weather/
│   ├── client.py    # API client for both providers; translates every failure
│   ├── models.py    # WeatherReport dataclass
│   ├── errors.py    # WeatherAPIError hierarchy
│   └── cli.py       # Argument parsing and dashboard formatting
├── tests/
│   └── test_client.py
├── .env.example
└── requirements.txt
```

## What I learned

- How REST APIs communicate through HTTP status codes, and why each failure mode (404, 401, 500, timeout) deserves its own handling instead of one generic "error".
- Why secrets belong in environment variables and `.env` files — and why `.env` itself must stay out of Git.
- How mocking (`unittest.mock`) makes API code testable: fast, deterministic tests that never depend on a live network.
- Normalising two different providers' JSON into one internal data model, so the display code never cares where the data came from.
