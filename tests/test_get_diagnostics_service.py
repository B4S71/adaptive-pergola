"""Tests for the get_diagnostics service."""

from __future__ import annotations

import datetime as dt
import enum
import json
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.adaptive_pergola.services.diagnostics_service import (
    async_handle_get_diagnostics,
)
from custom_components.adaptive_pergola.const import DOMAIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_coordinator(entry_id="entry-1", name="Test Cover", cover_type="cover_blind"):
    coord = MagicMock()
    coord.config_entry.entry_id = entry_id
    coord.config_entry.data = {"name": name}
    coord.config_entry.domain = DOMAIN
    coord._cover_type = cover_type  # noqa: SLF001
    coord.last_update_success = True
    coord._last_update_success_time = dt.datetime(2026, 4, 28, 12, 0, 0, tzinfo=dt.UTC)  # noqa: SLF001
    coord.entities = [f"cover.{name.lower().replace(' ', '_')}"]
    coord.data = MagicMock()
    coord.data.diagnostics = {
        "pipeline": {"handler": "solar"},
        "sun": {"elevation": 25.5},
    }
    return coord


def make_hass(*coordinators):
    hass = MagicMock()
    entries = []
    for coord in coordinators:
        entry = MagicMock()
        entry.entry_id = coord.config_entry.entry_id
        entry.runtime_data = coord
        entry.state = ConfigEntryState.LOADED
        entries.append(entry)
    hass.config_entries.async_entries = MagicMock(return_value=entries)
    hass.config_entries.async_get_entry.side_effect = lambda eid: next(
        (
            MagicMock(domain=DOMAIN, entry_id=eid)
            for coord in coordinators
            if coord.config_entry.entry_id == eid
        ),
        None,
    )
    return hass


def make_call(hass, data=None, *, is_admin=True, user_id="user-1"):
    """Build a fake ServiceCall.

    Defaults to an admin caller (the common case). ``async_is_admin_call`` reads
    ``call.context.user_id`` then awaits ``hass.auth.async_get_user`` — both are
    wired here so the permission check resolves deterministically.
    """
    from unittest.mock import AsyncMock

    call = MagicMock()
    call.hass = hass
    call.data = data or {}
    call.context = MagicMock()
    call.context.user_id = user_id
    user = MagicMock()
    user.is_admin = is_admin
    hass.auth = MagicMock()
    hass.auth.async_get_user = AsyncMock(return_value=user)
    return call


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_versioned_envelope():
    """Response always has version, generated_at, count, entries."""
    coord = make_coordinator()
    hass = make_hass(coord)
    call = make_call(hass)

    result = await async_handle_get_diagnostics(call)

    assert result["version"] == 1
    assert "generated_at" in result
    assert "count" in result
    assert "entries" in result


@pytest.mark.asyncio
async def test_entry_keyed_by_config_entry_id():
    """Single coordinator → one entry keyed by its config entry ID."""
    coord = make_coordinator(entry_id="abc-123")
    hass = make_hass(coord)
    call = make_call(hass)

    result = await async_handle_get_diagnostics(call)

    assert result["count"] == 1
    assert "abc-123" in result["entries"]
    assert result["entries"]["abc-123"]["config_entry_id"] == "abc-123"
    assert result["entries"]["abc-123"]["name"] == "Test Cover"
    assert result["entries"]["abc-123"]["cover_type"] == "cover_blind"


@pytest.mark.asyncio
async def test_no_coordinators_returns_empty_envelope():
    """No ACP instances → count 0, empty entries, no exception."""
    hass = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    call = make_call(hass)

    result = await async_handle_get_diagnostics(call)

    assert result["count"] == 0
    assert result["entries"] == {}


@pytest.mark.asyncio
async def test_unknown_explicit_entry_raises():
    """Explicit config_entry_id that doesn't exist raises ServiceValidationError."""
    from homeassistant.exceptions import ServiceValidationError

    hass = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_get_entry.return_value = None
    call = make_call(hass, data={"config_entry_id": ["nonexistent-id"]})

    with pytest.raises(ServiceValidationError):
        await async_handle_get_diagnostics(call)


