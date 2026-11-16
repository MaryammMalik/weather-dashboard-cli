"""Custom exceptions for the Weather Dashboard.

A small hierarchy rooted at :class:`WeatherAPIError` lets the CLI show a
friendly, specific message for each failure mode (unknown city, timeout,
authentication problem, or a generic service failure) instead of dumping a
raw traceback on the user.
"""


class WeatherAPIError(Exception):
    """Base class for every error raised by the weather client."""


class CityNotFoundError(WeatherAPIError):
    """Raised when the weather service cannot find the requested city."""


class WeatherTimeoutError(WeatherAPIError):
    """Raised when a request to the weather service times out."""


class WeatherAuthenticationError(WeatherAPIError):
    """Raised when the configured API key is missing or rejected."""


class WeatherServiceError(WeatherAPIError):
    """Raised for any other failed or unreachable-service request."""
