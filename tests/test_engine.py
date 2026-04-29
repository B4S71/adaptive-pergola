from __future__ import annotations

from datetime import datetime, timedelta

from custom_components.adaptive_pergola.const import (
    ACTUATOR_MODE_COVER_TILT,
    ACTUATOR_MODE_NUMBER_CUSTOM,
    TRACKING_BALANCED,
    TRACKING_MAX_LIGHT,
    TRACKING_MAX_SHADE,
)
from custom_components.adaptive_pergola.engine import (
    actuator_percent_for_angle,
    angle_for_actuator_percent,
    blocking_angle_for_sun,
    command_value_from_decision,
    compute_tracking_decision,
    direct_sun_penetration_depth,
    light_angle_for_sun,
    openness_fraction_for_angle,
    project_pergola_shadow,
    shade_angle_for_sun,
)
from custom_components.adaptive_pergola.models import (
    ActuatorConfig,
    AdditionalProtectedAreaConfig,
    CommandTarget,
    ControlConfig,
    HouseAttachment,
    PergolaGeometry,
    ShadowCastingWallConfig,
    SunPosition,
    TrackingConfig,
    WeatherConfig,
    WeatherReadings,
)


def build_config(*, strategy: str = TRACKING_BALANCED) -> ControlConfig:
    return ControlConfig(
        geometry=PergolaGeometry(
            slat_width_m=0.18,
            slat_thickness_m=0.02,
            slat_axis_spacing_m=0.20,
            slat_axis_height_m=2.5,
            pergola_length_m=4.0,
            pergola_width_m=3.0,
            slat_axis_azimuth_deg=0.0,
            pergola_orientation_azimuth_deg=90.0,
            opening_azimuth_deg=90.0,
        ),
        actuator=ActuatorConfig(
            closed_angle_deg=0.0,
            open_angle_deg=90.0,
            max_travel_angle_deg=135.0,
        ),
        target=CommandTarget(
            entity_id="cover.pergola_demo",
            mode=ACTUATOR_MODE_COVER_TILT,
        ),
        tracking=TrackingConfig(
            strategy=strategy,
            max_direct_sun_depth_m=0.40,
            open_before_sunrise_minutes=30,
            preopen_actuator_percent=20,
        ),
        weather=WeatherConfig(
            override_actuator_percent=0,
            wind_speed_threshold=40.0,
            rain_threshold=0.8,
        ),
        additional_protected_area=AdditionalProtectedAreaConfig(),
        shadow_casting_wall=ShadowCastingWallConfig(),
    )


def test_openness_fraction_reaches_one_at_open_angle() -> None:
    actuator = ActuatorConfig(open_angle_deg=90.0, max_travel_angle_deg=135.0)
    assert openness_fraction_for_angle(actuator, 90.0) == 1.0


def test_piecewise_actuator_mapping_honours_open_point_percent() -> None:
    actuator = ActuatorConfig(
        open_angle_deg=90.0,
        max_travel_angle_deg=135.0,
        open_actuator_percent=75.0,
    )

    assert actuator_percent_for_angle(actuator, 0.0) == 0
    assert actuator_percent_for_angle(actuator, 90.0) == 75
    assert actuator_percent_for_angle(actuator, 135.0) == 100


def test_piecewise_angle_mapping_honours_open_point_percent() -> None:
    actuator = ActuatorConfig(
        open_angle_deg=90.0,
        max_travel_angle_deg=135.0,
        open_actuator_percent=75.0,
    )

    assert angle_for_actuator_percent(actuator, 0.0) == 0.0
    assert angle_for_actuator_percent(actuator, 75.0) == 90.0
    assert angle_for_actuator_percent(actuator, 100.0) == 135.0


def test_blocking_angle_returns_non_negative_value() -> None:
    geometry = build_config().geometry
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=35.0)
    assert blocking_angle_for_sun(geometry, sun) >= 0.0


def test_direct_sun_penetration_decreases_with_shade_angle() -> None:
    config = build_config()
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=22.0)

    depth_open = direct_sun_penetration_depth(
        config.geometry, config.actuator, sun, config.actuator.open_angle_deg
    )
    depth_closed = direct_sun_penetration_depth(
        config.geometry, config.actuator, sun, config.actuator.closed_angle_deg
    )

    assert depth_open > depth_closed


