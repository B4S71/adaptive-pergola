"""Sync/duplicate coverage tests.

These tests are a safety net: adding a new CONF_* option to any option schema
in config_flow.py will cause test_all_option_schema_keys_are_in_sync_categories_or_excluded
to fail unless you also:
  - Add the key to the appropriate SYNC_CATEGORIES entry in config_flow.py, OR
  - Add it to _DUPLICATE_ONLY_KEYS below (for options that intentionally copy
    only via the Duplicate flow and are not selectively syncable, e.g. debug flags).

Adding a key to _SHARED_OPTIONS_EXCLUDED instead will be caught by
test_shared_options_excluded_is_exact — that set is intentionally small and
rarely changes.
"""

import voluptuous as vol

from custom_components.adaptive_pergola.config_flow import (
    AUTOMATION_SCHEMA,
    CUSTOM_POSITION_SCHEMA,
    DEBUG_SCHEMA,
    GEOMETRY_LOUVERED_ROOF_SCHEMA,
    INTERPOLATION_OPTIONS,
    LIGHT_CLOUD_SCHEMA,
    MANUAL_OVERRIDE_SCHEMA,
    MOTION_OVERRIDE_SCHEMA,
    POSITION_SCHEMA,
    SYNC_CATEGORIES,
    SUN_TRACKING_SCHEMA,
    TEMPERATURE_CLIMATE_SCHEMA,
    WEATHER_OPTIONS,
    WEATHER_OVERRIDE_SCHEMA,
    _SHARED_OPTIONS_EXCLUDED,
    _build_glare_zones_schema,
)
from custom_components.adaptive_pergola.const import (
    BLIND_SPOT_SLOTS,
    CONF_AZIMUTH,
    CONF_DEBUG_CATEGORIES,
    CONF_DEBUG_EVENT_BUFFER_SIZE,
    CONF_DEBUG_MODE,
    CONF_DEVICE_ID,
    CONF_DRY_RUN,
    CONF_ENABLE_GLARE_ZONES,
    CONF_ENTITIES,
    CONF_SUN_WINDOW_END,
    CONF_SUN_WINDOW_START,
)

# Options intentionally in the Duplicate flow (copy-all) but NOT in selective sync.
# Only add here when the option is genuinely non-transferable across covers
# (e.g. per-instance debug flags). All other options should be in SYNC_CATEGORIES.
_DUPLICATE_ONLY_KEYS: frozenset[str] = frozenset(
    {
        # Transient-only sun-window form fields (docs/CONFIG_FLOW_REWORK.md,
        # stage 2): shown on the sun-tracking step but popped on submit and
        # converted to the canonical set_azimuth / fov_left / fov_right keys.
        # Never persisted, so never synced or duplicated.
        CONF_SUN_WINDOW_START,
        CONF_SUN_WINDOW_END,
        CONF_DRY_RUN,
        CONF_DEBUG_MODE,
        CONF_DEBUG_CATEGORIES,
        CONF_DEBUG_EVENT_BUFFER_SIZE,
        # Louvered-roof geometry + behaviour keys. Upstream (Adaptive Cover
        # Pro) never listed the louvered geometry schema in SYNC_CATEGORIES,
        # so these copy via the Duplicate flow only. Listed here to preserve
        # that behaviour byte-for-byte in the pergola split; promoting them
        # to a SYNC_CATEGORIES entry is a deliberate future product change.
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
        "morning_position",
        "morning_position_hold",
        "morning_position_lead",
    }
)

