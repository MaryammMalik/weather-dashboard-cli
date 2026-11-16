"""Weather API client.

Two public REST providers are supported:

* **OpenWeatherMap** — used whenever an ``OPENWEATHER_API_KEY`` is
  available (loaded from the environment, ideally via a ``.env`` file and
  python-dotenv, as the task brief recommends).
* **Open-Meteo** — a free public API that needs no key. It is used as the
  fallback so the dashboard still works out of the box.

Every failure mode the brief calls out — invalid city, timeout, and failed
requests — is converted into a specific :class:`WeatherAPIError` subclass
so the CLI can present a clean, friendly message.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from .errors import (
    CityNotFoundError,
    WeatherAPIError,
    WeatherAuthenticationError,
    WeatherServiceError,
    WeatherTimeoutError,
)
from .models import WeatherReport

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_TIMEOUT = 10  # seconds

# WMO weather codes used by Open-Meteo, mapped to readable descriptions.
WMO_DESCRIPTIONS: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


class WeatherClient:
    """Fetch current weather for a city from a public REST API.

    Args:
        api_key: OpenWeatherMap API key. When ``None`` the value is read
            from the ``OPENWEATHER_API_KEY`` environment variable; when no
            key is available at all, the keyless Open-Meteo API is used.
        timeout: Per-request timeout in seconds.
        session: Optional ``requests`` session (handy for testing).
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
        self.api_key = api_key or None
        self.timeout = timeout
        self.session = session or requests.Session()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_weather(self, city: str, units: str = "metric") -> WeatherReport:
        """Return the current weather for ``city``.

        Args:
            city: City name, e.g. ``"Faisalabad"`` or ``"London"``.
            units: ``"metric"`` (°C, m/s) or ``"imperial"`` (°F, mph).

        Raises:
            CityNotFoundError: If the city cannot be found.
            WeatherTimeoutError: If a request times out.
            WeatherAuthenticationError: If the API key is rejected.
            WeatherServiceError: For any other request failure.
            ValueError: If ``city`` is empty or ``units`` is invalid.
        """
        city = city.strip()
        if not city:
            raise ValueError("City name must not be empty.")
        if units not in ("metric", "imperial"):
            raise ValueError("Units must be 'metric' or 'imperial'.")

        if self.api_key:
            return self._from_openweather(city, units)
        return self._from_open_meteo(city, units)

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------
    def _from_openweather(self, city: str, units: str) -> WeatherReport:
        """Fetch and normalise an OpenWeatherMap response."""
        params = {"q": city, "appid": self.api_key, "units": units}
        data = self._get_json(OPENWEATHER_URL, params, provider="OpenWeatherMap")
        try:
            main = data["main"]
            weather = data["weather"][0]
            return WeatherReport(
                city=str(data.get("name", city)),
                country=str(data.get("sys", {}).get("country", "")),
                description=str(weather.get("description", "")).capitalize(),
                temperature=float(main["temp"]),
                feels_like=float(main["feels_like"]),
                humidity=int(main["humidity"]),
                pressure=int(main["pressure"]),
                wind_speed=float(data.get("wind", {}).get("speed", 0.0)),
                units=units,
                source="OpenWeatherMap",
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise WeatherServiceError(
                "OpenWeatherMap returned an unexpected response format."
            ) from exc

    def _from_open_meteo(self, city: str, units: str) -> WeatherReport:
        """Fetch and normalise an Open-Meteo response (no key needed)."""
        geo = self._get_json(
            GEOCODING_URL,
            {"name": city, "count": 1, "language": "en", "format": "json"},
            provider="Open-Meteo",
        )
        results = geo.get("results") or []
        if not results:
            raise CityNotFoundError(
                f"City '{city}' was not found. Check the spelling and try again."
            )
        place = results[0]

        temperature_unit = "celsius" if units == "metric" else "fahrenheit"
        wind_unit = "ms" if units == "metric" else "mph"
        forecast = self._get_json(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "weather_code,pressure_msl,wind_speed_10m"
                ),
                "temperature_unit": temperature_unit,
                "wind_speed_unit": wind_unit,
            },
            provider="Open-Meteo",
        )
        try:
            current = forecast["current"]
            code = int(current["weather_code"])
            return WeatherReport(
                city=str(place.get("name", city)),
                country=str(place.get("country_code", "")).upper(),
                description=WMO_DESCRIPTIONS.get(code, "unknown").capitalize(),
                temperature=float(current["temperature_2m"]),
                feels_like=float(current["apparent_temperature"]),
                humidity=int(current["relative_humidity_2m"]),
                pressure=int(round(float(current["pressure_msl"]))),
                wind_speed=float(current["wind_speed_10m"]),
                units=units,
                source="Open-Meteo",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WeatherServiceError(
                "Open-Meteo returned an unexpected response format."
            ) from exc

    # ------------------------------------------------------------------
    # HTTP helper — one place where every failure mode is translated
    # ------------------------------------------------------------------
    def _get_json(
        self, url: str, params: dict[str, Any], provider: str
    ) -> dict[str, Any]:
        """GET ``url`` and return the decoded JSON body.

        Raises:
            CityNotFoundError: On HTTP 404.
            WeatherAuthenticationError: On HTTP 401/403.
            WeatherTimeoutError: On a request timeout.
            WeatherServiceError: On any other failure.
        """
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise WeatherTimeoutError(
                f"The request to {provider} timed out after "
                f"{self.timeout} seconds. Please try again."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise WeatherServiceError(
                f"Could not reach {provider}: {exc}"
            ) from exc

        if response.status_code == 404:
            raise CityNotFoundError(
                "The requested city was not found. "
                "Check the spelling and try again."
            )
        if response.status_code in (401, 403):
            raise WeatherAuthenticationError(
                f"{provider} rejected the API key. Check that "
                "OPENWEATHER_API_KEY is set correctly in your .env file."
            )
        if response.status_code != 200:
            raise WeatherServiceError(
                f"{provider} request failed with status "
                f"{response.status_code}."
            )

        try:
            return response.json()
        except ValueError as exc:
            raise WeatherServiceError(
                f"{provider} returned a response that was not valid JSON."
            ) from exc


def load_api_key() -> str | None:
    """Load ``OPENWEATHER_API_KEY`` from a local ``.env`` file, if present.

    Uses python-dotenv when it is installed; silently continues with the
    plain environment otherwise (the brief allows either approach).
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return os.environ.get("OPENWEATHER_API_KEY", "").strip() or None
