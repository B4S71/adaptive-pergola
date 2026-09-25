"""Regression tests for temperature chatter and persistent release conditions."""

from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_pergola.managers.custom_position_hysteresis import (
    CustomPositionHysteresis,
)
from custom_components.adaptive_pergola.pipeline.snapshot_builder import (
    PipelineSnapshotBuilder,
)
from custom_components.adaptive_pergola.pipeline.handlers.custom_position import (
    CustomPositionHandler,
)
from custom_components.adaptive_pergola.services.options_service import (
    validate_options_patch,
)

SENSOR = "sensor.hysteresis_temperature"
ON = "{{ states('sensor.hysteresis_temperature') | float(99) < 4 }}"
OFF = "{{ is_number(states('sensor.hysteresis_temperature')) and states('sensor.hysteresis_temperature') | float(0) >= 5 }}"
OPTIONS = {
    "custom_position_template_1": ON,
    "custom_position_release_template_1": OFF,
    "custom_position_1": 75,
    "custom_position_priority_1": 100,
}


def builder(hass, latch=None):
    """Use real HA state/template evaluation, stub unrelated collaborators."""
    return PipelineSnapshotBuilder(
        hass,
        MagicMock(),
        climate_provider=MagicMock(),
        toggles=MagicMock(),
        policy=MagicMock(),
        config_service=MagicMock(),
        hysteresis=latch,
    )


@pytest.mark.parametrize("release", [True, False])
async def test_recorded_night_sequence(hass, release):
    """The 3.9/4.0 °C trace must hold 75% until the separate 5 °C boundary."""
    b = builder(hass)
    options = dict(OPTIONS)
    if not release:
        options.pop("custom_position_release_template_1")
    temperatures = [4, 3.9, 4, 3.9, 4, 4.999, 5, 4.5, 4, 3.99]
    expected_states = (
        [False, True, True, True, True, True, False, False, False, True]
        if release
        else [False, True, False, True, False, False, False, False, False, True]
    )
    for temperature, expected in zip(temperatures, expected_states, strict=True):
        hass.states.async_set(SENSOR, temperature)
        state = b.read_custom_position_sensors(options)[0]
        assert state.is_on is expected
        assert state.hysteresis_held is (expected and temperature >= 4)
        if state.hysteresis_held:
            assert CustomPositionHandler._trigger_label(state) == "hysteresis hold"
        assert b.read_custom_position_sensors(options)[0] == state


async def test_invalid_release_and_unavailable_sensor_hold(hass):
    """Missing readings and template failures cannot drop an active latch."""
    b = builder(hass)
    for temperature, expected in [
        (3.9, True),
        ("unavailable", True),
        ("unknown", True),
        (5, False),
    ]:
        hass.states.async_set(SENSOR, temperature)
        assert b.read_custom_position_sensors(OPTIONS)[0].is_on is expected
    options = dict(OPTIONS, custom_position_release_template_1="{{ 1 / 0 }}")
    hass.states.async_set(SENSOR, 3)
    assert b.read_custom_position_sensors(options)[0].is_on
    hass.states.async_set(SENSOR, 6)
    assert b.read_custom_position_sensors(options)[0].is_on


async def test_disable_remove_and_edit_invalidate(hass):
    """No stale activation survives disabling, removing or changing a rule."""
    for patch in [
        {"custom_position_enabled_1": False},
        {"custom_position_1": None},
        {"custom_position_release_template_1": "{{ false }}"},
    ]:
        b = builder(hass)
        hass.states.async_set(SENSOR, 3)
        assert b.read_custom_position_sensors(OPTIONS)[0].is_on
        hass.states.async_set(SENSOR, 4.5)
        b.read_custom_position_sensors(OPTIONS | patch)
        assert not b.read_custom_position_sensors(OPTIONS)[0].is_on


async def test_slot_independence_activation_precedence_and_sensor_combine(hass):
    """AND input still controls activation; either true activation beats release."""
    b = builder(hass)
    options = OPTIONS | {
        "custom_position_sensors_1": ["binary_sensor.enable"],
        "custom_position_template_mode_1": "and",
        "custom_position_template_10": "{{ true }}",
        "custom_position_release_template_10": "{{ true }}",
        "custom_position_10": 20,
    }
    hass.states.async_set(SENSOR, 3)
    hass.states.async_set("binary_sensor.enable", "off")
    a, other = b.read_custom_position_sensors(options)
    assert not a.is_on and other.is_on
    hass.states.async_set("binary_sensor.enable", "on")
    assert b.read_custom_position_sensors(options)[0].is_on
    hass.states.async_set("binary_sensor.enable", "off")
    assert b.read_custom_position_sensors(options)[0].is_on
    hass.states.async_set(SENSOR, 5)
    assert not b.read_custom_position_sensors(options)[0].is_on


