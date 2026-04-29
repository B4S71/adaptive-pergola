"""Button platform for Adaptive Pergola."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up Adaptive Pergola buttons."""
    coordinator: AdaptivePergolaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AdaptivePergolaApplyNowButton(coordinator),
            AdaptivePergolaResetManualOverrideButton(coordinator),
        ]
    )


class AdaptivePergolaApplyNowButton(AdaptivePergolaEntity, ButtonEntity):
    """Force-apply the current target value once."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="apply_now", name="Apply Target Now")

    async def async_press(self) -> None:
        await self.coordinator.async_apply_current_decision()


class AdaptivePergolaResetManualOverrideButton(AdaptivePergolaEntity, ButtonEntity):
    """Clear manual override and resume automatic control immediately."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(
            coordinator,
            unique_suffix="reset_manual_override",
            name="Reset Manual Override",
        )

    async def async_press(self) -> None:
        await self.coordinator.async_reset_manual_override()
