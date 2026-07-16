"""Tests for policy-owned i18n of the config summary (follow-up to #258).

The cover-type label (``display_label``) and the physical-dimension /
geometry block (``summary_geometry_lines`` + the shared helper) were deferred
from #258 as policy-owned. This file covers the new machinery for the
louvered-roof policy (the only physical cover type in Adaptive Pergola):

* the ``labels`` override param on ``display_label`` and
  ``summary_geometry_lines`` (and the shared ``window_dimensions_lines``),
* English back-compat when ``labels`` is ``None`` or a key is untranslated,
* a drift guard that ``summary_i18n/en.json``'s ``cover_types`` /
  ``geometry`` subtrees are byte-identical to the code-owned
  ``COVER_TYPE_LABELS_EN`` / ``GEOMETRY_LABELS_EN`` dicts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.adaptive_pergola.const import (
    CONF_DISTANCE,
    CONF_HEIGHT_WIN,
    CONF_LR_AXIS_AZIMUTH,
    CONF_LR_PLANE_PITCH,
    CONF_LR_PROTECTED_HEIGHT,
    CONF_LR_ROOF_HEIGHT,
    CONF_LR_THETA_MAX,
    CONF_LR_THETA_MIN,
)
from custom_components.adaptive_pergola.cover_types._helpers import (
    window_dimensions_lines,
)
from custom_components.adaptive_pergola.cover_types._summary_labels import (
    COVER_TYPE_LABELS_EN,
    GEOMETRY_LABELS_EN,
)
from custom_components.adaptive_pergola.cover_types.louvered_roof import (
    LouveredRoofPolicy,
)

pytestmark = pytest.mark.unit

SUMMARY_I18N_DIR = (
    Path(__file__).parent.parent
    / "custom_components"
    / "adaptive_pergola"
    / "summary_i18n"
)


# ---------------------------------------------------------------------------
# (a) display_label override + English back-compat
# ---------------------------------------------------------------------------


def test_display_label_override_and_default() -> None:
    """A labels override wins; ``labels=None`` keeps the English default."""
    assert (
        LouveredRoofPolicy().display_label(labels={"cover_types.louvered_roof": "FOO"})
        == "FOO"
    )
    assert LouveredRoofPolicy().display_label() == "Louvered Roof"


def test_display_label_untranslated_key_falls_back_to_english() -> None:
    """An override dict missing the policy's key still yields English."""
    assert LouveredRoofPolicy().display_label(labels={"cover_types.blind": "X"}) == (
        "Louvered Roof"
    )


# ---------------------------------------------------------------------------
# (b) summary_geometry_lines override leaves non-overridden lines English
# ---------------------------------------------------------------------------

_LR_CONFIG = {
    CONF_LR_AXIS_AZIMUTH: 180,
    CONF_LR_PLANE_PITCH: 5,
    CONF_LR_ROOF_HEIGHT: 2.5,
    CONF_LR_PROTECTED_HEIGHT: 1.0,
    CONF_LR_THETA_MIN: 0,
    CONF_LR_THETA_MAX: 135,
}


def test_louvered_geometry_override_one_line_other_stays_english() -> None:
    """Overriding one geometry template translates only that line."""
    labels = {"geometry.louvered_roof.axis": "Achse {v}° Azimut"}
    out = LouveredRoofPolicy().summary_geometry_lines(_LR_CONFIG, labels=labels)
    joined = ", ".join(out)
    assert "Achse 180° Azimut" in joined  # overridden
    assert "plane pitch 5°" in joined  # non-overridden → English
    assert "travel 0°–135°" in joined  # non-overridden → English


def test_louvered_geometry_default_is_english() -> None:
    """``labels=None`` yields byte-identical English (back-compat)."""
    out = LouveredRoofPolicy().summary_geometry_lines(_LR_CONFIG)
    assert out == [
        "axis 180° azimuth, plane pitch 5°, roof 2.5m over protected 1.0m, "
        "travel 0°–135°"
    ]


def test_window_dims_helper_override() -> None:
    """The shared window-dimensions helper honors a labels override."""
    config = {CONF_HEIGHT_WIN: 2.1, CONF_DISTANCE: 0.5}
    labels = {"geometry.window.tall": "{h}m hohes Fenster"}
    out = window_dimensions_lines(config, labels=labels)
    joined = ", ".join(out)
    assert "2.1m hohes Fenster" in joined  # overridden
    assert "blocking sun 0.5m from the glass" in joined  # English


# ---------------------------------------------------------------------------
# (c) drift guard — en.json subtrees byte-identical to the code dicts
# ---------------------------------------------------------------------------


def _flatten(node: object, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(node, str):
        out[prefix] = node
    return out


def _en_config_summary() -> dict:
    with (SUMMARY_I18N_DIR / "en.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def test_cover_type_labels_match_en_json() -> None:
    """``summary_i18n/en.json['cover_types']`` == ``COVER_TYPE_LABELS_EN``."""
    en = _flatten(_en_config_summary().get("cover_types", {}))
    expected = {
        k.removeprefix("cover_types."): v for k, v in COVER_TYPE_LABELS_EN.items()
    }
    assert en == expected


def test_geometry_labels_match_en_json() -> None:
    """``summary_i18n/en.json['geometry']`` == ``GEOMETRY_LABELS_EN``."""
    en = _flatten(_en_config_summary().get("geometry", {}))
    expected = {k.removeprefix("geometry."): v for k, v in GEOMETRY_LABELS_EN.items()}
    assert en == expected
