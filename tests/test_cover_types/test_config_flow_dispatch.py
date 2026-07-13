"""Verify config-flow / options-service dispatch hooks on each policy.

Pins the contract for ``geometry_schema``, ``entity_selector_filter``, and
``summary_geometry_lines`` so future cover-type policies don't silently
short-circuit a config-flow entry point.
"""

from __future__ import annotations

import pytest

from custom_components.adaptive_pergola.cover_types import (
    LouveredRoofPolicy,
    get_policy,
)
from custom_components.adaptive_pergola.cover_types._tilt_math import (
    TILT_CAPABLE_ENTITY_FILTER,
)
from custom_components.adaptive_pergola.cover_types.louvered_roof import (
    GEOMETRY_LOUVERED_ROOF_SCHEMA,
)


@pytest.mark.unit
class TestGeometrySchemaDispatch:
    """``policy.geometry_schema()`` returns the right schema per cover type."""

    def test_louvered_roof(self):
        assert (
            LouveredRoofPolicy().geometry_schema() is GEOMETRY_LOUVERED_ROOF_SCHEMA
        )


@pytest.mark.unit
class TestEntitySelectorFilter:
    """``entity_selector_filter`` reflects each policy's capability needs."""

    def test_louvered_roof_requires_tilt_position(self):
        # The louvered roof drives its slats via set_tilt_position, so the
        # entity picker filters to tilt-capable covers (HA's
        # supported_features filter is OR-of-listed, not AND — the
        # missing-set_position case surfaces via cover_capability_warnings).
        assert (
            LouveredRoofPolicy().entity_selector_filter()
            is TILT_CAPABLE_ENTITY_FILTER
        )


@pytest.mark.unit
class TestSummaryGeometryLines:
    """``summary_geometry_lines`` renders the right geometry block per type."""

    def test_louvered_roof_renders_axis_heights_travel(self):
        lines = LouveredRoofPolicy().summary_geometry_lines(
            {
                "lr_axis_azimuth": 180,
                "lr_plane_pitch": 5,
                "lr_roof_height": 2.5,
                "lr_protected_height": 1.0,
                "lr_theta_min": 0,
                "lr_theta_max": 135,
            }
        )
        assert lines == [
            "axis 180° azimuth, plane pitch 5°, roof 2.5m over protected 1.0m, "
            "travel 0°–135°"
        ]

    def test_empty_config_renders_nothing(self):
        assert LouveredRoofPolicy().summary_geometry_lines({}) == []


@pytest.mark.unit
class TestGetPolicyAcceptsBothForms:
    """``get_policy`` accepts plain strings and ``StrEnum`` members."""

    def test_string_input(self):
        assert isinstance(get_policy("cover_louvered_roof"), LouveredRoofPolicy)

    def test_strenum_input(self):
        from custom_components.adaptive_pergola.const import CoverType

        assert isinstance(get_policy(CoverType.LOUVERED_ROOF), LouveredRoofPolicy)


@pytest.mark.unit
class TestSupportsGlareZones:
    """``supports_glare_zones`` is the single seam for the blind-only feature."""

    def test_louvered_roof_does_not_support(self):
        assert LouveredRoofPolicy.supports_glare_zones is False
