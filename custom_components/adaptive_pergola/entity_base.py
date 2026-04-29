"""Shared entity base classes for Adaptive Pergola."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AdaptivePergolaCoordinator


class AdaptivePergolaEntity(CoordinatorEntity[AdaptivePergolaCoordinator]):
    """Base entity bound to the Adaptive Pergola coordinator."""

    def __init__(
        self,
        coordinator: AdaptivePergolaCoordinator,
        *,
        unique_suffix: str,
        name: str,
    ) -> None:
        """Initialize the shared entity fields."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_suffix}"
        self._attr_name = f"{coordinator.config_entry.title} {name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the virtual device for this controller."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=self.coordinator.config_entry.title,
            model="Pergola Sun Controller",
        )
