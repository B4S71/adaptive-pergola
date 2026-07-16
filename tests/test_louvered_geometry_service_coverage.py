"""Guard: every UI-settable louvered geometry field is reachable via a service.

The louvered-roof geometry fields live in the cover-type policy's own schema
(cover_types/louvered_roof.py), not the central FIELD_SPECS table, so the
FIELD_VALIDATORS reconciliation (test_field_validators_cover_specs) does not
reach them — they are maintained by hand in two allowlists. That drifted: the
shading-extension arms (lr_shade_ext_azimuth_1/2, lr_shade_ext_distance_1/2) and
lr_tilt_vertical_pct were exposed in the config-flow UI but missing from both the
set_geometry section and FIELD_VALIDATORS, so no runtime service could set them —
even though they change the computed position.

These tests pin the schema and the allowlists together so the next louvered
geometry field added to the UI can't silently become UI-only.
"""

from __future__ import annotations

import voluptuous as vol
import pytest

from custom_components.adaptive_pergola.cover_types.louvered_roof import (
    geometry_louvered_roof_schema,
)
from custom_components.adaptive_pergola.services.options_service import (
    FIELD_VALIDATORS,
    _SECTION_GEOMETRY_LOUVERED,
)

pytestmark = pytest.mark.unit


def _schema_keys() -> set[str]:
    schema = geometry_louvered_roof_schema(None)
    return {
        key
        for marker in schema.schema
        if isinstance((key := getattr(marker, "schema", marker)), str)
    }


def test_every_louvered_schema_field_is_service_settable() -> None:
    """Every field the louvered geometry UI exposes must be in FIELD_VALIDATORS.

    FIELD_VALIDATORS is what set_option checks and what validate_options_patch
    (used by set_geometry) checks, so a key absent from it cannot be set by any
    service regardless of section membership.
    """
    unreachable = _schema_keys() - set(FIELD_VALIDATORS)
    assert not unreachable, (
        f"Louvered geometry fields {sorted(unreachable)} are settable in the "
        "config-flow UI but have no FIELD_VALIDATORS entry, so no service can "
        "set them"
    )


def test_shade_extension_fields_are_in_the_geometry_section() -> None:
    """The shading-extension + vertical-tilt fields belong to set_geometry.

    They are geometry, so they should be settable via set_geometry (grouped with
    the other louvered geometry), not only via the generic set_option escape
    hatch.
    """
    expected = {
        "lr_shade_ext_azimuth_1",
        "lr_shade_ext_azimuth_2",
        "lr_shade_ext_distance_1",
        "lr_shade_ext_distance_2",
        "lr_tilt_vertical_pct",
    }
    assert expected <= _SECTION_GEOMETRY_LOUVERED


@pytest.mark.parametrize(
    ("key", "good", "bad"),
    [
        ("lr_shade_ext_azimuth_1", 92, 400),
        ("lr_shade_ext_azimuth_2", 90, -1),
        ("lr_shade_ext_distance_1", 8, 99),
        ("lr_shade_ext_distance_2", 0, 50),
        ("lr_tilt_vertical_pct", 75, 200),
    ],
)
def test_shade_extension_validators_enforce_ranges(key, good, bad) -> None:
    """The new validators accept in-range values and reject out-of-range ones."""
    assert FIELD_VALIDATORS[key](good) == float(good)
    with pytest.raises(vol.Invalid):
        FIELD_VALIDATORS[key](bad)
