"""Typed configuration models for Adaptive Pergola."""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass

from .const import ACTUATOR_MODES, TRACKING_BALANCED, TRACKING_STRATEGIES


def derived_open_actuator_percent(
    closed_angle_deg: float,
    open_angle_deg: float,
    max_travel_angle_deg: float,
) -> float:
    """Derive the historical linear actuator percentage for the open angle."""
    total_travel = max_travel_angle_deg - closed_angle_deg
    if total_travel <= 0:
        return 100.0
    open_span = open_angle_deg - closed_angle_deg
    if open_span <= 0:
        return 0.0
    if open_angle_deg >= max_travel_angle_deg:
        return 100.0
    return max(0.0, min(100.0, (open_span / total_travel) * 100.0))


@dataclass(frozen=True)
class SunPosition:
    """Current solar position in degrees."""

    azimuth_deg: float
    elevation_deg: float


@dataclass(frozen=True)
class HouseAttachment:
    """Optional simplified house geometry next to the pergola."""

    height_m: float
    extends_left_m: float
    extends_right_m: float


@dataclass(frozen=True)
class PergolaGeometry:
    """Physical pergola and slat geometry."""

    slat_width_m: float
    slat_thickness_m: float
    slat_axis_spacing_m: float
    slat_axis_height_m: float
    pergola_length_m: float
    pergola_width_m: float
    slat_axis_azimuth_deg: float
    pergola_orientation_azimuth_deg: float
    opening_azimuth_deg: float
    house_attachment: HouseAttachment | None = None

    @property
    def axis_azimuth_deg(self) -> float:
        """Compatibility alias for older code paths."""
        return self.slat_axis_azimuth_deg


@dataclass(frozen=True)
class ActuatorConfig:
    """Mechanical slat travel and preferred optical opening."""

    closed_angle_deg: float = 0.0
    open_angle_deg: float = 90.0
    max_travel_angle_deg: float = 135.0
    open_actuator_percent: float | None = None
    closes_again_after_open: bool = False

    def clamp_angle(self, angle_deg: float) -> float:
        """Clamp an angle to the mechanical travel range."""
        return max(self.closed_angle_deg, min(self.max_travel_angle_deg, angle_deg))

    def resolved_open_actuator_percent(self) -> float:
        """Return the configured or derived actuator percentage at the open point."""
        if self.open_actuator_percent is None:
            return derived_open_actuator_percent(
                self.closed_angle_deg,
                self.open_angle_deg,
                self.max_travel_angle_deg,
            )
        return max(0.0, min(100.0, self.open_actuator_percent))


@dataclass(frozen=True)
class CommandTarget:
    """How the calculated target is mapped to a Home Assistant entity."""

    entity_id: str
    mode: str
    value_min: float = 0.0
    value_max: float = 100.0

    def __post_init__(self) -> None:
        """Validate command target mode."""
        if self.mode not in ACTUATOR_MODES:
            msg = f"Unsupported command mode: {self.mode}"
            raise ValueError(msg)


@dataclass(frozen=True)
class TrackingConfig:
    """User-facing tracking behaviour configuration."""

    strategy: str = TRACKING_BALANCED
    max_direct_sun_depth_m: float = 0.25
    open_before_sunrise_minutes: int = 0
    preopen_actuator_percent: int = 0

    def __post_init__(self) -> None:
        """Validate strategy selection."""
        if self.strategy not in TRACKING_STRATEGIES:
            msg = f"Unsupported strategy: {self.strategy}"
            raise ValueError(msg)


@dataclass(frozen=True)
class WeatherConfig:
    """Weather override thresholds and fallback position."""

    override_actuator_percent: int = 0
    wind_speed_threshold: float | None = None
    rain_threshold: float | None = None
    severe_binary_enabled: bool = True


@dataclass(frozen=True)
class WeatherReadings:
    """Current weather inputs for safety override."""

    wind_speed: float | None = None
    rain_rate: float | None = None
    is_raining: bool = False
    is_windy: bool = False
    severe: bool = False


@dataclass(frozen=True)
class AdditionalProtectedAreaConfig:
    """Optional extra rectangular protection zone aligned with the pergola."""

    enabled: bool = False
    length_m: float = 0.0
    width_m: float = 0.0
    offset_east_m: float = 0.0
    offset_north_m: float = 0.0


@dataclass(frozen=True)
class ProjectionResult:
    """3D projection result for the current sun/slat configuration."""

    sun_in_front: bool
    projected_elevation_deg: float
    orientation_projected_elevation_deg: float
    width_projected_elevation_deg: float
    full_sun_depth_m: float
    direct_sun_depth_m: float
    orientation_penetration_depth_m: float
    width_penetration_depth_m: float
    sun_patch_start_x_m: float | None
    sun_patch_end_x_m: float | None
    sun_patch_start_y_m: float | None
    sun_patch_end_y_m: float | None
    openness_fraction: float
    lateral_shift_on_house_m: float
    house_hit_height_m: float | None
    hits_house_wall: bool
    house_overlap_start_m: float | None
    house_overlap_end_m: float | None
    base_protected_overlap_m2: float
    additional_protected_overlap_m2: float
    effective_protected_overlap_m2: float
    protected_zone_breached: bool


@dataclass(frozen=True)
class ControlConfig:
    """Complete controller configuration bundle."""

    geometry: PergolaGeometry
    actuator: ActuatorConfig
    target: CommandTarget
    tracking: TrackingConfig
    weather: WeatherConfig | None = None
    additional_protected_area: AdditionalProtectedAreaConfig | None = None


@dataclass(frozen=True)
class TrackingDecision:
    """Final controller output for the current sun/weather state."""

    actuator_percent: int
    target_angle_deg: float
    openness_percent: int
    strategy_used: str
    weather_override_active: bool
    reason: str
    projection: ProjectionResult

    @property
    def direct_sun_depth_m(self) -> float:
        """Convenience access to the protected-floor penetration depth."""
        return self.projection.direct_sun_depth_m

    @property
    def hits_house_wall(self) -> bool:
        """Whether the computed sun path reaches the configured house wall."""
        return self.projection.hits_house_wall


@dataclass(frozen=True)
class AdaptivePergolaData:
    """Coordinator payload exposed to Home Assistant entities."""

    sun: SunPosition
    weather: WeatherReadings
    decision: TrackingDecision
    command_value: float
    command_mode: str
    target_entity: str
    automatic_control: bool
    auto_apply: bool
    last_applied_value: float | None
    manual_override_active: bool
    manual_override_until: datetime | None
    manual_override_remaining_seconds: int
    manual_override_value: float | None
