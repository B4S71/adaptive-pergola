"""Tests for the privilege + privacy hardening (ACP-005/006/007/008/009/016/017).

A non-admin authenticated user (guest/kid account, a scoped token) is the trust
boundary these guard: HA gates the options flow and diagnostics download behind
admin, but plain hass.services.async_register handlers get no check at all.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import Unauthorized

from custom_components.adaptive_pergola.diagnostics import (
    TO_REDACT,
    _jsonify,
    _sanitize,
)
from custom_components.adaptive_pergola.services.diagnostics_service import (
    _OCCUPANCY_KEYS,
    _redact_occupancy,
)
from custom_components.adaptive_pergola.services.permissions import (
    async_is_admin_call,
    async_require_admin,
)

pytestmark = pytest.mark.unit


def _call(*, user_id="u1", is_admin=True):
    call = MagicMock()
    call.context = MagicMock()
    call.context.user_id = user_id
    user = MagicMock()
    user.is_admin = is_admin
    call.hass = MagicMock()
    call.hass.auth.async_get_user = AsyncMock(return_value=user)
    return call


# --- permission helper (ACP-005/008/009) ---------------------------------


async def test_admin_call_allowed():
    assert await async_is_admin_call(_call(is_admin=True)) is True
    await async_require_admin(_call(is_admin=True))  # must not raise


async def test_non_admin_call_rejected():
    assert await async_is_admin_call(_call(is_admin=False)) is False
    with pytest.raises(Unauthorized):
        await async_require_admin(_call(is_admin=False))


async def test_internal_call_treated_as_trusted():
    """user_id None = automation/internal call; async_get_user must not be probed."""
    call = _call(user_id=None)
    assert await async_is_admin_call(call) is True
    call.hass.auth.async_get_user.assert_not_called()


# --- tiered diagnostics payload (ACP-005) --------------------------------


def test_redact_occupancy_strips_only_occupancy_keys():
    diag = {
        "motion_sensors": ["binary_sensor.kids_room"],
        "motion_detected": True,
        "event_timeline": [{"ts": "t", "reason": "x"}],
        "calculated_position": 35,
        "sun_azimuth": 180.0,
        "nested": {"presence_entity": "person.alice", "gamma": 12.0},
    }
    out = _redact_occupancy(diag)
    for key in ("motion_sensors", "motion_detected", "event_timeline"):
        assert key not in out
    # Geometry / position / sun survive so a card still renders.
    assert out["calculated_position"] == 35
    assert out["sun_azimuth"] == 180.0
    assert "presence_entity" not in out["nested"]
    assert out["nested"]["gamma"] == 12.0


def test_occupancy_keys_include_context_ids():
    """ACP-007's structured user_id must be in the strip set."""
    assert {"context_user_id", "context_id", "event_timeline"} <= _OCCUPANCY_KEYS


# --- diagnostics-download redaction (ACP-006) ----------------------------


def test_to_redact_covers_household_and_templates():
    # Occupancy / identity (CONF_DEVICE_ID's value is "linked_device_id")
    for key in ("name", "motion_sensors", "presence_entity", "linked_device_id"):
        assert key in TO_REDACT
    # Every condition template (raw user Jinja)
    assert "is_sunny_template" in TO_REDACT
    assert "presence_template" in TO_REDACT
    # Per-slot custom-position trigger sensors
    assert "custom_position_sensors_1" in TO_REDACT
    # ACP-007 structured ids
    assert "context_user_id" in TO_REDACT


def test_redaction_actually_applied_to_config_options():
    from homeassistant.components.diagnostics import async_redact_data

    options = {
        "motion_sensors": ["binary_sensor.kids_room"],
        "presence_entity": "person.alice",
        "fov_left": 45,
    }
    redacted = async_redact_data(options, TO_REDACT)
    assert redacted["motion_sensors"] == "**REDACTED**"
    assert redacted["presence_entity"] == "**REDACTED**"
    assert redacted["fov_left"] == 45  # non-sensitive kept


# --- ACP-016 -------------------------------------------------------------


def test_sanitize_is_jsonify_alias():
    """_sanitize kept as a back-compat alias; _jsonify is the honest name."""
    assert _sanitize is _jsonify
