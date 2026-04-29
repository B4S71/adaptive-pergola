"""Weather override logic reused from the Adaptive Cover Pro concept."""

from __future__ import annotations

from .models import WeatherConfig, WeatherReadings


def is_weather_override_active(
    config: WeatherConfig | None,
    readings: WeatherReadings | None,
) -> bool:
    """Return whether the safety override must retract or open the pergola."""
    if config is None or readings is None:
        return False
    if readings.severe and config.severe_binary_enabled:
        return True
    if readings.is_raining or readings.is_windy:
        return True
    if (
        config.wind_speed_threshold is not None
        and readings.wind_speed is not None
        and readings.wind_speed >= config.wind_speed_threshold
    ):
        return True
    if (
        config.rain_threshold is not None
        and readings.rain_rate is not None
        and readings.rain_rate >= config.rain_threshold
    ):
        return True
    return False
