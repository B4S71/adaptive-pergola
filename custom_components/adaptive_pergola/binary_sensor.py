"""Binary sensors for Adaptive Pergola."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdaptivePergolaCoordinator
from .entity_base import AdaptivePergolaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Pergola binary sensors."""
    coordinator: AdaptivePergolaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AdaptivePergolaWeatherOverrideBinarySensor(coordinator),
            AdaptivePergolaManualOverrideBinarySensor(coordinator),
            AdaptivePergolaProtectedZoneBinarySensor(coordinator),
            AdaptivePergolaHouseWallBinarySensor(coordinator),
        ]
    )


class AdaptivePergolaWeatherOverrideBinarySensor(AdaptivePergolaEntity, BinarySensorEntity):
    """Show whether weather safety override is currently active."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="weather_override", name="Weather Override")

    @property
    def is_on(self) -> bool | None:
        return None if self.coordinator.data is None else self.coordinator.data.decision.weather_override_active


class AdaptivePergolaManualOverrideBinarySensor(AdaptivePergolaEntity, BinarySensorEntity):
    """Show whether manual override is currently pausing automation."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="manual_override", name="Manual Override")

    @property
    def is_on(self) -> bool | None:
        return None if self.coordinator.data is None else self.coordinator.data.manual_override_active

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            "expires_at": (
                data.manual_override_until.isoformat()
                if data.manual_override_until is not None
                else None
            ),
            "remaining_seconds": data.manual_override_remaining_seconds,
            "manual_value": data.manual_override_value,
        }


class AdaptivePergolaProtectedZoneBinarySensor(AdaptivePergolaEntity, BinarySensorEntity):
    """Show whether the configured protected zone is currently breached."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="protected_zone", name="Protected Zone Breached")

    @property
    def is_on(self) -> bool | None:
        return None if self.coordinator.data is None else self.coordinator.data.decision.projection.protected_zone_breached


class AdaptivePergolaHouseWallBinarySensor(AdaptivePergolaEntity, BinarySensorEntity):
    """Show whether sunlight reaches the configured house wall."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="house_wall_hit", name="House Wall Hit")

    @property
    def is_on(self) -> bool | None:
        return None if self.coordinator.data is None else self.coordinator.data.decision.hits_house_wall
