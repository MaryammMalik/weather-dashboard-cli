"""Data model for a single weather report."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WeatherReport:
    """A provider-independent snapshot of current weather for one city.

    Attributes:
        city: Resolved city name returned by the provider.
        country: Two-letter country code, when the provider supplies one.
        description: Human-readable condition, e.g. ``"clear sky"``.
        temperature: Current temperature in the requested unit system.
        feels_like: Apparent temperature in the same unit system.
        humidity: Relative humidity as a percentage (0-100).
        pressure: Atmospheric pressure in hPa.
        wind_speed: Wind speed in m/s (metric) or mph (imperial).
        units: ``"metric"`` or ``"imperial"``.
        source: Name of the provider that produced this report.
    """

    city: str
    country: str
    description: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    units: str = "metric"
    source: str = ""

    @property
    def temperature_unit(self) -> str:
        """Return ``°C`` for metric or ``°F`` for imperial."""
        return "°C" if self.units == "metric" else "°F"

    @property
    def wind_unit(self) -> str:
        """Return ``m/s`` for metric or ``mph`` for imperial."""
        return "m/s" if self.units == "metric" else "mph"

    @property
    def location(self) -> str:
        """Return ``"City, CC"`` (or just the city when no country)."""
        return f"{self.city}, {self.country}" if self.country else self.city
