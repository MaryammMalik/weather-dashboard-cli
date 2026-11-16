"""Command-line interface for the Weather Dashboard.

Usage:
    python -m weather "Faisalabad"
    python -m weather "New York" --units imperial
"""

from __future__ import annotations

import argparse
import sys

from .client import WeatherClient, load_api_key
from .errors import WeatherAPIError
from .models import WeatherReport

LINE = "=" * 52


def format_report(report: WeatherReport) -> str:
    """Render a :class:`WeatherReport` as a clean, readable dashboard."""
    rows = [
        ("Condition", report.description),
        (
            "Temperature",
            f"{report.temperature:.1f} {report.temperature_unit} "
            f"(feels like {report.feels_like:.1f} {report.temperature_unit})",
        ),
        ("Humidity", f"{report.humidity} %"),
        ("Pressure", f"{report.pressure} hPa"),
        ("Wind", f"{report.wind_speed:.1f} {report.wind_unit}"),
        ("Source", report.source),
    ]
    body = "\n".join(f"  {label:<14}: {value}" for label, value in rows)
    return (
        f"{LINE}\n"
        f"  Weather Dashboard — {report.location}\n"
        f"{LINE}\n"
        f"{body}\n"
        f"{LINE}"
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="weather-dashboard",
        description="Fetch live weather for a city from a public REST API.",
    )
    parser.add_argument("city", nargs="+", help="City name, e.g. Faisalabad")
    parser.add_argument(
        "--units",
        choices=("metric", "imperial"),
        default="metric",
        help="Unit system: metric (°C) or imperial (°F). Default: metric.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds. Default: 10.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code (0 = success)."""
    args = build_parser().parse_args(argv)
    city = " ".join(args.city)

    client = WeatherClient(api_key=load_api_key(), timeout=args.timeout)
    try:
        report = client.get_weather(city, units=args.units)
    except WeatherAPIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
