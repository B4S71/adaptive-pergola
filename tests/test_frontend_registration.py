"""Tests for the frontend iconset registration flag handling (ACP-021)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.adaptive_pergola.frontend import (
    _REGISTERED_KEY,
    async_register_frontend,
)

pytestmark = pytest.mark.unit


def _make_hass():
    hass = MagicMock()
    hass.data = {}
    hass.http.async_register_static_paths = AsyncMock()
    return hass


async def test_registers_once_and_sets_flag():
    hass = _make_hass()
    with patch(
        "custom_components.adaptive_pergola.frontend.add_extra_js_url"
    ) as add_js:
        await async_register_frontend(hass)
    assert hass.data[_REGISTERED_KEY] is True
    hass.http.async_register_static_paths.assert_awaited_once()
    add_js.assert_called_once()


async def test_second_call_is_a_noop():
    hass = _make_hass()
    hass.data[_REGISTERED_KEY] = True
    with patch("custom_components.adaptive_pergola.frontend.add_extra_js_url"):
        await async_register_frontend(hass)
    hass.http.async_register_static_paths.assert_not_awaited()


async def test_static_path_failure_clears_flag_for_retry():
    """If the static path was never registered, a later entry may retry."""
    hass = _make_hass()
    hass.http.async_register_static_paths.side_effect = RuntimeError("boom")
    with patch("custom_components.adaptive_pergola.frontend.add_extra_js_url"):
        await async_register_frontend(hass)
    assert hass.data[_REGISTERED_KEY] is False


async def test_js_injection_failure_keeps_flag_set():
    """The static path IS registered, so the flag must stay set (ACP-021).

    Resetting it here would let the next entry re-register the same aiohttp
    route, raising a duplicate-resource error and leaving the iconset never
    injected. The JS URL injection is best-effort; the path is what must not be
    registered twice.
    """
    hass = _make_hass()
    with patch(
        "custom_components.adaptive_pergola.frontend.add_extra_js_url",
        side_effect=RuntimeError("frontend not ready"),
    ):
        await async_register_frontend(hass)
    assert hass.data[_REGISTERED_KEY] is True
    hass.http.async_register_static_paths.assert_awaited_once()
