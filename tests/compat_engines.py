"""Test-only compat engines for removed blind/awning/tilt cover types.

These classes preserve the shared base-class contract used by infrastructure
tests without keeping the removed product engines in the shipped package.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from custom_components.adaptive_pergola.config_types import (
    HorizontalConfig,
    TiltConfig,
    VerticalConfig,
)
from custom_components.adaptive_pergola.engine.covers.base import AdaptiveGeneralCover


def _clamp_percent(value: float) -> float:
    """Clamp a floating-point percentage into the inclusive 0..100 range."""
    return max(0.0, min(100.0, value))


@dataclass
class AdaptiveVerticalCover(AdaptiveGeneralCover):
    """Minimal vertical-cover compat engine for shared contract tests."""

    vert_config: VerticalConfig

    def calculate_position(self) -> float:
        """Project a simple drop percentage from the effective sun height."""
        effective_distance = max(
            0.0, self.vert_config.distance + self.vert_config.window_depth
        )
        projected_drop = (
            effective_distance * math.tan(math.radians(max(self.sol_elev, 0.0)))
            + self.vert_config.sill_height
        )
        coverage_ratio = 1.0 - min(
            max(projected_drop / max(self.vert_config.h_win, 0.001), 0.0), 1.0
        )
        position = _clamp_percent(coverage_ratio * 100.0)
        self._last_calc_details = {
            "sol_elev_deg": float(self.sol_elev),
            "gamma_deg": float(self.gamma),
            "effective_distance_m": round(effective_distance, 4),
            "projected_drop_m": round(projected_drop, 4),
            "position_pct": round(position, 2),
        }
        return position

    def calculate_percentage(self) -> float:
        """Return the compat percentage for shared solar helpers."""
        return self.calculate_position()


@dataclass
class AdaptiveHorizontalCover(AdaptiveGeneralCover):
    """Minimal horizontal-awning compat engine for shared contract tests."""

    vert_config: VerticalConfig
    horiz_config: HorizontalConfig

    def calculate_position(self) -> float:
        """Estimate awning extension from sun elevation and configured length."""
        sun_factor = math.sin(math.radians(max(self.sol_elev, 0.0)))
        extension_ratio = min(
            max(
                (self.horiz_config.awn_length * sun_factor)
                / max(self.vert_config.h_win, 0.001),
                0.0,
            ),
            1.0,
        )
        position = _clamp_percent(extension_ratio * 100.0)
        self._last_calc_details = {
            "sol_elev_deg": float(self.sol_elev),
            "gamma_deg": float(self.gamma),
            "awn_angle_deg": float(self.horiz_config.awn_angle),
            "awn_length_m": round(self.horiz_config.awn_length, 4),
            "position_pct": round(position, 2),
        }
        return position

    def calculate_percentage(self) -> float:
        """Return the compat percentage for shared solar helpers."""
        return self.calculate_position()


@dataclass
class AdaptiveTiltCover(AdaptiveGeneralCover):
    """Minimal tilt compat engine for shared contract tests."""

    tilt_config: TiltConfig

    @property
    def beta(self) -> float:
        """Return the compat slat angle in radians."""
        return math.radians((self.calculate_position() - 50.0) * 1.8)

    def calculate_position(self) -> float:
        """Map sun side and elevation onto a tilt percentage."""
        if str(self.tilt_config.mode) == "mode2":
            magnitude = min(
                max((180.0 - max(self.sol_elev, 0.0)) / 180.0 * 50.0, 0.0), 50.0
            )
            position = 50.0 + magnitude if self.gamma >= 0 else 50.0 - magnitude
        else:
            position = (max(self.sol_elev, 0.0) / 90.0) * 100.0
        position = _clamp_percent(position)
        beta = math.radians((position - 50.0) * 1.8)
        self._last_calc_details = {
            "sol_elev_deg": float(self.sol_elev),
            "gamma_deg": float(self.gamma),
            "beta_rad": round(beta, 6),
            "tilt_mode": str(self.tilt_config.mode),
            "position_pct": round(position, 2),
        }
        return position

    def calculate_percentage(self) -> float:
        """Return the compat percentage for shared solar helpers."""
        return self.calculate_position()


__all__ = [
    "AdaptiveHorizontalCover",
    "AdaptiveTiltCover",
    "AdaptiveVerticalCover",
]
