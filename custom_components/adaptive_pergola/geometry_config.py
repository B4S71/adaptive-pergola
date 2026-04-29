"""Helpers for normalizing and validating pergola geometry settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    CONF_AXIS_AZIMUTH_DEG,
    CONF_OPENING_AZIMUTH_DEG,
    CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG,
    CONF_SLAT_AXIS_AZIMUTH_DEG,
    DEFAULT_OPENING_AZIMUTH_DEG,
    DEFAULT_PERGOLA_ORIENTATION_AZIMUTH_DEG,
    DEFAULT_SLAT_AXIS_AZIMUTH_DEG,
)
from .sun import normalize_angle, signed_angle_delta


def normalize_geometry_config(data: Mapping[str, Any]) -> dict[str, Any]:
    """Populate the explicit geometry fields, inferring legacy values when needed."""
    normalized = dict(data)

    legacy_axis = normalized.get(CONF_AXIS_AZIMUTH_DEG)
    slat_axis = float(
        normalized.get(
            CONF_SLAT_AXIS_AZIMUTH_DEG,
            legacy_axis if legacy_axis is not None else DEFAULT_SLAT_AXIS_AZIMUTH_DEG,
        )
    )

    inferred_orientation = DEFAULT_PERGOLA_ORIENTATION_AZIMUTH_DEG
    if legacy_axis is not None:
        inferred_orientation = (float(legacy_axis) + 90.0) % 360.0
    orientation = float(
        normalized.get(CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG, inferred_orientation)
    )

    inferred_opening = orientation if legacy_axis is not None else DEFAULT_OPENING_AZIMUTH_DEG
    opening = float(normalized.get(CONF_OPENING_AZIMUTH_DEG, inferred_opening))

    normalized[CONF_SLAT_AXIS_AZIMUTH_DEG] = normalize_angle(slat_axis)
    normalized[CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG] = normalize_angle(orientation)
    normalized[CONF_OPENING_AZIMUTH_DEG] = normalize_angle(opening)
    return normalized


def strip_legacy_geometry_keys(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized geometry data without deprecated storage keys."""
    normalized = normalize_geometry_config(data)
    normalized.pop(CONF_AXIS_AZIMUTH_DEG, None)
    return normalized


def validate_opening_direction(data: Mapping[str, Any], *, tolerance_deg: float = 5.0) -> bool:
    """Return True when the configured opening direction is perpendicular to the axis."""
    normalized = normalize_geometry_config(data)
    axis = float(normalized[CONF_SLAT_AXIS_AZIMUTH_DEG])
    opening = float(normalized[CONF_OPENING_AZIMUTH_DEG])
    perpendicular_error = abs(abs(signed_angle_delta(axis, opening)) - 90.0)
    return perpendicular_error <= tolerance_deg