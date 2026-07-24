"""Option-schema key guard.

Every key rendered by a pergola-facing option-schema must be listed in
``_KNOWN_OPTION_KEYS`` (or in ``_TRANSIENT_FORM_KEYS`` for form-only fields
that are never persisted). The test fails when a new CONF_* option is added
to any schema without updating this file — making every new persisted option
a conscious, reviewed decision.

This replaces the pre-stage-4 sync/duplicate coverage scaffolding (the
selective-sync and duplicate flows were deleted with the rest of the
Adaptive-Cover-Pro heritage, docs/CONFIG_FLOW_REWORK.md): the old
``SYNC_CATEGORIES`` / duplicate-only bookkeeping collapsed into this single
known-keys list.
"""

import voluptuous as vol

from custom_components.adaptive_pergola.config_flow import (
    AUTOMATION_SCHEMA,
    CUSTOM_POSITION_SCHEMA,
    DEBUG_SCHEMA,
    GEOMETRY_LOUVERED_ROOF_SCHEMA,
    LIGHT_CLOUD_SCHEMA,
    MANUAL_OVERRIDE_SCHEMA,
    MOTION_OVERRIDE_SCHEMA,
    POSITION_SCHEMA,
    SUN_TRACKING_SCHEMA,
    TEMPERATURE_CLIMATE_SCHEMA,
    WEATHER_OPTIONS,
    WEATHER_OVERRIDE_SCHEMA,
)
from custom_components.adaptive_pergola.const import (
    CONF_SUN_WINDOW_END,
    CONF_SUN_WINDOW_START,
)

# Transient form-only fields: rendered on a step but popped on submit and never
# persisted (stage 2 sun-window presentation of the canonical azimuth/fov keys).
_TRANSIENT_FORM_KEYS: frozenset[str] = frozenset(
    {
        CONF_SUN_WINDOW_START,
        CONF_SUN_WINDOW_END,
    }
)

# Every key any pergola-facing option schema may render. Includes the inline
# cover-entities keys ("group", "device_id") that have no module-level schema.
_KNOWN_OPTION_KEYS: frozenset[str] = frozenset(
    {
        "climate_mode",
        "cloud_coverage_entity",
        "cloud_coverage_threshold",
        "cloud_suppression",
        "cloudy_position",
        "custom_position_1",
        "custom_position_10",
        "custom_position_2",
        "custom_position_3",
        "custom_position_4",
        "custom_position_5",
        "custom_position_6",
        "custom_position_7",
        "custom_position_8",
        "custom_position_9",
        "custom_position_min_mode_1",
        "custom_position_min_mode_10",
        "custom_position_min_mode_2",
        "custom_position_min_mode_3",
        "custom_position_min_mode_4",
        "custom_position_min_mode_5",
        "custom_position_min_mode_6",
        "custom_position_min_mode_7",
        "custom_position_min_mode_8",
        "custom_position_min_mode_9",
        "custom_position_priority_1",
        "custom_position_priority_10",
        "custom_position_priority_2",
        "custom_position_priority_3",
        "custom_position_priority_4",
        "custom_position_priority_5",
        "custom_position_priority_6",
        "custom_position_priority_7",
        "custom_position_priority_8",
        "custom_position_priority_9",
        "custom_position_sensors_1",
        "custom_position_sensors_10",
        "custom_position_sensors_2",
        "custom_position_sensors_3",
        "custom_position_sensors_4",
        "custom_position_sensors_5",
        "custom_position_sensors_6",
        "custom_position_sensors_7",
        "custom_position_sensors_8",
        "custom_position_sensors_9",
        "custom_position_template_1",
        "custom_position_template_10",
        "custom_position_template_2",
        "custom_position_template_3",
        "custom_position_template_4",
        "custom_position_template_5",
        "custom_position_template_6",
        "custom_position_template_7",
        "custom_position_template_8",
        "custom_position_template_9",
        "custom_position_template_mode_1",
        "custom_position_template_mode_10",
        "custom_position_template_mode_2",
        "custom_position_template_mode_3",
        "custom_position_template_mode_4",
        "custom_position_template_mode_5",
        "custom_position_template_mode_6",
        "custom_position_template_mode_7",
        "custom_position_template_mode_8",
        "custom_position_template_mode_9",
        "custom_position_use_my_1",
        "custom_position_use_my_10",
        "custom_position_use_my_2",
        "custom_position_use_my_3",
        "custom_position_use_my_4",
        "custom_position_use_my_5",
        "custom_position_use_my_6",
        "custom_position_use_my_7",
        "custom_position_use_my_8",
        "custom_position_use_my_9",
        "debug_categories",
        "debug_event_buffer_size",
        "debug_mode",
        "default_percentage",
        "delta_position",
        "delta_time",
        "device_id",
        "dry_run",
        "enable_max_position",
        "enable_min_position",
        "enable_my_position_entities",
        "enable_sun_tracking",
        "end_entity",
        "end_of_window_position",
        "end_time",
        "endpoint_use_open_close",
        "enforce_delta_at_endpoints",
        "group",
        "irradiance_entity",
        "irradiance_threshold",
        "is_sunny_sensor",
        "is_sunny_template",
        "is_sunny_template_mode",
        "lr_airflow_by_temp",
        "lr_axis_azimuth",
        "lr_footprint_x",
        "lr_footprint_y",
        "lr_low_sun_position",
        "lr_max_light_position",
        "lr_plane_pitch",
        "lr_protected_height",
        "lr_roof_height",
        "lr_shade_airflow",
        "lr_shade_ext_azimuth_1",
        "lr_shade_ext_azimuth_2",
        "lr_shade_ext_distance_1",
        "lr_shade_ext_distance_2",
        "lr_slat_chord",
        "lr_slat_spacing",
        "lr_slat_thickness",
        "lr_theta_max",
        "lr_theta_min",
        "lr_tilt_vertical_pct",
        "lux_entity",
        "lux_threshold",
        "manual_ignore_external",
        "manual_ignore_intermediate",
        "manual_override_duration",
        "manual_override_input_entities",
        "manual_override_reset",
        "manual_threshold",
        "max_coverage_steps",
        "max_elevation",
        "max_position",
        "min_elevation",
        "min_position",
        "min_position_sun_tracking",
        "minimize_movements",
        "morning_position",
        "morning_position_hold",
        "morning_position_lead",
        "motion_media_players",
        "motion_sensors",
        "motion_template",
        "motion_template_mode",
        "motion_timeout",
        "motion_timeout_mode",
        "my_position_value",
        "open_close_threshold",
        "outside_temp",
        "outside_threshold",
        "presence_entity",
        "presence_template",
        "presence_template_mode",
        "resync_endstop_mode",
        "resync_travel_threshold",
        "start_entity",
        "start_time",
        "summer_close_bypass_sun_floor",
        "sunset_position",
        "sunset_use_my",
        "temp_entity",
        "temp_high",
        "temp_low",
        "transit_timeout",
        "weather_bypass_auto_control",
        "weather_enabled",
        "weather_entity",
        "weather_is_raining_sensor",
        "weather_is_raining_template",
        "weather_is_raining_template_mode",
        "weather_is_windy_sensor",
        "weather_is_windy_template",
        "weather_is_windy_template_mode",
        "weather_override_min_mode",
        "weather_override_position",
        "weather_rain_sensor",
        "weather_rain_threshold",
        "weather_severe_sensors",
        "weather_state",
        "weather_timeout",
        "weather_wind_direction_sensor",
        "weather_wind_direction_tolerance",
        "weather_wind_speed_sensor",
        "weather_wind_speed_threshold",
        "winter_close_insulation",
    }
)