async def test_reload_restart_and_deletion(hass):
    """Restored latches retain the band, release at 5, and are deleted with entry."""
    latch = CustomPositionHysteresis(hass, "hysteresis-test")
    await latch.async_load()
    hass.states.async_set(SENSOR, 3.9)
    assert builder(hass, latch).read_custom_position_sensors(OPTIONS)[0].is_on
    await latch.async_save()
    hass.states.async_set(SENSOR, 4.5)
    restored = CustomPositionHysteresis(hass, "hysteresis-test")
    await restored.async_load()
    b = builder(hass, restored)
    assert b.read_custom_position_sensors(OPTIONS)[0].hysteresis_held
    # An unrelated config edit does not discard the saved state.
    assert b.read_custom_position_sensors(OPTIONS | {"delta_position": 2})[0].is_on
    hass.states.async_set(SENSOR, 5)
    assert not b.read_custom_position_sensors(OPTIONS)[0].is_on
    await restored.async_save()
    await restored.async_remove()
    empty = CustomPositionHysteresis(hass, "hysteresis-test")
    await empty.async_load()
    hass.states.async_set(SENSOR, 4.5)
    assert not builder(hass, empty).read_custom_position_sensors(OPTIONS)[0].is_on
    await empty.async_save()
    await empty.async_remove()


@pytest.mark.parametrize("slot", range(1, 11))
def test_release_field_supported_by_option_validation(slot):
    """All slots accept the optional release condition through options services."""
    validate_options_patch({f"custom_position_release_template_{slot}": OFF}, {})


async def test_release_while_offline_is_reported_once(hass):
    """A restored safety latch exposes its release even without a prior snapshot."""
    original = CustomPositionHysteresis(hass, "offline-release")
    hass.states.async_set(SENSOR, 3.9)
    assert builder(hass, original).read_custom_position_sensors(OPTIONS)[0].is_on
    await original.async_save()
    restored = CustomPositionHysteresis(hass, "offline-release")
    await restored.async_load()
    hass.states.async_set(SENSOR, 5)
    b = builder(hass, restored)
    assert not b.read_custom_position_sensors(OPTIONS)[0].is_on
    assert not b.read_custom_position_sensors(OPTIONS)[0].is_on
    assert restored.pop_released_slots() == {1}
    assert restored.pop_released_slots() == set()
    await restored.async_save()
    await restored.async_remove()


@pytest.mark.integration
async def test_startup_release_survives_platform_restore_refreshes(hass, freezer):
    """Early switch restore refreshes must not consume an offline release edge."""
    from homeassistant.components.cover import CoverEntityFeature

    from custom_components.adaptive_pergola.const import CoverType
    from tests.ha_helpers import VERTICAL_OPTIONS
    from tests.test_services_integration import _setup

    freezer.move_to("2026-09-25T04:00:00+00:00")
    options = (
        VERTICAL_OPTIONS
        | OPTIONS
        | {
            "start_time": "07:30:00",
            "end_time": "20:00:00",
            "default_percentage": 0,
        }
    )
    latch = CustomPositionHysteresis(hass, "offline-startup")
    hass.states.async_set(SENSOR, 3.9)
    assert builder(hass, latch).read_custom_position_sensors(options)[0].is_on
    await latch.async_save()
    hass.states.async_set(SENSOR, 5)
    hass.states.async_set(
        "cover.test_blind",
        "open",
        {
            "current_tilt_position": 75,
            "supported_features": int(CoverEntityFeature.SET_TILT_POSITION),
        },
    )
    calls = []

    async def move(call):
        calls.append(call.data)

    entry = await _setup(
        hass,
        entry_id="offline-startup",
        cover_type=CoverType.LOUVERED_ROOF,
        options=options,
    )
    hass.services.async_register("cover", "set_cover_tilt_position", move)
    coord = entry.runtime_data
    # Simulate the refreshes performed by switch RestoreEntity hooks before
    # the formal first refresh (all control switches have now restored).
    await coord.async_refresh()
    await coord.async_refresh()
    assert not calls
    coord.first_refresh = True
    await coord.async_refresh()
    assert len(calls) == 1
    assert calls[0]["tilt_position"] == 0
    await coord.async_refresh()
    assert len(calls) == 1
