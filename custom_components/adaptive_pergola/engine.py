"""Core pergola controller derived from Adaptive Cover Pro concepts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from .const import TRACKING_BALANCED, TRACKING_MAX_LIGHT, TRACKING_MAX_SHADE
from .models import (
    ActuatorConfig,
    CommandTarget,
    ControlConfig,
    PergolaGeometry,
    ProjectionResult,
    SunPosition,
    TrackingDecision,
    WeatherReadings,
)
from .sun import projected_elevation_deg, signed_angle_delta
from .weather import is_weather_override_active


@dataclass(frozen=True)
class PergolaOptics:
    """Intermediate optical metrics for one slat angle."""

    openness_fraction: float
    projection: ProjectionResult


@dataclass(frozen=True)
class _Rect:
    """Axis-aligned rectangle in the pergola-local ground plane."""

    start_x_m: float
    end_x_m: float
    start_y_m: float
    end_y_m: float


def actuator_percent_for_angle(actuator: ActuatorConfig, angle_deg: float) -> int:
    """Convert a mechanical angle into a 0-100 actuator command."""
    clamped = actuator.clamp_angle(angle_deg)
    travel = actuator.max_travel_angle_deg - actuator.closed_angle_deg
    if travel <= 0:
        return 0
    open_percent = actuator.resolved_open_actuator_percent()
    open_span = actuator.open_angle_deg - actuator.closed_angle_deg
    tail_span = actuator.max_travel_angle_deg - actuator.open_angle_deg

    if (
        open_span <= 0
        or tail_span < 0
        or open_percent <= 0.0
        or open_percent >= 100.0
    ):
        return round(((clamped - actuator.closed_angle_deg) / travel) * 100)

    if clamped <= actuator.open_angle_deg:
        return round(((clamped - actuator.closed_angle_deg) / open_span) * open_percent)

    if tail_span == 0:
        return round(open_percent)

    tail_percent = 100.0 - open_percent
    return round(open_percent + (((clamped - actuator.open_angle_deg) / tail_span) * tail_percent))


def angle_for_actuator_percent(actuator: ActuatorConfig, actuator_percent: float) -> float:
    """Convert a 0-100 actuator command back into a mechanical angle."""
    clamped_percent = max(0.0, min(100.0, actuator_percent))
    travel = actuator.max_travel_angle_deg - actuator.closed_angle_deg
    if travel <= 0:
        return actuator.closed_angle_deg

    open_percent = actuator.resolved_open_actuator_percent()
    open_span = actuator.open_angle_deg - actuator.closed_angle_deg
    tail_span = actuator.max_travel_angle_deg - actuator.open_angle_deg

    if (
        open_span <= 0
        or tail_span < 0
        or open_percent <= 0.0
        or open_percent >= 100.0
    ):
        return actuator.clamp_angle(
            actuator.closed_angle_deg + ((travel * clamped_percent) / 100.0)
        )

    if clamped_percent <= open_percent:
        return actuator.clamp_angle(
            actuator.closed_angle_deg + ((open_span * clamped_percent) / open_percent)
        )

    if tail_span == 0:
        return actuator.open_angle_deg

    tail_percent = 100.0 - open_percent
    return actuator.clamp_angle(
        actuator.open_angle_deg
        + (tail_span * (clamped_percent - open_percent) / tail_percent)
    )


def openness_fraction_for_angle(actuator: ActuatorConfig, angle_deg: float) -> float:
    """Return the optical opening fraction for a slat angle."""
    clamped = actuator.clamp_angle(angle_deg)
    if clamped <= actuator.closed_angle_deg:
        return 0.0
    if clamped <= actuator.open_angle_deg:
        span = actuator.open_angle_deg - actuator.closed_angle_deg
        if span <= 0:
            return 0.0
        return (clamped - actuator.closed_angle_deg) / span
    if not actuator.closes_again_after_open:
        return 1.0
    tail = actuator.max_travel_angle_deg - actuator.open_angle_deg
    if tail <= 0:
        return 1.0
    return max(0.0, 1.0 - ((clamped - actuator.open_angle_deg) / tail))


def _roof_normal_azimuth_deg(geometry: PergolaGeometry) -> float:
    """Return the configured pergola orientation from house to front edge."""
    return geometry.pergola_orientation_azimuth_deg


def _width_axis_azimuth_deg(geometry: PergolaGeometry) -> float:
    """Return the pergola width axis, positive from left to right."""
    return (geometry.pergola_orientation_azimuth_deg + 90.0) % 360.0


def _projected_elevation_magnitude_deg(elevation_deg: float, horizontal_delta_deg: float) -> float:
    """Return the magnitude of the apparent sun elevation in a horizontal plane."""
    return abs(projected_elevation_deg(elevation_deg, horizontal_delta_deg))


def _rect_overlap_area(first: _Rect | None, second: _Rect | None) -> float:
    """Return the overlapping area of two rectangles in square metres."""
    if first is None or second is None:
        return 0.0
    overlap_x = max(0.0, min(first.end_x_m, second.end_x_m) - max(first.start_x_m, second.start_x_m))
    overlap_y = max(0.0, min(first.end_y_m, second.end_y_m) - max(first.start_y_m, second.start_y_m))
    return overlap_x * overlap_y


def _pergola_footprint_rect(geometry: PergolaGeometry) -> _Rect:
    """Return the base protected area directly below the pergola."""
    return _Rect(
        start_x_m=0.0,
        end_x_m=geometry.pergola_length_m,
        start_y_m=0.0,
        end_y_m=geometry.pergola_width_m,
    )


def _sun_from_right_side(geometry: PergolaGeometry, sun: SunPosition) -> bool:
    """Return True if the sun arrives from the positive width side."""
    return abs(signed_angle_delta(_width_axis_azimuth_deg(geometry), sun.azimuth_deg)) < 90.0


def _east_north_offset_to_local(geometry: PergolaGeometry, east_m: float, north_m: float) -> tuple[float, float]:
    """Convert an east/north offset into pergola-local x/y coordinates."""
    orientation_rad = math.radians(geometry.pergola_orientation_azimuth_deg)
    width_axis_rad = math.radians(_width_axis_azimuth_deg(geometry))
    local_x = (east_m * math.sin(orientation_rad)) + (north_m * math.cos(orientation_rad))
    local_y = (east_m * math.sin(width_axis_rad)) + (north_m * math.cos(width_axis_rad))
    return (local_x, local_y)


def _additional_protected_area_rect(
    geometry: PergolaGeometry,
    additional_protected_area,
) -> _Rect | None:
    """Return the optional extra protected area in pergola-local coordinates."""
    if (
        additional_protected_area is None
        or not additional_protected_area.enabled
        or additional_protected_area.length_m <= 0
        or additional_protected_area.width_m <= 0
    ):
        return None
    origin_x, origin_y = _east_north_offset_to_local(
        geometry,
        additional_protected_area.offset_east_m,
        additional_protected_area.offset_north_m,
    )
    return _Rect(
        start_x_m=origin_x,
        end_x_m=origin_x + additional_protected_area.length_m,
        start_y_m=origin_y,
        end_y_m=origin_y + additional_protected_area.width_m,
    )


def _sun_patch_rect(
    geometry: PergolaGeometry,
    sun: SunPosition,
    orientation_full_depth_m: float,
    width_full_depth_m: float,
) -> _Rect:
    """Project the pergola roof footprint onto the ground along the current sun vector."""
    shift_x = -orientation_full_depth_m if sun_in_front_of_pergola(geometry, sun) else orientation_full_depth_m
    shift_y = -width_full_depth_m if _sun_from_right_side(geometry, sun) else width_full_depth_m
    return _Rect(
        start_x_m=shift_x,
        end_x_m=geometry.pergola_length_m + shift_x,
        start_y_m=shift_y,
        end_y_m=geometry.pergola_width_m + shift_y,
    )


def sun_in_front_of_pergola(geometry: PergolaGeometry, sun: SunPosition) -> bool:
    """Return True if the sun can enter from the pergola front edge."""
    front_normal = _roof_normal_azimuth_deg(geometry)
    return abs(signed_angle_delta(front_normal, sun.azimuth_deg)) < 90.0


def _full_sun_penetration_depth(geometry: PergolaGeometry, projected_elevation: float) -> float:
    """Return the geometric penetration depth without slat attenuation."""
    effective_elevation = max(projected_elevation, 0.1)
    return geometry.slat_axis_height_m / math.tan(math.radians(effective_elevation))


def _house_overlap(
    geometry: PergolaGeometry,
    lateral_shift: float,
) -> tuple[float | None, float | None]:
    """Return the illuminated overlap span on the attached house wall."""
    if geometry.house_attachment is None:
        return (None, None)
    illuminated_start = lateral_shift
    illuminated_end = geometry.pergola_width_m + lateral_shift
    house_start = -geometry.house_attachment.extends_left_m
    house_end = geometry.pergola_width_m + geometry.house_attachment.extends_right_m
    overlap_start = max(illuminated_start, house_start)
    overlap_end = min(illuminated_end, house_end)
    if overlap_end <= overlap_start:
        return (None, None)
    return (overlap_start, overlap_end)


def blocking_angle_for_sun(geometry: PergolaGeometry, sun: SunPosition) -> float:
    """Compute a slat angle that minimizes direct sun through the slat spacing.

    The formula is analogous to the ACP venetian-blind tilt calculation, but is
    used here only as a first-order approximation for a horizontal pergola roof.
    """
    if sun.elevation_deg <= 0:
        return 0.0

    cross_section_delta = signed_angle_delta(geometry.opening_azimuth_deg, sun.azimuth_deg)
    beta_deg = _projected_elevation_magnitude_deg(sun.elevation_deg, cross_section_delta)
    beta_rad = math.radians(beta_deg)
    ratio = geometry.slat_axis_spacing_m / geometry.slat_width_m
    discriminant = (math.tan(beta_rad) ** 2) - (ratio**2) + 1.0
    if discriminant < 0:
        return 0.0

    numerator = math.tan(beta_rad) + math.sqrt(discriminant)
    denominator = 1.0 + ratio
    angle_rad = 2.0 * math.atan(numerator / denominator)
    return max(0.0, math.degrees(angle_rad))


def light_angle_for_sun(
    geometry: PergolaGeometry,
    actuator: ActuatorConfig,
    sun: SunPosition,
) -> float:
    """Compute a sun-following angle for maximum-light operation.

    In max-light mode the slats should follow the real solar elevation, independent
    of the horizontal sun azimuth. The configured open angle acts as the upper
    limit for this tracking.
    """
    del geometry
    if sun.elevation_deg <= 0:
        return actuator.closed_angle_deg

    return actuator.clamp_angle(min(sun.elevation_deg, actuator.open_angle_deg))


def shade_angle_for_sun(
    geometry: PergolaGeometry,
    actuator: ActuatorConfig,
    sun: SunPosition,
) -> float:
    """Compute a sun-following shade angle based on the light angle plus 90 degrees."""
    light_angle = light_angle_for_sun(geometry, actuator, sun)
    if sun.elevation_deg <= 0:
        return actuator.closed_angle_deg
    return actuator.clamp_angle(light_angle + 90.0)


def project_pergola_shadow(
    geometry: PergolaGeometry,
    actuator: ActuatorConfig,
    sun: SunPosition,
    angle_deg: float,
    *,
    tolerance_depth_m: float,
    additional_protected_area=None,
) -> ProjectionResult:
    """Project direct sunlight under the pergola and onto the attached house.

    Coordinate model:
    - x-axis: from attached house toward the open front edge of the pergola
    - y-axis: along the slat axis from left to right
    - z-axis: vertical

    The result intentionally stays conservative: floor penetration is modelled as
    a projected sun patch on the ground, while house impact is treated as a hard
    hit if direct rays can still reach the wall at any meaningful opening.
    """
    if sun.elevation_deg <= 0:
        return ProjectionResult(
            sun_in_front=False,
            projected_elevation_deg=0.0,
            orientation_projected_elevation_deg=0.0,
            width_projected_elevation_deg=0.0,
            full_sun_depth_m=0.0,
            direct_sun_depth_m=0.0,
            orientation_penetration_depth_m=0.0,
            width_penetration_depth_m=0.0,
            sun_patch_start_x_m=None,
            sun_patch_end_x_m=None,
            sun_patch_start_y_m=None,
            sun_patch_end_y_m=None,
            openness_fraction=0.0,
            lateral_shift_on_house_m=0.0,
            house_hit_height_m=None,
            hits_house_wall=False,
            house_overlap_start_m=None,
            house_overlap_end_m=None,
            base_protected_overlap_m2=0.0,
            additional_protected_overlap_m2=0.0,
            effective_protected_overlap_m2=0.0,
            protected_zone_breached=False,
        )

    front_delta = signed_angle_delta(_roof_normal_azimuth_deg(geometry), sun.azimuth_deg)
    width_delta = signed_angle_delta(_width_axis_azimuth_deg(geometry), sun.azimuth_deg)
    cross_section_delta = signed_angle_delta(geometry.opening_azimuth_deg, sun.azimuth_deg)
    projected_elevation = _projected_elevation_magnitude_deg(sun.elevation_deg, cross_section_delta)
    orientation_projected_elevation = _projected_elevation_magnitude_deg(
        sun.elevation_deg, front_delta
    )
    width_projected_elevation = _projected_elevation_magnitude_deg(sun.elevation_deg, width_delta)
    openness = openness_fraction_for_angle(actuator, angle_deg)
    front_full_depth = _full_sun_penetration_depth(geometry, orientation_projected_elevation)
    width_full_depth = _full_sun_penetration_depth(geometry, width_projected_elevation)
    front_direct_depth = front_full_depth * openness
    width_direct_depth = width_full_depth * openness
    direct_depth = max(front_direct_depth, width_direct_depth)

    sun_patch = _sun_patch_rect(geometry, sun, front_full_depth, width_full_depth)
    base_overlap_area = _rect_overlap_area(sun_patch, _pergola_footprint_rect(geometry))
    additional_overlap_area = _rect_overlap_area(
        sun_patch,
        _additional_protected_area_rect(geometry, additional_protected_area),
    )
    effective_overlap_area = (base_overlap_area + additional_overlap_area) * openness

    sun_in_front = sun_in_front_of_pergola(geometry, sun)
    lateral_shift = (
        geometry.pergola_length_m * math.tan(math.radians(front_delta)) if sun_in_front else 0.0
    )
    house_hit_height = None
    if sun_in_front:
        house_hit_height = geometry.slat_axis_height_m - (
            geometry.pergola_length_m
            * math.tan(math.radians(max(orientation_projected_elevation, 0.1)))
        )

    overlap_start, overlap_end = _house_overlap(geometry, lateral_shift)
    hits_house = False
    if (
        geometry.house_attachment is not None
        and openness > 0.05
        and sun_in_front
        and overlap_start is not None
        and house_hit_height is not None
        and house_hit_height >= 0
        and house_hit_height <= geometry.house_attachment.height_m
        and sun_patch.start_x_m < 0
    ):
        hits_house = True

    protected_zone_breached = effective_overlap_area > 0.01 or hits_house
    return ProjectionResult(
        sun_in_front=sun_in_front,
        projected_elevation_deg=round(projected_elevation, 3),
        orientation_projected_elevation_deg=round(orientation_projected_elevation, 3),
        width_projected_elevation_deg=round(width_projected_elevation, 3),
        full_sun_depth_m=round(max(front_full_depth, width_full_depth), 3),
        direct_sun_depth_m=round(direct_depth, 3),
        orientation_penetration_depth_m=round(front_direct_depth, 3),
        width_penetration_depth_m=round(width_direct_depth, 3),
        sun_patch_start_x_m=round(sun_patch.start_x_m, 3),
        sun_patch_end_x_m=round(sun_patch.end_x_m, 3),
        sun_patch_start_y_m=round(sun_patch.start_y_m, 3),
        sun_patch_end_y_m=round(sun_patch.end_y_m, 3),
        openness_fraction=openness,
        lateral_shift_on_house_m=round(lateral_shift, 3),
        house_hit_height_m=None if house_hit_height is None else round(house_hit_height, 3),
        hits_house_wall=hits_house,
        house_overlap_start_m=None if overlap_start is None else round(overlap_start, 3),
        house_overlap_end_m=None if overlap_end is None else round(overlap_end, 3),
        base_protected_overlap_m2=round(base_overlap_area, 3),
        additional_protected_overlap_m2=round(additional_overlap_area, 3),
        effective_protected_overlap_m2=round(effective_overlap_area, 3),
        protected_zone_breached=protected_zone_breached,
    )


def direct_sun_penetration_depth(
    geometry: PergolaGeometry,
    actuator: ActuatorConfig,
    sun: SunPosition,
    angle_deg: float,
) -> float:
    """Estimate how far direct sunlight reaches below the pergola roof.

    The model deliberately stays conservative and simple for a first version:
    it tracks the maximum penetration from the pergola front/back and side edges
    and attenuates it with the current slat openness.
    """
    return project_pergola_shadow(
        geometry,
        actuator,
        sun,
        angle_deg,
        tolerance_depth_m=geometry.pergola_length_m,
    ).direct_sun_depth_m


def optics_for_angle(
    geometry: PergolaGeometry,
    actuator: ActuatorConfig,
    sun: SunPosition,
    angle_deg: float,
    *,
    tolerance_depth_m: float,
    additional_protected_area=None,
) -> PergolaOptics:
    """Build optical metrics for a specific slat angle."""
    openness = openness_fraction_for_angle(actuator, angle_deg)
    projection = project_pergola_shadow(
        geometry,
        actuator,
        sun,
        angle_deg,
        tolerance_depth_m=tolerance_depth_m,
        additional_protected_area=additional_protected_area,
    )
    return PergolaOptics(openness_fraction=openness, projection=projection)


def should_preopen_before_sunrise(
    config: ControlConfig,
    now: datetime | None,
    next_sunrise: datetime | None,
) -> bool:
    """Return True when the anti-condensation pre-open window is active."""
    if now is None or next_sunrise is None:
        return False
    lead_minutes = config.tracking.open_before_sunrise_minutes
    if lead_minutes <= 0 or config.tracking.preopen_actuator_percent <= 0:
        return False
    start = next_sunrise - timedelta(minutes=lead_minutes)
    return start <= now < next_sunrise


def command_value_from_decision(target: CommandTarget, decision: TrackingDecision) -> float:
    """Map a tracking decision to the configured actuator target value."""
    if target.mode in {"cover_tilt_percentage", "cover_position_percentage"}:
        return float(decision.actuator_percent)
    if target.mode == "number_angle_degrees":
        return float(decision.target_angle_deg)
    if target.mode == "number_actuator_percentage":
        return float(decision.actuator_percent)
    return target.value_min + (
        (decision.actuator_percent / 100.0) * (target.value_max - target.value_min)
    )


def compute_tracking_decision(
    config: ControlConfig,
    sun: SunPosition,
    weather: WeatherReadings | None = None,
    *,
    now: datetime | None = None,
    next_sunrise: datetime | None = None,
) -> TrackingDecision:
    """Compute the current pergola command from sun and weather data."""
    if is_weather_override_active(config.weather, weather):
        override_percent = config.weather.override_actuator_percent if config.weather else 0
        target_angle = angle_for_actuator_percent(config.actuator, override_percent)
        optics = optics_for_angle(
            config.geometry,
            config.actuator,
            sun,
            target_angle,
            tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
            additional_protected_area=config.additional_protected_area,
        )
        return TrackingDecision(
            actuator_percent=override_percent,
            target_angle_deg=round(target_angle, 2),
            openness_percent=round(optics.openness_fraction * 100),
            strategy_used="weather_override",
            weather_override_active=True,
            reason="weather override active",
            projection=optics.projection,
        )

    if should_preopen_before_sunrise(config, now, next_sunrise):
        target_percent = config.tracking.preopen_actuator_percent
        target_angle = angle_for_actuator_percent(config.actuator, target_percent)
        optics = optics_for_angle(
            config.geometry,
            config.actuator,
            sun,
            target_angle,
            tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
            additional_protected_area=config.additional_protected_area,
        )
        return TrackingDecision(
            actuator_percent=target_percent,
            target_angle_deg=round(target_angle, 2),
            openness_percent=round(optics.openness_fraction * 100),
            strategy_used="preopen_before_sunrise",
            weather_override_active=False,
            reason="pre-open window active before sunrise",
            projection=optics.projection,
        )

    light_angle = light_angle_for_sun(config.geometry, config.actuator, sun)
    shade_angle = shade_angle_for_sun(config.geometry, config.actuator, sun)

    light_optics = optics_for_angle(
        config.geometry,
        config.actuator,
        sun,
        light_angle,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
        additional_protected_area=config.additional_protected_area,
    )
    shade_optics = optics_for_angle(
        config.geometry,
        config.actuator,
        sun,
        shade_angle,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
        additional_protected_area=config.additional_protected_area,
    )

    if config.tracking.strategy == TRACKING_MAX_LIGHT:
        selected_angle = light_angle
        selected_optics = light_optics
        reason = "max_light strategy tracks the solar elevation"
    elif config.tracking.strategy == TRACKING_MAX_SHADE:
        selected_angle = shade_angle
        selected_optics = shade_optics
        reason = "max_shade strategy uses max_light plus 90 degrees capped by travel"
    else:
        if light_optics.projection.protected_zone_breached:
            selected_angle = shade_angle
            selected_optics = shade_optics
            reason = (
                "balanced strategy switched to shade because protected zone was breached"
            )
        else:
            selected_angle = light_angle
            selected_optics = light_optics
            reason = "balanced strategy keeps maximum light within tolerance"

    return TrackingDecision(
        actuator_percent=actuator_percent_for_angle(config.actuator, selected_angle),
        target_angle_deg=round(selected_angle, 2),
        openness_percent=round(selected_optics.openness_fraction * 100),
        strategy_used=config.tracking.strategy,
        weather_override_active=False,
        reason=reason,
        projection=selected_optics.projection,
    )
