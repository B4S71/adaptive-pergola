"""Tests for SunData polar region fallbacks (midnight sun / polar night).

The sunrise/sunset calls go through the ``astral.sun`` module functions
(HA deprecated ``get_astral_location``, and ``astral.Observer`` has no
``sunrise``/``sunset`` methods of its own), so these patch those functions
rather than stubbing methods on a location object.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

import pytest
from astral import Observer

from custom_components.adaptive_pergola.sun import SunData

_SUNSET_FN = "custom_components.adaptive_pergola.sun.astral.sun.sunset"
_SUNRISE_FN = "custom_components.adaptive_pergola.sun.astral.sun.sunrise"


def _make_sun_data() -> SunData:
    """Build a SunData with a real astral Observer."""
    return SunData(timezone="UTC", observer=Observer(48.0, 14.0, 0.0))


@pytest.mark.unit
def test_sunset_polar_midnight_sun_returns_sentinel():
    """SunData.sunset() returns 23:59:59 when astral raises ValueError (midnight sun)."""
    sd = _make_sun_data()
    with patch(_SUNSET_FN, side_effect=ValueError("Sun never sets at this latitude")):
        result = sd.sunset()

    today = date.today()
    assert result == datetime(today.year, today.month, today.day, 23, 59, 59)


@pytest.mark.unit
def test_sunset_polar_attribute_error_returns_sentinel():
    """SunData.sunset() returns 23:59:59 when astral raises AttributeError."""
    sd = _make_sun_data()
    with patch(_SUNSET_FN, side_effect=AttributeError):
        result = sd.sunset()

    today = date.today()
    assert result == datetime(today.year, today.month, today.day, 23, 59, 59)


@pytest.mark.unit
def test_sunrise_polar_night_returns_sentinel():
    """SunData.sunrise() returns 00:01:00 when astral raises ValueError (polar night)."""
    sd = _make_sun_data()
    with patch(_SUNRISE_FN, side_effect=ValueError("Sun never rises at this latitude")):
        result = sd.sunrise()

    today = date.today()
    assert result == datetime(today.year, today.month, today.day, 0, 1, 0)


@pytest.mark.unit
def test_sunrise_polar_attribute_error_returns_sentinel():
    """SunData.sunrise() returns 00:01:00 when astral raises AttributeError."""
    sd = _make_sun_data()
    with patch(_SUNRISE_FN, side_effect=AttributeError):
        result = sd.sunrise()

    today = date.today()
    assert result == datetime(today.year, today.month, today.day, 0, 1, 0)


@pytest.mark.unit
def test_sunset_normal_returns_astral_result():
    """SunData.sunset() returns the astral result when no exception is raised."""
    sd = _make_sun_data()
    expected = datetime(2024, 6, 21, 20, 30, 0)
    with patch(_SUNSET_FN, return_value=expected):
        assert sd.sunset() == expected


@pytest.mark.unit
def test_sunrise_normal_returns_astral_result():
    """SunData.sunrise() returns the astral result when no exception is raised."""
    sd = _make_sun_data()
    expected = datetime(2024, 6, 21, 4, 15, 0)
    with patch(_SUNRISE_FN, return_value=expected):
        assert sd.sunrise() == expected


@pytest.mark.unit
def test_next_sunrise_polar_night_returns_tomorrow_sentinel():
    """SunData.next_sunrise() returns tomorrow 00:01:00 during polar night."""
    from datetime import timedelta

    sd = _make_sun_data()
    with patch(_SUNRISE_FN, side_effect=ValueError("Sun never rises")):
        result = sd.next_sunrise()

    tomorrow = date.today() + timedelta(days=1)
    assert result == datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 1, 0)


@pytest.mark.unit
def test_sunrise_sunset_use_the_observer():
    """The observer (lat/lon/elevation) is what astral is asked about.

    Guards the migration from ``Location.sunrise(date, local=False)`` — which
    silently defaulted ``observer_elevation`` to 0.0 — to the observer-carried
    elevation, so the pergola's sunset now agrees with HA's own ``sun.sun``.
    """
    observer = Observer(48.0, 14.0, 0.0)
    sd = SunData(timezone="UTC", observer=observer)
    with patch(_SUNSET_FN, return_value=datetime(2024, 6, 21, 20, 30)) as spy:
        sd.sunset()
    assert spy.call_args.args[0] is observer