# Named module-level option schemas from config_flow.py.
# CONFIG_SCHEMA (data-step, has "name"/"mode") is intentionally excluded.
_OPTION_SCHEMAS: list[vol.Schema] = [
    GEOMETRY_LOUVERED_ROOF_SCHEMA,
    SUN_TRACKING_SCHEMA,  # renders the transient sun_window_* fields (stage 2)
    POSITION_SCHEMA,
    AUTOMATION_SCHEMA,
    MANUAL_OVERRIDE_SCHEMA,
    CUSTOM_POSITION_SCHEMA,
    MOTION_OVERRIDE_SCHEMA,
    DEBUG_SCHEMA,
    WEATHER_OVERRIDE_SCHEMA,
    LIGHT_CLOUD_SCHEMA,
    TEMPERATURE_CLIMATE_SCHEMA,
    WEATHER_OPTIONS,
]


def _keys(schema: vol.Schema) -> frozenset[str]:
    """Extract all string keys from a voluptuous Schema."""
    result: set[str] = set()
    for marker in schema.schema:
        key = (
            marker.schema if isinstance(marker, vol.Required | vol.Optional) else marker
        )
        if isinstance(key, str):
            result.add(key)
    return frozenset(result)


def _all_option_schema_keys() -> frozenset[str]:
    """Return every option key any pergola-facing schema renders."""
    keys: set[str] = set()
    for schema in _OPTION_SCHEMAS:
        keys |= _keys(schema)
    # Inline in _build_cover_entity_schema (no module-level constant).
    keys.update({"group", "device_id"})
    return frozenset(keys)


class TestOptionSchemaKeysAreKnown:
    """Every option-schema key must be a known key or an explicit transient."""

    def test_every_schema_key_is_known_or_transient(self):
        unknown = _all_option_schema_keys() - _KNOWN_OPTION_KEYS - _TRANSIENT_FORM_KEYS
        assert not unknown, (
            f"Option keys not in the known-keys list: {sorted(unknown)}\n"
            "Fix: add the key to _KNOWN_OPTION_KEYS in this file (persisted "
            "option) or to _TRANSIENT_FORM_KEYS (form-only, popped on submit)."
        )

    def test_known_keys_list_carries_no_dead_entries(self):
        # The reverse direction: a key removed from every schema must also be
        # removed here, so the list never drifts into fiction.
        dead = _KNOWN_OPTION_KEYS - _all_option_schema_keys()
        assert not dead, (
            f"_KNOWN_OPTION_KEYS entries no longer rendered by any schema: {sorted(dead)}\n"
            "Remove them from this file (storage stays readable regardless)."
        )

    def test_transient_keys_never_overlap_known(self):
        overlap = _TRANSIENT_FORM_KEYS & _KNOWN_OPTION_KEYS
        assert not overlap, (
            f"Keys marked transient are also listed as persisted: {sorted(overlap)}"
        )
