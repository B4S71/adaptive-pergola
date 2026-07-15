"""Config-flow behaviour for the FOV-from-measurements button (#565).

Covers the schema rendering (toggle present alongside the transient sun-window
fields), the button press that derives the canonical ``fov_left``/``fov_right``
and re-renders the form (surfaced through the sun-window fields since stage 2
of docs/CONFIG_FLOW_REWORK.md), the normal save path when the button is not
pressed, and the transient nature of the toggle (never persisted).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol

from custom_components.adaptive_pergola.config_flow import (
    ConfigFlowHandler,
    OptionsFlowHandler,
    _get_sun_tracking_schema,
    _sun_tracking_placeholders,
)
from custom_components.adaptive_pergola.const import (
    CONF_FOV_COMPUTE,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_SUN_WINDOW_END,
    CONF_SUN_WINDOW_START,
    CONF_WINDOW_DEPTH,
    CONF_WINDOW_WIDTH,
    CoverType,
)


def _keys(schema) -> set[str]:
    return {str(m) for m in schema.schema}


def _suggested(result, key):
    for m in result["data_schema"].schema:
        if str(m) == key and m.description:
            return m.description.get("suggested_value")
    raise AssertionError(f"no suggested_value for {key!r}")


# ----------------------------------------------------------------------------
# Computed-FOV preview placeholder (rendered in the fov_compute help text, #565)
# ----------------------------------------------------------------------------


def test_preview_shows_hemisphere_at_zero_depth():
    # A flush window (depth 0, the default) is not "nothing to derive" — it is
    # the full hemisphere, 90°/90°. The preview must always render, never be
    # blank, so the button's help text fulfils its "computed value" promise.
    ph = _sun_tracking_placeholders(
        CoverType.BLIND, {CONF_WINDOW_WIDTH: 0, CONF_WINDOW_DEPTH: 0}
    )
    assert "90°/90°" in ph["computed_fov"]


def test_preview_narrows_with_reveal_depth():
    # width 2.0 / depth 0.5 → atan(4) ≈ 76°.
    ph = _sun_tracking_placeholders(
        CoverType.BLIND, {CONF_WINDOW_WIDTH: 2.0, CONF_WINDOW_DEPTH: 0.5}
    )
    assert "76°/76°" in ph["computed_fov"]


def test_preview_empty_for_type_without_button():
    # Awnings have no FOV-from-measurements button → no computed preview, but
    # the placeholder key is still present (HA raises on a missing reference).
    ph = _sun_tracking_placeholders(
        CoverType.AWNING, {CONF_WINDOW_WIDTH: 2.0, CONF_WINDOW_DEPTH: 0.5}
    )
    assert ph["computed_fov"] == ""


# ----------------------------------------------------------------------------
# Schema rendering
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("cover_type", [CoverType.BLIND])
def test_supported_types_show_button_and_window_fields(cover_type):
    # Stage 2: the form carries the transient sun-window fields instead of the
    # raw azimuth/fov sliders; the button still derives the canonical fov keys.
    keys = _keys(_get_sun_tracking_schema(cover_type))
    assert CONF_FOV_COMPUTE in keys
    assert CONF_SUN_WINDOW_START in keys
    assert CONF_SUN_WINDOW_END in keys
    assert CONF_FOV_LEFT not in keys
    assert CONF_FOV_RIGHT not in keys


def test_awning_has_no_button():
    keys = _keys(_get_sun_tracking_schema(CoverType.AWNING))
    assert CONF_FOV_COMPUTE not in keys
    assert CONF_SUN_WINDOW_START in keys
    assert CONF_SUN_WINDOW_END in keys


# ----------------------------------------------------------------------------
# Options-flow save path
# ----------------------------------------------------------------------------


def _options_flow(options: dict, sensor_type=CoverType.BLIND) -> OptionsFlowHandler:
    entry = MagicMock()
    entry.options = dict(options)
    entry.data = {"sensor_type": sensor_type}
    flow = OptionsFlowHandler(entry)
    flow.hass = MagicMock()
    flow.hass.states.get.return_value = None
    flow.sensor_type = sensor_type
    flow.options = dict(options)
    flow.async_step_init = AsyncMock(return_value={"type": "menu"})
    return flow


@pytest.mark.asyncio
async def test_button_press_derives_fov_and_rerenders():
    # width 2.0 / depth 0.5 → atan(4) ≈ 76°. Ticking the button fills the
    # sliders and re-renders the form rather than advancing.
    flow = _options_flow({CONF_WINDOW_WIDTH: 2.0, CONF_WINDOW_DEPTH: 0.5})
    advanced = False

    async def _next():
        nonlocal advanced
        advanced = True
        return {"type": "menu"}

    flow.async_step_init = _next
    result = await flow.async_step_sun_tracking(
        {
            CONF_FOV_COMPUTE: True,
            CONF_SUN_WINDOW_START: 90,  # 180° ± 90°
            CONF_SUN_WINDOW_END: 270,
        }
    )
    assert advanced is False
    assert result["type"] == "form"
    assert result["step_id"] == "sun_tracking"
    # The re-rendered form surfaces the derived angle through the sun-window
    # fields: azimuth 180 ± derived 76° → 104..256.
    assert _suggested(result, CONF_SUN_WINDOW_START) == 104
    assert _suggested(result, CONF_SUN_WINDOW_END) == 256
    # The toggle is never written to options.
    assert CONF_FOV_COMPUTE not in flow.options


@pytest.mark.asyncio
async def test_button_not_pressed_saves_typed_values():
    flow = _options_flow({CONF_WINDOW_WIDTH: 2.0, CONF_WINDOW_DEPTH: 0.5})
    result = await flow.async_step_sun_tracking(
        {
            CONF_FOV_COMPUTE: False,
            CONF_SUN_WINDOW_START: 150,  # span 70 → azimuth 185, fov 35/35
            CONF_SUN_WINDOW_END: 220,
        }
    )
    assert result["type"] == "menu"  # advanced (saved)
    assert flow.options[CONF_FOV_LEFT] == 35
    assert flow.options[CONF_FOV_RIGHT] == 35
    assert CONF_FOV_COMPUTE not in flow.options
    assert CONF_SUN_WINDOW_START not in flow.options
    assert CONF_SUN_WINDOW_END not in flow.options


@pytest.mark.asyncio
async def test_absent_toggle_saves_typed_values():
    # The toggle may be omitted entirely (default off) → typed values saved.
    flow = _options_flow({CONF_WINDOW_WIDTH: 2.0, CONF_WINDOW_DEPTH: 0.5})
    await flow.async_step_sun_tracking(
        {
            CONF_SUN_WINDOW_START: 100,  # span 140 → azimuth 170, fov 70/70
            CONF_SUN_WINDOW_END: 240,
        }
    )
    assert flow.options[CONF_FOV_LEFT] == 70
    assert flow.options[CONF_FOV_RIGHT] == 70


@pytest.mark.asyncio
async def test_legacy_fov_mode_key_dropped_on_save():
    # An entry created before the button replaced the selector may carry a stale
    # ``fov_mode`` option — it must be dropped on the next sun-tracking save.
    flow = _options_flow(
        {CONF_WINDOW_WIDTH: 2.0, CONF_WINDOW_DEPTH: 0.5, "fov_mode": "measurements"}
    )
    await flow.async_step_sun_tracking(
        {
            CONF_SUN_WINDOW_START: 135,
            CONF_SUN_WINDOW_END: 225,
        }
    )
    assert "fov_mode" not in flow.options


# ----------------------------------------------------------------------------
# Create-flow parity
# ----------------------------------------------------------------------------


def _create_flow(sensor_type: str = CoverType.BLIND) -> ConfigFlowHandler:
    """Build a minimal ConfigFlowHandler suitable for unit tests."""
    flow = ConfigFlowHandler.__new__(ConfigFlowHandler)
    flow.hass = MagicMock()
    flow.hass.config.units = MagicMock()
    flow.hass.config.units.is_metric = True
    flow.hass.states.get.return_value = None
    flow.type_blind = sensor_type
    flow.config = {}
    flow.async_step_position = AsyncMock(
        return_value={"type": "form", "step_id": "position"}
    )
    return flow


@pytest.mark.asyncio
async def test_create_flow_button_press_then_save():
    flow = _create_flow()
    flow.config[CONF_WINDOW_WIDTH] = 2.0
    flow.config[CONF_WINDOW_DEPTH] = 0.5

    # Button press → re-render, no advance. The derived 76° halves surface via
    # the sun-window fields around the default azimuth 180 → 104..256.
    result1 = await flow.async_step_sun_tracking(
        {CONF_FOV_COMPUTE: True}
    )
    assert result1["type"] == "form"
    assert result1["step_id"] == "sun_tracking"
    assert _suggested(result1, CONF_SUN_WINDOW_START) == 104
    assert _suggested(result1, CONF_SUN_WINDOW_END) == 256

    # Plain submit → advance to position, persisting the canonical fov values.
    result2 = await flow.async_step_sun_tracking(
        {
            CONF_SUN_WINDOW_START: 104,
            CONF_SUN_WINDOW_END: 256,
        }
    )
    assert result2["step_id"] == "position"
    assert flow.config[CONF_FOV_LEFT] == 76
    assert flow.config[CONF_FOV_RIGHT] == 76
    assert CONF_FOV_COMPUTE not in flow.config
    assert CONF_SUN_WINDOW_START not in flow.config


def test_sun_window_fields_are_required():
    # The transient sun-window fields replace the old Optional fov sliders
    # (stage 2); they are Required — the button re-render always supplies
    # suggested values, so the frontend Required check never blocks it.
    schema = _get_sun_tracking_schema(CoverType.BLIND)
    markers = {str(m): m for m in schema.schema}
    assert CONF_FOV_LEFT not in markers
    assert CONF_FOV_RIGHT not in markers
    assert isinstance(markers[CONF_SUN_WINDOW_START], vol.Required)
    assert isinstance(markers[CONF_SUN_WINDOW_END], vol.Required)
