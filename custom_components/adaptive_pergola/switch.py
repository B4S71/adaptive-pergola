"""Switch platform for Adaptive Pergola."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Adaptive Pergola switches."""
    coordinator: AdaptivePergolaCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AdaptivePergolaAutomaticControlSwitch(coordinator),
            AdaptivePergolaAutoApplySwitch(coordinator),
        ]
    )


class AdaptivePergolaAutomaticControlSwitch(AdaptivePergolaEntity, SwitchEntity):
    """Switch automatic control on and off."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="automatic_control", name="Automatic Control")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.automatic_control

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_automatic_control(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_automatic_control(False)


class AdaptivePergolaAutoApplySwitch(AdaptivePergolaEntity, SwitchEntity):
    """Switch live command application on and off."""

    def __init__(self, coordinator: AdaptivePergolaCoordinator) -> None:
        super().__init__(coordinator, unique_suffix="auto_apply", name="Live Apply")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.auto_apply

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_auto_apply(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_auto_apply(False)
