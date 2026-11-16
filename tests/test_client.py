"""Tests for the weather client and CLI.

Bonus requirement (Task 5): every API response is **mocked**, so the suite
never depends on a live network call — the same ``unittest.mock`` approach
taught in Module 6 (APIs & Applied Testing).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from weather.cli import format_report, main
from weather.client import WeatherClient
from weather.errors import (
    CityNotFoundError,
    WeatherAuthenticationError,
    WeatherServiceError,
    WeatherTimeoutError,
)
from weather.models import WeatherReport

OWM_PAYLOAD = {
    "name": "Faisalabad",
    "sys": {"country": "PK"},
    "weather": [{"description": "clear sky"}],
    "main": {
        "temp": 31.0,
        "feels_like": 32.5,
        "humidity": 40,
        "pressure": 1009,
    },
    "wind": {"speed": 4.2},
}

GEO_PAYLOAD = {
    "results": [
        {
            "name": "Faisalabad",
            "country_code": "pk",
            "latitude": 31.4181,
            "longitude": 73.0791,
        }
    ]
}

FORECAST_PAYLOAD = {
    "current": {
        "temperature_2m": 31.0,
        "apparent_temperature": 32.5,
        "relative_humidity_2m": 40,
        "weather_code": 0,
        "pressure_msl": 1009.0,
        "wind_speed_10m": 4.2,
    }
}


def make_response(status_code: int = 200, payload: dict | None = None) -> Mock:
    """Build a mock ``requests`` response."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response


def make_client(api_key: str | None, *responses: object) -> WeatherClient:
    """Build a client whose session returns the given responses in order."""
    session = Mock()
    session.get.side_effect = list(responses)
    return WeatherClient(api_key=api_key, session=session)


# ----------------------------------------------------------------------
# OpenWeatherMap path
# ----------------------------------------------------------------------
def test_openweather_success() -> None:
    client = make_client("test-key", make_response(200, OWM_PAYLOAD))
    report = client.get_weather("Faisalabad")
    assert report.city == "Faisalabad"
    assert report.country == "PK"
    assert report.temperature == 31.0
    assert report.description == "Clear sky"
    assert report.source == "OpenWeatherMap"


def test_openweather_invalid_city_raises() -> None:
    client = make_client("test-key", make_response(404))
    with pytest.raises(CityNotFoundError):
        client.get_weather("Notarealcity")


def test_openweather_bad_key_raises() -> None:
    client = make_client("bad-key", make_response(401))
    with pytest.raises(WeatherAuthenticationError):
        client.get_weather("Faisalabad")


# ----------------------------------------------------------------------
# Open-Meteo path (no key)
# ----------------------------------------------------------------------
def test_open_meteo_success() -> None:
    client = make_client(
        None,
        make_response(200, GEO_PAYLOAD),
        make_response(200, FORECAST_PAYLOAD),
    )
    report = client.get_weather("Faisalabad")
    assert report.city == "Faisalabad"
    assert report.country == "PK"
    assert report.description == "Clear sky"
    assert report.humidity == 40
    assert report.source == "Open-Meteo"


def test_open_meteo_unknown_city_raises() -> None:
    client = make_client(None, make_response(200, {"results": []}))
    with pytest.raises(CityNotFoundError):
        client.get_weather("Notarealcity")


# ----------------------------------------------------------------------
# Failure modes shared by both providers
# ----------------------------------------------------------------------
def test_timeout_raises() -> None:
    session = Mock()
    session.get.side_effect = requests.exceptions.Timeout("too slow")
    client = WeatherClient(api_key="k", session=session)
    with pytest.raises(WeatherTimeoutError):
        client.get_weather("Faisalabad")


def test_connection_error_raises() -> None:
    session = Mock()
    session.get.side_effect = requests.exceptions.ConnectionError("down")
    client = WeatherClient(api_key="k", session=session)
    with pytest.raises(WeatherServiceError):
        client.get_weather("Faisalabad")


def test_server_error_raises() -> None:
    client = make_client("k", make_response(500))
    with pytest.raises(WeatherServiceError):
        client.get_weather("Faisalabad")


def test_empty_city_rejected() -> None:
    client = make_client("k")
    with pytest.raises(ValueError):
        client.get_weather("   ")


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def test_format_report_is_readable() -> None:
    report = WeatherReport(
        city="Faisalabad",
        country="PK",
        description="Clear sky",
        temperature=31.0,
        feels_like=32.5,
        humidity=40,
        pressure=1009,
        wind_speed=4.2,
        source="Open-Meteo",
    )
    text = format_report(report)
    assert "Faisalabad, PK" in text
    assert "31.0 °C" in text
    assert "Clear sky" in text


def test_cli_success(capsys: pytest.CaptureFixture[str]) -> None:
    report = WeatherReport(
        city="Lahore",
        country="PK",
        description="Sunny",
        temperature=33.0,
        feels_like=34.0,
        humidity=35,
        pressure=1010,
        wind_speed=3.0,
        source="Open-Meteo",
    )
    with patch("weather.cli.WeatherClient") as mock_client:
        mock_client.return_value.get_weather.return_value = report
        assert main(["Lahore"]) == 0
    assert "Lahore, PK" in capsys.readouterr().out


def test_cli_unknown_city_returns_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch("weather.cli.WeatherClient") as mock_client:
        mock_client.return_value.get_weather.side_effect = CityNotFoundError(
            "City 'X' was not found."
        )
        assert main(["X"]) == 1
    assert "not found" in capsys.readouterr().err
