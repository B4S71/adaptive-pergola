"""Config flow for Adaptive Pergola."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    ACTUATOR_MODE_COVER_POSITION,
    ACTUATOR_MODE_COVER_TILT,
    ACTUATOR_MODE_NUMBER_ANGLE,
    ACTUATOR_MODE_NUMBER_CUSTOM,
    ACTUATOR_MODE_NUMBER_PERCENT,
    ACTUATOR_MODES,
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
    CONF_IS_RAINING_SENSOR,
    CONF_IS_WINDY_SENSOR,
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
    CONF_RAIN_SENSOR,
    CONF_RAIN_THRESHOLD,
    CONF_SHADOW_CASTING_WALL_HEIGHT_M,
    CONF_SHADOW_CASTING_WALL_LENGTH_M,
    CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
    CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
    CONF_SLAT_AXIS_AZIMUTH_DEG,
    CONF_SEVERE_SENSORS,
    CONF_SLAT_AXIS_HEIGHT_M,
    CONF_SLAT_AXIS_SPACING_M,
    CONF_SLAT_THICKNESS_M,
    CONF_SLAT_WIDTH_M,
    CONF_TARGET_ENTITY,
    CONF_TRACKING_MODE,
    CONF_WEATHER_OVERRIDE_POSITION,
    CONF_WIND_SPEED_SENSOR,
    CONF_WIND_SPEED_THRESHOLD,
    DEFAULT_AUTOMATIC_CONTROL,
    DEFAULT_AUTO_APPLY,
    DEFAULT_MANUAL_IGNORE_INTERMEDIATE,
    DEFAULT_MANUAL_OVERRIDE_DURATION,
    DEFAULT_MANUAL_OVERRIDE_RESET,
    DEFAULT_CLOSES_AGAIN_AFTER_OPEN,
    DEFAULT_CLOSED_ANGLE_DEG,
    DEFAULT_COMMAND_MODE,
    DEFAULT_COMMAND_VALUE_MAX,
    DEFAULT_COMMAND_VALUE_MIN,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
    DEFAULT_HAS_HOUSE_ATTACHMENT,
    DEFAULT_HAS_ADDITIONAL_PROTECTED_AREA,
    DEFAULT_HAS_SHADOW_CASTING_WALL,
    DEFAULT_HOUSE_EXTENDS_LEFT_M,
    DEFAULT_HOUSE_EXTENDS_RIGHT_M,
    DEFAULT_HOUSE_HEIGHT_M,
    DEFAULT_MAX_DIRECT_SUN_DEPTH_M,
    DEFAULT_MAX_TRAVEL_ANGLE_DEG,
    DEFAULT_NAME,
    DEFAULT_OPEN_ANGLE_DEG,
    DEFAULT_OPENING_AZIMUTH_DEG,
    DEFAULT_OPEN_BEFORE_SUNRISE_MINUTES,
    DEFAULT_PERGOLA_LENGTH_M,
    DEFAULT_PERGOLA_ORIENTATION_AZIMUTH_DEG,
    DEFAULT_PERGOLA_WIDTH_M,
    DEFAULT_PREOPEN_ACTUATOR_PERCENT,
    DEFAULT_RAIN_THRESHOLD,
    DEFAULT_SHADOW_CASTING_WALL_HEIGHT_M,
    DEFAULT_SHADOW_CASTING_WALL_LENGTH_M,
    DEFAULT_SHADOW_CASTING_WALL_OFFSET_EAST_M,
    DEFAULT_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
    DEFAULT_SLAT_AXIS_AZIMUTH_DEG,
    DEFAULT_SLAT_AXIS_HEIGHT_M,
    DEFAULT_SLAT_AXIS_SPACING_M,
    DEFAULT_SLAT_THICKNESS_M,
    DEFAULT_SLAT_WIDTH_M,
    DEFAULT_TRACKING_MODE,
    DEFAULT_WEATHER_OVERRIDE_POSITION,
    DEFAULT_WIND_SPEED_THRESHOLD,
    DOMAIN,
    TRACKING_STRATEGIES,
)
from .geometry_config import (
    normalize_geometry_config,
    strip_legacy_geometry_keys,
    validate_opening_direction,
)
from .models import derived_open_actuator_percent


def _schema(current: dict[str, Any], *, include_name: bool) -> vol.Schema:
    """Build the setup schema with defaults."""
    current = normalize_geometry_config(current)
    open_actuator_percent_default = current.get(
        CONF_OPEN_ACTUATOR_PERCENT,
        derived_open_actuator_percent(
            float(current.get(CONF_CLOSED_ANGLE_DEG, DEFAULT_CLOSED_ANGLE_DEG)),
            float(current.get(CONF_OPEN_ANGLE_DEG, DEFAULT_OPEN_ANGLE_DEG)),
            float(current.get(CONF_MAX_TRAVEL_ANGLE_DEG, DEFAULT_MAX_TRAVEL_ANGLE_DEG)),
        ),
    )
    schema: dict[Any, Any] = {
        vol.Required(
            CONF_TARGET_ENTITY,
            default=current.get(CONF_TARGET_ENTITY, vol.UNDEFINED),
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["cover", "number", "input_number"])
        ),
        vol.Required(
            CONF_COMMAND_MODE,
            default=current.get(CONF_COMMAND_MODE, DEFAULT_COMMAND_MODE),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=ACTUATOR_MODES, mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(
            CONF_COMMAND_VALUE_MIN,
            default=current.get(CONF_COMMAND_VALUE_MIN, DEFAULT_COMMAND_VALUE_MIN),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_COMMAND_VALUE_MAX,
            default=current.get(CONF_COMMAND_VALUE_MAX, DEFAULT_COMMAND_VALUE_MAX),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_AUTOMATIC_CONTROL,
            default=current.get(CONF_AUTOMATIC_CONTROL, DEFAULT_AUTOMATIC_CONTROL),
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_AUTO_APPLY,
            default=current.get(CONF_AUTO_APPLY, DEFAULT_AUTO_APPLY),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_MANUAL_OVERRIDE_DURATION,
            default=current.get(
                CONF_MANUAL_OVERRIDE_DURATION,
                dict(DEFAULT_MANUAL_OVERRIDE_DURATION),
            ),
        ): selector.DurationSelector(),
        vol.Optional(
            CONF_MANUAL_OVERRIDE_RESET,
            default=current.get(CONF_MANUAL_OVERRIDE_RESET, DEFAULT_MANUAL_OVERRIDE_RESET),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_MANUAL_THRESHOLD,
            default=current.get(CONF_MANUAL_THRESHOLD, vol.UNDEFINED),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=99,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(
            CONF_MANUAL_IGNORE_INTERMEDIATE,
            default=current.get(
                CONF_MANUAL_IGNORE_INTERMEDIATE,
                DEFAULT_MANUAL_IGNORE_INTERMEDIATE,
            ),
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_TRACKING_MODE,
            default=current.get(CONF_TRACKING_MODE, DEFAULT_TRACKING_MODE),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=TRACKING_STRATEGIES, mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Required(
            CONF_SLAT_WIDTH_M,
            default=current.get(CONF_SLAT_WIDTH_M, DEFAULT_SLAT_WIDTH_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.05, max=0.5, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_SLAT_THICKNESS_M,
            default=current.get(CONF_SLAT_THICKNESS_M, DEFAULT_SLAT_THICKNESS_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.005, max=0.1, step=0.001, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_SLAT_AXIS_SPACING_M,
            default=current.get(CONF_SLAT_AXIS_SPACING_M, DEFAULT_SLAT_AXIS_SPACING_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0.05, max=0.5, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_SLAT_AXIS_HEIGHT_M,
            default=current.get(CONF_SLAT_AXIS_HEIGHT_M, DEFAULT_SLAT_AXIS_HEIGHT_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1.5, max=5.0, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_PERGOLA_LENGTH_M,
            default=current.get(CONF_PERGOLA_LENGTH_M, DEFAULT_PERGOLA_LENGTH_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1.0, max=10.0, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_PERGOLA_WIDTH_M,
            default=current.get(CONF_PERGOLA_WIDTH_M, DEFAULT_PERGOLA_WIDTH_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1.0, max=10.0, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_SLAT_AXIS_AZIMUTH_DEG,
            default=current.get(CONF_SLAT_AXIS_AZIMUTH_DEG, DEFAULT_SLAT_AXIS_AZIMUTH_DEG),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=359, step=1, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG,
            default=current.get(
                CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG,
                DEFAULT_PERGOLA_ORIENTATION_AZIMUTH_DEG,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=359, step=1, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_OPENING_AZIMUTH_DEG,
            default=current.get(CONF_OPENING_AZIMUTH_DEG, DEFAULT_OPENING_AZIMUTH_DEG),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=359, step=1, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_CLOSED_ANGLE_DEG,
            default=current.get(CONF_CLOSED_ANGLE_DEG, DEFAULT_CLOSED_ANGLE_DEG),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=180, step=1, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_OPEN_ANGLE_DEG,
            default=current.get(CONF_OPEN_ANGLE_DEG, DEFAULT_OPEN_ANGLE_DEG),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=180, step=1, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_OPEN_ACTUATOR_PERCENT,
            default=open_actuator_percent_default,
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_MAX_TRAVEL_ANGLE_DEG,
            default=current.get(CONF_MAX_TRAVEL_ANGLE_DEG, DEFAULT_MAX_TRAVEL_ANGLE_DEG),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=180, step=1, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_CLOSES_AGAIN_AFTER_OPEN,
            default=current.get(CONF_CLOSES_AGAIN_AFTER_OPEN, DEFAULT_CLOSES_AGAIN_AFTER_OPEN),
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_HAS_HOUSE_ATTACHMENT,
            default=current.get(CONF_HAS_HOUSE_ATTACHMENT, DEFAULT_HAS_HOUSE_ATTACHMENT),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_HOUSE_HEIGHT_M,
            default=current.get(CONF_HOUSE_HEIGHT_M, DEFAULT_HOUSE_HEIGHT_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_HOUSE_EXTENDS_LEFT_M,
            default=current.get(CONF_HOUSE_EXTENDS_LEFT_M, DEFAULT_HOUSE_EXTENDS_LEFT_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_HOUSE_EXTENDS_RIGHT_M,
            default=current.get(CONF_HOUSE_EXTENDS_RIGHT_M, DEFAULT_HOUSE_EXTENDS_RIGHT_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_HAS_ADDITIONAL_PROTECTED_AREA,
            default=current.get(
                CONF_HAS_ADDITIONAL_PROTECTED_AREA,
                DEFAULT_HAS_ADDITIONAL_PROTECTED_AREA,
            ),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
            default=current.get(
                CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
                DEFAULT_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
            default=current.get(
                CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
                DEFAULT_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
            default=current.get(
                CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
                DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-20, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
            default=current.get(
                CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
                DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-20, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_HAS_SHADOW_CASTING_WALL,
            default=current.get(
                CONF_HAS_SHADOW_CASTING_WALL,
                DEFAULT_HAS_SHADOW_CASTING_WALL,
            ),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_SHADOW_CASTING_WALL_LENGTH_M,
            default=current.get(
                CONF_SHADOW_CASTING_WALL_LENGTH_M,
                DEFAULT_SHADOW_CASTING_WALL_LENGTH_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_SHADOW_CASTING_WALL_HEIGHT_M,
            default=current.get(
                CONF_SHADOW_CASTING_WALL_HEIGHT_M,
                DEFAULT_SHADOW_CASTING_WALL_HEIGHT_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
            default=current.get(
                CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
                DEFAULT_SHADOW_CASTING_WALL_OFFSET_EAST_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-20, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
            default=current.get(
                CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
                DEFAULT_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
            ),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-20, max=20, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_MAX_DIRECT_SUN_DEPTH_M,
            default=current.get(CONF_MAX_DIRECT_SUN_DEPTH_M, DEFAULT_MAX_DIRECT_SUN_DEPTH_M),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=0.01, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_OPEN_BEFORE_SUNRISE_MINUTES,
            default=current.get(CONF_OPEN_BEFORE_SUNRISE_MINUTES, DEFAULT_OPEN_BEFORE_SUNRISE_MINUTES),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=180, step=1, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(
            CONF_PREOPEN_ACTUATOR_PERCENT,
            default=current.get(CONF_PREOPEN_ACTUATOR_PERCENT, DEFAULT_PREOPEN_ACTUATOR_PERCENT),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_WIND_SPEED_SENSOR,
            default=current.get(CONF_WIND_SPEED_SENSOR, vol.UNDEFINED),
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"])),
        vol.Optional(
            CONF_RAIN_SENSOR,
            default=current.get(CONF_RAIN_SENSOR, vol.UNDEFINED),
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"])),
        vol.Optional(
            CONF_IS_RAINING_SENSOR,
            default=current.get(CONF_IS_RAINING_SENSOR, vol.UNDEFINED),
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"])),
        vol.Optional(
            CONF_IS_WINDY_SENSOR,
            default=current.get(CONF_IS_WINDY_SENSOR, vol.UNDEFINED),
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"])),
        vol.Optional(
            CONF_SEVERE_SENSORS,
            default=current.get(CONF_SEVERE_SENSORS, []),
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"], multiple=True)
        ),
        vol.Optional(
            CONF_WIND_SPEED_THRESHOLD,
            default=current.get(CONF_WIND_SPEED_THRESHOLD, DEFAULT_WIND_SPEED_THRESHOLD),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=200, step=0.1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_RAIN_THRESHOLD,
            default=current.get(CONF_RAIN_THRESHOLD, DEFAULT_RAIN_THRESHOLD),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=0.1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(
            CONF_WEATHER_OVERRIDE_POSITION,
            default=current.get(CONF_WEATHER_OVERRIDE_POSITION, DEFAULT_WEATHER_OVERRIDE_POSITION),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
        ),
    }
    if include_name:
        schema = {
            vol.Required(CONF_NAME, default=current.get(CONF_NAME, DEFAULT_NAME)): selector.TextSelector(),
            **schema,
        }
    return vol.Schema(schema)


def _validate(data: dict[str, Any], *, include_name: bool) -> dict[str, str]:
    """Validate cross-field configuration rules."""
    data = normalize_geometry_config(data)
    errors: dict[str, str] = {}
    target_entity = data.get(CONF_TARGET_ENTITY, "")
    command_mode = data.get(CONF_COMMAND_MODE)

    if command_mode in {ACTUATOR_MODE_COVER_TILT, ACTUATOR_MODE_COVER_POSITION} and not target_entity.startswith("cover."):
        errors[CONF_TARGET_ENTITY] = "invalid_target_domain"

    if command_mode in {
        ACTUATOR_MODE_NUMBER_ANGLE,
        ACTUATOR_MODE_NUMBER_PERCENT,
        ACTUATOR_MODE_NUMBER_CUSTOM,
    } and not target_entity.startswith(("number.", "input_number.")):
        errors[CONF_TARGET_ENTITY] = "invalid_target_domain"

    closed_angle = float(data.get(CONF_CLOSED_ANGLE_DEG, 0.0))
    open_angle = float(data.get(CONF_OPEN_ANGLE_DEG, 0.0))
    max_travel = float(data.get(CONF_MAX_TRAVEL_ANGLE_DEG, 0.0))
    open_actuator_percent = float(
        data.get(
            CONF_OPEN_ACTUATOR_PERCENT,
            derived_open_actuator_percent(closed_angle, open_angle, max_travel),
        )
    )
    if not (closed_angle <= open_angle <= max_travel):
        errors[CONF_OPEN_ANGLE_DEG] = "invalid_angle_range"

    if not (0.0 <= open_actuator_percent <= 100.0):
        errors[CONF_OPEN_ACTUATOR_PERCENT] = "invalid_percentage_range"

    if command_mode == ACTUATOR_MODE_NUMBER_CUSTOM and float(data.get(CONF_COMMAND_VALUE_MIN, 0.0)) == float(data.get(CONF_COMMAND_VALUE_MAX, 0.0)):
        errors[CONF_COMMAND_VALUE_MAX] = "invalid_custom_range"

    if data.get(CONF_HAS_HOUSE_ATTACHMENT) and float(data.get(CONF_HOUSE_HEIGHT_M, 0.0)) <= 0:
        errors[CONF_HOUSE_HEIGHT_M] = "invalid_house_height"

    if data.get(CONF_HAS_ADDITIONAL_PROTECTED_AREA):
        if float(data.get(CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M, 0.0)) <= 0:
            errors[CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M] = "invalid_protected_area_size"
        if float(data.get(CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M, 0.0)) <= 0:
            errors[CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M] = "invalid_protected_area_size"

    if data.get(CONF_HAS_SHADOW_CASTING_WALL):
        if float(data.get(CONF_SHADOW_CASTING_WALL_LENGTH_M, 0.0)) <= 0:
            errors[CONF_SHADOW_CASTING_WALL_LENGTH_M] = "invalid_shadow_wall_size"
        if float(data.get(CONF_SHADOW_CASTING_WALL_HEIGHT_M, 0.0)) <= 0:
            errors[CONF_SHADOW_CASTING_WALL_HEIGHT_M] = "invalid_shadow_wall_size"

    if not validate_opening_direction(data):
        errors[CONF_OPENING_AZIMUTH_DEG] = "invalid_opening_direction"

    if include_name and not str(data.get(CONF_NAME, "")).strip():
        errors[CONF_NAME] = "required"

    return errors


class AdaptivePergolaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Pergola."""

    VERSION = 6

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input, include_name=True)
            if not errors:
                stored_input = strip_legacy_geometry_keys(user_input)
                await self.async_set_unique_id(stored_input[CONF_TARGET_ENTITY])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=stored_input[CONF_NAME],
                    data=stored_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}, include_name=True),
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Import a YAML-configured pergola entry."""
        errors = _validate(user_input, include_name=True)
        if errors:
            return self.async_abort(reason="invalid_import")
        stored_input = strip_legacy_geometry_keys(user_input)
        await self.async_set_unique_id(stored_input[CONF_TARGET_ENTITY])
        self._abort_if_unique_id_configured(updates=stored_input)
        return self.async_create_entry(title=stored_input[CONF_NAME], data=stored_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return AdaptivePergolaOptionsFlow()


class AdaptivePergolaOptionsFlow(OptionsFlow):
    """Handle Adaptive Pergola options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        current = normalize_geometry_config({**self.config_entry.data, **self.config_entry.options})
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input, include_name=False)
            if not errors:
                return self.async_create_entry(title="", data=strip_legacy_geometry_keys(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or current, include_name=False),
            errors=errors,
        )
