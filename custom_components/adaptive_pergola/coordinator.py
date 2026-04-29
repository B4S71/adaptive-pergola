"""Runtime coordinator for Adaptive Pergola."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ACTUATOR_MODE_COVER_POSITION,
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
    CONF_IS_RAINING_SENSOR,
    CONF_IS_WINDY_SENSOR,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_DIRECT_SUN_DEPTH_M,
    CONF_MAX_TRAVEL_ANGLE_DEG,
    CONF_OPEN_ANGLE_DEG,
    CONF_OPEN_ACTUATOR_PERCENT,
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
    DEFAULT_AUTO_APPLY,
    DEFAULT_AUTOMATIC_CONTROL,
    DEFAULT_COMMAND_EPSILON,
    DEFAULT_COMMAND_VALUE_MAX,
    DEFAULT_COMMAND_VALUE_MIN,
    DEFAULT_MANUAL_IGNORE_INTERMEDIATE,
    DEFAULT_MANUAL_OVERRIDE_DURATION,
    DEFAULT_MANUAL_OVERRIDE_RESET,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
    DEFAULT_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
    DEFAULT_HAS_SHADOW_CASTING_WALL,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DEFAULT_SHADOW_CASTING_WALL_HEIGHT_M,
    DEFAULT_SHADOW_CASTING_WALL_LENGTH_M,
    DEFAULT_SHADOW_CASTING_WALL_OFFSET_EAST_M,
    DEFAULT_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
    DOMAIN,
    MANUAL_OVERRIDE_TOLERANCE_PERCENT,
    MANUAL_OVERRIDE_WAIT_FOR_TARGET_SECONDS,
    SUN_ENTITY_ID,
)
from .engine import command_value_from_decision, compute_tracking_decision
from .geometry_config import normalize_geometry_config
from .models import (
    ActuatorConfig,
    AdditionalProtectedAreaConfig,
    AdaptivePergolaData,
    CommandTarget,
    ControlConfig,
    HouseAttachment,
    PergolaGeometry,
    ShadowCastingWallConfig,
    SunPosition,
    TrackingConfig,
    WeatherConfig,
    WeatherReadings,
)

LOGGER = logging.getLogger(__name__)
_TRANSIENT_TARGET_STATES = {"opening", "closing"}


class AdaptivePergolaCoordinator(DataUpdateCoordinator[AdaptivePergolaData]):
    """Periodic calculation and command coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS),
        )
        self.config_entry = entry
        config = self.merged_config
        self.automatic_control = config.get(CONF_AUTOMATIC_CONTROL, DEFAULT_AUTOMATIC_CONTROL)
        self.auto_apply = config.get(CONF_AUTO_APPLY, DEFAULT_AUTO_APPLY)
        self.tracking_mode = config.get(CONF_TRACKING_MODE)
        self._last_applied_value: float | None = None
        self._force_apply_once = False
        self._force_apply_bypass_manual_override = False
        self._manual_override_until = None
        self._manual_override_value: float | None = None
        self._expected_target_value: float | None = None
        self._wait_for_target_until = None

    @property
    def merged_config(self) -> dict:
        """Return merged entry data and options."""
        return {**self.config_entry.data, **self.config_entry.options}

    @property
    def manual_override_active(self) -> bool:
        """Return whether a manual override is currently active."""
        return self._manual_override_until is not None and dt_util.utcnow() < self._manual_override_until

    @property
    def manual_override_until(self):
        """Return the expiry timestamp of the current manual override."""
        return self._manual_override_until if self.manual_override_active else None

    @property
    def manual_override_remaining_seconds(self) -> int:
        """Return the remaining override duration in whole seconds."""
        until = self.manual_override_until
        if until is None:
            return 0
        return max(0, int((until - dt_util.utcnow()).total_seconds()))

    def _queue_force_apply(self, *, bypass_manual_override: bool = False) -> None:
        """Schedule a one-shot apply on the next refresh."""
        self._force_apply_once = True
        self._force_apply_bypass_manual_override = (
            self._force_apply_bypass_manual_override or bypass_manual_override
        )

    def _manual_override_duration(self) -> timedelta:
        """Return the configured override duration."""
        duration = self.merged_config.get(
            CONF_MANUAL_OVERRIDE_DURATION,
            DEFAULT_MANUAL_OVERRIDE_DURATION,
        )
        if not isinstance(duration, dict):
            return timedelta()
        try:
            return timedelta(**duration)
        except TypeError:
            return timedelta()

    def _manual_override_should_reset(self) -> bool:
        """Return whether repeated manual moves extend the override timer."""
        return bool(
            self.merged_config.get(
                CONF_MANUAL_OVERRIDE_RESET,
                DEFAULT_MANUAL_OVERRIDE_RESET,
            )
        )

    def _manual_ignore_intermediate(self) -> bool:
        """Return whether transient opening/closing states should be ignored."""
        return bool(
            self.merged_config.get(
                CONF_MANUAL_IGNORE_INTERMEDIATE,
                DEFAULT_MANUAL_IGNORE_INTERMEDIATE,
            )
        )

    def _effective_manual_threshold(self) -> float:
        """Return the override threshold including the tolerance floor."""
        raw_threshold = self.merged_config.get(CONF_MANUAL_THRESHOLD)
        try:
            threshold = float(raw_threshold)
        except (TypeError, ValueError):
            threshold = 0.0
        return max(threshold, MANUAL_OVERRIDE_TOLERANCE_PERCENT)

    def _clear_wait_for_target(self) -> None:
        """Stop suppressing state changes for a pending command."""
        self._expected_target_value = None
        self._wait_for_target_until = None

    def _set_wait_for_target(self, expected_value: float) -> None:
        """Suppress manual-override detection while our command is in flight."""
        self._expected_target_value = expected_value
        self._wait_for_target_until = dt_util.utcnow() + timedelta(
            seconds=MANUAL_OVERRIDE_WAIT_FOR_TARGET_SECONDS
        )

    def _clear_manual_override(self) -> None:
        """Clear the active manual override state."""
        self._manual_override_until = None
        self._manual_override_value = None

    def _set_manual_override(self, current_value: float) -> None:
        """Enable or refresh manual override state after a user move."""
        was_active = self.manual_override_active
        if was_active and not self._manual_override_should_reset():
            self._manual_override_value = current_value
            return

        self._manual_override_until = dt_util.utcnow() + self._manual_override_duration()
        self._manual_override_value = current_value
        self.logger.debug(
            "Manual override %s until %s after target moved to %s",
            "refreshed" if was_active else "enabled",
            self._manual_override_until,
            current_value,
        )

    def _expire_manual_override_if_needed(self) -> bool:
        """Clear expired manual override state and report whether it changed."""
        if self._manual_override_until is None:
            return False
        if dt_util.utcnow() < self._manual_override_until:
            return False
        self.logger.debug("Manual override expired")
        self._clear_manual_override()
        return True

    async def async_handle_state_change(self, event: Event) -> None:
        """Refresh immediately when a tracked dependency or target changes."""
        entity_id = event.data.get("entity_id")
        if entity_id == self.merged_config.get(CONF_TARGET_ENTITY):
            await self.async_handle_target_change(event)
        else:
            self.logger.debug("Dependency changed: %s", entity_id)
        await self.async_refresh()

    async def async_handle_target_change(self, event: Event) -> None:
        """Detect manual target movements and start a temporary automation pause."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return

        mode = self.merged_config.get(CONF_COMMAND_MODE)
        if mode is None:
            return

        if self._manual_ignore_intermediate() and new_state.state in _TRANSIENT_TARGET_STATES:
            return

        current_value = self._target_value_from_state(new_state, mode=mode)
        if current_value is None:
            return

        old_value = self._target_value_from_state(old_state, mode=mode)
        if old_value is not None and abs(old_value - current_value) < DEFAULT_COMMAND_EPSILON:
            return

        if self._wait_for_target_until is not None:
            if (
                self._expected_target_value is not None
                and abs(current_value - self._expected_target_value)
                < MANUAL_OVERRIDE_TOLERANCE_PERCENT
            ):
                self._clear_wait_for_target()
                return
            if dt_util.utcnow() < self._wait_for_target_until:
                return
            self._clear_wait_for_target()

        expected_value = self._expected_target_value
        if expected_value is None:
            expected_value = self._last_applied_value
        if expected_value is None and self.data is not None:
            expected_value = self.data.command_value
        if expected_value is None:
            return

        delta = abs(current_value - expected_value)
        threshold = self._effective_manual_threshold()
        if delta < threshold:
            return

        self._set_manual_override(current_value)

    async def async_set_automatic_control(self, enabled: bool) -> None:
        """Toggle automatic control."""
        self.automatic_control = enabled
        if enabled and self.auto_apply:
            self._queue_force_apply()
        await self.async_refresh()

    async def async_set_auto_apply(self, enabled: bool) -> None:
        """Toggle live command application."""
        self.auto_apply = enabled
        if enabled and self.automatic_control:
            self._queue_force_apply()
        await self.async_refresh()

    async def async_set_tracking_mode(self, mode: str) -> None:
        """Switch tracking strategy at runtime."""
        self.tracking_mode = mode
        if self.auto_apply and self.automatic_control:
            self._queue_force_apply()
        await self.async_refresh()

    async def async_apply_current_decision(self) -> None:
        """Force-send the currently computed target value once."""
        self._queue_force_apply(bypass_manual_override=True)
        await self.async_refresh()

    async def async_reset_manual_override(self) -> None:
        """Clear manual override and optionally re-apply the current target."""
        self._clear_manual_override()
        if self.automatic_control and self.auto_apply:
            self._queue_force_apply(bypass_manual_override=True)
        await self.async_refresh()

    def _read_float(self, entity_id: str | None) -> float | None:
        """Read a float state from Home Assistant."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable"}:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def _is_on(self, entity_id: str | None) -> bool:
        """Read a binary-like state from Home Assistant."""
        if not entity_id:
            return False
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == "on"

    def _read_sun(self) -> tuple[SunPosition, object | None]:
        """Read sun position and next sunrise from sun.sun."""
        state = self.hass.states.get(SUN_ENTITY_ID)
        if state is None:
            raise UpdateFailed("sun.sun is not available")
        try:
            azimuth = float(state.attributes["azimuth"])
            elevation = float(state.attributes["elevation"])
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed("sun.sun is missing azimuth/elevation") from err
        next_rising = dt_util.parse_datetime(state.attributes.get("next_rising"))
        return (SunPosition(azimuth_deg=azimuth, elevation_deg=elevation), next_rising)

    def _build_control_config(self) -> ControlConfig:
        """Build typed runtime configuration from entry settings."""
        config = normalize_geometry_config(self.merged_config)
        house = None
        if config.get(CONF_HAS_HOUSE_ATTACHMENT):
            house = HouseAttachment(
                height_m=float(config.get(CONF_HOUSE_HEIGHT_M, 0.0)),
                extends_left_m=float(config.get(CONF_HOUSE_EXTENDS_LEFT_M, 0.0)),
                extends_right_m=float(config.get(CONF_HOUSE_EXTENDS_RIGHT_M, 0.0)),
            )

        weather_sensor_configured = any(
            config.get(key)
            for key in [
                CONF_WIND_SPEED_SENSOR,
                CONF_RAIN_SENSOR,
                CONF_IS_RAINING_SENSOR,
                CONF_IS_WINDY_SENSOR,
            ]
        ) or bool(config.get(CONF_SEVERE_SENSORS, []))

        weather = None
        if weather_sensor_configured:
            weather = WeatherConfig(
                override_actuator_percent=int(config.get(CONF_WEATHER_OVERRIDE_POSITION, 0)),
                wind_speed_threshold=float(config.get(CONF_WIND_SPEED_THRESHOLD, 0.0)),
                rain_threshold=float(config.get(CONF_RAIN_THRESHOLD, 0.0)),
                severe_binary_enabled=True,
            )

        additional_protected_area = AdditionalProtectedAreaConfig(
            enabled=bool(config.get(CONF_HAS_ADDITIONAL_PROTECTED_AREA, False)),
            length_m=float(
                config.get(
                    CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
                    DEFAULT_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
                )
            ),
            width_m=float(
                config.get(
                    CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
                    DEFAULT_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
                )
            ),
            offset_east_m=float(
                config.get(
                    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
                    DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
                )
            ),
            offset_north_m=float(
                config.get(
                    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
                    DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
                )
            ),
        )
        shadow_casting_wall = ShadowCastingWallConfig(
            enabled=bool(
                config.get(CONF_HAS_SHADOW_CASTING_WALL, DEFAULT_HAS_SHADOW_CASTING_WALL)
            ),
            length_m=float(
                config.get(
                    CONF_SHADOW_CASTING_WALL_LENGTH_M,
                    DEFAULT_SHADOW_CASTING_WALL_LENGTH_M,
                )
            ),
            height_m=float(
                config.get(
                    CONF_SHADOW_CASTING_WALL_HEIGHT_M,
                    DEFAULT_SHADOW_CASTING_WALL_HEIGHT_M,
                )
            ),
            offset_east_m=float(
                config.get(
                    CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
                    DEFAULT_SHADOW_CASTING_WALL_OFFSET_EAST_M,
                )
            ),
            offset_north_m=float(
                config.get(
                    CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
                    DEFAULT_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
                )
            ),
        )

        return ControlConfig(
            geometry=PergolaGeometry(
                slat_width_m=float(config[CONF_SLAT_WIDTH_M]),
                slat_thickness_m=float(config[CONF_SLAT_THICKNESS_M]),
                slat_axis_spacing_m=float(config[CONF_SLAT_AXIS_SPACING_M]),
                slat_axis_height_m=float(config[CONF_SLAT_AXIS_HEIGHT_M]),
                pergola_length_m=float(config[CONF_PERGOLA_LENGTH_M]),
                pergola_width_m=float(config[CONF_PERGOLA_WIDTH_M]),
                slat_axis_azimuth_deg=float(config[CONF_SLAT_AXIS_AZIMUTH_DEG]),
                pergola_orientation_azimuth_deg=float(config[CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG]),
                opening_azimuth_deg=float(config[CONF_OPENING_AZIMUTH_DEG]),
                house_attachment=house,
            ),
            actuator=ActuatorConfig(
                closed_angle_deg=float(config[CONF_CLOSED_ANGLE_DEG]),
                open_angle_deg=float(config[CONF_OPEN_ANGLE_DEG]),
                max_travel_angle_deg=float(config[CONF_MAX_TRAVEL_ANGLE_DEG]),
                open_actuator_percent=(
                    float(config[CONF_OPEN_ACTUATOR_PERCENT])
                    if CONF_OPEN_ACTUATOR_PERCENT in config
                    else None
                ),
                closes_again_after_open=bool(config.get(CONF_CLOSES_AGAIN_AFTER_OPEN, False)),
            ),
            target=CommandTarget(
                entity_id=config[CONF_TARGET_ENTITY],
                mode=config[CONF_COMMAND_MODE],
                value_min=float(config.get(CONF_COMMAND_VALUE_MIN, DEFAULT_COMMAND_VALUE_MIN)),
                value_max=float(config.get(CONF_COMMAND_VALUE_MAX, DEFAULT_COMMAND_VALUE_MAX)),
            ),
            tracking=TrackingConfig(
                strategy=self.tracking_mode or config[CONF_TRACKING_MODE],
                max_direct_sun_depth_m=float(config[CONF_MAX_DIRECT_SUN_DEPTH_M]),
                open_before_sunrise_minutes=int(config[CONF_OPEN_BEFORE_SUNRISE_MINUTES]),
                preopen_actuator_percent=int(config[CONF_PREOPEN_ACTUATOR_PERCENT]),
            ),
            weather=weather,
            additional_protected_area=additional_protected_area,
            shadow_casting_wall=shadow_casting_wall,
        )

    def _read_weather(self) -> WeatherReadings:
        """Read current weather inputs from configured entities."""
        config = self.merged_config
        return WeatherReadings(
            wind_speed=self._read_float(config.get(CONF_WIND_SPEED_SENSOR)),
            rain_rate=self._read_float(config.get(CONF_RAIN_SENSOR)),
            is_raining=self._is_on(config.get(CONF_IS_RAINING_SENSOR)),
            is_windy=self._is_on(config.get(CONF_IS_WINDY_SENSOR)),
            severe=any(self._is_on(entity_id) for entity_id in config.get(CONF_SEVERE_SENSORS, [])),
        )

    def _target_value_from_state(self, state: State | None, *, mode: str) -> float | None:
        """Read a target value from a Home Assistant state object."""
        if state is None:
            return None
        if mode == ACTUATOR_MODE_COVER_TILT:
            value = state.attributes.get("current_tilt_position")
        elif mode == ACTUATOR_MODE_COVER_POSITION:
            value = state.attributes.get("current_position")
        else:
            value = state.state
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _current_target_value(self, target: CommandTarget) -> float | None:
        """Read the current actuator value from the target entity."""
        return self._target_value_from_state(
            self.hass.states.get(target.entity_id),
            mode=target.mode,
        )

    async def _async_apply_command(self, target: CommandTarget, command_value: float, *, force: bool) -> None:
        """Send the calculated command to the configured entity."""
        current = self._current_target_value(target)
        if (
            not force
            and current is not None
            and abs(current - command_value) < DEFAULT_COMMAND_EPSILON
        ):
            self._last_applied_value = current
            self._clear_wait_for_target()
            return

        if target.mode == ACTUATOR_MODE_COVER_TILT:
            await self.hass.services.async_call(
                "cover",
                "set_cover_tilt_position",
                {
                    "entity_id": target.entity_id,
                    "tilt_position": int(round(command_value)),
                },
                blocking=False,
            )
            self._last_applied_value = float(int(round(command_value)))
            self._set_wait_for_target(self._last_applied_value)
            return

        if target.mode == ACTUATOR_MODE_COVER_POSITION:
            await self.hass.services.async_call(
                "cover",
                "set_cover_position",
                {
                    "entity_id": target.entity_id,
                    "position": int(round(command_value)),
                },
                blocking=False,
            )
            self._last_applied_value = float(int(round(command_value)))
            self._set_wait_for_target(self._last_applied_value)
            return

        domain = target.entity_id.split(".", maxsplit=1)[0]
        await self.hass.services.async_call(
            domain,
            "set_value",
            {
                "entity_id": target.entity_id,
                "value": round(command_value, 2),
            },
            blocking=False,
        )
        self._last_applied_value = round(command_value, 2)
        self._set_wait_for_target(self._last_applied_value)

    async def _async_update_data(self) -> AdaptivePergolaData:
        """Recompute state and optionally apply the new target."""
        control_config = self._build_control_config()
        sun, next_rising = self._read_sun()
        weather = self._read_weather()
        self._expire_manual_override_if_needed()

        decision = compute_tracking_decision(
            control_config,
            sun,
            weather,
            now=dt_util.now(),
            next_sunrise=next_rising,
        )
        command_value = command_value_from_decision(control_config.target, decision)

        force_apply = self._force_apply_once
        bypass_manual_override = self._force_apply_bypass_manual_override
        self._force_apply_once = False
        self._force_apply_bypass_manual_override = False
        if force_apply or (self.automatic_control and self.auto_apply):
            if (
                self.manual_override_active
                and not bypass_manual_override
                and not decision.weather_override_active
            ):
                self.logger.debug(
                    "Skipping auto-apply because manual override is active until %s",
                    self.manual_override_until,
                )
            else:
                await self._async_apply_command(
                    control_config.target,
                    command_value,
                    force=force_apply,
                )

        return AdaptivePergolaData(
            sun=sun,
            weather=weather,
            decision=decision,
            command_value=round(command_value, 2),
            command_mode=control_config.target.mode,
            target_entity=control_config.target.entity_id,
            automatic_control=self.automatic_control,
            auto_apply=self.auto_apply,
            last_applied_value=self._last_applied_value,
            manual_override_active=self.manual_override_active,
            manual_override_until=self.manual_override_until,
            manual_override_remaining_seconds=self.manual_override_remaining_seconds,
            manual_override_value=self._manual_override_value,
        )