"""Shared permission checks for Adaptive Pergola services (ACP-005/008/009).

Plain ``hass.services.async_register`` handlers get no permission check from
Home Assistant — unlike the options flow and the diagnostics download, which HA
gates behind admin. These helpers add that gate back so a non-admin authenticated
user (guest/kid account, a script under a scoped token) cannot drive
state-changing services or read occupancy data across every instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.exceptions import Unauthorized

if TYPE_CHECKING:
    from homeassistant.core import ServiceCall


async def async_is_admin_call(call: ServiceCall) -> bool:
    """Return whether *call* was made by an admin (or an internal/automation call).

    A ``context.user_id`` of None means the call originated inside Home
    Assistant — an automation, a script, or the integration itself — with no
    user attached. Those are trusted: they already run with full internal
    privilege and are not the boundary this guards. A call carrying a user_id is
    admin only when that user's ``is_admin`` is set.
    """
    user_id = call.context.user_id
    if user_id is None:
        return True
    user = await call.hass.auth.async_get_user(user_id)
    return bool(user and user.is_admin)


async def async_require_admin(call: ServiceCall) -> None:
    """Raise :class:`Unauthorized` when *call* is from a non-admin user."""
    if not await async_is_admin_call(call):
        raise Unauthorized(context=call.context)
