"""Field + policy registration for the FOV-from-measurements button (#565).

The "Generate field of view from measurements" button is a transient
``CONF_FOV_COMPUTE`` toggle: ticking it fills the canonical ``fov_left``/
``fov_right`` keys from the window width + reveal depth (surfaced on the form
through the transient sun-window fields since stage 2 of
docs/CONFIG_FLOW_REWORK.md), then the form re-renders un-ticked. It is never
persisted, so it must NOT appear in ``live_option_keys``. Cover types that carry
window geometry (vertical blinds) advertise it; awnings/tilt don't.
"""

from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.adaptive_pergola import config_fields as cf
from custom_components.adaptive_pergola.config_flow import _get_sun_tracking_schema
from custom_components.adaptive_pergola.const import (
    CONF_FOV_COMPUTE,
    CONF_SUN_WINDOW_END,
    CONF_SUN_WINDOW_START,
    CoverType,
)
from custom_components.adaptive_pergola.cover_types import get_policy


def _keys(schema) -> list[str]:
    return [str(m) for m in schema.schema]


def test_conf_fov_compute_key():
    assert CONF_FOV_COMPUTE == "fov_compute"


def test_fov_compute_field_spec_registered_as_bool():
    spec = cf.FIELD_SPECS[CONF_FOV_COMPUTE]
    assert spec.validator is cf.ValidatorKind.BOOL
    assert spec.section == cf.SECTION_SUN_TRACKING


def test_fov_compute_default_is_false():
    assert cf.option_default(CONF_FOV_COMPUTE) is False


def test_no_legacy_fov_mode_symbols():
    # The two-mode selector was removed; its const symbols must be gone.
    from custom_components.adaptive_pergola import const

    assert not hasattr(const, "FovMode")
    assert not hasattr(const, "CONF_FOV_MODE")


@pytest.mark.parametrize(
    ("cover_type", "supported"),
    [
        (CoverType.BLIND, True),
        
        (CoverType.AWNING, False),
        (CoverType.TILT, False),
    ],
)
def test_supports_fov_compute_per_cover_type(cover_type, supported):
    assert get_policy(cover_type).supports_fov_compute is supported


@pytest.mark.parametrize("cover_type", [CoverType.BLIND])
def test_toggle_in_schema_with_window_fields(cover_type):
    keys = _keys(_get_sun_tracking_schema(cover_type))
    assert CONF_FOV_COMPUTE in keys
    assert CONF_SUN_WINDOW_START in keys
    assert CONF_SUN_WINDOW_END in keys


@pytest.mark.parametrize("cover_type", [CoverType.AWNING, CoverType.TILT])
def test_no_toggle_for_unsupported_cover_types(cover_type):
    keys = _keys(_get_sun_tracking_schema(cover_type))
    assert CONF_FOV_COMPUTE not in keys
    # The transient sun-window fields are still present.
    assert CONF_SUN_WINDOW_START in keys
    assert CONF_SUN_WINDOW_END in keys


@pytest.mark.parametrize("cover_type", [CoverType.BLIND])
def test_toggle_is_transient_not_a_live_option_key(cover_type):
    # The toggle is popped before save, so it must never be a persisted option
    # key — otherwise options_service would treat a stale value as savable.
    assert CONF_FOV_COMPUTE not in get_policy(cover_type).live_option_keys()


@pytest.mark.parametrize("cover_type", [CoverType.BLIND, CoverType.AWNING])
def test_sun_window_fields_required_with_defaults(cover_type):
    # Stage 2: the transient sun-window fields replaced the fov sliders. They
    # are Required with the default 90..270 window (azimuth 180 ± 90°) — the
    # button re-render always supplies suggested values, so the frontend
    # Required check never blocks it.
    schema = _get_sun_tracking_schema(cover_type)
    markers = {str(m): m for m in schema.schema}
    assert isinstance(markers[CONF_SUN_WINDOW_START], vol.Required)
    assert isinstance(markers[CONF_SUN_WINDOW_END], vol.Required)
    assert markers[CONF_SUN_WINDOW_START].default() == 90
    assert markers[CONF_SUN_WINDOW_END].default() == 270
