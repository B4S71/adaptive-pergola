"""Unit tests for the transient sun-window <-> canonical azimuth/fov helpers.

Stage 2 of docs/CONFIG_FLOW_REWORK.md: the sun-tracking step presents the
tracking range as a clockwise compass window (``sun_window_start`` /
``sun_window_end``) while storage stays canonical (``set_azimuth`` midpoint +
symmetric ``fov_left``/``fov_right`` halves). All values are whole degrees;
an odd span splits deterministically as ``fov_left = span // 2`` with
``fov_right`` taking the extra degree, so the exact [start, end] coverage is
preserved. A zero span (start == end) is rejected — the form shows a field
error instead of storing a full-circle window.
"""

from __future__ import annotations

import pytest

from custom_components.adaptive_pergola.config_flow import (
    _apply_sun_window_submit,
    sun_window_from_canonical,
    sun_window_to_canonical,
)
from custom_components.adaptive_pergola.const import (
    CONF_AZIMUTH,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_SUN_WINDOW_END,
    CONF_SUN_WINDOW_START,
)

pytestmark = pytest.mark.unit


class TestSunWindowToCanonical:
    def test_simple_symmetric_window(self):
        # 90..270 → span 180, midpoint 180 (south), 90° each side.
        assert sun_window_to_canonical(90, 270) == (180, 90, 90)

    def test_wrap_through_north_odd_span(self):
        # 137 → 2 wraps through north: span 225 (odd) → fov_left 112 (floor),
        # fov_right 113 (the extra degree), azimuth = 137 + 112 = 249. The
        # coverage stays exactly [137, 2]: 249 − 112 = 137, 249 + 113 = 362 ≡ 2.
        assert sun_window_to_canonical(137, 2) == (249, 112, 113)

    def test_zero_span_rejected(self):
        # start == end is NOT the full circle — the window must span ≥ 1°.
        with pytest.raises(ValueError):
            sun_window_to_canonical(137, 137)

    def test_midpoint_wraps_past_north(self):
        # 350 → 30: span 40, midpoint 10.
        assert sun_window_to_canonical(350, 30) == (10, 20, 20)

    def test_odd_span_deterministic_split(self):
        # span 45 → fov 22/23, azimuth = 0 + 22 = 22.
        assert sun_window_to_canonical(0, 45) == (22, 22, 23)

    def test_float_slider_values_are_rounded(self):
        # HA NumberSelector submits floats (e.g. 137.0) — treated as ints.
        assert sun_window_to_canonical(137.0, 2.0) == (249, 112, 113)


class TestSunWindowFromCanonical:
    def test_simple_symmetric_window(self):
        assert sun_window_from_canonical(180, 90, 90) == (90, 270)

    def test_wrap_through_north(self):
        assert sun_window_from_canonical(249, 112, 113) == (137, 2)

    def test_asymmetric_legacy_fov(self):
        # Legacy entries may carry asymmetric fov halves — the display window
        # still covers the same compass range (azimuth 182, fov 45/180 → the
        # 137..2 window from the scope doc).
        assert sun_window_from_canonical(182, 45, 180) == (137, 2)

    def test_legacy_half_degree_values_rounded(self):
        # Pre-rework entries may hold half-degree canonical values — display
        # rounds to the whole-degree sliders.
        assert sun_window_from_canonical(249.5, 112.5, 112.5) == (137, 2)


class TestRoundTrip:
    @pytest.mark.parametrize(
        ("start", "end"),
        [(90, 270), (137, 2), (350, 30), (0, 359), (0, 45), (359, 0)],
    )
    def test_window_survives_round_trip(self, start, end):
        azimuth, fov_l, fov_r = sun_window_to_canonical(start, end)
        assert sun_window_from_canonical(azimuth, fov_l, fov_r) == (start, end)

    def test_asymmetric_config_recentres_to_equivalent_window(self):
        # A stored asymmetric config (azimuth 182, fov 45/180) displays as the
        # 137..2 window; resubmitting that window stores a *centered* canonical
        # form (azimuth 249, fov 112/113). That recentring is intended — the
        # [start, end] coverage is identical and stable from then on.
        start, end = sun_window_from_canonical(182, 45, 180)
        assert (start, end) == (137, 2)
        azimuth, fov_l, fov_r = sun_window_to_canonical(start, end)
        assert (azimuth, fov_l, fov_r) == (249, 112, 113)
        # Same coverage, now stable under further round trips.
        assert sun_window_from_canonical(azimuth, fov_l, fov_r) == (137, 2)


class TestApplySunWindowSubmit:
    def test_pops_transient_and_writes_canonical(self):
        user_input = {
            CONF_SUN_WINDOW_START: 137,
            CONF_SUN_WINDOW_END: 2,
            "min_elevation": 20,  # unrelated keys pass through untouched
        }
        assert _apply_sun_window_submit(user_input) is None
        assert CONF_SUN_WINDOW_START not in user_input
        assert CONF_SUN_WINDOW_END not in user_input
        assert user_input[CONF_AZIMUTH] == 249
        assert user_input[CONF_FOV_LEFT] == 112
        assert user_input[CONF_FOV_RIGHT] == 113
        assert user_input["min_elevation"] == 20

    def test_zero_span_returns_error_and_keeps_keys(self):
        # start == end → field error; the transient keys stay so the error
        # re-render shows the user's own input instead of resetting the form.
        user_input = {CONF_SUN_WINDOW_START: 137, CONF_SUN_WINDOW_END: 137}
        errors = _apply_sun_window_submit(user_input)
        assert errors == {CONF_SUN_WINDOW_END: "sun_window_span"}
        assert user_input[CONF_SUN_WINDOW_START] == 137
        assert user_input[CONF_SUN_WINDOW_END] == 137
        assert CONF_AZIMUTH not in user_input

    def test_noop_without_transient_keys(self):
        # Direct canonical submissions (legacy unit tests) pass through.
        user_input = {CONF_AZIMUTH: 180, CONF_FOV_LEFT: 45, CONF_FOV_RIGHT: 45}
        assert _apply_sun_window_submit(user_input) is None
        assert user_input == {
            CONF_AZIMUTH: 180,
            CONF_FOV_LEFT: 45,
            CONF_FOV_RIGHT: 45,
        }

    def test_partial_submit_pops_without_writing(self):
        user_input = {CONF_SUN_WINDOW_START: 137}
        assert _apply_sun_window_submit(user_input) is None
        assert user_input == {}
