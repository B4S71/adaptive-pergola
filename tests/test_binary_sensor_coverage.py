"""Unit tests for binary_sensor.py uncovered branches."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_pergola.binary_sensor import (
    AdaptivePergolaPositionMismatchSensor,
)
from custom_components.adaptive_pergola.const import (
    CONF_SENSOR_TYPE,
    CoverType,
)


def _make_config_entry(options: dict | None = None, sensor_type: str = CoverType.BLIND):
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"name": "Test", CONF_SENSOR_TYPE: sensor_type}
    entry.options = options or {}
    return entry


def _make_coordinator(mock_hass=None):
    coord = MagicMock()
    coord.hass = mock_hass or MagicMock()
    coord.logger = MagicMock()
    coord.entities = []
    coord._cmd_svc = MagicMock()
    coord._cmd_svc._position_tolerance = 5
    coord._cmd_svc.get_target = MagicMock(return_value=None)
    return coord


# ---------------------------------------------------------------------------
# Position mismatch sensor: is_on logic
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_position_mismatch_is_on_true_when_delta_exceeds_tolerance():
    """is_on returns True when any entity has |target - actual| > tolerance."""
    coord = _make_coordinator()
    coord.entities = ["cover.test"]
    coord._cmd_svc.get_target = MagicMock(return_value=50)
    coord.get_current_position = MagicMock(return_value=42)  # delta = 8 > 5
    coord._cmd_svc._position_tolerance = 5

    config_entry = _make_config_entry()
    sensor = AdaptivePergolaPositionMismatchSensor(
        config_entry=config_entry,
        unique_id="test_entry",
        coordinator=coord,
    )

    assert sensor.is_on is True


@pytest.mark.unit
def test_position_mismatch_is_on_false_when_delta_within_tolerance():
    """is_on returns False when all entities have |target - actual| <= tolerance."""
    coord = _make_coordinator()
    coord.entities = ["cover.test"]
    coord._cmd_svc.get_target = MagicMock(return_value=50)
    coord.get_current_position = MagicMock(return_value=48)  # delta = 2 <= 5
    coord._cmd_svc._position_tolerance = 5

    config_entry = _make_config_entry()
    sensor = AdaptivePergolaPositionMismatchSensor(
        config_entry=config_entry,
        unique_id="test_entry",
        coordinator=coord,
    )

    assert sensor.is_on is False


@pytest.mark.unit
def test_position_mismatch_is_on_false_when_no_target():
    """is_on returns False when no target has been set (target is None)."""
    coord = _make_coordinator()
    coord.entities = ["cover.test"]
    coord._cmd_svc.get_target = MagicMock(return_value=None)  # no target
    coord.get_current_position = MagicMock(return_value=50)

    config_entry = _make_config_entry()
    sensor = AdaptivePergolaPositionMismatchSensor(
        config_entry=config_entry,
        unique_id="test_entry",
        coordinator=coord,
    )

    assert sensor.is_on is False


@pytest.mark.unit
def test_position_mismatch_is_on_false_when_actual_none():
    """is_on returns False when actual position is None (cover unavailable)."""
    coord = _make_coordinator()
    coord.entities = ["cover.test"]
    coord._cmd_svc.get_target = MagicMock(return_value=50)
    coord.get_current_position = MagicMock(return_value=None)

    config_entry = _make_config_entry()
    sensor = AdaptivePergolaPositionMismatchSensor(
        config_entry=config_entry,
        unique_id="test_entry",
        coordinator=coord,
    )

    assert sensor.is_on is False


# ---------------------------------------------------------------------------
# Position mismatch sensor: extra_state_attributes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_position_mismatch_extra_state_attributes_with_mismatch():
    """extra_state_attributes includes per-entity detail when target/actual both set."""
    coord = _make_coordinator()
    coord.entities = ["cover.test"]
    coord._cmd_svc.get_target = MagicMock(return_value=50)
    coord.get_current_position = MagicMock(return_value=42)
    coord._cmd_svc._position_tolerance = 5
    coord._cmd_svc.get_diagnostics.return_value = {
        "target": 50,
        "actual": 42,
        "retry_count": 0,
    }

    config_entry = _make_config_entry()
    sensor = AdaptivePergolaPositionMismatchSensor(
        config_entry=config_entry,
        unique_id="test_entry",
        coordinator=coord,
    )

    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert "tolerance" in attrs
    assert "entities" in attrs
    entity_detail = attrs["entities"]["cover.test"]
    assert entity_detail["target_position"] == 50
    assert entity_detail["actual_position"] == 42
    assert entity_detail["mismatch"] is True


@pytest.mark.unit
def test_position_mismatch_extra_state_attributes_no_entities():
    """extra_state_attributes omits 'entities' key when no diagnostics are available."""
    coord = _make_coordinator()
    coord.entities = ["cover.test"]
    coord._cmd_svc.get_target = MagicMock(return_value=None)
    coord._cmd_svc._position_tolerance = 5
    coord._cmd_svc.get_diagnostics.return_value = {
        "target": None,
        "actual": None,
        "retry_count": 0,
    }

    config_entry = _make_config_entry()
    sensor = AdaptivePergolaPositionMismatchSensor(
        config_entry=config_entry,
        unique_id="test_entry",
        coordinator=coord,
    )

    attrs = sensor.extra_state_attributes
    assert "tolerance" in attrs
    assert "entities" not in attrs
