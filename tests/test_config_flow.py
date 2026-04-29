from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adaptive_pergola.const import (
    ACTUATOR_MODE_COVER_TILT,
    CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
    CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
    CONF_AUTOMATIC_CONTROL,
    CONF_AUTO_APPLY,
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
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _user_input() -> dict:
    return {
        CONF_NAME: "Pergola Demo",
        CONF_TARGET_ENTITY: "cover.pergola_tilt_demo",
        CONF_COMMAND_MODE: ACTUATOR_MODE_COVER_TILT,
        CONF_COMMAND_VALUE_MIN: 0.0,
        CONF_COMMAND_VALUE_MAX: 100.0,
        CONF_AUTOMATIC_CONTROL: True,
        CONF_AUTO_APPLY: True,
        CONF_MANUAL_OVERRIDE_DURATION: {"hours": 2},
        CONF_MANUAL_OVERRIDE_RESET: False,
        CONF_MANUAL_THRESHOLD: 5.0,
        CONF_MANUAL_IGNORE_INTERMEDIATE: False,
        CONF_TRACKING_MODE: TRACKING_BALANCED,
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
        CONF_OPEN_BEFORE_SUNRISE_MINUTES: 20,
        CONF_PREOPEN_ACTUATOR_PERCENT: 15,
        CONF_WIND_SPEED_THRESHOLD: 40.0,
        CONF_RAIN_THRESHOLD: 0.8,
        CONF_WEATHER_OVERRIDE_POSITION: 0,
    }


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "form"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _user_input(),
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Pergola Demo"
    assert result["data"][CONF_TARGET_ENTITY] == "cover.pergola_tilt_demo"
    assert result["data"][CONF_MANUAL_OVERRIDE_DURATION] == {"hours": 2}
    assert result["data"][CONF_MANUAL_THRESHOLD] == 5.0


async def test_user_flow_rejects_non_perpendicular_opening_direction(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "form"

    user_input = _user_input()
    user_input[CONF_OPENING_AZIMUTH_DEG] = user_input[CONF_SLAT_AXIS_AZIMUTH_DEG]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_OPENING_AZIMUTH_DEG] == "invalid_opening_direction"


async def test_user_flow_rejects_invalid_additional_protected_area_size(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "form"

    user_input = _user_input()
    user_input[CONF_HAS_ADDITIONAL_PROTECTED_AREA] = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M] == "invalid_protected_area_size"
    assert result["errors"][CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M] == "invalid_protected_area_size"


async def test_user_flow_rejects_invalid_shadow_casting_wall_size(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "form"

    user_input = _user_input()
    user_input[CONF_HAS_SHADOW_CASTING_WALL] = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_SHADOW_CASTING_WALL_LENGTH_M] == "invalid_shadow_wall_size"
    assert result["errors"][CONF_SHADOW_CASTING_WALL_HEIGHT_M] == "invalid_shadow_wall_size"


async def test_user_flow_rejects_invalid_open_actuator_percent(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    assert result["type"] == "form"

    user_input = _user_input()
    user_input[CONF_OPEN_ACTUATOR_PERCENT] = 120.0
    with pytest.raises(InvalidData) as exc:
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input,
        )

    assert exc.value.schema_errors[CONF_OPEN_ACTUATOR_PERCENT] == "Value 120.0 is too large"


async def test_import_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data=_user_input(),
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Pergola Demo"


async def test_options_flow_initializes_with_existing_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Pergola Demo",
        data=_user_input(),
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"
