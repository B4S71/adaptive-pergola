from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adaptive_pergola import async_migrate_entry
from custom_components.adaptive_pergola.const import (
    ACTUATOR_MODE_COVER_TILT,
    ACTUATOR_MODE_NUMBER_CUSTOM,
    CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
    CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
    CONF_AUTOMATIC_CONTROL,
    CONF_AUTO_APPLY,
    CONF_AXIS_AZIMUTH_DEG,
    CONF_CLOSES_AGAIN_AFTER_OPEN,
    CONF_CLOSED_ANGLE_DEG,
    CONF_COMMAND_MODE,
    CONF_COMMAND_VALUE_MAX,
    CONF_COMMAND_VALUE_MIN,
    CONF_HAS_ADDITIONAL_PROTECTED_AREA,
    CONF_HAS_HOUSE_ATTACHMENT,
    CONF_HAS_SHADOW_CASTING_WALL,
    CONF_HOUSE_EXTENDS_LEFT_M,
    CONF_HOUSE_EXTENDS_RIGHT_M,
    CONF_HOUSE_HEIGHT_M,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_DIRECT_SUN_DEPTH_M,
    CONF_MAX_TRAVEL_ANGLE_DEG,
    CONF_NAME,
    CONF_OPEN_ACTUATOR_PERCENT,
    CONF_OPEN_ANGLE_DEG,
    CONF_OPENING_AZIMUTH_DEG,
    CONF_OPEN_BEFORE_SUNRISE_MINUTES,
    CONF_PERGOLA_LENGTH_M,
    CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG,
    CONF_PERGOLA_WIDTH_M,
    CONF_PREOPEN_ACTUATOR_PERCENT,
    CONF_RAIN_THRESHOLD,
    CONF_SHADOW_CASTING_WALL_HEIGHT_M,
    CONF_SHADOW_CASTING_WALL_LENGTH_M,
    CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
    CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
    CONF_SLAT_AXIS_AZIMUTH_DEG,
    CONF_SLAT_AXIS_HEIGHT_M,
    CONF_SLAT_AXIS_SPACING_M,
    CONF_SLAT_THICKNESS_M,
    CONF_SLAT_WIDTH_M,
    CONF_TARGET_ENTITY,
    CONF_TRACKING_MODE,
    CONF_WEATHER_OVERRIDE_POSITION,
    CONF_WIND_SPEED_THRESHOLD,
    DOMAIN,
    TRACKING_BALANCED,
    TRACKING_MAX_LIGHT,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _entry_data(
    *,
    target_entity: str,
    command_mode: str,
    custom_max: float = 100.0,
    tracking_mode: str = TRACKING_BALANCED,
) -> dict:
    return {
        CONF_NAME: "Demo Pergola",
        CONF_TARGET_ENTITY: target_entity,
        CONF_COMMAND_MODE: command_mode,
        CONF_COMMAND_VALUE_MIN: 0.0,
        CONF_COMMAND_VALUE_MAX: custom_max,
        CONF_AUTOMATIC_CONTROL: True,
        CONF_AUTO_APPLY: True,
        CONF_MANUAL_OVERRIDE_DURATION: {"hours": 2},
        CONF_MANUAL_OVERRIDE_RESET: False,
        CONF_MANUAL_THRESHOLD: 5.0,
        CONF_MANUAL_IGNORE_INTERMEDIATE: False,
        CONF_TRACKING_MODE: tracking_mode,
        CONF_SLAT_WIDTH_M: 0.18,
        CONF_SLAT_THICKNESS_M: 0.02,
        CONF_SLAT_AXIS_SPACING_M: 0.20,
        CONF_SLAT_AXIS_HEIGHT_M: 2.5,
        CONF_PERGOLA_LENGTH_M: 4.0,
        CONF_PERGOLA_WIDTH_M: 3.0,
        CONF_SLAT_AXIS_AZIMUTH_DEG: 0.0,
        CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG: 90.0,
        CONF_OPENING_AZIMUTH_DEG: 90.0,
        CONF_CLOSED_ANGLE_DEG: 0.0,
        CONF_OPEN_ANGLE_DEG: 90.0,
        CONF_OPEN_ACTUATOR_PERCENT: 75.0,
        CONF_MAX_TRAVEL_ANGLE_DEG: 135.0,
        CONF_CLOSES_AGAIN_AFTER_OPEN: False,
        CONF_HAS_HOUSE_ATTACHMENT: True,
        CONF_HOUSE_HEIGHT_M: 3.0,
        CONF_HOUSE_EXTENDS_LEFT_M: 1.0,
        CONF_HOUSE_EXTENDS_RIGHT_M: 1.0,
        CONF_HAS_ADDITIONAL_PROTECTED_AREA: False,
        CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M: 0.0,
        CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M: 0.0,
        CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M: 0.0,
        CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M: 0.0,
        CONF_HAS_SHADOW_CASTING_WALL: False,
        CONF_SHADOW_CASTING_WALL_LENGTH_M: 0.0,
        CONF_SHADOW_CASTING_WALL_HEIGHT_M: 0.0,
        CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M: 0.0,
        CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M: 0.0,
        CONF_MAX_DIRECT_SUN_DEPTH_M: 0.4,
        CONF_OPEN_BEFORE_SUNRISE_MINUTES: 0,
        CONF_PREOPEN_ACTUATOR_PERCENT: 0,
        CONF_WIND_SPEED_THRESHOLD: 40.0,
        CONF_RAIN_THRESHOLD: 0.8,
        CONF_WEATHER_OVERRIDE_POSITION: 0,
    }


def _set_sun_state(
    hass: HomeAssistant,
    *,
    azimuth: float = 90.0,
    elevation: float = 25.0,
) -> None:
    hass.states.async_set(
        "sun.sun",
        "above_horizon",
        {
            "azimuth": azimuth,
            "elevation": elevation,
            "next_rising": datetime(2026, 4, 29, 6, 0, 0).isoformat(),
        },
    )


def _set_cover_state(hass: HomeAssistant, entity_id: str, tilt_position: float) -> None:
    hass.states.async_set(
        entity_id,
        "open",
        {
            "current_position": tilt_position,
            "current_tilt_position": tilt_position,
        },
    )


def _register_capture_service(
    hass: HomeAssistant,
    domain: str,
    service: str,
    calls: list[dict],
) -> None:
    async def _capture(call) -> None:
        calls.append(call.data)

    hass.services.async_register(domain, service, _capture)


async def test_setup_applies_cover_tilt_command_and_creates_entities(hass: HomeAssistant) -> None:
    _set_sun_state(hass)
    _set_cover_state(hass, "cover.pergola_tilt_demo", 0)
    service_calls: list[dict] = []
    _register_capture_service(hass, "cover", "set_cover_tilt_position", service_calls)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Demo Pergola",
        data=_entry_data(
            target_entity="cover.pergola_tilt_demo",
            command_mode=ACTUATOR_MODE_COVER_TILT,
            tracking_mode=TRACKING_MAX_LIGHT,
        ),
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert service_calls
    assert service_calls[0]["entity_id"] == "cover.pergola_tilt_demo"
    assert "tilt_position" in service_calls[0]
    assert hass.states.get("sensor.demo_pergola_target_command") is not None
    assert hass.states.get("binary_sensor.demo_pergola_manual_override") is not None
    assert hass.states.get("binary_sensor.demo_pergola_protected_zone_breached") is not None
    assert hass.states.get("button.demo_pergola_reset_manual_override") is not None


async def test_setup_scales_vendor_number_command(hass: HomeAssistant) -> None:
    _set_sun_state(hass)
    hass.states.async_set("input_number.pergola_vendor_target", "0", {"min": 0, "max": 255})
    service_calls: list[dict] = []
    _register_capture_service(hass, "input_number", "set_value", service_calls)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Vendor Pergola",
        data=_entry_data(
            target_entity="input_number.pergola_vendor_target",
            command_mode=ACTUATOR_MODE_NUMBER_CUSTOM,
            custom_max=255.0,
            tracking_mode=TRACKING_MAX_LIGHT,
        ),
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert service_calls
    assert service_calls[0]["entity_id"] == "input_number.pergola_vendor_target"
    assert service_calls[0]["value"] > 0


async def test_migrate_entry_populates_explicit_geometry_fields(hass: HomeAssistant) -> None:
    legacy_data = {
        **_entry_data(
            target_entity="cover.pergola_tilt_demo",
            command_mode=ACTUATOR_MODE_COVER_TILT,
        ),
        CONF_AXIS_AZIMUTH_DEG: 0.0,
    }
    legacy_data.pop(CONF_SLAT_AXIS_AZIMUTH_DEG, None)
    legacy_data.pop(CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG, None)
    legacy_data.pop(CONF_OPENING_AZIMUTH_DEG, None)
    legacy_data.pop(CONF_OPEN_ACTUATOR_PERCENT, None)
    legacy_data.pop(CONF_MANUAL_OVERRIDE_DURATION, None)
    legacy_data.pop(CONF_MANUAL_OVERRIDE_RESET, None)
    legacy_data.pop(CONF_MANUAL_IGNORE_INTERMEDIATE, None)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Legacy Pergola",
        version=1,
        data=legacy_data,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 6
    assert entry.data[CONF_SLAT_AXIS_AZIMUTH_DEG] == 0.0
    assert entry.data[CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG] == 90.0
    assert entry.data[CONF_OPENING_AZIMUTH_DEG] == 90.0
    assert round(entry.data[CONF_OPEN_ACTUATOR_PERCENT], 2) == 66.67
    assert entry.data[CONF_MANUAL_OVERRIDE_DURATION] == {"hours": 2}
    assert entry.data[CONF_MANUAL_OVERRIDE_RESET] is False
    assert entry.data[CONF_MANUAL_IGNORE_INTERMEDIATE] is False
    assert entry.data[CONF_HAS_ADDITIONAL_PROTECTED_AREA] is False
    assert entry.data[CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M] == 0.0
    assert entry.data[CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M] == 0.0
    assert entry.data[CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M] == 0.0
    assert entry.data[CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M] == 0.0
    assert entry.data[CONF_HAS_SHADOW_CASTING_WALL] is False
    assert entry.data[CONF_SHADOW_CASTING_WALL_LENGTH_M] == 0.0
    assert entry.data[CONF_SHADOW_CASTING_WALL_HEIGHT_M] == 0.0
    assert entry.data[CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M] == 0.0
    assert entry.data[CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M] == 0.0
    assert CONF_AXIS_AZIMUTH_DEG not in entry.data


async def test_manual_override_blocks_auto_apply_until_reset(hass: HomeAssistant) -> None:
    _set_sun_state(hass, elevation=25.0)
    _set_cover_state(hass, "cover.pergola_tilt_demo", 0)
    service_calls: list[dict] = []
    _register_capture_service(hass, "cover", "set_cover_tilt_position", service_calls)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Demo Pergola",
        data=_entry_data(
            target_entity="cover.pergola_tilt_demo",
            command_mode=ACTUATOR_MODE_COVER_TILT,
            tracking_mode=TRACKING_MAX_LIGHT,
        ),
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    initial_target = float(service_calls[-1]["tilt_position"])
    _set_cover_state(hass, "cover.pergola_tilt_demo", initial_target)
    await hass.async_block_till_done()
    service_calls.clear()

    _set_cover_state(hass, "cover.pergola_tilt_demo", 60)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.demo_pergola_manual_override").state == "on"

    _set_sun_state(hass, elevation=40.0)
    await hass.async_block_till_done()
    assert service_calls == []

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.demo_pergola_reset_manual_override"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.demo_pergola_manual_override").state == "off"
    assert service_calls
    assert service_calls[-1]["entity_id"] == "cover.pergola_tilt_demo"


async def test_manual_override_expires_and_resumes_automation(hass: HomeAssistant) -> None:
    _set_sun_state(hass, elevation=25.0)
    _set_cover_state(hass, "cover.pergola_tilt_demo", 0)
    service_calls: list[dict] = []
    _register_capture_service(hass, "cover", "set_cover_tilt_position", service_calls)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Demo Pergola",
        data=_entry_data(
            target_entity="cover.pergola_tilt_demo",
            command_mode=ACTUATOR_MODE_COVER_TILT,
            tracking_mode=TRACKING_MAX_LIGHT,
        ),
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    initial_target = float(service_calls[-1]["tilt_position"])
    _set_cover_state(hass, "cover.pergola_tilt_demo", initial_target)
    await hass.async_block_till_done()
    service_calls.clear()

    _set_cover_state(hass, "cover.pergola_tilt_demo", 60)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator._manual_override_until = dt_util.utcnow() - timedelta(seconds=1)

    _set_sun_state(hass, elevation=40.0)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.demo_pergola_manual_override").state == "off"
    assert service_calls
    assert service_calls[-1]["entity_id"] == "cover.pergola_tilt_demo"
