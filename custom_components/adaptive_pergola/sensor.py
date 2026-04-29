"""Sensor platform for Adaptive Pergola."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdaptivePergolaCoordinator
from .entity_base import AdaptivePergolaEntity
from .geometry_config import normalize_geometry_config


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Pergola sensors."""
    coordinator: AdaptivePergolaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AdaptivePergolaCommandSensor(coordinator),
            AdaptivePergolaAngleSensor(coordinator),
            AdaptivePergolaPenetrationSensor(coordinator),
            AdaptivePergolaStrategySensor(coordinator),
        ]
    )


class AdaptivePergolaCommandSensor(AdaptivePergolaEntity, SensorEntity):
    """Expose the current command value sent or recommended by the integration."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        """Initialize the command sensor."""
        super().__init__(coordinator, unique_suffix="command_value", name="Target Command")

    @property
    def native_value(self) -> float | None:
        """Return the mapped target command value."""
        return None if self.coordinator.data is None else self.coordinator.data.command_value

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return rich diagnostics for live testing."""
        data = self.coordinator.data
        if data is None:
            return {}
        config = normalize_geometry_config(self.coordinator.merged_config)
        projection = data.decision.projection
        return {
            "command_mode": data.command_mode,
            "target_entity": data.target_entity,
            "target_angle_deg": data.decision.target_angle_deg,
            "actuator_percent": data.decision.actuator_percent,
            "openness_percent": data.decision.openness_percent,
            "strategy": data.decision.strategy_used,
            "reason": data.decision.reason,
            "automatic_control": data.automatic_control,
            "auto_apply": data.auto_apply,
            "last_applied_value": data.last_applied_value,
            "manual_override_active": data.manual_override_active,
            "manual_override_until": (
                data.manual_override_until.isoformat()
                if data.manual_override_until is not None
                else None
            ),
            "manual_override_remaining_seconds": data.manual_override_remaining_seconds,
            "manual_override_value": data.manual_override_value,
            "weather_override_active": data.decision.weather_override_active,
            "sun_azimuth_deg": data.sun.azimuth_deg,
            "sun_elevation_deg": data.sun.elevation_deg,
            "slat_axis_azimuth_deg": config.get("slat_axis_azimuth_deg"),
            "pergola_orientation_azimuth_deg": config.get("pergola_orientation_azimuth_deg"),
            "opening_azimuth_deg": config.get("opening_azimuth_deg"),
            "closed_angle_deg": config.get("closed_angle_deg"),
            "open_angle_deg": config.get("open_angle_deg"),
            "open_actuator_percent": config.get("open_actuator_percent"),
            "max_travel_angle_deg": config.get("max_travel_angle_deg"),
            "closes_again_after_open": config.get("closes_again_after_open"),
            "has_additional_protected_area": config.get("has_additional_protected_area"),
            "additional_protected_area_length_m": config.get("additional_protected_area_length_m"),
            "additional_protected_area_width_m": config.get("additional_protected_area_width_m"),
            "additional_protected_area_offset_east_m": config.get("additional_protected_area_offset_east_m"),
            "additional_protected_area_offset_north_m": config.get("additional_protected_area_offset_north_m"),
            "slat_projected_elevation_deg": projection.projected_elevation_deg,
            "orientation_projected_elevation_deg": projection.orientation_projected_elevation_deg,
            "width_projected_elevation_deg": projection.width_projected_elevation_deg,
            "full_sun_depth_m": projection.full_sun_depth_m,
            "direct_sun_depth_m": projection.direct_sun_depth_m,
            "orientation_penetration_depth_m": projection.orientation_penetration_depth_m,
            "width_penetration_depth_m": projection.width_penetration_depth_m,
            "sun_patch_start_x_m": projection.sun_patch_start_x_m,
            "sun_patch_end_x_m": projection.sun_patch_end_x_m,
            "sun_patch_start_y_m": projection.sun_patch_start_y_m,
            "sun_patch_end_y_m": projection.sun_patch_end_y_m,
            "base_protected_overlap_m2": projection.base_protected_overlap_m2,
            "additional_protected_overlap_m2": projection.additional_protected_overlap_m2,
            "effective_protected_overlap_m2": projection.effective_protected_overlap_m2,
            "protected_zone_breached": projection.protected_zone_breached,
            "hits_house_wall": projection.hits_house_wall,
            "house_hit_height_m": projection.house_hit_height_m,
            "house_overlap_start_m": projection.house_overlap_start_m,
            "house_overlap_end_m": projection.house_overlap_end_m,
            "lateral_shift_on_house_m": projection.lateral_shift_on_house_m,
        }


class AdaptivePergolaAngleSensor(AdaptivePergolaEntity, SensorEntity):
    """Expose the computed lamella target angle."""

    _attr_native_unit_of_measurement = "°"

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        """Initialize the angle sensor."""
        super().__init__(coordinator, unique_suffix="target_angle", name="Target Angle")

    @property
    def native_value(self) -> float | None:
        """Return the target angle in degrees."""
        return None if self.coordinator.data is None else self.coordinator.data.decision.target_angle_deg


class AdaptivePergolaPenetrationSensor(AdaptivePergolaEntity, SensorEntity):
    """Expose the direct sun penetration depth below the pergola."""

    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        """Initialize the penetration sensor."""
        super().__init__(coordinator, unique_suffix="penetration", name="Direct Sun Penetration")

    @property
    def native_value(self) -> float | None:
        """Return the direct sun penetration depth in metres."""
        return None if self.coordinator.data is None else self.coordinator.data.decision.direct_sun_depth_m


class AdaptivePergolaStrategySensor(AdaptivePergolaEntity, SensorEntity):
    """Expose the currently active tracking strategy."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        """Initialize the strategy sensor."""
        super().__init__(coordinator, unique_suffix="strategy", name="Tracking Strategy")

    @property
    def native_value(self) -> str | None:
        """Return the active tracking strategy."""
        return None if self.coordinator.data is None else self.coordinator.data.decision.strategy_used
