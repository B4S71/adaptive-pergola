"""Register the custom louvred-roof slat iconset with the HA frontend.

Home Assistant's ``icons.json`` can only point at existing ``mdi:`` icons and
only switches on entity *state*, so it cannot express a position-driven custom
SVG. Instead we serve a small JS module that registers the ``acp`` icon set
(``acp:pergola-slats-<pct>``) and inject it into the frontend. ``cover.py`` then
returns the matching icon name from its ``icon`` property, giving every
tilt-capable pergola slat a position-aware glyph automatically.

Registration is global (one iconset per HA instance) and idempotent: the first
config entry to load wires it up, later entries and reloads are no-ops.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, _LOGGER

_JS_FILE = "acp_icons.js"
_URL_PATH = f"/{DOMAIN}/frontend/{_JS_FILE}"
# Bump when acp_icons.js changes so browsers re-fetch past the cache.
_CACHE_BUST = "acp-slats-1"
_REGISTERED_KEY = f"{DOMAIN}_frontend_iconset_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and inject the slat iconset module exactly once per HA instance."""
    if hass.data.get(_REGISTERED_KEY):
        return
    hass.data[_REGISTERED_KEY] = True

    js_path = Path(__file__).parent / "frontend" / _JS_FILE
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_URL_PATH, str(js_path), False)]
        )
    except Exception:  # noqa: BLE001 - a frontend hiccup must not fail entry setup
        # The static path was NOT registered — clear the flag so the next entry
        # retries. Only this branch resets it: if the path registration
        # succeeded, retrying would register the same aiohttp route twice and
        # raise a duplicate-resource error, leaving the iconset never injected
        # (ACP-021).
        hass.data[_REGISTERED_KEY] = False
        _LOGGER.warning("Failed to register the pergola slat iconset", exc_info=True)
        return

    try:
        add_extra_js_url(hass, f"{_URL_PATH}?v={_CACHE_BUST}")
    except Exception:  # noqa: BLE001 - injection failed but the path is registered
        # Leave _REGISTERED_KEY set: the static path is live, so a retry must not
        # re-register it. The JS URL injection is best-effort.
        _LOGGER.warning("Failed to inject the pergola slat iconset URL", exc_info=True)
