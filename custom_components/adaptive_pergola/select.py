"""Select platform for Adaptive Pergola."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TRACKING_STRATEGIES
from .coordinator import AdaptivePergolaCoordinator
from .entity_base import AdaptivePergolaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Pergola select entities."""
    coordinator: AdaptivePergolaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AdaptivePergolaTrackingModeSelect(coordinator)])


class AdaptivePergolaTrackingModeSelect(AdaptivePergolaEntity, SelectEntity):
    """Allow live switching between tracking strategies."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="tracking_mode", name="Tracking Mode")
        self._attr_options = TRACKING_STRATEGIES

    @property
    def current_option(self) -> str | None:
        return self.coordinator.tracking_mode

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_tracking_mode(option)
