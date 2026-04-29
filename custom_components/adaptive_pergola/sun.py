"""Solar geometry helpers for Adaptive Pergola."""

from __future__ import annotations

import math


def normalize_angle(angle_deg: float) -> float:
    """Normalize an angle to the range [0, 360)."""
    return angle_deg % 360.0


def signed_angle_delta(from_angle_deg: float, to_angle_deg: float) -> float:
    """Return the shortest signed angular delta in degrees."""
    delta = (to_angle_deg - from_angle_deg + 180.0) % 360.0 - 180.0
    return delta


def projected_elevation_deg(elevation_deg: float, horizontal_delta_deg: float) -> float:
    """Project the sun elevation into the plane perpendicular to the slat axis.

    This mirrors the venetian-blind beta approach from Adaptive Cover Pro:
    when the sun travels along the slat axis, the apparent elevation in the
    slat cross-section becomes steeper.
    """
    elevation_rad = math.radians(elevation_deg)
    delta_rad = math.radians(horizontal_delta_deg)
    cosine = math.cos(delta_rad)
    if abs(cosine) < 1e-6:
        return 89.9
    projected = math.atan(math.tan(elevation_rad) / cosine)
    return math.degrees(projected)