def test_max_light_strategy_tracks_solar_elevation() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=30.0)

    decision = compute_tracking_decision(config, sun)

    assert decision.strategy_used == TRACKING_MAX_LIGHT
    assert decision.target_angle_deg == 30.0
    assert decision.actuator_percent == 22


def test_max_light_strategy_uses_solar_elevation_even_on_opposite_side() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    sun = SunPosition(azimuth_deg=270.0, elevation_deg=30.0)

    decision = compute_tracking_decision(config, sun)

    assert decision.target_angle_deg == 30.0


def test_light_angle_matches_solar_elevation() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=30.0)

    angle = light_angle_for_sun(config.geometry, config.actuator, sun)

    assert round(angle, 2) == 30.0


def test_light_angle_returns_closed_angle_below_horizon() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=-5.0)

    angle = light_angle_for_sun(config.geometry, config.actuator, sun)

    assert angle == config.actuator.closed_angle_deg


def test_max_shade_strategy_uses_light_angle_plus_90() -> None:
    config = build_config(strategy=TRACKING_MAX_SHADE)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=20.0)

    decision = compute_tracking_decision(config, sun)

    assert decision.strategy_used == TRACKING_MAX_SHADE
    assert decision.target_angle_deg == 110.0
    assert decision.actuator_percent == 81
    assert decision.openness_percent == 100


def test_max_shade_strategy_caps_at_max_travel() -> None:
    config = build_config(strategy=TRACKING_MAX_SHADE)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=60.0)

    decision = compute_tracking_decision(config, sun)

    assert decision.target_angle_deg == 135.0


def test_shade_angle_uses_light_plus_90_independent_of_azimuth() -> None:
    config = build_config(strategy=TRACKING_MAX_SHADE)
    sun = SunPosition(azimuth_deg=270.0, elevation_deg=25.0)

    angle = shade_angle_for_sun(config.geometry, config.actuator, sun)

    assert angle == 115.0


def test_balanced_strategy_switches_to_shade_when_tolerance_exceeded() -> None:
    config = build_config(strategy=TRACKING_BALANCED)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=40.0)

    decision = compute_tracking_decision(config, sun)
    shade_decision = compute_tracking_decision(
        build_config(strategy=TRACKING_MAX_SHADE),
        sun,
    )

    assert decision.strategy_used == TRACKING_BALANCED
    assert decision.target_angle_deg == shade_decision.target_angle_deg
    assert "switched to shade" in decision.reason


def test_side_sun_penetration_uses_pergola_width_when_axis_is_parallel_to_front() -> None:
    config = build_config(strategy=TRACKING_BALANCED)
    config = ControlConfig(
        geometry=PergolaGeometry(
            slat_width_m=config.geometry.slat_width_m,
            slat_thickness_m=config.geometry.slat_thickness_m,
            slat_axis_spacing_m=config.geometry.slat_axis_spacing_m,
            slat_axis_height_m=config.geometry.slat_axis_height_m,
            pergola_length_m=config.geometry.pergola_length_m,
            pergola_width_m=config.geometry.pergola_width_m,
            slat_axis_azimuth_deg=270.0,
            pergola_orientation_azimuth_deg=270.0,
            opening_azimuth_deg=0.0,
            house_attachment=config.geometry.house_attachment,
        ),
        actuator=config.actuator,
        target=config.target,
        tracking=config.tracking,
        weather=config.weather,
    )
    sun = SunPosition(azimuth_deg=180.0, elevation_deg=54.0)

    projection = project_pergola_shadow(
        config.geometry,
        config.actuator,
        sun,
        config.actuator.open_angle_deg,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
    )

    assert projection.orientation_penetration_depth_m < 0.1
    assert projection.width_penetration_depth_m > 1.0
    assert projection.protected_zone_breached is True


def test_additional_protected_area_is_checked_outside_pergola_footprint() -> None:
    config = build_config(strategy=TRACKING_BALANCED)
    config = ControlConfig(
        geometry=config.geometry,
        actuator=config.actuator,
        target=config.target,
        tracking=config.tracking,
        weather=config.weather,
        additional_protected_area=AdditionalProtectedAreaConfig(
            enabled=True,
            length_m=4.0,
            width_m=3.0,
            offset_east_m=-4.0,
            offset_north_m=0.0,
        ),
    )
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=25.0)

    projection = project_pergola_shadow(
        config.geometry,
        config.actuator,
        sun,
        config.actuator.open_angle_deg,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
        additional_protected_area=config.additional_protected_area,
    )

    assert projection.base_protected_overlap_m2 == 0.0
    assert projection.additional_protected_overlap_m2 > 0.0
    assert projection.protected_zone_breached is True


