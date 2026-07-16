"""Regression tests for the crash-hardening fixes (ACP-001, 002, 003, 018, 022).

Each test pins a value that was previously accepted by validation, persisted to
``config_entry.options``, and only then raised — on every coordinator cycle,
permanently, surviving restart.
"""

from __future__ import annotations

import datetime as dt

import pytest
import voluptuous as vol

from custom_components.adaptive_pergola.helpers import get_datetime_from_str
from custom_components.adaptive_pergola.services.options_service import (
    _duration_v,
    _time_v,
)

pytestmark = pytest.mark.unit


# --- ACP-001 -------------------------------------------------------------


@pytest.mark.parametrize("state", ["", "off", "None", "0", "12345", "unavailable-ish"])
def test_get_datetime_from_str_returns_none_for_unparseable(state):
    """A sensor reporting a non-date state degrades to None instead of raising.

    The start/end entity selectors offer the ``sensor`` domain, so this needs no
    attacker — an admin picks a sensor the UI offered and it reports "off".
    dateutil raises ParserError (a ValueError subclass), which propagated out of
    the coordinator update and took every entity on the instance unavailable.
    """
    assert get_datetime_from_str(state) is None


def test_get_datetime_from_str_still_parses_valid_input():
    """The guard must not swallow legitimate values."""
    assert get_datetime_from_str("2026-04-18T06:30:00") == dt.datetime(
        2026, 4, 18, 6, 30
    )
    assert get_datetime_from_str(None) is None


# --- ACP-002 -------------------------------------------------------------


@pytest.mark.parametrize("bad", ["99:99:99", "25:61:61", "aa:bb:cc", ""])
def test_time_validator_rejects_out_of_range(bad):
    """_TIME_RE matched the shape only, so "99:99:99" persisted and then raised."""
    with pytest.raises(vol.Invalid):
        _time_v()(bad)


def test_time_validator_leniency_is_bounded():
    """cv.time is looser on *shape* than the old regex but strict on *range*.

    HA's dt_util.parse_time accepts a short form and ignores trailing junk, so
    "07:30" and "1:2:3:4" pass where the old ^\\d{2}:\\d{2}:\\d{2}$ regex would
    have rejected them. That is fine: the values that actually crashed were the
    out-of-range ones, and anything dateutil later fails to read now degrades to
    None via get_datetime_from_str rather than raising.
    """
    assert _time_v()("07:30") == dt.time(7, 30)
    assert _time_v()("1:2:3:4") == dt.time(1, 2, 3)


@pytest.mark.parametrize("good", ["07:30:00", "00:00:00", "23:59:59"])
def test_time_validator_accepts_valid(good):
    """Valid times, including the BLANK_TIME sentinel "00:00:00", still pass."""
    assert _time_v()(good) is not None


def test_time_validator_accepts_none():
    """None clears the field."""
    assert _time_v()(None) is None


# --- ACP-003 -------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        {"evil": 1},  # -> TypeError from timedelta(**d)
        {"days": 1e308},  # -> OverflowError from timedelta(**d)
        {"hours": "x"},
        {},
        "abc",
        5,
    ],
)
def test_duration_validator_rejects_bad_dicts(bad):
    """`vol.Any(None, dict)` accepted any dict; timedelta(**d) raised at use time.

    Note {"days": 1e308}: cv.time_period_dict raises OverflowError rather than
    vol.Invalid for that one, which would escape the caller's `except vol.Invalid`
    and surface as an unhandled error, so _duration_v translates it.
    """
    with pytest.raises(vol.Invalid):
        _duration_v()(bad)


@pytest.mark.parametrize("good", [{"hours": 2}, {"minutes": 30}, {"seconds": 45}])
def test_duration_validator_accepts_valid(good):
    """Real durations still pass and coerce to a timedelta."""
    assert isinstance(_duration_v()(good), dt.timedelta)


def test_duration_validator_accepts_none():
    """None clears the field."""
    assert _duration_v()(None) is None


# --- ACP-018 -------------------------------------------------------------


def test_zero_window_height_falls_back_to_default():
    """A stored 0 must not reach the division in position_utils.

    Not UI-reachable (_RANGE_HEIGHT_WIN starts at 0.1), but every sibling field
    already used the `or DEFAULT` idiom and was immune; this one used
    `is not None` and let a 0 through to a ZeroDivisionError.
    """
    from unittest.mock import MagicMock

    from custom_components.adaptive_pergola.const import (
        CONF_HEIGHT_WIN,
        DEFAULT_WINDOW_HEIGHT,
    )
    from custom_components.adaptive_pergola.services.configuration_service import (
        ConfigurationService,
    )

    svc = ConfigurationService(
        hass=MagicMock(),
        config_entry=MagicMock(),
        logger=MagicMock(),
        cover_type="cover_blind",
        temp_toggle=None,
        lux_toggle=None,
        irradiance_toggle=None,
    )

    assert svc.get_vertical_data({CONF_HEIGHT_WIN: 0}).h_win == DEFAULT_WINDOW_HEIGHT
    # None still falls back, and a real value is preserved.
    assert svc.get_vertical_data({}).h_win == DEFAULT_WINDOW_HEIGHT
    assert svc.get_vertical_data({CONF_HEIGHT_WIN: 2.1}).h_win == 2.1
