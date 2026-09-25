"""Persistent per-slot latches for custom-position release conditions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store

from ..const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class CustomPositionHysteresis:
    """Hold an activated slot until its separate release condition is true.

    Activation wins if both conditions are true. A changed slot definition
    invalidates its saved state so an old latch cannot activate a new rule.
    """

    def __init__(self, hass: HomeAssistant | None = None, entry_id: str | None = None):
        """Create an in-memory latch, optionally backed by HA storage."""
        self._states: dict[str, dict] = {}
        self._released_slots: set[int] = set()
        self._store = (
            Store(hass, 1, f"{DOMAIN}.{entry_id}.custom_position_hysteresis")
            if hass is not None and entry_id is not None
            else None
        )

    async def async_load(self) -> None:
        """Restore states before the first control cycle."""
        if self._store is not None:
            self._states = await self._store.async_load() or {}

    async def async_save(self) -> None:
        """Flush pending changes when unloading the entry."""
        if self._store is not None:
            await self._store.async_save(self._states)

    async def async_remove(self) -> None:
        """Remove storage when the entry is deleted."""
        if self._store is not None:
            await self._store.async_remove()

    def _changed(self) -> None:
        if self._store is not None:
            self._store.async_delay_save(lambda: self._states, 1)

    def clear(self, slot: int) -> None:
        """Forget disabled, removed or non-hysteretic slots."""
        self._released_slots.discard(slot)
        if self._states.pop(str(slot), None) is not None:
            self._changed()

    def pop_released_slots(self) -> set[int]:
        """Consume release edges, including a restored latch released at startup."""
        released, self._released_slots = self._released_slots, set()
        return released

    def evaluate(
        self, slot: int, definition: dict, activation: bool, release: bool | None
    ) -> bool:
        """Evaluate once; repeated reads with the same inputs are idempotent."""
        key = str(slot)
        fingerprint = json.dumps(definition, sort_keys=True)
        previous = self._states.get(key, {})
        was_active = (
            previous.get("fingerprint") == fingerprint
            and previous.get("active") is True
        )
        active = activation or (was_active and release is not True)
        if active:
            self._released_slots.discard(slot)
        elif was_active:
            self._released_slots.add(slot)
        current = {"fingerprint": fingerprint, "active": active}
        if previous != current:
            self._states[key] = current
            self._changed()
        return active