def test_shadow_casting_wall_reduces_effective_overlap() -> None:
    config = build_config(strategy=TRACKING_BALANCED)
    config = ControlConfig(
        geometry=config.geometry,
        actuator=config.actuator,
        target=config.target,
        tracking=config.tracking,
        weather=config.weather,
        additional_protected_area=config.additional_protected_area,
        shadow_casting_wall=ShadowCastingWallConfig(
            enabled=True,
            length_m=4.0,
            height_m=2.5,
            offset_east_m=-2.0,
            offset_north_m=-2.0,
        ),
    )
    sun = SunPosition(azimuth_deg=0.0, elevation_deg=45.0)

    without_wall = project_pergola_shadow(
        config.geometry,
        config.actuator,
        sun,
        45.0,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
        additional_protected_area=config.additional_protected_area,
    )
    with_wall = project_pergola_shadow(
        config.geometry,
        config.actuator,
        sun,
        45.0,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
        additional_protected_area=config.additional_protected_area,
        shadow_casting_wall=config.shadow_casting_wall,
    )

    assert without_wall.protected_zone_breached is True
    assert with_wall.total_shadow_relief_m2 > 0.2
    assert with_wall.effective_protected_overlap_m2 < without_wall.effective_protected_overlap_m2


def test_weather_override_has_priority() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=35.0)
    weather = WeatherReadings(wind_speed=50.0)

    decision = compute_tracking_decision(config, sun, weather)

    assert decision.weather_override_active is True
    assert decision.strategy_used == "weather_override"
    assert decision.actuator_percent == 0


def test_preopen_before_sunrise_window_is_applied() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    now = datetime(2026, 4, 28, 5, 45)
    next_sunrise = now + timedelta(minutes=15)
    sun = SunPosition(azimuth_deg=30.0, elevation_deg=-4.0)

    decision = compute_tracking_decision(
        config,
        sun,
        now=now,
        next_sunrise=next_sunrise,
    )

    assert decision.strategy_used == "preopen_before_sunrise"
    assert decision.actuator_percent == 20


def test_house_wall_hit_is_detected_for_attached_pergola() -> None:
    config = build_config(strategy=TRACKING_BALANCED)
    config = ControlConfig(
        geometry=PergolaGeometry(
            slat_width_m=config.geometry.slat_width_m,
            slat_thickness_m=config.geometry.slat_thickness_m,
            slat_axis_spacing_m=config.geometry.slat_axis_spacing_m,
            slat_axis_height_m=config.geometry.slat_axis_height_m,
            pergola_length_m=config.geometry.pergola_length_m,
            pergola_width_m=config.geometry.pergola_width_m,
            slat_axis_azimuth_deg=config.geometry.slat_axis_azimuth_deg,
            pergola_orientation_azimuth_deg=config.geometry.pergola_orientation_azimuth_deg,
            opening_azimuth_deg=config.geometry.opening_azimuth_deg,
            house_attachment=HouseAttachment(
                height_m=3.0,
                extends_left_m=1.0,
                extends_right_m=1.0,
            ),
        ),
        actuator=config.actuator,
        target=config.target,
        tracking=config.tracking,
        weather=config.weather,
    )
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=25.0)

    projection = project_pergola_shadow(
        config.geometry,
        config.actuator,
        sun,
        config.actuator.open_angle_deg,
        tolerance_depth_m=config.tracking.max_direct_sun_depth_m,
    )

    assert projection.hits_house_wall is True
    assert projection.house_hit_height_m is not None
    assert projection.protected_zone_breached is True


def test_number_custom_command_scales_to_vendor_range() -> None:
    config = build_config(strategy=TRACKING_MAX_LIGHT)
    sun = SunPosition(azimuth_deg=90.0, elevation_deg=30.0)
    decision = compute_tracking_decision(config, sun)
    target = CommandTarget(
        entity_id="input_number.vendor_target",
        mode=ACTUATOR_MODE_NUMBER_CUSTOM,
        value_min=20.0,
        value_max=180.0,
    )

    command_value = command_value_from_decision(target, decision)

    assert round(command_value, 1) == 55.2