@pytest.mark.asyncio
async def test_sanitizer_handles_numpy_datetime_enum_dataclass():
    """Diagnostics containing numpy scalars, datetimes, enums, and dataclasses are JSON-serializable."""
    try:
        import numpy as np

        numpy_val = np.float64(42.5)
    except ImportError:
        numpy_val = 42.5  # numpy not available in test env, use plain float

    class Colour(enum.Enum):
        RED = "red"

    @dataclass
    class Point:
        x: float
        y: float

    coord = make_coordinator()
    coord.data.diagnostics = {
        "numpy_val": numpy_val,
        "timestamp": dt.datetime(2026, 4, 28, tzinfo=dt.UTC),
        "colour": Colour.RED,
        "point": Point(1.0, 2.0),
        "tags": {"b", "a"},
    }
    hass = make_hass(coord)
    call = make_call(hass)

    result = await async_handle_get_diagnostics(call)

    # Must be fully JSON-serializable
    json.dumps(result)

    diag = result["entries"]["entry-1"]["diagnostics"]
    assert diag["numpy_val"] == 42.5
    assert diag["timestamp"] == "2026-04-28T00:00:00+00:00"
    assert diag["colour"] == "red"
    assert diag["point"] == {"x": 1.0, "y": 2.0}
    assert diag["tags"] == ["a", "b"]


@pytest.mark.asyncio
async def test_coord_data_none_returns_error_payload_without_raising():
    """When coord.data is None and build_diagnostic_data raises, returns error payload."""
    coord = make_coordinator()
    coord.data = None
    coord.build_diagnostic_data.side_effect = RuntimeError("update in progress")
    hass = make_hass(coord)
    call = make_call(hass)

    result = await async_handle_get_diagnostics(call)

    entry = result["entries"]["entry-1"]
    assert "error" in entry["diagnostics"]
    assert "diagnostics_unavailable" in entry["diagnostics"]["error"]


@pytest.mark.asyncio
async def test_multiple_coordinators_returns_one_entry_each():
    """Multiple coordinators each appear as a separate entry."""
    coord1 = make_coordinator(entry_id="e1", name="North")
    coord2 = make_coordinator(entry_id="e2", name="South")
    hass = make_hass(coord1, coord2)
    call = make_call(hass)

    result = await async_handle_get_diagnostics(call)

    assert result["count"] == 2
    assert "e1" in result["entries"]
    assert "e2" in result["entries"]


@pytest.mark.asyncio
async def test_explicit_config_entry_id_targets_single_coordinator():
    """config_entry_id field bypasses entity/device target resolution."""
    coord1 = make_coordinator(entry_id="e1", name="North")
    coord2 = make_coordinator(entry_id="e2", name="South")
    hass = make_hass(coord1, coord2)
    # make async_get_entry return a valid entry for e1 only in this test
    hass.config_entries.async_get_entry.side_effect = lambda eid: (
        MagicMock(domain=DOMAIN, entry_id=eid) if eid == "e1" else None
    )
    call = make_call(hass, data={"config_entry_id": ["e1"]})

    result = await async_handle_get_diagnostics(call)

    assert result["count"] == 1
    assert "e1" in result["entries"]
    assert "e2" not in result["entries"]


def test_translations_contain_get_diagnostics_key():
    """en.json, de.json, and fr.json all contain the services.get_diagnostics key."""
    import json
    from pathlib import Path

    translations_dir = (
        Path(__file__).parent.parent
        / "custom_components"
        / "adaptive_pergola"
        / "translations"
    )
    for lang in ("en", "de", "fr"):
        data = json.loads((translations_dir / f"{lang}.json").read_text())
        assert "get_diagnostics" in data.get("services", {}), (
            f"{lang}.json missing services.get_diagnostics"
        )


# ---------------------------------------------------------------------------
# Tiered payload: admin full, non-admin occupancy-stripped (ACP-005)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_gets_occupancy_fields():
    """An admin caller sees motion/presence/event_timeline."""
    coord = make_coordinator()
    coord.data.diagnostics = {
        "motion_sensors": ["binary_sensor.kids_room"],
        "motion_detected": True,
        "event_timeline": [{"ts": "t"}],
        "calculated_position": 35,
    }
    hass = make_hass(coord)
    call = make_call(hass, is_admin=True)

    result = await async_handle_get_diagnostics(call)
    diag = result["entries"]["entry-1"]["diagnostics"]
    assert result["reduced"] is False
    assert diag["motion_sensors"] == ["binary_sensor.kids_room"]
    assert "event_timeline" in diag


@pytest.mark.asyncio
async def test_non_admin_gets_reduced_payload():
    """A non-admin caller gets the same payload with occupancy stripped."""
    coord = make_coordinator()
    coord.data.diagnostics = {
        "motion_sensors": ["binary_sensor.kids_room"],
        "motion_detected": True,
        "event_timeline": [{"ts": "t"}],
        "calculated_position": 35,
    }
    hass = make_hass(coord)
    call = make_call(hass, is_admin=False)

    result = await async_handle_get_diagnostics(call)
    diag = result["entries"]["entry-1"]["diagnostics"]
    assert result["reduced"] is True
    assert "motion_sensors" not in diag
    assert "motion_detected" not in diag
    assert "event_timeline" not in diag
    # The card still renders — geometry/position survive.
    assert diag["calculated_position"] == 35