# Named module-level option schemas from config_flow.py.
# CONFIG_SCHEMA (data-step, has "name"/"mode") is intentionally excluded.
_OPTION_SCHEMAS: list[vol.Schema] = [
    GEOMETRY_LOUVERED_ROOF_SCHEMA,
    # Renders the transient sun_window_start/end fields (stage 2); the canonical
    # CONF_AZIMUTH they map to stays in _SHARED_OPTIONS_EXCLUDED, the canonical
    # fov_left/fov_right stay in SYNC_CATEGORIES["sun_tracking"].
    SUN_TRACKING_SCHEMA,
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
    INTERPOLATION_OPTIONS,
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
    """Return every option key that can end up in config_entry.options."""
    keys: set[str] = set()

    # Keys from all named module-level schemas
    for schema in _OPTION_SCHEMAS:
        keys |= _keys(schema)

    # Glare zone slot keys — dynamic schema, must call the builder to enumerate
    keys |= _keys(_build_glare_zones_schema())

    # Keys that only appear in inline schemas (not importable module-level constants).
    # Update this set if you add a new option directly inside an async_step_* method.
    keys.update(
        {
            CONF_ENABLE_GLARE_ZONES,  # added by _get_sun_tracking_schema() extension
            # Blind-spot slots 1–3 are rendered inline by blind_spot_schema (#701).
            *(
                keys[sub]
                for keys in BLIND_SPOT_SLOTS.values()
                for sub in ("left", "right", "elevation")
            ),
            CONF_ENTITIES,  # inline in _build_cover_entity_schema
            CONF_DEVICE_ID,
        }
    )

    return frozenset(keys)


class TestSyncCoverage:
    """Verify all option schema keys are covered by the duplicate/sync flows."""

    def test_all_option_schema_keys_are_in_sync_categories_or_excluded(self):
        """Every option schema key must be covered by selective sync or an explicit exemption.

        Fails when a new CONF_* is added to a schema but SYNC_CATEGORIES is not updated.
        """
        all_sync_keys = frozenset().union(*SYNC_CATEGORIES.values())
        intentionally_uncovered = _SHARED_OPTIONS_EXCLUDED | _DUPLICATE_ONLY_KEYS

        schema_keys = _all_option_schema_keys()
        uncovered = schema_keys - all_sync_keys - intentionally_uncovered

        assert not uncovered, (
            f"Option keys not in SYNC_CATEGORIES or a known exclusion set: {sorted(uncovered)}\n"
            "Fix: add the key to the right SYNC_CATEGORIES entry in config_flow.py,\n"
            "or add it to _DUPLICATE_ONLY_KEYS in this file if it should only copy via Duplicate."
        )

    def test_shared_options_excluded_is_exact(self):
        """_SHARED_OPTIONS_EXCLUDED must stay exactly {CONF_ENTITIES, CONF_AZIMUTH, CONF_DEVICE_ID}.

        Catches an option accidentally added to the exclusion set, which would
        silently drop it from the Duplicate flow as well as selective sync.
        If you genuinely need a new per-window exclusion, update this assertion
        with an explanation comment.
        """
        assert (
            frozenset({CONF_ENTITIES, CONF_AZIMUTH, CONF_DEVICE_ID})
            == _SHARED_OPTIONS_EXCLUDED
        )

    def test_duplicate_only_keys_are_not_in_sync_categories(self):
        """Keys listed as duplicate-only must not also appear in SYNC_CATEGORIES.

        If a debug option is later promoted to a sync-able setting, remove it
        from _DUPLICATE_ONLY_KEYS.
        """
        all_sync_keys = frozenset().union(*SYNC_CATEGORIES.values())
        incorrectly_in_sync = _DUPLICATE_ONLY_KEYS & all_sync_keys

        assert not incorrectly_in_sync, (
            f"Keys are in both _DUPLICATE_ONLY_KEYS and SYNC_CATEGORIES: {sorted(incorrectly_in_sync)}.\n"
            "Remove them from _DUPLICATE_ONLY_KEYS in this file."
        )

    def test_shared_options_excluded_not_in_sync_categories(self):
        """Per-window excluded keys must not appear in SYNC_CATEGORIES either.

        These keys are intentionally skipped in both flows; putting them in
        SYNC_CATEGORIES would be contradictory.
        """
        all_sync_keys = frozenset().union(*SYNC_CATEGORIES.values())
        overlap = _SHARED_OPTIONS_EXCLUDED & all_sync_keys

        assert not overlap, (
            f"Keys in _SHARED_OPTIONS_EXCLUDED are also in SYNC_CATEGORIES: {sorted(overlap)}.\n"
            "Remove them from one or the other."
        )
