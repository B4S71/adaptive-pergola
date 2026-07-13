"""Shared tilt-axis math and selector config for slat-based cover types.

Extracted from the former ``TiltPolicy`` (``cover_types/tilt.py``) when the
integration was slimmed down to the louvered-roof (pergola) cover type. The
louvered roof drives a tilt axis, so the climate handler and config flow still
need the MODE1/MODE2 angle → percent translation and the tilt-capable entity
filter — without importing (and thereby registering) the tilt-only policy.
"""

from __future__ import annotations

from homeassistant.helpers import selector

from ..const import CLIMATE_TILT_PCT_NEGATIVE_HEMISPHERE_OFFSET, TiltMode

# Filter for cover entities that expose ``set_tilt_position``. HA's
# ``supported_features`` filter is OR-of-listed, not AND; the missing-
# set_position case surfaces as a config-flow capability warning.
TILT_CAPABLE_ENTITY_FILTER = selector.EntityFilterSelectorConfig(
    domain="cover",
    supported_features=["cover.CoverEntityFeature.SET_TILT_POSITION"],
)


def is_mode2(mode: TiltMode | str | None) -> bool:
    """Return True when *mode* is MODE2 (bi-directional 0–180°)."""
    return mode == TiltMode.MODE2 or mode == TiltMode.MODE2.value


def climate_tilt_percentage(
    *,
    angle_deg: float,
    mode: TiltMode | str,
    gamma_deg: float,
    sun_through: bool = False,
) -> int:
    """Convert a target slat angle to a tilt percentage that blocks the sun.

    Single source of truth for the climate handler's angle → percent
    translation across MODE1/MODE2 and positive/negative sun hemispheres.

    Args:
        angle_deg: Target slat angle in degrees (e.g. CLIMATE_SUMMER_TILT_ANGLE).
        mode: Tilt mode — TiltMode enum value or its string ("mode1"/"mode2").
        gamma_deg: Sun azimuth offset from window normal, in degrees.
            When negative, the sun is on the opposite hemisphere and MODE2 must
            flip its answer onto the other closed side.
        sun_through: When True, return the OPEN hemisphere instead of closed
            (winter heating: let sun reach the window).  Mirrors the
            ``sun_through`` flag on ``position_for_intent``.

    Returns:
        Tilt percentage (0–100) for the cover entity.

    """
    # Normalise mode (accept enum or string for backward compatibility with
    # call sites that historically compared against both forms).
    if not is_mode2(mode):
        # MODE1: 0° → 0%, 90° → 100%.
        return round((angle_deg / TiltMode.MODE1.max_degrees) * 100)

    # MODE2: bi-directional 0–180° scale where 50% is horizontal/open.
    # Choose hemisphere by sun side (gamma) and intent (sun_through).
    max_degrees = TiltMode.MODE2.max_degrees
    # Closed-hemisphere mapping for MODE2:
    #   gamma >= 0 → angle on the positive-side closed hemisphere
    #               → (180 - angle) / 180 * 100  (== 100 - mode1_pct/2)
    #   gamma <  0 → angle on the negative-side closed hemisphere
    #               → angle / 180 * 100
    # sun_through (winter heating) flips to the open hemisphere by mirroring
    # the angle across horizontal (+90° offset).
    if sun_through:
        effective_angle = (
            CLIMATE_TILT_PCT_NEGATIVE_HEMISPHERE_OFFSET + angle_deg
            if gamma_deg >= 0
            else CLIMATE_TILT_PCT_NEGATIVE_HEMISPHERE_OFFSET - angle_deg
        )
    else:
        effective_angle = max_degrees - angle_deg if gamma_deg >= 0 else angle_deg
    return round((effective_angle / max_degrees) * 100)
