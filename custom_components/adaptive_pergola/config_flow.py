"""Config flow for Adaptive Pergola integration."""

from __future__ import annotations

import json
import logging
from functools import cache
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    BLANK_TIME,
    BLIND_SPOT_ELEV_MODE_ABOVE,
    BLIND_SPOT_SLOTS,
    DEFAULT_BLIND_SPOT_ELEVATION_MODE,
    CONF_AZIMUTH,
    CONF_CLIMATE_MODE,
    CONF_CLOUD_SUPPRESSION,
    CONF_CLOUDY_POSITION,
    CONF_DAYTIME_GATE_SENSORS,
    CONF_DAYTIME_GATE_TEMPLATE,
    CONF_DAYTIME_GATE_TEMPLATE_MODE,
    CONF_DEFAULT_HEIGHT,
    CONF_DEFAULT_TILT,
    CONF_DELTA_POSITION,
    CONF_DELTA_TIME,
    CONF_DEVICE_ID,
    CONF_DISTANCE,
    CONF_ENABLE_BLIND_SPOT,
    CONF_ENABLE_GLARE_ZONES,
    CONF_ENABLE_MAX_POSITION,
    CONF_ENABLE_MIN_POSITION,
    CONF_ENABLE_MY_POSITION_ENTITIES,
    CONF_ENABLE_POSITION_MATCHING,
    CONF_ENABLE_PROXY_COVER,
    CONF_ENABLE_SUN_TRACKING,
    CONF_END_ENTITY,
    CONF_END_OF_WINDOW_POS,
    CONF_END_TIME,
    CONF_ENDPOINT_USE_OPEN_CLOSE,
    CONF_ENFORCE_DELTA_AT_ENDPOINTS,
    CONF_ENTITIES,
    CONF_MY_POSITION_VALUE,
    CONF_SUNSET_USE_MY,
    CUSTOM_POSITION_SAFETY_PRIORITY,
    CUSTOM_POSITION_SLOT_NUMBERS,
    CUSTOM_POSITION_SLOTS,
    DEFAULT_CUSTOM_POSITION_PRIORITY,
    DEFAULT_ENABLE_MY_POSITION_ENTITIES,
    DEFAULT_ENABLE_POSITION_MATCHING,
    DEFAULT_ENABLE_PROXY_COVER,
    DEFAULT_ENDPOINT_USE_OPEN_CLOSE,
    DEFAULT_MAX_COVERAGE_STEPS,
    DEFAULT_MINIMIZE_MOVEMENTS,
    CONF_FOV_COMPUTE,
    CONF_FOV_LEFT,
    CONF_FOV_RIGHT,
    CONF_SUN_WINDOW_END,
    CONF_SUN_WINDOW_START,
    DEFAULT_FOV_LEFT,
    DEFAULT_FOV_RIGHT,
    DEFAULT_WINDOW_AZIMUTH,
    CONF_INTERP,
    CONF_INTERP_END,
    CONF_INTERP_START,
    CONF_INVERSE_STATE,
    CONF_CLOUD_COVERAGE_ENTITY,
    CONF_CLOUD_COVERAGE_THRESHOLD,
    CONF_IRRADIANCE_ENTITY,
    CONF_IRRADIANCE_THRESHOLD,
    CONF_IS_SUNNY_SENSOR,
    CONF_IS_SUNNY_TEMPLATE,
    CONF_LUX_ENTITY,
    CONF_LUX_THRESHOLD,
    CONF_MANUAL_IGNORE_EXTERNAL,
    CONF_MANUAL_IGNORE_INTERMEDIATE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_MANUAL_OVERRIDE_INPUT_ENTITIES,
    CONF_MANUAL_OVERRIDE_RESET,
    CONF_MANUAL_THRESHOLD,
    CONF_MAX_COVERAGE_STEPS,
    CONF_MAX_ELEVATION,
    CONF_MAX_POSITION,
    CONF_MIN_ELEVATION,
    CONF_MIN_POSITION,
    CONF_MIN_POSITION_SUN_TRACKING,
    CONF_MINIMIZE_MOVEMENTS,
    CONF_MODE,
    CONF_MOTION_MEDIA_PLAYERS,
    CONF_MOTION_SENSORS,
    CONF_MOTION_TEMPLATE,
    CONF_MOTION_TEMPLATE_MODE,
    CONF_MOTION_TIMEOUT,
    CONF_MOTION_TIMEOUT_MODE,
    DEFAULT_MOTION_TEMPLATE_MODE,
    DEFAULT_MOTION_TIMEOUT_MODE,
    DEFAULT_TEMPLATE_COMBINE_MODE,
    MOTION_TIMEOUT_MODE_HOLD,
    MOTION_TIMEOUT_MODE_RETURN,
    DEFAULT_RESYNC_ENDSTOP_MODE,
    RESYNC_ENDSTOP_MODE_CLOSE,
    RESYNC_ENDSTOP_MODE_NEAREST,
    RESYNC_ENDSTOP_MODE_OPEN,
    CONF_OPEN_CLOSE_THRESHOLD,
    CONF_OUTSIDE_THRESHOLD,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_POSITION_TOLERANCE,
    CONF_PRESENCE_ENTITY,
    CONF_PRESENCE_TEMPLATE,
    CONF_RESYNC_ENDSTOP_MODE,
    CONF_RESYNC_TRAVEL_THRESHOLD,
    CONF_RETURN_SUNSET,
    CONF_SENSOR_TYPE,
    CONF_START_ENTITY,
    CONF_START_TIME,
    CONF_SUMMER_CLOSE_BYPASS_SUN_FLOOR,
    CONF_SUNRISE_OFFSET,
    CONF_SUNRISE_TIME_ENTITY,
    CONF_SUNSET_OFFSET,
    CONF_SUNSET_POS,
    CONF_SUNSET_TIME_ENTITY,
    CONF_SUNSET_TILT,
    CONF_TEMP_ENTITY,
    CONF_TEMP_HIGH,
    CONF_TEMP_LOW,
    CONF_TILT_MODE,
    CONF_TRANSPARENT_BLIND,
    CONF_WINTER_CLOSE_INSULATION,
    CONF_WEATHER_ENTITY,
    CONF_WEATHER_IS_RAINING_SENSOR,
    CONF_WEATHER_IS_RAINING_TEMPLATE,
    CONF_WEATHER_IS_WINDY_SENSOR,
    CONF_WEATHER_IS_WINDY_TEMPLATE,
    CONF_WEATHER_OVERRIDE_MIN_MODE,
    CONF_WEATHER_OVERRIDE_POSITION,
    CONF_WEATHER_RAIN_SENSOR,
    CONF_WEATHER_RAIN_THRESHOLD,
    CONF_WEATHER_SEVERE_SENSORS,
    CONF_WEATHER_STATE,
    CONF_WEATHER_TIMEOUT,
    CONF_WEATHER_WIND_DIRECTION_SENSOR,
    CONF_WEATHER_WIND_DIRECTION_TOLERANCE,
    CONF_WEATHER_WIND_SPEED_SENSOR,
    CONF_WEATHER_WIND_SPEED_THRESHOLD,
    CONF_WEATHER_BYPASS_AUTO_CONTROL,
    CONF_WEATHER_ENABLED,
    CONF_WINDOW_DEPTH,
    CONF_WINDOW_WIDTH,
    DEFAULT_DELTA_POSITION,
    DEFAULT_DELTA_TIME,
    DEFAULT_MANUAL_OVERRIDE_DURATION,
    DEFAULT_MOTION_TIMEOUT,
    CONF_DEBUG_CATEGORIES,
    CONF_DEBUG_EVENT_BUFFER_SIZE,
    CONF_DEBUG_MODE,
    CONF_DRY_RUN,
    CONF_TRANSIT_TIMEOUT,
    DEBUG_CATEGORIES_ALL,
    DEFAULT_DEBUG_EVENT_BUFFER_SIZE,
    DEFAULT_TRANSIT_TIMEOUT_SECONDS,
    MAX_DEBUG_EVENT_BUFFER_SIZE,
    MAX_TRANSIT_TIMEOUT,
    MIN_TRANSIT_TIMEOUT,
    MODE2_OPEN_HORIZONTAL_PERCENT,
    DOMAIN,
    CoverType,
    TemplateCombineMode,
)
from .engine.sun_geometry import computed_fov_line, fov_from_reveal
from .helpers import (
    custom_position_slot_configured,
    custom_position_slot_sensors,
    mirror_legacy_slot_sensor_keys,
)

_LOGGER = logging.getLogger(__name__)

# Cover-type picker options, derived from the policy registry so a new cover
# type appears in the create flow automatically (no edit here). Order follows
# registration order (blind, awning, tilt, venetian, …). Virtual entry types
# that drive no cover (Building Profile) are filtered out via the
# ``controls_cover`` discriminator — they get their own top-level create option,
# not a cover-type dropdown entry.


_STANDALONE_SENTINEL = "__standalone__"

# Instance name used when the create flow cannot derive one from the selected
# cover's device (no cover picked, or the entity has no device).
_DEFAULT_INSTANCE_NAME = "Pergola"

_WIKI_BASE_URL = "https://github.com/B4S71/adaptive-pergola"


def _geometry_wiki_link(sensor_type: str | None) -> str:
    """Build the per-type wiki "Learn more" link from the policy's anchor.

    A fifth cover type opts in by overriding ``CoverTypePolicy.wiki_anchor()``
    on its subclass — no edit here is required.
    """
    # Avoid POLICY_REGISTRY lookup before its module-level import below.
    from .cover_types import POLICY_REGISTRY as _registry, get_policy as _get

    anchor = (
        _get(sensor_type).wiki_anchor() if sensor_type in _registry else "Cover-Types"
    )
    return f"[Learn more]({_WIKI_BASE_URL}/{anchor})"


# ---------------------------------------------------------------------------
# Step-specific schemas (replace old monolithic OPTIONS / VERTICAL_OPTIONS / etc.)
# ---------------------------------------------------------------------------

# Geometry schemas live next to each cover-type policy. Re-exported here so
# in-tree consumers (tests, sync coverage) keep their existing import paths.
from .cover_types import (  # noqa: E402
    POLICY_REGISTRY,
    LouveredRoofPolicy,
    get_policy,
)
from .cover_types._tilt_math import is_mode2 as _tilt_is_mode2  # noqa: E402
from .cover_types.louvered_roof import GEOMETRY_LOUVERED_ROOF_SCHEMA  # noqa: E402, F401
from .unit_system import (  # noqa: E402
    options_to_display,
    sensor_unit_label,
    user_input_to_canonical,
)

# Dynamic (sensor-unit / locale aware) section builders live in config_dynamic;
# re-exported here so the step handlers and the existing test imports keep their
# call sites. config_flow is a consumer of these — not their owner.
from . import config_fields  # noqa: E402
from .config_dynamic import (  # noqa: E402
    behavior_schema as _behavior_schema,
    light_cloud_schema,
    sun_tracking_schema,
    temperature_climate_schema,
    weather_override_schema,
)
from .pipeline.handlers import (  # noqa: E402
    HANDLER_PRIORITY_CONF,
    resolve_handler_priority,
)
from .priority_chain import build_priority_chain  # noqa: E402


def _handler_priority_overrides(config: dict[str, Any]) -> dict[str, int]:
    """Effective built-in handler priorities for *config* (override or default).

    Fed to :func:`build_priority_chain` so the rendered ladder and the summary
    decision-chain reflect the user's configured priorities, not just the class
    defaults.
    """
    return {
        name: resolve_handler_priority(config, name) for name in HANDLER_PRIORITY_CONF
    }


# Module-level constant for tests / imports. Identical to the legacy
# vol.Schema(...) shape — metric labels, no hass needed. ``sun_tracking_schema``
# is re-exported from ``config_dynamic`` above.
SUN_TRACKING_SCHEMA = sun_tracking_schema()

# Keys in SUN_TRACKING_SCHEMA stored in canonical metres.
_SUN_TRACKING_LENGTH_KEYS: tuple[str, ...] = (CONF_DISTANCE,)

_BINARY_ON_DOMAINS = ["binary_sensor", "input_boolean", "switch", "schedule"]
_PRESENCE_LIKE_DOMAINS = _BINARY_ON_DOMAINS + ["device_tracker", "person", "zone"]
_NUMERIC_DOMAINS = ["sensor", "input_number", "number"]


def _binary_on_selector(*, multiple: bool = False) -> selector.EntitySelector:
    """Return a single or multi-pick selector for on/off entities."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=_BINARY_ON_DOMAINS, multiple=multiple)
    )


def _presence_like_selector(*, multiple: bool = False) -> selector.EntitySelector:
    """Return a selector for presence-shaped entities (motion, occupancy, presence)."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=_PRESENCE_LIKE_DOMAINS, multiple=multiple)
    )


def _template_combine_mode_selector() -> selector.SelectSelector:
    """Return the shared OR/AND combine-mode selector (motion + daytime gate)."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[m.value for m in TemplateCombineMode],
            mode=selector.SelectSelectorMode.LIST,
            translation_key="template_combine_mode",
        )
    )


# ── Layer 2a: positions ─────────────────────────────────────────────────────
# Every percentage target value lives here and only here (#613). Handlers and
# the behavior step reference these positions; they never redefine one.
POSITION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEFAULT_HEIGHT, default=60): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(
            CONF_ENABLE_MAX_POSITION, default=False
        ): selector.BooleanSelector(),
        vol.Optional(CONF_MAX_POSITION, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=100,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(
            CONF_ENABLE_MIN_POSITION, default=False
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_ENFORCE_DELTA_AT_ENDPOINTS, default=False
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_ENDPOINT_USE_OPEN_CLOSE,
            default=DEFAULT_ENDPOINT_USE_OPEN_CLOSE,
        ): selector.BooleanSelector(),
        vol.Optional(CONF_MIN_POSITION, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=99,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(CONF_MIN_POSITION_SUN_TRACKING): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=99,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(CONF_SUNSET_POS): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(CONF_END_OF_WINDOW_POS): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(
            CONF_ENABLE_MY_POSITION_ENTITIES,
            default=DEFAULT_ENABLE_MY_POSITION_ENTITIES,
        ): selector.BooleanSelector(),
        vol.Optional(CONF_MY_POSITION_VALUE): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=99,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(CONF_SUNSET_USE_MY, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_OPEN_CLOSE_THRESHOLD, default=50): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=99,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        # CONF_INTERP (position-calibration master toggle) removed from the
        # pergola-facing form — heritage key, meaningless for a tilt-only
        # pergola (docs/CONFIG_FLOW_REWORK.md, stage 3). Stored values on old
        # entries stay readable; runtime keeps its default.
    }
)

# ── Layer 2b: behavior (timing & thresholds) ────────────────────────────────
# Non-percentage tuning: sunset/sunrise timing, position tolerance/matching, and
# inverse-state. Separated from the L2a positions so each surface is single-
# purpose (#613).
BEHAVIOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SUNSET_TIME_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        vol.Optional(CONF_SUNRISE_TIME_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        vol.Optional(CONF_SUNSET_OFFSET, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-120,
                max=120,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="minutes",
            )
        ),
        vol.Optional(CONF_SUNRISE_OFFSET, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-120,
                max=120,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="minutes",
            )
        ),
        vol.Optional(CONF_RETURN_SUNSET, default=False): selector.BooleanSelector(),
        # Daytime gate (issue #632): a binary-sensor list and/or a Jinja condition
        # template that REPLACES the astronomical sunset/sunrise boundary when set.
        # On/truthy = daytime (track); off/falsy = dark (apply sunset position).
        # Mirrors the motion gate shape (sensors + template + combine mode). Lives on
        # the behavior step beside the sunset-timing options it overrides.
        vol.Optional(CONF_DAYTIME_GATE_SENSORS, default=[]): _binary_on_selector(
            multiple=True
        ),
        vol.Optional(CONF_DAYTIME_GATE_TEMPLATE): selector.TemplateSelector(),
        vol.Optional(
            CONF_DAYTIME_GATE_TEMPLATE_MODE, default=DEFAULT_TEMPLATE_COMBINE_MODE
        ): _template_combine_mode_selector(),
        vol.Optional(CONF_POSITION_TOLERANCE, default=3): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=20,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(
            CONF_ENABLE_POSITION_MATCHING,
            default=DEFAULT_ENABLE_POSITION_MATCHING,
        ): selector.BooleanSelector(),
        # CONF_INVERSE_STATE removed from the pergola-facing form — heritage
        # key for covers reporting 0=open/100=closed; meaningless for the
        # louvered roof (docs/CONFIG_FLOW_REWORK.md, stage 3). Stored values
        # on old entries stay readable; runtime keeps its default.
    }
)

# Keys in POSITION_SCHEMA with default=vol.UNDEFINED that voluptuous omits when
# cleared by the user. Both flow handlers must call optional_entities() with this
# list before dict.update() — otherwise the prior value survives a clear
# (issue #439; same class as #323).
_POSITION_OPTIONAL_KEYS: list[str] = [
    CONF_SUNSET_POS,
    CONF_END_OF_WINDOW_POS,
    CONF_MY_POSITION_VALUE,
    CONF_MIN_POSITION_SUN_TRACKING,
]

# Same clear-handling for the L2b behavior step's entity pickers.
_BEHAVIOR_OPTIONAL_KEYS: list[str] = [
    CONF_SUNSET_TIME_ENTITY,
    CONF_SUNRISE_TIME_ENTITY,
    # Daytime gate template has no schema default → cleared = absent (issue #632).
    # The sensor list carries default=[] so it round-trips on its own (NOT here).
    CONF_DAYTIME_GATE_TEMPLATE,
]

# ── Layer 4: global motion constraints ──────────────────────────────────────
# Applied after the pipeline picks a position, regardless of which handler won:
# movement deltas, the schedule window, and the movement-minimization controls
# (relocated here from the sun-tracking step, #613).
AUTOMATION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DELTA_POSITION, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=90,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(CONF_DELTA_TIME, default=2): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=2,
                max=60,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="minutes",
            )
        ),
        # Accumulated-travel end-stop re-sync (drift compensation). Cleared =
        # disabled; both flow handlers strip the key via optional_entities().
        vol.Optional(CONF_RESYNC_TRAVEL_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=1000,
                step=5,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="%",
            )
        ),
        # Which end stop the re-sync detour drives to (0, 100, or nearest).
        vol.Optional(
            CONF_RESYNC_ENDSTOP_MODE, default=DEFAULT_RESYNC_ENDSTOP_MODE
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    RESYNC_ENDSTOP_MODE_NEAREST,
                    RESYNC_ENDSTOP_MODE_CLOSE,
                    RESYNC_ENDSTOP_MODE_OPEN,
                ],
                mode=selector.SelectSelectorMode.LIST,
                translation_key="resync_endstop_mode",
            )
        ),
        vol.Optional(
            CONF_MINIMIZE_MOVEMENTS, default=DEFAULT_MINIMIZE_MOVEMENTS
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_MAX_COVERAGE_STEPS, default=DEFAULT_MAX_COVERAGE_STEPS
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=10,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
            )
        ),
        vol.Optional(CONF_START_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        # No default: a cleared TimeSelector must leave the key absent so it can
        # be stripped (issue #492). Blank stripping is enforced in
        # async_step_automation since the suggested-values path can re-add it.
        vol.Optional(CONF_START_TIME): selector.TimeSelector(),
        vol.Optional(CONF_END_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
        ),
        vol.Optional(CONF_END_TIME): selector.TimeSelector(),
    }
)

MANUAL_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_MANUAL_OVERRIDE_DURATION, default={"hours": 2}
        ): selector.DurationSelector(),
        vol.Optional(
            CONF_MANUAL_OVERRIDE_RESET, default=False
        ): selector.BooleanSelector(),
        vol.Optional(CONF_MANUAL_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=99,
                step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="%",
            )
        ),
        vol.Optional(
            CONF_MANUAL_IGNORE_INTERMEDIATE, default=False
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_MANUAL_IGNORE_EXTERNAL, default=False
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_MANUAL_OVERRIDE_INPUT_ENTITIES, default=[]
        ): _binary_on_selector(multiple=True),
        vol.Optional(
            CONF_TRANSIT_TIMEOUT,
            default=DEFAULT_TRANSIT_TIMEOUT_SECONDS,
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=MIN_TRANSIT_TIMEOUT,
                max=MAX_TRANSIT_TIMEOUT,
                step=5,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="seconds",
            )
        ),
    }
)


def _build_custom_position_schema_dict(sensor_type: str | None = None) -> dict:
    """Compose the custom-position schema dict for the given cover type.

    Delegates to ``config_fields.custom_position_schema``; per-slot and global
    tilt fields are included for cover types whose policy advertises
    custom-position tilt extras (venetian today). A new cover type opts in by
    returning those keys from ``extra_field_keys`` — no edit here.
    """
    include_tilt = sensor_type in POLICY_REGISTRY and bool(
        get_policy(sensor_type).extra_field_keys(config_fields.SECTION_CUSTOM_POSITION)
    )
    return dict(config_fields.custom_position_schema(include_tilt=include_tilt).schema)


CUSTOM_POSITION_SCHEMA = vol.Schema(_build_custom_position_schema_dict())

# Keys in CUSTOM_POSITION_SCHEMA that have no schema default (template,
# position, priority, tilt). Voluptuous omits them from user_input when
# cleared, so both flow handlers must call optional_entities() with this list
# before dict.update() -- otherwise the prior value survives a clear (issue
# #323). The `sensors` list key carries default=[] so a cleared multi-select
# round-trips as [] on its own (it must NOT become None — None would re-enable
# the legacy single-sensor fallback).
_CUSTOM_POSITION_OPTIONAL_KEYS: list[str] = [
    slot[field]
    for slot in CUSTOM_POSITION_SLOTS.values()
    for field in ("template", "position", "priority", "tilt")
] + [CONF_DEFAULT_TILT, CONF_SUNSET_TILT]

# Built-in handler priority sliders: clearing one omits it from user_input, so
# optional_entities() nulls it and resolve_handler_priority falls back to the
# class default.
_PIPELINE_PRIORITY_OPTIONAL_KEYS: list[str] = list(config_fields.PIPELINE_PRIORITY_KEYS)

MOTION_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_MOTION_SENSORS, default=[]): _presence_like_selector(
            multiple=True
        ),
        vol.Optional(
            CONF_MOTION_MEDIA_PLAYERS, default=[]
        ): config_fields.media_player_selector(multiple=True),
        vol.Optional(CONF_MOTION_TEMPLATE): selector.TemplateSelector(),
        vol.Optional(
            CONF_MOTION_TEMPLATE_MODE, default=DEFAULT_MOTION_TEMPLATE_MODE
        ): _template_combine_mode_selector(),
        vol.Optional(
            CONF_MOTION_TIMEOUT, default=DEFAULT_MOTION_TIMEOUT
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=30,
                max=3600,
                step=30,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="seconds",
            )
        ),
        vol.Optional(
            CONF_MOTION_TIMEOUT_MODE, default=DEFAULT_MOTION_TIMEOUT_MODE
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[MOTION_TIMEOUT_MODE_RETURN, MOTION_TIMEOUT_MODE_HOLD],
                mode=selector.SelectSelectorMode.LIST,
                translation_key="motion_timeout_mode",
            )
        ),
    }
)

DEBUG_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DRY_RUN, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_DEBUG_MODE, default=False): selector.BooleanSelector(),
        vol.Optional(
            CONF_DEBUG_CATEGORIES,
            default=[],
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=DEBUG_CATEGORIES_ALL,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
                translation_key="debug_categories",
            )
        ),
        vol.Optional(
            CONF_DEBUG_EVENT_BUFFER_SIZE,
            default=DEFAULT_DEBUG_EVENT_BUFFER_SIZE,
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=10,
                max=MAX_DEBUG_EVENT_BUFFER_SIZE,
                step=10,
                mode=selector.NumberSelectorMode.SLIDER,
            )
        ),
    }
)


# Module-level constant for tests / imports. Uses empty/fallback labels; the
# retraction pickers are always part of the schema (no per-cover gate).
# ``weather_override_schema`` is re-exported from ``config_dynamic`` above.
WEATHER_OVERRIDE_SCHEMA = weather_override_schema()

# Keys in WEATHER_OVERRIDE_SCHEMA with default=vol.UNDEFINED. Voluptuous omits
# them from user_input when cleared, so both flow handlers must call
# optional_entities() with this list before dict.update() -- otherwise the prior
# value survives a clear (issue #323).
_WEATHER_OVERRIDE_OPTIONAL_KEYS: list[str] = [
    CONF_WEATHER_WIND_SPEED_SENSOR,
    CONF_WEATHER_WIND_DIRECTION_SENSOR,
    CONF_WEATHER_RAIN_SENSOR,
    CONF_WEATHER_IS_RAINING_SENSOR,
    CONF_WEATHER_IS_RAINING_TEMPLATE,
    CONF_WEATHER_IS_WINDY_SENSOR,
    CONF_WEATHER_IS_WINDY_TEMPLATE,
]


# --- Light & Cloud (works without climate mode) ---
# ``light_cloud_schema`` is re-exported from ``config_dynamic`` above.
# Module-level constant for tests / imports.
LIGHT_CLOUD_SCHEMA = light_cloud_schema()

# Keys in LIGHT_CLOUD_SCHEMA with default=vol.UNDEFINED (entity fields use
# explicit UNDEFINED; CONF_CLOUDY_POSITION uses bare vol.Optional which also
# produces default=vol.UNDEFINED). Both flow handlers must call
# optional_entities() with this list before dict.update() -- see #323 and #392.
_LIGHT_CLOUD_OPTIONAL_KEYS: list[str] = [
    CONF_CLOUDY_POSITION,
    CONF_WEATHER_ENTITY,
    CONF_IS_SUNNY_SENSOR,
    CONF_IS_SUNNY_TEMPLATE,
    CONF_LUX_ENTITY,
    CONF_IRRADIANCE_ENTITY,
    CONF_CLOUD_COVERAGE_ENTITY,
]

# --- Temperature Climate Mode ---
#
# The temperature thresholds are interpreted in the configured **sensor's**
# unit, not Home Assistant's locale unit — so the selector label reflects the
# sensor's ``unit_of_measurement`` attribute when set, falling back to HA's
# ``temperature_unit`` otherwise. Ranges are kept wide enough for either
# Celsius or Fahrenheit users to enter sensible values.

# ``temperature_climate_schema`` is re-exported from ``config_dynamic`` above.
# Module-level constant for tests / imports. Uses literal "°" label (legacy).
TEMPERATURE_CLIMATE_SCHEMA = temperature_climate_schema()

# Keys in TEMPERATURE_CLIMATE_SCHEMA with default=vol.UNDEFINED (CONF_TEMP_ENTITY
# is a bare vol.Optional). Both flow handlers must call optional_entities() with
# this list before dict.update() -- see #323.
_TEMPERATURE_CLIMATE_OPTIONAL_KEYS: list[str] = [
    CONF_TEMP_ENTITY,
    CONF_OUTSIDETEMP_ENTITY,
    CONF_PRESENCE_ENTITY,
    CONF_PRESENCE_TEMPLATE,
]

WEATHER_OPTIONS = vol.Schema(
    {
        vol.Optional(
            CONF_WEATHER_STATE, default=["sunny", "partlycloudy", "cloudy", "clear"]
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=True,
                sort=False,
                options=[
                    "clear-night",
                    "clear",
                    "cloudy",
                    "fog",
                    "hail",
                    "lightning",
                    "lightning-rainy",
                    "partlycloudy",
                    "pouring",
                    "rainy",
                    "snowy",
                    "snowy-rainy",
                    "sunny",
                    "windy",
                    "windy-variant",
                    "exceptional",
                ],
            )
        )
    }
)


def _get_azimuth_edges(data) -> int:
    """Return the total azimuth field-of-view span (fov_left + fov_right)."""
    return data[CONF_FOV_LEFT] + data[CONF_FOV_RIGHT]


_WEATHER_SAFETY_WIKI = "https://github.com/B4S71/adaptive-pergola"


def _weather_override_placeholders(
    hass: HomeAssistant | None,
    options: dict[str, Any] | None,
) -> dict[str, str]:
    """description_placeholders for the weather_override step.

    Returns ``learn_more``, ``wind_unit``, and ``rain_unit``. The unit strings
    are read from the configured sensor's ``unit_of_measurement``; when no
    sensor is configured (or its state is unavailable) the helper falls back to
    HA's locale unit so the field still carries a unit label.
    """
    opts = options or {}
    if hass is not None:
        wind_fallback = str(hass.config.units.wind_speed_unit)
        rain_fallback = str(hass.config.units.accumulated_precipitation_unit)
    else:
        wind_fallback = ""
        rain_fallback = ""
    return {
        "learn_more": _WEATHER_SAFETY_WIKI,
        "wind_unit": sensor_unit_label(
            hass, opts.get(CONF_WEATHER_WIND_SPEED_SENSOR), wind_fallback
        ),
        "rain_unit": sensor_unit_label(
            hass, opts.get(CONF_WEATHER_RAIN_SENSOR), rain_fallback
        ),
    }


def _stringify_templatable(suggested: dict) -> dict:
    """Coerce templatable threshold values to strings for the template editor.

    The ``TemplateSelector`` code editor only renders a *string* value; legacy
    entries store these thresholds as numbers, so a raw int/float collapses the
    field to nothing (issue #577). Stringify them before
    ``add_suggested_values_to_schema`` injects the suggested value. Whole-valued
    floats render without a trailing ``.0``; ``None`` and existing strings
    (including templates) are left untouched.
    """
    out = dict(suggested)
    for key in config_fields.TEMPLATABLE_KEYS:
        value = out.get(key)
        if value is None or isinstance(value, str):
            continue
        if isinstance(value, float) and value.is_integer():
            out[key] = str(int(value))
        else:
            out[key] = str(value)
    return out


def _format_duration(dur: dict | int | float | None) -> str:
    """Format a DurationSelector value (dict or legacy int minutes) as human-readable text.

    A DurationSelector stores ``{"hours": H, "minutes": M, "seconds": S}``.
    Legacy configs may store a plain number (treated as minutes).
    Zero-valued components are omitted unless all are zero (returns "0 min").
    Examples:
        {"hours": 5, "minutes": 0, "seconds": 0} -> "5 h"
        {"hours": 2, "minutes": 15, "seconds": 0} -> "2 h 15 min"
        {"hours": 0, "minutes": 30, "seconds": 0} -> "30 min"
        {"hours": 0, "minutes": 0, "seconds": 45} -> "45 s"
        120 (legacy int)                           -> "120 min"

    """
    if dur is None:
        return ""
    if isinstance(dur, int | float):
        return f"{int(dur)} min"
    h = int(dur.get("hours", 0) or 0)
    m = int(dur.get("minutes", 0) or 0)
    s = int(dur.get("seconds", 0) or 0)
    parts = []
    if h:
        parts.append(f"{h} h")
    if m:
        parts.append(f"{m} min")
    if s:
        parts.append(f"{s} s")
    return " ".join(parts) if parts else "0 min"


def _check_cover_capabilities(
    config: dict,
    sensor_type: str | None,
    hass: HomeAssistant | None,
) -> tuple[dict[str, dict[str, bool] | None], list[str]]:
    """Inspect bound cover entities and return capabilities + warning lines.

    Returns:
        cap_map:  entity_id → feature dict (None if entity unavailable)
        warnings: list of ⚠️ strings — per-entity and cross-entity issues

    """
    entities: list[str] = config.get(CONF_ENTITIES) or []
    if hass is None or not entities:
        return {}, []

    from .helpers import check_cover_features

    cap_map: dict[str, dict[str, bool] | None] = {}
    warnings: list[str] = []

    from .cover_types.base import CAP_HAS_SET_POSITION, caps_get

    for eid in entities:
        caps = check_cover_features(hass, eid)
        cap_map[eid] = caps
        if caps is None:
            warnings.append(f"⚠️ {eid}: not ready (unavailable)")
        else:
            if not caps_get(caps, CAP_HAS_SET_POSITION):
                warnings.append(
                    f"⚠️ {eid} is open/close-only — will be driven via "
                    "threshold compare, not set_position."
                )
            state = hass.states.get(eid)
            if state and state.attributes.get("assumed_state"):
                warnings.append(
                    f"⚠️ {eid} has assumed_state — real position cannot be "
                    "read back, which may affect position verification and delta-bypass."
                )

    known: dict[str, dict[str, bool]] = {
        eid: caps for eid, caps in cap_map.items() if caps is not None
    }

    if known:
        has_pos = {
            eid for eid, caps in known.items() if caps_get(caps, CAP_HAS_SET_POSITION)
        }
        no_pos = {
            eid
            for eid, caps in known.items()
            if not caps_get(caps, CAP_HAS_SET_POSITION)
        }

        if has_pos and no_pos:
            warnings.append(
                "⚠️ Mixed capabilities: some covers support set_position, "
                "others are open/close-only — they will be driven differently."
            )

        if sensor_type is not None:
            warnings.extend(get_policy(sensor_type).cover_capability_warnings(known))

        min_pos_val = config.get(CONF_MIN_POSITION)
        max_pos_val = config.get(CONF_MAX_POSITION)
        enable_min_val = config.get(CONF_ENABLE_MIN_POSITION)
        enable_max_val = config.get(CONF_ENABLE_MAX_POSITION)
        limits_in_use = (
            (min_pos_val is not None and min_pos_val != 0)
            or (max_pos_val is not None and max_pos_val != 100)
            or enable_min_val
            or enable_max_val
        )
        oc_only = [eid for eid in no_pos if eid in known]
        if limits_in_use and oc_only:
            oc_str = ", ".join(oc_only)
            warnings.append(
                f"⚠️ Position limits are configured but {oc_str} "
                "is open/close-only — limits will be ignored on that cover."
            )

    return cap_map, warnings


def _build_cover_capabilities_text(
    config: dict,
    sensor_type: str | None,
    hass: HomeAssistant | None = None,
) -> str:
    """Build a Cover Capabilities block for the Debug & Diagnostics screen.

    Returns a markdown string (possibly empty) describing each bound cover's
    detected features plus any cross-entity consistency warnings.
    """
    entities: list[str] = config.get(CONF_ENTITIES) or []
    if hass is None or not entities:
        return ""

    cap_map, warnings = _check_cover_capabilities(config, sensor_type, hass)

    from .cover_types.base import (
        CAP_HAS_CLOSE,
        CAP_HAS_OPEN,
        CAP_HAS_SET_POSITION,
        CAP_HAS_SET_TILT_POSITION,
        CAP_HAS_STOP,
        caps_get,
    )

    cap_label_map = {
        CAP_HAS_SET_POSITION: "set position",
        CAP_HAS_SET_TILT_POSITION: "set tilt",
        CAP_HAS_OPEN: "open",
        CAP_HAS_CLOSE: "close",
        CAP_HAS_STOP: "stop",
    }

    lines: list[str] = ["**Cover Capabilities**"]
    for eid in entities:
        caps = cap_map.get(eid)
        if caps is None:
            lines.append(f"{eid}: not ready (unavailable)")
        else:
            cap_list = ", ".join(
                label for key, label in cap_label_map.items() if caps_get(caps, key)
            )
            lines.append(f"{eid}: {cap_list or 'none detected'}")

    if warnings:
        lines.extend(warnings)

    return "\n".join(lines)


async def _compute_todays_sun_times(hass: HomeAssistant, config: dict) -> dict | None:
    """Compute today's raw/effective sunrise/sunset + solar-control window.

    Runs the pandas/astral-heavy work in an executor. Returns ``None`` on any
    failure so the summary renders gracefully when location/astral data is
    unavailable. All returned datetimes are naive local (HA-configured TZ).
    """
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    from .config_types import CoverConfig
    from .engine.sun_geometry import SunGeometry
    from .state.sun_provider import SunProvider

    def _to_local(value):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt_util.UTC)
        return dt_util.as_local(value).replace(tzinfo=None)

    def _compute() -> dict | None:
        try:
            sun_data = SunProvider(hass).create_sun_data(hass.config.time_zone)
            sunrise_raw_utc = sun_data.sunrise()
            sunset_raw_utc = sun_data.sunset()

            cfg = CoverConfig.from_options(config)
            geometry = SunGeometry(0.0, 0.0, sun_data, cfg, _LOGGER)
            solar_start_utc, solar_end_utc = geometry.solar_times()

            sunrise_local = _to_local(sunrise_raw_utc)
            sunset_local = _to_local(sunset_raw_utc)
            sunrise_eff = (
                sunrise_local + timedelta(minutes=int(cfg.sunrise_off))
                if sunrise_local is not None
                else None
            )
            sunset_eff = (
                sunset_local + timedelta(minutes=int(cfg.sunset_off))
                if sunset_local is not None
                else None
            )

            return {
                "sunrise_raw": sunrise_local,
                "sunset_raw": sunset_local,
                "sunrise_eff": sunrise_eff,
                "sunset_eff": sunset_eff,
                "solar_start": _to_local(solar_start_utc),
                "solar_end": _to_local(solar_end_utc),
            }
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to compute today's sun times", exc_info=True)
            return None

    return await hass.async_add_executor_job(_compute)


def _cover_type_label(
    sensor_type: str | None, labels: dict[str, str] | None = None
) -> str:
    """Return the human-readable label for a cover type, falling back to 'Cover'.

    ``labels`` is the translated ``cover_types.*`` bundle threaded from
    ``_build_config_summary``; ``None`` (entry titles, no flow context) keeps
    the policy's English default.
    """
    if sensor_type is not None and sensor_type in POLICY_REGISTRY:
        return get_policy(sensor_type).display_label(labels)
    return "Cover"


# ---------------------------------------------------------------------------
# Configuration-summary i18n (issue #258)
# ---------------------------------------------------------------------------
#
# Every user-facing phrase rendered by ``_build_config_summary`` lives here as a
# dotted-key → English template. This dict is BOTH:
#   * the single source of truth for the English output (so the 188 regression
#     tests in test_config_flow_summary.py stay byte-identical), AND
#   * the per-key fallback used when a translated key is missing/dropped.
#
# ``summary_i18n/en.json`` mirrors these exact keys/values as a nested tree. The
# flattened dotted keys (``rules`` → ``force`` → ``rules.force``) match the
# dotted keys here verbatim — see ``_load_summary_labels``. This data lives in a
# dedicated ``summary_i18n/`` bundle rather than under ``translations/`` because
# hassfest validates ``translations/en.json`` against HA's strict schema, which
# forbids a custom ``config_summary`` top-level category.
#
# Each value is a Python ``str.format`` template. Literal ``{`` / ``}`` that are
# NOT format fields (the cloud "weather in {set}" notation) are escaped as
# ``{{`` / ``}}``. Priority badges are NOT baked in — ``_badge(N)`` is appended
# AFTER ``.format()`` so handler-priority integers stay imported, never
# duplicated into translation strings.
#
# DEFERRED (stay English / policy-owned, translated in a follow-up):
#   * cover-type label (``policy.display_label()``)
#   * physical-dimension block (``policy.summary_geometry_lines()``)
#   * decision-priority short labels (Force/Weather/...) and the ✅/❌/→ marks
#   * cover-capability warning lines built in ``_check_cover_capabilities``
_SUMMARY_LABELS_EN: dict[str, str] = {
    # --- banners / section headers ---
    "banner.dry_run": (
        "⚠️ **Dry-run mode is ON** — positions are computed and logged, but "
        "no commands are sent and covers will NOT move."
    ),
    "headers.your_cover": "**Your Cover**",
    "cover.type_with_entities": "{type_label} controlling {entity_str}",
    "headers.cover_warnings": "**Cover Warnings**",
    "headers.how_it_decides": "**How It Decides** (first matching rule wins)",
    # --- singular/plural words ---
    "words.sensor_singular": "sensor",
    "words.sensor_plural": "sensors",
    "words.source_singular": "source",
    "words.source_plural": "sources",
    # --- shared fragments ---
    "fragments.as_minimum": " (as minimum)",
    "fragments.safety": " 🔒 safety: acts outside the time window too",
    "fragments.template_value": "[template]",
    # --- Weather safety (90) ---
    "rules.weather": (
        "🌧️ Weather safety: if {wx_condition} → covers retract to "
        "{weather_pos}%{weather_min}{delay}{bypass}"
    ),
    "weather.wind": "wind > {thresh}",
    "weather.wind_dir": " from window ±{tol}°",
    "weather.rain": "rain > {thresh}",
    "weather.is_raining": "is-raining",
    "weather.is_windy": "is-windy",
    "weather.severe": "{count} severe weather sensor(s)",
    "weather.condition_default": "weather condition",
    "weather.condition_join": " or ",
    "weather.delay": " (waits {delay}s after clearing)",
    "weather.bypass": " ⚠️ halts all automation while triggered",
    "weather.disabled_warning": (
        "🌧️ Weather safety: ⚠️ sensors configured but the feature is "
        "turned OFF — weather overrides are ignored"
    ),
    # --- Manual override (80) ---
    "rules.manual": (
        "✋ Manual override: pauses automatic control when you move the cover{detail}"
    ),
    "manual.pauses_for": "pauses for {duration}",
    "manual.threshold": "threshold {threshold}%",
    "manual.resets_on_move": "resets on next move",
    "manual.ignore_intermediate": "ignores intermediate positions",
    "manual.ignore_external": "ACP-only (ignores external moves)",
    "manual.input_entities": "input-sensor override: {count} sensor(s)",
    "manual.transit_timeout": "transit timeout: {seconds}s",
    # --- Custom positions ---
    "rules.custom_tilt_only": (
        "🎯 Custom #{slot}: if {trigger} is on → tilt only "
        "(slat fixed at {slat}%; position driven by sun tracking)"
    ),
    "rules.custom": (
        "🎯 Custom #{slot}: if {trigger} is on → {target}{cp_min}{tilt_note}"
        " — bypasses delta gates and auto-control{safety}"
    ),
    "custom.tilt_note": ", tilt {tilt}%",
    "custom.trigger_sensors": "any of {n} sensors",
    "custom.trigger_template": "template",
    "custom.trigger_join": " or ",
    "warnings.custom_tilt_only_conflict": (
        "⚠️ Custom #{slot}: tilt only is on — "
        "Use as minimum / Use My position are ignored for this slot."
    ),
    "warnings.custom_and_no_sensors": (
        "⚠️ Custom #{slot}: combine mode AND is set but no trigger sensors are "
        "configured — the template alone activates the slot."
    ),
    "warnings.custom_safety_bypass": (
        "⚠️ Custom #{slot} is at safety priority ({safety}) — it bypasses the "
        "automatic-control toggle, manual override, and the start/end time "
        "window, so it can move the cover even when automatic control is OFF "
        "and outside your schedule. Lower its priority below {safety} to make "
        "it respect those gates."
    ),
    # --- Motion (75) ---
    "rules.motion": (
        "🚶 Motion-based: if no occupancy for {motion_timeout}s ({sources}) → {action}"
    ),
    "motion.template_source": "occupancy template",
    "motion.action_hold": (
        "covers hold current position (return to default when sun leaves FOV)"
    ),
    "motion.action_return": "covers return to default ({default_pos}%)",
    "warnings.motion_hold_no_sensors": (
        "⚠️ hold_position mode is set but no motion sensors or media "
        "players are configured — the setting has no effect until a "
        "motion source is added"
    ),
    # --- Cloud suppression (60) ---
    "rules.cloud": ("☁️ Cloud suppression: skips sun tracking{cloud} → {fallback}"),
    "cloud.is_sunny": "is_sunny={value}",
    "cloud.lux": "lux < {thresh} lx",
    "cloud.lux_no_thresh": "lux ({entity})",
    "cloud.irradiance": "irradiance < {thresh} W/m²",
    "cloud.irradiance_no_thresh": "irradiance ({entity})",
    "cloud.coverage": "cloud > {thresh}%",
    "cloud.coverage_no_thresh": "cloud ({entity})",
    "cloud.weather_in": "weather in {{{states}}}",
    "cloud.when": " when {parts}",
    "cloud.fallback_cloudy": "cloudy position {pos}%",
    "cloud.fallback_default": "default ({default_pos}%)",
    "info.light_sensors_off": (
        "📊 Light sensors configured ({names}) but cloud suppression is off."
    ),
    "info.light_lux": "lux",
    "info.light_irradiance": "irradiance",
    "info.light_cloud_coverage": "cloud coverage",
    "warnings.cloudy_pos_ignored": (
        "⚠️ Cloudy position ({pos}%) configured but cloud suppression is "
        "disabled — value will be ignored."
    ),
    # --- Climate (50) ---
    "rules.climate": ("🌡️ Climate mode: adjusts strategy for heating/cooling{detail}"),
    "climate.comfort_range": "comfort range {lo}–{hi}°C",
    "climate.using": "using {entity}",
    "climate.outside_thresh": "outside: {entity} > {thresh}°C",
    "climate.outside": "outside: {entity}",
    "climate.weather": "weather: {entity}",
    "climate.presence": "presence: {entity}",
    "climate.transparent": "transparent blind",
    "climate.winter_close": "closes fully in winter for insulation",
    "climate.summer_full_close": "closes fully in summer heat",
    # --- Glare (45) ---
    "rules.glare": (
        "🔆 Glare zones: lowers blind further to protect floor areas from glare{detail}"
    ),
    "glare.zones": "zones: {names}",
    "glare.window": "{width:.2f}m window",
    "glare.z_height": "Z height: {values}",
    "glare.z_value": "{z:.2f}m",
    # --- Solar (40) ---
    "rules.solar": (
        "☀️ Tracks the sun{sun_desc} and calculates position to block "
        "direct sunlight{today}"
    ),
    "rules.solar_disabled": (
        "☀️ Sun tracking disabled — covers hold position; climate, manual "
        "override, custom positions, and other overrides remain active"
    ),
    "solar.azimuth": "azimuth {azimuth}°",
    "solar.fov": "±{fov_l}°/{fov_r}° field of view",
    "solar.elev_above": "above {elev}°",
    "solar.elev_below": "below {elev}°",
    "solar.elevation": "elevation {parts}",
    "solar.elev_join": " and ",
    "solar.today_window": (" (today: sun in window {start} → {end})"),
    "solar.today_no_window": " (today: sun does not enter window)",
    "solar.minimize_one_step": "moves straight to full coverage and holds (1 step)",
    "solar.minimize_steps": "reaches full coverage in up to {steps} steps",
    "solar.minimize": (
        "{indent}🪟 Minimize movements — {detail}, rounding toward more "
        "coverage to reduce motor movements."
    ),
    # --- Timing window ---
    "timing.from_entity": "from {entity}",
    "timing.from_time": "from {time}",
    "timing.until_entity": "until {entity}",
    "timing.until_time": "until {time}",
    "timing.active_daylight": "Active during daylight",
    "timing.line": "{indent}🕒 {timing}.",
    "timing.ann_via": "via {entity}",
    "timing.ann_today": "today ~{time}",
    "timing.offset_plus": "+{minutes} min",
    "timing.offset_minus": "{minutes} min",
    "timing.after_end_to_default": "{indent}🔚 After end time → {default_pos}%.",
    "timing.after_sunset": "{indent}🌅 After sunset{ann} → {target}.",
    "timing.after_label": "{indent}🌅 After {label}{ann} → {target}.",
    "timing.label_end_or_sunset": "end time/sunset",
    "timing.label_sunset": "sunset",
    "timing.after_sunrise": (
        "{indent}🌄 After sunrise{ann} → {default_pos}% (tracking resumes)."
    ),
    "timing.return_sunset": "{indent}🔚 Return to sunset position at end time: on",
    "timing.end_of_window": (
        "{indent}🔚 End-of-window position → {target} from end time until sunset "
        "(then the sunset position applies, if set)."
    ),
    "timing.end_of_window_needs_return": (
        '{indent}⚠️ End-of-window position is set but "Move covers when end time '
        'is reached" is OFF — it will not be applied. Turn that toggle on.'
    ),
    # --- Daytime gate (issue #632) ---
    "timing.gate_sensors": "{indent}🌗 Daytime gate: {sensors} decide day vs dark.",
    "timing.gate_template": "{indent}🌗 Daytime gate: a template decides day vs dark.",
    "timing.gate_both": (
        "{indent}🌗 Daytime gate: {sensors} and a template ({mode}) decide day vs dark."
    ),
    "timing.gate_explainer": (
        "{indent}When the gate reads daytime ACP sun-tracks; when it reads dark "
        "ACP applies the sunset position. The gate replaces the astronomical "
        "sunset/sunrise boundary; start/end times still clamp the window."
    ),
    "timing.gate_offset_ignored": (
        "{indent}⚠️ Sunset/Sunrise Offset is ignored while a daytime gate is set "
        "— the gate, not the clock, decides the boundary."
    ),
    # --- Blind spot ---
    "blind_spot.line": (
        "🟥 Blind spot: ignores sun at {bs} inward from FOV left (e.g. tree "
        "or roof overhang)."
    ),
    "blind_spot.range": "{left}°–{right}°",
    "blind_spot.elevation": "up to {elev}° elevation",
    "blind_spot.elevation_above": "above {elev}° elevation",
    # --- Default fallback (0) ---
    "rules.default": "🌙 Default (no rule matches) → {default_pos}%",
    "default.tilt": ("  ↳ Default tilt: {tilt}% (explicit; overrides solar-computed)"),
    "default.sunset_tilt": (
        "  ↳ Sunset tilt: {tilt}% (explicit; overrides solar-computed)"
    ),
    # --- Position limits ---
    "headers.position_limits": "**Position Limits**",
    "limits.range": "Range: {lo}–{hi}{qualifier}",
    "limits.qualifier_both": " (during sun tracking only)",
    "limits.qualifier_min": " (min during sun tracking only)",
    "limits.qualifier_max": " (max during sun tracking only)",
    "limits.default": "Default: {pos}%",
    "limits.min_change": "Min change: {delta}%",
    "limits.min_interval": "Min interval: {delta} min",
    "limits.position_tolerance": "Position tolerance: {tol}%",
    "limits.position_matching_on": "📍 Position matching on (re-sends until the cover reaches target)",
    "limits.position_matching_off": "📍 Position matching off (commands once; a settle past tolerance becomes a manual override)",
    "limits.inverse_state": "Inverse state",
    "limits.open_close_threshold": "Open/close threshold: {thresh}%",
    "limits.calibration": "Calibration {lo}→{hi}",
    "limits.calibration_on": "Position calibration on",
    "limits.sun_tracking_min": "Sun-tracking min: {pos}%",
    "limits.separator": " · ",
    "warnings.sun_track_min_below_floor": (
        "⚠️ Sun-tracking min {sun_min}% < min position {min_pos}% — "
        "always-on floor dominates; sun-tracking floor will be raised to "
        "{min_pos}%."
    ),
    "warnings.mode2_min_position": (
        "⚠️ Tilt MODE2 + min position {min_pos}% — in MODE2 the open "
        "(horizontal) slat angle IS 50%, so any min position ≥ 50 "
        "collapses every climate/glare-control decision to the floor "
        "and the cover stops blocking heat."
    ),
    # --- My preset / Somfy ---
    "my.entities_enabled": "🎛️ My-preset entities: enabled",
    "my.entities_disabled": "🎛️ My-preset entities: disabled",
    "my.somfy_preset": "🎛️ Somfy My preset: {pos}% (used where enabled above)",
    "my.label_my_set": "My ({pos}%)",
    "my.label_my_unset": "My (not set → {pct}%)",
    "my.label_plain": "{pct}%",
    "warnings.somfy_my_unset": (
        "⚠️ Somfy My preset is enabled for one or more targets but "
        "My Preset Value is not set — falls back to configured %."
    ),
    # --- Proxy cover ---
    "headers.proxy_enabled": "**Proxy cover**: enabled",
    "headers.proxy_disabled": "**Proxy cover**: disabled",
    "warnings.proxy_no_min": (
        "⚠️ Proxy cover is enabled but no custom-position slot has "
        "Use as minimum on — the managed cover will not clamp."
    ),
    # --- Decision priority chain ---
    "headers.decision_priority": (
        "**Decision Priority** (highest wins, ✅ active ❌ not configured)"
    ),
}


_SUMMARY_I18N_DIR = Path(__file__).parent / "summary_i18n"


def _flatten_summary_labels(node: object, prefix: str = "") -> dict[str, str]:
    """Flatten a nested label tree to dotted keys (``rules.force`` → template)."""
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(
                _flatten_summary_labels(value, f"{prefix}.{key}" if prefix else key)
            )
    elif isinstance(node, str):
        out[prefix] = node
    return out


@cache
def _summary_label_overlay(language: str) -> tuple[tuple[str, str], ...]:
    """Return the flattened ``summary_i18n/<language>.json`` bundle.

    Cached (the bundles are shipped, read-only) and returned as a tuple of items
    so the cached value cannot be mutated by callers. ``en`` and any missing or
    malformed file yield an empty overlay — the English defaults then apply.
    """
    if not language or language == "en":
        return ()
    path = _SUMMARY_I18N_DIR / f"{language}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    return tuple(_flatten_summary_labels(data).items())


def _load_summary_labels_sync(language: str) -> dict[str, str]:
    """Build the config-summary labels for ``language``.

    English defaults overlaid with the translated bundle. Pure/synchronous —
    safe to unit-test directly.
    """
    return {**_SUMMARY_LABELS_EN, **dict(_summary_label_overlay(language))}


async def _load_summary_labels(hass: HomeAssistant, language: str) -> dict[str, str]:
    """Load the translated config-summary labels for ``language``.

    The labels live in the integration's ``summary_i18n/`` bundle (a custom
    ``config_summary`` category cannot live under ``translations/`` — hassfest
    rejects it). This overlays the language bundle onto the English defaults so
    any missing key falls back to English. ``language`` is the per-user flow
    language (``self.context.get("language", "en")``) — never the system
    language. File I/O is offloaded to the executor.

    Both ``ConfigFlow.async_step_summary`` and ``OptionsFlow.async_step_summary``
    call this single helper (no duplication).
    """
    return await hass.async_add_executor_job(_load_summary_labels_sync, language)


def _build_config_summary(  # noqa: C901, PLR0912, PLR0915
    config: dict,
    sensor_type: str | None,
    hass: HomeAssistant | None = None,
    sun_times: dict | None = None,
    labels: dict[str, str] | None = None,
) -> str:
    """Build a narrative summary of the current configuration.

    Produces four sections:
      1. Your Cover  — what is controlled and physical setup
      2. How It Decides — full decision chain: each rule's trigger, target, and
         today's sun times inline; priority badge [N] at end of each rule
      3. Position Limits — compact one-liner for range/default/delta/flags
      4. Decision Priority — compact chain showing active/inactive handlers

    ``labels`` maps the summary's dotted keys to translated templates. When
    ``None`` (unit tests, no hass) the English defaults in ``_SUMMARY_LABELS_EN``
    are used, so the output is byte-identical to the pre-i18n strings.
    """
    L = labels or _SUMMARY_LABELS_EN
    _ph = L["fragments.template_value"]
    # ---- Gather all values up front ----------------------------------------
    # ``L`` here is the FULL flow bundle (``_SUMMARY_LABELS_EN`` keys + the
    # policy-owned ``cover_types.*`` / ``geometry.*`` keys when a translated
    # bundle is loaded). The policies layer it over their own English base
    # (``COVER_TYPE_LABELS_EN`` / ``GEOMETRY_LABELS_EN``), so passing ``L`` —
    # even the policy-key-less ``_SUMMARY_LABELS_EN`` default — still yields
    # English for the policy lines while translating everything present.
    type_label = _cover_type_label(sensor_type, L)

    entities: list[str] = config.get(CONF_ENTITIES) or []
    default_pos = config.get(CONF_DEFAULT_HEIGHT, 0)
    weather_pos = config.get(CONF_WEATHER_OVERRIDE_POSITION, 0)
    motion_timeout = config.get(CONF_MOTION_TIMEOUT, 300)
    manual_dur = config.get(CONF_MANUAL_OVERRIDE_DURATION)

    from .helpers import motion_entities
    from .templates import is_template_string

    has_weather = any(
        [
            config.get(CONF_WEATHER_WIND_SPEED_SENSOR),
            config.get(CONF_WEATHER_RAIN_SENSOR),
            config.get(CONF_WEATHER_IS_RAINING_SENSOR),
            config.get(CONF_WEATHER_IS_WINDY_SENSOR),
            is_template_string(config.get(CONF_WEATHER_IS_RAINING_TEMPLATE)),
            is_template_string(config.get(CONF_WEATHER_IS_WINDY_TEMPLATE)),
            bool(config.get(CONF_WEATHER_SEVERE_SENSORS)),
        ]
    )

    def _thresh_display(value: Any, *, placeholder: str) -> str:
        return placeholder if is_template_string(str(value)) else str(value)

    _motion_sources = motion_entities(config)
    _has_motion_template = is_template_string(config.get(CONF_MOTION_TEMPLATE))
    has_motion = bool(_motion_sources) or _has_motion_template
    # Build per-slot custom position data:
    # list of
    #   (slot, trigger_desc, position, priority, use_my, tilt, tilt_only,
    #    has_trigger)
    _custom_slots: list[tuple[int, str, int, int, bool, int | None, bool, bool]] = []
    _and_no_sensor_slots: list[int] = []
    for _i, _slot_keys in CUSTOM_POSITION_SLOTS.items():
        if not custom_position_slot_configured(config, _slot_keys):
            continue
        _sensors = custom_position_slot_sensors(config, _slot_keys)
        _has_tpl = is_template_string(config.get(_slot_keys["template"]))
        # Footgun: AND mode with no sensors degenerates to template-only.
        if (
            _has_tpl
            and not _sensors
            and config.get(_slot_keys["template_mode"]) == "and"
        ):
            _and_no_sensor_slots.append(_i)
        _trigger_parts: list[str] = []
        if len(_sensors) == 1:
            _trigger_parts.append(_sensors[0])
        elif _sensors:
            _trigger_parts.append(L["custom.trigger_sensors"].format(n=len(_sensors)))
        if _has_tpl:
            _trigger_parts.append(L["custom.trigger_template"])
        _trigger = L["custom.trigger_join"].join(_trigger_parts)
        _pos = config.get(_slot_keys["position"])
        _pri = int(
            config.get(_slot_keys["priority"]) or DEFAULT_CUSTOM_POSITION_PRIORITY
        )
        _use_my = bool(config.get(_slot_keys["use_my"]))
        _slot_tilt = config.get(_slot_keys["tilt"])
        _tilt_only = bool(config.get(_slot_keys["tilt_only"]))
        _has_trigger = bool(_sensors) or _has_tpl
        _custom_slots.append(
            (
                _i,
                _trigger,
                int(_pos),
                _pri,
                _use_my,
                _slot_tilt,
                _tilt_only,
                _has_trigger,
            )
        )
    has_custom_position = bool(_custom_slots)
    my_pos = config.get(CONF_MY_POSITION_VALUE)  # None = not configured
    has_cloud = bool(config.get(CONF_CLOUD_SUPPRESSION))
    has_climate = bool(config.get(CONF_CLIMATE_MODE))
    sun_tracking_enabled = config.get(CONF_ENABLE_SUN_TRACKING, True)
    summary_policy = (
        get_policy(sensor_type)
        if sensor_type is not None and sensor_type in POLICY_REGISTRY
        else LouveredRoofPolicy()
    )
    has_glare = summary_policy.supports_glare_zones and bool(
        config.get(CONF_ENABLE_GLARE_ZONES)
    )

    def _pos_label(raw_pct: int, use_my: bool) -> str:
        """Render a target as 'My (N%)' when the My preset flag is active."""
        if use_my and my_pos is not None:
            return L["my.label_my_set"].format(pos=my_pos)
        if use_my:
            return L["my.label_my_unset"].format(pct=raw_pct)
        return L["my.label_plain"].format(pct=raw_pct)

    def _badge(priority: int) -> str:
        """Render a priority badge suffix: two nbsp + [N]."""
        return f"\u00a0\u00a0[{priority}]"

    # Effective built-in handler priorities (configured overrides or class
    # defaults). Each rule's badge reads its own handler here so a re-ordered
    # chain shows the user's real numbers, not the hardcoded defaults.
    _prio = _handler_priority_overrides(config)

    def _fmt_sun_dt(value) -> str | None:
        """Format a sun-times datetime as HH:MM; None passes through."""
        return value.strftime("%H:%M") if value is not None else None

    def _offset_str(minutes: int) -> str:
        """Format a minutes offset as (+N min) / (-N min); 0 → empty."""
        if minutes > 0:
            return L["timing.offset_plus"].format(minutes=minutes)
        if minutes < 0:
            return L["timing.offset_minus"].format(minutes=minutes)
        return ""

    _solar_start = sun_times.get("solar_start") if sun_times else None
    _solar_end = sun_times.get("solar_end") if sun_times else None
    _sunset_eff = sun_times.get("sunset_eff") if sun_times else None
    _sunrise_eff = sun_times.get("sunrise_eff") if sun_times else None

    lines: list[str] = []

    # Dry-run banner — surfaced first because it overrides everything below: when
    # on, the full decision chain is still computed and logged but no commands are
    # sent, so covers never move. Without this the summary reads as if it drives
    # covers regardless of the dry-run toggle on the Debug screen.
    if config.get(CONF_DRY_RUN):
        lines.append(L["banner.dry_run"])
        lines.append("")

    # =========================================================================
    # Section 1: Your Cover
    # =========================================================================
    lines.append(L["headers.your_cover"])

    # Type + entities
    if entities:
        entity_str = ", ".join(entities)
        lines.append(
            L["cover.type_with_entities"].format(
                type_label=type_label, entity_str=entity_str
            )
        )
    else:
        lines.append(type_label)

    # Physical dimensions in plain English. The render mode is per-cover-type;
    # each ``CoverTypePolicy.summary_geometry_lines`` owns its block. Legacy
    # configs without ``sensor_type`` fall back to the vertical-blind layout
    # via ``summary_policy`` chosen at the top of this function. ``L`` threads
    # the translated ``geometry.*`` bundle (or the policy-key-less EN default,
    # which still renders English over the policy's own base layer).
    lines.extend(summary_policy.summary_geometry_lines(config, L))

    # =========================================================================
    # Section 1c: Cover Capability Warnings
    # =========================================================================
    _, cap_warnings = _check_cover_capabilities(config, sensor_type, hass)
    if cap_warnings:
        lines.append("")
        lines.append(L["headers.cover_warnings"])
        lines.extend(cap_warnings)

    # =========================================================================
    # Section 2: How It Decides
    # =========================================================================
    lines.append("")
    lines.append(L["headers.how_it_decides"])

    # Weather safety override (90). The master toggle (issue #719) gates the
    # whole feature. A summary config missing the key is treated as enabled
    # (back-compat — the warning must only fire on an explicit opt-out); a new
    # cover that leaves the toggle off after configuring sensors gets the
    # OFF-with-sensors footgun warning instead of the normal rule line.
    weather_enabled = config.get(CONF_WEATHER_ENABLED, True)
    if has_weather and not weather_enabled:
        lines.append(L["weather.disabled_warning"])
    elif has_weather:
        wx_parts = []
        wind_sensor = config.get(CONF_WEATHER_WIND_SPEED_SENSOR)
        wind_thresh = config.get(CONF_WEATHER_WIND_SPEED_THRESHOLD)
        wind_dir_sensor = config.get(CONF_WEATHER_WIND_DIRECTION_SENSOR)
        wind_dir_tol = config.get(CONF_WEATHER_WIND_DIRECTION_TOLERANCE)
        rain_sensor = config.get(CONF_WEATHER_RAIN_SENSOR)
        rain_thresh = config.get(CONF_WEATHER_RAIN_THRESHOLD)
        is_rain = config.get(CONF_WEATHER_IS_RAINING_SENSOR) or is_template_string(
            config.get(CONF_WEATHER_IS_RAINING_TEMPLATE)
        )
        is_wind = config.get(CONF_WEATHER_IS_WINDY_SENSOR) or is_template_string(
            config.get(CONF_WEATHER_IS_WINDY_TEMPLATE)
        )
        severe = config.get(CONF_WEATHER_SEVERE_SENSORS) or []
        if wind_sensor and wind_thresh is not None:
            wind_part = L["weather.wind"].format(
                thresh=_thresh_display(wind_thresh, placeholder=_ph)
            )
            if wind_dir_sensor and wind_dir_tol is not None:
                wind_part += L["weather.wind_dir"].format(
                    tol=_thresh_display(wind_dir_tol, placeholder=_ph)
                )
            wx_parts.append(wind_part)
        if rain_sensor and rain_thresh is not None:
            wx_parts.append(
                L["weather.rain"].format(
                    thresh=_thresh_display(rain_thresh, placeholder=_ph)
                )
            )
        if is_rain:
            wx_parts.append(L["weather.is_raining"])
        if is_wind:
            wx_parts.append(L["weather.is_windy"])
        if severe:
            wx_parts.append(L["weather.severe"].format(count=len(severe)))
        wx_condition = (
            L["weather.condition_join"].join(wx_parts)
            if wx_parts
            else L["weather.condition_default"]
        )
        wx_delay = config.get(CONF_WEATHER_TIMEOUT)
        delay_str = L["weather.delay"].format(delay=wx_delay) if wx_delay else ""
        weather_min_str = (
            L["fragments.as_minimum"]
            if config.get(CONF_WEATHER_OVERRIDE_MIN_MODE)
            else ""
        )
        bypass_str = (
            L["weather.bypass"] if config.get(CONF_WEATHER_BYPASS_AUTO_CONTROL) else ""
        )
        lines.append(
            L["rules.weather"].format(
                wx_condition=wx_condition,
                weather_pos=weather_pos,
                weather_min=weather_min_str,
                delay=delay_str,
                bypass=bypass_str,
            )
            + _badge(_prio["weather"])
        )

    # Manual override (80)
    mo_parts = []
    if manual_dur is not None:
        mo_parts.append(
            L["manual.pauses_for"].format(duration=_format_duration(manual_dur))
        )
    threshold = config.get(CONF_MANUAL_THRESHOLD)
    if threshold is not None:
        mo_parts.append(L["manual.threshold"].format(threshold=threshold))
    if config.get(CONF_MANUAL_OVERRIDE_RESET):
        mo_parts.append(L["manual.resets_on_move"])
    if config.get(CONF_MANUAL_IGNORE_INTERMEDIATE):
        mo_parts.append(L["manual.ignore_intermediate"])
    if config.get(CONF_MANUAL_IGNORE_EXTERNAL):
        mo_parts.append(L["manual.ignore_external"])
    input_entities = config.get(CONF_MANUAL_OVERRIDE_INPUT_ENTITIES)
    if input_entities:
        mo_parts.append(L["manual.input_entities"].format(count=len(input_entities)))
    transit_timeout = config.get(CONF_TRANSIT_TIMEOUT)
    if (
        transit_timeout is not None
        and int(transit_timeout) != DEFAULT_TRANSIT_TIMEOUT_SECONDS
    ):
        mo_parts.append(
            L["manual.transit_timeout"].format(seconds=int(transit_timeout))
        )
    mo_str = f" ({', '.join(mo_parts)})" if mo_parts else ""
    lines.append(
        L["rules.manual"].format(detail=mo_str) + _badge(_prio["manual_override"])
    )

    # Custom positions — each slot at its own configured priority
    if has_custom_position:
        for (
            _slot,
            _trigger,
            _pos,
            _pri,
            _use_my,
            _slot_tilt,
            _tilt_only,
            _has_trigger,
        ) in _custom_slots:
            tilt_note = (
                L["custom.tilt_note"].format(tilt=_slot_tilt)
                if _slot_tilt is not None
                else ""
            )
            # Priority-100 slots inherit the old force-override safety
            # semantics — flag it inline so the behavior is discoverable.
            safety_note = (
                L["fragments.safety"] if _pri >= CUSTOM_POSITION_SAFETY_PRIORITY else ""
            )
            if _tilt_only:
                # Tilt-only fixes the slat angle and lets the position pipeline
                # (solar etc.) drive the carriage — min_mode/use_my are ignored.
                slat = _slot_tilt if _slot_tilt is not None else 0
                lines.append(
                    L["rules.custom_tilt_only"].format(
                        slot=_slot, trigger=_trigger, slat=slat
                    )
                    + _badge(_pri)
                )
            else:
                target = _pos_label(_pos, _use_my)
                cp_min = (
                    L["fragments.as_minimum"]
                    if config.get(f"custom_position_min_mode_{_slot}")
                    else ""
                )
                lines.append(
                    L["rules.custom"].format(
                        slot=_slot,
                        trigger=_trigger,
                        target=target,
                        cp_min=cp_min,
                        tilt_note=tilt_note,
                        safety=safety_note,
                    )
                    + _badge(_pri)
                )
        # Mutual-exclusion warning: tilt_only wins over min_mode / use_my
        # (issue #514). Surface the conflict so the user knows the latter two
        # are ignored for that slot.
        for (
            _slot,
            _trigger,
            _pos,
            _pri,
            _use_my,
            _slot_tilt,
            _tilt_only,
            _has_trigger,
        ) in _custom_slots:
            if _tilt_only and (
                config.get(f"custom_position_min_mode_{_slot}") or _use_my
            ):
                lines.append(L["warnings.custom_tilt_only_conflict"].format(slot=_slot))
            # Footgun (issue #711): a safety-priority slot with a live trigger
            # bypasses the auto-control toggle, manual override, and the time
            # window — it can move the cover at any hour with automation off.
            if _pri >= CUSTOM_POSITION_SAFETY_PRIORITY and _has_trigger:
                lines.append(
                    L["warnings.custom_safety_bypass"].format(
                        slot=_slot, safety=CUSTOM_POSITION_SAFETY_PRIORITY
                    )
                )
        # Footgun warning: AND combine mode with no sensors — the template
        # gates nothing and the slot degenerates to template-only OR.
        for _slot in _and_no_sensor_slots:
            lines.append(L["warnings.custom_and_no_sensors"].format(slot=_slot))

    # Motion timeout (75)
    timeout_mode = config.get(CONF_MOTION_TIMEOUT_MODE, DEFAULT_MOTION_TIMEOUT_MODE)
    if has_motion:
        n = len(_motion_sources)
        sensor_word = L["words.source_singular"] if n == 1 else L["words.source_plural"]
        src_parts = []
        if n:
            src_parts.append(f"{n} {sensor_word}")
        if _has_motion_template:
            src_parts.append(L["motion.template_source"])
        sources = ", ".join(src_parts)
        if timeout_mode == MOTION_TIMEOUT_MODE_HOLD:
            action = L["motion.action_hold"]
        else:
            action = L["motion.action_return"].format(default_pos=default_pos)
        lines.append(
            L["rules.motion"].format(
                motion_timeout=motion_timeout,
                sources=sources,
                action=action,
            )
            + _badge(_prio["motion_timeout"])
        )
    elif timeout_mode == MOTION_TIMEOUT_MODE_HOLD:
        lines.append(L["warnings.motion_hold_no_sensors"])

    # Cloud suppression (60)
    if has_cloud:
        cloud_parts = []
        is_sunny_value = config.get(CONF_IS_SUNNY_SENSOR) or (
            L["fragments.template_value"]
            if is_template_string(config.get(CONF_IS_SUNNY_TEMPLATE))
            else None
        )
        if is_sunny_value:
            cloud_parts.append(L["cloud.is_sunny"].format(value=is_sunny_value))
        if v := config.get(CONF_LUX_ENTITY):
            t = config.get(CONF_LUX_THRESHOLD)
            cloud_parts.append(
                L["cloud.lux"].format(thresh=_thresh_display(t, placeholder=_ph))
                if t is not None
                else L["cloud.lux_no_thresh"].format(entity=v)
            )
        if v := config.get(CONF_IRRADIANCE_ENTITY):
            t = config.get(CONF_IRRADIANCE_THRESHOLD)
            cloud_parts.append(
                L["cloud.irradiance"].format(thresh=_thresh_display(t, placeholder=_ph))
                if t is not None
                else L["cloud.irradiance_no_thresh"].format(entity=v)
            )
        if v := config.get(CONF_CLOUD_COVERAGE_ENTITY):
            t = config.get(CONF_CLOUD_COVERAGE_THRESHOLD)
            cloud_parts.append(
                L["cloud.coverage"].format(thresh=_thresh_display(t, placeholder=_ph))
                if t is not None
                else L["cloud.coverage_no_thresh"].format(entity=v)
            )
        wx_states = config.get(CONF_WEATHER_STATE) or []
        if wx_states and config.get(CONF_WEATHER_ENTITY):
            cloud_parts.append(
                L["cloud.weather_in"].format(states=", ".join(wx_states))
            )
        cloud_str = (
            L["cloud.when"].format(parts=", ".join(cloud_parts)) if cloud_parts else ""
        )
        cloudy_pos = config.get(CONF_CLOUDY_POSITION)
        if cloudy_pos is not None:
            fallback_label = L["cloud.fallback_cloudy"].format(pos=cloudy_pos)
        else:
            fallback_label = L["cloud.fallback_default"].format(default_pos=default_pos)
        lines.append(
            L["rules.cloud"].format(cloud=cloud_str, fallback=fallback_label)
            + _badge(_prio["cloud_suppression"])
        )
    elif any(
        [
            config.get(CONF_LUX_ENTITY),
            config.get(CONF_IRRADIANCE_ENTITY),
            config.get(CONF_CLOUD_COVERAGE_ENTITY),
            config.get(CONF_IS_SUNNY_SENSOR),
        ]
    ):
        # Sensors configured but suppression toggle off — mention them as informational
        sensor_names = []
        if config.get(CONF_LUX_ENTITY):
            sensor_names.append(L["info.light_lux"])
        if config.get(CONF_IRRADIANCE_ENTITY):
            sensor_names.append(L["info.light_irradiance"])
        if config.get(CONF_CLOUD_COVERAGE_ENTITY):
            sensor_names.append(L["info.light_cloud_coverage"])
        if v := config.get(CONF_IS_SUNNY_SENSOR):
            sensor_names.append(v)
        lines.append(L["info.light_sensors_off"].format(names=", ".join(sensor_names)))

    # Warn if cloudy_position set but cloud suppression is disabled
    cloudy_pos_cfg = config.get(CONF_CLOUDY_POSITION)
    if cloudy_pos_cfg is not None and not has_cloud:
        lines.append(L["warnings.cloudy_pos_ignored"].format(pos=cloudy_pos_cfg))

    # Climate mode (50)
    if has_climate:
        cl_parts = []
        lo = config.get(CONF_TEMP_LOW)
        hi = config.get(CONF_TEMP_HIGH)
        temp_entity = config.get(CONF_TEMP_ENTITY)
        if lo is not None and hi is not None:
            cl_parts.append(
                L["climate.comfort_range"].format(
                    lo=_thresh_display(lo, placeholder=_ph),
                    hi=_thresh_display(hi, placeholder=_ph),
                )
            )
        if temp_entity:
            cl_parts.append(L["climate.using"].format(entity=temp_entity))
        outside = config.get(CONF_OUTSIDETEMP_ENTITY)
        if outside:
            out_thresh = config.get(CONF_OUTSIDE_THRESHOLD)
            if out_thresh is not None:
                cl_parts.append(
                    L["climate.outside_thresh"].format(
                        entity=outside,
                        thresh=_thresh_display(out_thresh, placeholder=_ph),
                    )
                )
            else:
                cl_parts.append(L["climate.outside"].format(entity=outside))
        weather_ent = config.get(CONF_WEATHER_ENTITY)
        if weather_ent:
            cl_parts.append(L["climate.weather"].format(entity=weather_ent))
        presence = config.get(CONF_PRESENCE_ENTITY) or (
            L["fragments.template_value"]
            if is_template_string(config.get(CONF_PRESENCE_TEMPLATE))
            else None
        )
        if presence:
            cl_parts.append(L["climate.presence"].format(entity=presence))
        if config.get(CONF_TRANSPARENT_BLIND):
            cl_parts.append(L["climate.transparent"])
        if config.get(CONF_WINTER_CLOSE_INSULATION):
            cl_parts.append(L["climate.winter_close"])
        if config.get(CONF_SUMMER_CLOSE_BYPASS_SUN_FLOOR):
            cl_parts.append(L["climate.summer_full_close"])
        cl_str = f" ({', '.join(cl_parts)})" if cl_parts else ""
        lines.append(
            L["rules.climate"].format(detail=cl_str) + _badge(_prio["climate"])
        )

    # Glare zones — vertical only (45, below climate)
    if has_glare:
        zone_names = [
            config.get(f"glare_zone_{i}_name")
            for i in range(1, 5)
            if config.get(f"glare_zone_{i}_name")
        ]
        width = config.get(CONF_WINDOW_WIDTH)
        gz_parts = []
        if zone_names:
            gz_parts.append(L["glare.zones"].format(names=", ".join(zone_names)))
        if width:
            gz_parts.append(L["glare.window"].format(width=float(width)))
        z_values = [
            float(config.get(f"glare_zone_{i}_z") or 0.0)
            for i in range(1, 5)
            if config.get(f"glare_zone_{i}_name")
        ]
        if any(z > 0 for z in z_values):
            gz_parts.append(
                L["glare.z_height"].format(
                    values=", ".join(L["glare.z_value"].format(z=z) for z in z_values)
                )
            )
        gz_str = f" ({', '.join(gz_parts)})" if gz_parts else ""
        lines.append(
            L["rules.glare"].format(detail=gz_str) + _badge(_prio["glare_zone"])
        )

    # Solar tracking — baseline calculation (40)
    azimuth = config.get(CONF_AZIMUTH)
    fov_l = config.get(CONF_FOV_LEFT)
    fov_r = config.get(CONF_FOV_RIGHT)
    min_elev = config.get(CONF_MIN_ELEVATION)
    max_elev = config.get(CONF_MAX_ELEVATION)
    if sun_tracking_enabled:
        sun_parts = []
        if azimuth is not None:
            sun_parts.append(L["solar.azimuth"].format(azimuth=azimuth))
        if fov_l is not None and fov_r is not None:
            sun_parts.append(L["solar.fov"].format(fov_l=fov_l, fov_r=fov_r))
        elev_parts = []
        if min_elev is not None:
            elev_parts.append(L["solar.elev_above"].format(elev=min_elev))
        if max_elev is not None:
            elev_parts.append(L["solar.elev_below"].format(elev=max_elev))
        if elev_parts:
            sun_parts.append(
                L["solar.elevation"].format(parts=L["solar.elev_join"].join(elev_parts))
            )
        sun_desc = f" ({', '.join(sun_parts)})" if sun_parts else ""
        # Today's solar window annotation
        if _solar_start is not None and _solar_end is not None:
            today_str = L["solar.today_window"].format(
                start=_fmt_sun_dt(_solar_start), end=_fmt_sun_dt(_solar_end)
            )
        elif sun_times is not None:
            today_str = L["solar.today_no_window"]
        else:
            today_str = ""
        lines.append(
            L["rules.solar"].format(sun_desc=sun_desc, today=today_str)
            + _badge(_prio["solar"])
        )
        if config.get(CONF_MINIMIZE_MOVEMENTS, False):
            steps = int(config.get(CONF_MAX_COVERAGE_STEPS, 1))
            indent = "\u00a0" * 4
            if steps <= 1:
                detail = L["solar.minimize_one_step"]
            else:
                detail = L["solar.minimize_steps"].format(steps=steps)
            lines.append(L["solar.minimize"].format(indent=indent, detail=detail))
    else:
        lines.append(L["rules.solar_disabled"] + _badge(_prio["solar"]))

    # Timing window (sub-bullet under ☀️)
    start_time = config.get(CONF_START_TIME)
    start_entity = config.get(CONF_START_ENTITY)
    end_time = config.get(CONF_END_TIME)
    end_entity = config.get(CONF_END_ENTITY)
    sunset_pos = config.get(CONF_SUNSET_POS)
    eow_pos = config.get(CONF_END_OF_WINDOW_POS)
    sunset_off = config.get(CONF_SUNSET_OFFSET, 0) or 0
    sunrise_off = config.get(CONF_SUNRISE_OFFSET, 0) or 0
    sunset_time_entity = config.get(CONF_SUNSET_TIME_ENTITY)
    sunrise_time_entity = config.get(CONF_SUNRISE_TIME_ENTITY)
    timing_parts = []
    if start_entity:
        timing_parts.append(L["timing.from_entity"].format(entity=start_entity))
    elif start_time and start_time != BLANK_TIME:
        timing_parts.append(L["timing.from_time"].format(time=start_time))
    if end_entity:
        timing_parts.append(L["timing.until_entity"].format(entity=end_entity))
    elif end_time and end_time != BLANK_TIME:
        timing_parts.append(L["timing.until_time"].format(time=end_time))
    # A schedule key present but blank (cleared TimeSelector → "00:00:00") still
    # means the user configured the automation window — show "Active during
    # daylight" rather than nothing, so the summary reflects the real behavior
    # (issue #492). CONF_*_TIME default to BLANK_TIME, so test membership too.
    schedule_configured = any(
        config.get(key) not in (None, BLANK_TIME)
        for key in (CONF_START_ENTITY, CONF_END_ENTITY)
    ) or any(key in config for key in (CONF_START_TIME, CONF_END_TIME))
    if (
        timing_parts
        or sunset_pos is not None
        or schedule_configured
        or eow_pos is not None
    ):
        timing_str = (
            " ".join(timing_parts) if timing_parts else L["timing.active_daylight"]
        )
        indent = "\u00a0" * 4
        lines.append(L["timing.line"].format(indent=indent, timing=timing_str))
        if sunset_pos is not None:
            # Merge today's effective time (or entity ID) and offset into one parenthetical
            def _sun_annotation(
                today_dt, offset_min: int, entity_id: str | None = None
            ) -> str:
                parts = []
                if entity_id is not None:
                    parts.append(L["timing.ann_via"].format(entity=entity_id))
                elif today_dt is not None:
                    parts.append(
                        L["timing.ann_today"].format(time=_fmt_sun_dt(today_dt))
                    )
                off = _offset_str(int(offset_min))
                if off:
                    parts.append(off)
                return f" ({', '.join(parts)})" if parts else ""

            sunset_ann = _sun_annotation(_sunset_eff, sunset_off, sunset_time_entity)
            sunrise_ann = _sun_annotation(
                _sunrise_eff, sunrise_off, sunrise_time_entity
            )
            has_end_time = bool(end_time or end_entity)
            _sunset_use_my = bool(config.get(CONF_SUNSET_USE_MY))
            _sunset_target = _pos_label(int(sunset_pos), _sunset_use_my)
            if has_end_time and int(sunset_pos) != int(default_pos):
                lines.append(
                    L["timing.after_end_to_default"].format(
                        indent=indent, default_pos=default_pos
                    )
                )
                lines.append(
                    L["timing.after_sunset"].format(
                        indent=indent, ann=sunset_ann, target=_sunset_target
                    )
                )
            else:
                label = (
                    L["timing.label_end_or_sunset"]
                    if has_end_time
                    else L["timing.label_sunset"]
                )
                lines.append(
                    L["timing.after_label"].format(
                        indent=indent,
                        label=label,
                        ann=sunset_ann,
                        target=_sunset_target,
                    )
                )
            lines.append(
                L["timing.after_sunrise"].format(
                    indent=indent, ann=sunrise_ann, default_pos=default_pos
                )
            )
            if config.get(CONF_RETURN_SUNSET):
                lines.append(L["timing.return_sunset"].format(indent=indent))

        # End-of-window position (issue #625) — renders independently of
        # sunset_pos (a user may set it WITHOUT a sunset position). Footgun:
        # the position only applies when CONF_RETURN_SUNSET ("Move covers when
        # end time is reached") is on.
        if eow_pos is not None:
            lines.append(
                L["timing.end_of_window"].format(
                    indent=indent, target=_pos_label(int(eow_pos), use_my=False)
                )
            )
            if not config.get(CONF_RETURN_SUNSET):
                lines.append(
                    L["timing.end_of_window_needs_return"].format(indent=indent)
                )

    # Daytime gate (issue #632) — when configured it OWNS the day/night boundary,
    # replacing the astronomical sunset/sunrise calc. Rendered independently of the
    # timing window so it shows even with no sunset_pos / schedule configured.
    gate_sensors = config.get(CONF_DAYTIME_GATE_SENSORS) or []
    gate_template = config.get(CONF_DAYTIME_GATE_TEMPLATE)
    gate_has_template = is_template_string(gate_template)
    gate_mode = config.get(
        CONF_DAYTIME_GATE_TEMPLATE_MODE, DEFAULT_TEMPLATE_COMBINE_MODE
    )
    if gate_sensors or gate_has_template:
        indent = " " * 4
        sensors_str = ", ".join(gate_sensors)
        if gate_sensors and gate_has_template:
            lines.append(
                L["timing.gate_both"].format(
                    indent=indent, sensors=sensors_str, mode=gate_mode
                )
            )
        elif gate_sensors:
            lines.append(
                L["timing.gate_sensors"].format(indent=indent, sensors=sensors_str)
            )
        else:
            lines.append(L["timing.gate_template"].format(indent=indent))
        lines.append(L["timing.gate_explainer"].format(indent=indent))
        # Footgun: sunset/sunrise offsets are no-ops once the gate owns the
        # boundary. Only warn when an offset is actually set (avoid noise).
        if sunset_off or sunrise_off:
            lines.append(L["timing.gate_offset_ignored"].format(indent=indent))

    # Blind spot (sub-bullet / informational, no priority of its own). One line
    # per active slot — a slot is active when its left & right are both set
    # (issue #701). Slot 1 reuses the legacy unsuffixed keys.
    if config.get(CONF_ENABLE_BLIND_SPOT):
        for keys in BLIND_SPOT_SLOTS.values():
            bs_l = config.get(keys["left"])
            bs_r = config.get(keys["right"])
            if bs_l is None or bs_r is None:
                continue
            bs_e = config.get(keys["elevation"])
            bs_parts = [L["blind_spot.range"].format(left=bs_l, right=bs_r)]
            if bs_e is not None:
                # "above" blocks high sun; "below" (default) blocks low sun (#702).
                bs_mode = config.get(
                    keys["elevation_mode"], DEFAULT_BLIND_SPOT_ELEVATION_MODE
                )
                elev_key = (
                    "blind_spot.elevation_above"
                    if bs_mode == BLIND_SPOT_ELEV_MODE_ABOVE
                    else "blind_spot.elevation"
                )
                bs_parts.append(L[elev_key].format(elev=bs_e))
            lines.append(L["blind_spot.line"].format(bs=" ".join(bs_parts)))

    # Default fallback (priority 0) — shown as the final row of the chain
    lines.append(L["rules.default"].format(default_pos=default_pos) + _badge(0))
    # Explicit tilt for venetian covers (solar-computed when absent)
    _default_tilt = config.get(CONF_DEFAULT_TILT)
    _sunset_tilt = config.get(CONF_SUNSET_TILT)
    if _default_tilt is not None:
        lines.append(L["default.tilt"].format(tilt=_default_tilt))
    if _sunset_tilt is not None:
        lines.append(L["default.sunset_tilt"].format(tilt=_sunset_tilt))

    # =========================================================================
    # Section 3: Position Limits
    # =========================================================================
    limit_parts = []
    min_pos = config.get(CONF_MIN_POSITION)
    max_pos = config.get(CONF_MAX_POSITION)
    enable_min = config.get(CONF_ENABLE_MIN_POSITION)
    enable_max = config.get(CONF_ENABLE_MAX_POSITION)
    if min_pos is not None or max_pos is not None:
        lo_str = f"{min_pos}%" if min_pos is not None else "0%"
        hi_str = f"{max_pos}%" if max_pos is not None else "100%"
        # Per-side tracking-only qualifier for precision
        if enable_min and enable_max:
            qualifier = L["limits.qualifier_both"]
        elif enable_min and not enable_max:
            qualifier = L["limits.qualifier_min"]
        elif enable_max and not enable_min:
            qualifier = L["limits.qualifier_max"]
        else:
            qualifier = ""
        limit_parts.append(
            L["limits.range"].format(lo=lo_str, hi=hi_str, qualifier=qualifier)
        )
    if default_pos is not None:
        limit_parts.append(L["limits.default"].format(pos=default_pos))
    delta_pos = config.get(CONF_DELTA_POSITION)
    delta_time = config.get(CONF_DELTA_TIME)
    if delta_pos is not None:
        limit_parts.append(L["limits.min_change"].format(delta=delta_pos))
    if delta_time is not None:
        limit_parts.append(L["limits.min_interval"].format(delta=delta_time))
    pos_tol = config.get(CONF_POSITION_TOLERANCE)
    if pos_tol is not None:
        limit_parts.append(L["limits.position_tolerance"].format(tol=pos_tol))
    if config.get(CONF_ENABLE_POSITION_MATCHING):
        limit_parts.append(L["limits.position_matching_on"])
    else:
        limit_parts.append(L["limits.position_matching_off"])
    if config.get(CONF_INVERSE_STATE):
        limit_parts.append(L["limits.inverse_state"])
    oc_thresh = config.get(CONF_OPEN_CLOSE_THRESHOLD)
    if oc_thresh is not None:
        limit_parts.append(L["limits.open_close_threshold"].format(thresh=oc_thresh))
    if config.get(CONF_INTERP):
        interp_lo = config.get(CONF_INTERP_START)
        interp_hi = config.get(CONF_INTERP_END)
        if interp_lo is not None and interp_hi is not None:
            limit_parts.append(
                L["limits.calibration"].format(lo=interp_lo, hi=interp_hi)
            )
        else:
            limit_parts.append(L["limits.calibration_on"])
    min_pos_sun_track = config.get(CONF_MIN_POSITION_SUN_TRACKING)
    if min_pos_sun_track is not None:
        limit_parts.append(L["limits.sun_tracking_min"].format(pos=min_pos_sun_track))
    if limit_parts:
        lines.append("")
        lines.append(L["headers.position_limits"])
        lines.append(L["limits.separator"].join(limit_parts))

    # Footgun: sun-tracking floor below always-on floor is a no-op (issue #467).
    # The always-on min_pos dominates, so min_pos_sun_tracking < min_pos is a
    # configuration mistake. Surface it so the user can correct it.
    if (
        min_pos_sun_track is not None
        and min_pos is not None
        and min_pos > min_pos_sun_track
    ):
        lines.append(
            L["warnings.sun_track_min_below_floor"].format(
                sun_min=min_pos_sun_track, min_pos=min_pos
            )
        )

    # MODE2 + min_position footgun warning (issue #373).
    # In MODE2 the OPEN (horizontal) slat angle IS 50%, so any min_position
    # >= 50% collapses every climate/glare-control decision to the floor and
    # the cover stops blocking heat or glare. Surface this as a ⚠️ line so
    # users see it before saving the config.
    if (
        sensor_type in (CoverType.TILT, CoverType.VENETIAN)
        and _tilt_is_mode2(config.get(CONF_TILT_MODE))
        and min_pos is not None
        and min_pos >= MODE2_OPEN_HORIZONTAL_PERCENT
    ):
        lines.append(L["warnings.mode2_min_position"].format(min_pos=min_pos))

    # Somfy My preset info / warning
    _any_use_my = bool(config.get(CONF_SUNSET_USE_MY)) or any(
        bool(config.get(f"custom_position_use_my_{_i}"))
        for _i in CUSTOM_POSITION_SLOT_NUMBERS
    )
    _my_entities_enabled = bool(
        config.get(
            CONF_ENABLE_MY_POSITION_ENTITIES, DEFAULT_ENABLE_MY_POSITION_ENTITIES
        )
    )
    lines.append(
        L["my.entities_enabled"] if _my_entities_enabled else L["my.entities_disabled"]
    )
    if my_pos is not None:
        lines.append(L["my.somfy_preset"].format(pos=my_pos))
    elif _any_use_my or _my_entities_enabled:
        lines.append(L["warnings.somfy_my_unset"])

    # Proxy cover toggle (system-wide; not part of the decision chain)
    proxy_enabled = bool(config.get(CONF_ENABLE_PROXY_COVER))
    lines.append("")
    lines.append(
        L["headers.proxy_enabled"] if proxy_enabled else L["headers.proxy_disabled"]
    )
    if proxy_enabled:
        _any_min_mode = any(
            bool(config.get(f"custom_position_min_mode_{_i}"))
            for _i in CUSTOM_POSITION_SLOT_NUMBERS
        )
        if not _any_min_mode:
            lines.append(L["warnings.proxy_no_min"])

    # =========================================================================
    # Section 4: Decision Priority (compact reference)
    # =========================================================================
    def _ch(active: bool, short: str) -> str:
        mark = "✅" if active else "❌"
        return f"{mark}{short}"

    # Build the full priority chain (fixed anchors + per-slot custom positions)
    # via the shared helper, which owns the priority integers and ordering.
    _chain_entries = build_priority_chain(
        has_weather=has_weather,
        has_motion=has_motion,
        has_cloud=has_cloud,
        has_climate=has_climate,
        sun_tracking_enabled=sun_tracking_enabled,
        has_glare=has_glare,
        supports_glare=summary_policy.supports_glare_zones,
        custom_slots=_custom_slots,
        priorities=_handler_priority_overrides(config),
    )
    chain = [_ch(e.active, e.label) for e in _chain_entries]

    lines.append("")
    lines.append(L["headers.decision_priority"])
    lines.append(" → ".join(chain))

    return "\n".join(lines)


def _render_priority_scale(config: dict, policy) -> str:
    """Render the decision-priority ladder for the custom-slot step (#613).

    Shows every fixed handler anchor at its declared priority plus each
    configured custom slot interleaved at its own priority and marked with
    ``◀``, so the user sees where a 1–100 slot priority lands. Built from the
    shared :func:`build_priority_chain` — the priority integers live there, not
    here. HA options flows cannot recompute live as the slider moves, so the
    ladder reflects the *last submitted* priorities and refreshes on re-render.
    """
    custom_slots: list[tuple] = []
    for slot, slot_keys in CUSTOM_POSITION_SLOTS.items():
        if not custom_position_slot_configured(config, slot_keys):
            continue
        priority = int(
            config.get(slot_keys["priority"]) or DEFAULT_CUSTOM_POSITION_PRIORITY
        )
        # build_priority_chain reads index 0 (slot) and 3 (priority).
        custom_slots.append((slot, None, 0, priority, False, None, False))

    entries = build_priority_chain(
        has_weather=True,
        has_motion=True,
        has_cloud=True,
        has_climate=True,
        sun_tracking_enabled=True,
        has_glare=True,
        supports_glare=policy.supports_glare_zones,
        custom_slots=custom_slots,
        priorities=_handler_priority_overrides(config),
    )

    lines = ["```"]
    for entry in entries:
        marker = "◀" if entry.slot is not None else " "
        lines.append(f"{entry.priority:>3} {marker} {entry.label}")
    lines.append("```")
    return "\n".join(lines)


async def _get_devices_from_entities(
    hass: HomeAssistant, entity_ids: list[str]
) -> dict[str, str]:
    """Get devices associated with the given cover entity IDs."""
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    devices: dict[str, str] = {}
    for entity_id in entity_ids:
        entity_entry = entity_reg.async_get(entity_id)
        if entity_entry and entity_entry.device_id:
            device_entry = device_reg.async_get(entity_entry.device_id)
            if device_entry and entity_entry.device_id not in devices:
                name = (
                    device_entry.name_by_user
                    or device_entry.name
                    or entity_entry.device_id
                )
                devices[entity_entry.device_id] = name
    return devices


async def _get_device_name_for_entity(
    hass: HomeAssistant, entity_id: str
) -> str | None:
    """Return the parent device's display name for entity_id, or None.

    Returns name_by_user or name only — never the device_id UUID — so callers
    can safely use the result as a default user-facing name.
    """
    entity_reg = er.async_get(hass)
    entity_entry = entity_reg.async_get(entity_id)
    if not entity_entry or not entity_entry.device_id:
        return None
    device_reg = dr.async_get(hass)
    device_entry = device_reg.async_get(entity_entry.device_id)
    if not device_entry:
        return None
    return device_entry.name_by_user or device_entry.name or None


def _build_cover_entity_schema(
    sensor_type: str,
    devices: dict[str, str] | None = None,
    *,
    attach_device_by_default: bool = False,
    include_proxy_toggle: bool = True,
) -> vol.Schema:
    """Build entity selector schema based on cover type.

    When devices is provided and non-empty, a device association selector is
    appended so both fields appear on the same form.

    ``attach_device_by_default`` preselects the first associated device rather
    than "standalone": a pergola's slats always belong to their physical box,
    so the create flow attaches by default (the user can still pick
    standalone). The options flow leaves it False and drives the selection via
    suggested values from the stored option instead.

    ``include_proxy_toggle`` False omits the proxy-cover switch entirely — the
    create flow always enables the proxy cover, so it has nothing to ask. The
    options flow keeps the toggle so an existing entry can still turn it off.
    """
    entity_selector = selector.EntitySelector(
        selector.EntitySelectorConfig(
            multiple=True,
            filter=get_policy(sensor_type).entity_selector_filter(),
        )
    )
    schema_dict: dict = {vol.Optional(CONF_ENTITIES, default=[]): entity_selector}
    if devices:
        options_list = [
            {"value": _STANDALONE_SENTINEL, "label": "None (standalone device)"}
        ]
        for device_id, device_name in devices.items():
            options_list.append({"value": device_id, "label": device_name})
        device_default = (
            next(iter(devices)) if attach_device_by_default else _STANDALONE_SENTINEL
        )
        schema_dict[vol.Required(CONF_DEVICE_ID, default=device_default)] = (
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options_list,
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        )
    if include_proxy_toggle:
        schema_dict[
            vol.Optional(CONF_ENABLE_PROXY_COVER, default=DEFAULT_ENABLE_PROXY_COVER)
        ] = selector.BooleanSelector()
    return vol.Schema(schema_dict)


def _get_geometry_schema(
    sensor_type: str | None,
    hass: HomeAssistant | None = None,
    options: dict | None = None,
) -> vol.Schema:
    """Return the geometry schema for the given sensor type.

    Falls back to the louvered-roof schema for unknown / missing types so
    legacy configs still render *something* in the options flow. When *hass*
    is supplied the schema follows HA's configured unit system (metric vs.
    US-customary); ``hass=None`` keeps the legacy metric schema and is the
    path the existing test suite uses.
    """
    cls = POLICY_REGISTRY.get(sensor_type) if sensor_type is not None else None
    if cls is None:
        if hass is None:
            return GEOMETRY_LOUVERED_ROOF_SCHEMA
        from .cover_types.louvered_roof import geometry_louvered_roof_schema

        return geometry_louvered_roof_schema(hass)
    return get_policy(sensor_type).geometry_schema(hass, options)


def _geometry_unit_keys(
    sensor_type: str | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(length_keys, slat_keys)`` for the given cover type.

    ``length_keys`` are option keys stored in canonical metres,
    ``slat_keys`` in canonical centimetres. Empty tuples for unknown types.
    """
    cls = POLICY_REGISTRY.get(sensor_type) if sensor_type is not None else None
    if cls is None:
        return ((), ())
    policy = get_policy(sensor_type)
    return (policy.geometry_length_keys(), policy.geometry_slat_keys())


def _fov_compute_supported(sensor_type: str | None) -> bool:
    """Whether *sensor_type*'s policy exposes the FOV-from-measurements button."""
    return (
        sensor_type in POLICY_REGISTRY and get_policy(sensor_type).supports_fov_compute
    )


_SUN_TRACKING_WIKI = "https://github.com/B4S71/adaptive-pergola"


def _sun_tracking_placeholders(
    sensor_type: str | None,
    source_config: dict[str, Any],
) -> dict[str, str]:
    """Build description placeholders for the sun-tracking form.

    Always includes ``learn_more``. For cover types with the FOV-from-
    measurements button (#565) it adds a read-only ``computed_fov`` preview of
    the angle the button would produce from the window width + reveal depth, so
    the user sees it before pressing — rendered in the button's own help text
    (``data_description.fov_compute``), which receives the same placeholders.

    The preview is shown for *every* depth, including a flush window (depth 0):
    that is not "nothing to derive" — ``fov_from_reveal`` returns the full
    hemisphere (90°/90°) there, which is the correct, informative answer. Only
    cover types without the button get an empty ``computed_fov``.
    """
    # ``computed_fov`` is referenced unconditionally in the template, so it must
    # always be present — empty string for cover types without the button (HA
    # raises if a referenced placeholder is missing).
    computed = ""
    if _fov_compute_supported(sensor_type):
        computed = computed_fov_line(
            source_config.get(CONF_WINDOW_WIDTH),
            source_config.get(CONF_WINDOW_DEPTH),
        )
    return {"learn_more": _SUN_TRACKING_WIKI, "computed_fov": computed}


def sun_window_from_canonical(
    azimuth: float, fov_left: float, fov_right: float
) -> tuple[int, int]:
    """Derive the transient sun-window display values from the canonical keys.

    ``start = (azimuth − fov_left) % 360``, ``end = (azimuth + fov_right) % 360``.
    Pure helper — the inverse of :func:`sun_window_to_canonical`. The display
    fields are whole degrees (0–359 sliders), so values are rounded to ints —
    legacy entries may carry non-integer canonical values, but everything this
    integration writes is integral (see :func:`sun_window_to_canonical`), so
    windows written here round-trip exactly.
    """
    start = round((float(azimuth) - float(fov_left)) % 360) % 360
    end = round((float(azimuth) + float(fov_right)) % 360) % 360
    return start, end


def sun_window_to_canonical(start: float, end: float) -> tuple[int, int, int]:
    """Convert a transient sun-window submit to the canonical storage keys.

    ``span = (end − start) % 360`` (clockwise, wrap-aware; the window may wrap
    through north, e.g. 137° → 2°). Returns ``(azimuth, fov_left, fov_right)``:
    azimuth is the window midpoint, the fov halves split the span symmetrically.
    All values are whole degrees; an odd span cannot split evenly, so the
    deterministic rounding is ``fov_left = span // 2`` and ``fov_right`` takes
    the extra degree — with ``azimuth = (start + fov_left) % 360`` the exact
    ``[start, end]`` coverage is preserved and the round trip through
    :func:`sun_window_from_canonical` is lossless.

    Raises ``ValueError`` on a zero span (``start == end``): the full-circle
    window is not supported — the form validates this before converting and
    shows a field error instead (docs/CONFIG_FLOW_REWORK.md, stage 2).
    """
    start_i = round(float(start)) % 360
    end_i = round(float(end)) % 360
    span = (end_i - start_i) % 360
    if span == 0:
        raise ValueError("sun window must span at least 1°")
    fov_left = span // 2
    fov_right = span - fov_left
    azimuth = (start_i + fov_left) % 360
    return azimuth, fov_left, fov_right


def _apply_sun_window_submit(user_input: dict[str, Any]) -> dict[str, str] | None:
    """Pop the transient sun-window keys and write the canonical keys instead.

    Shared by both ``async_step_sun_tracking`` submit handlers (create + options
    flow), following the ``CONF_FOV_COMPUTE`` transient-field pattern: the two
    display keys never persist. Tolerates submissions that carry the canonical
    keys directly (unit tests driving the handler) — conversion only runs when
    both transient keys are present.

    Returns a form-errors dict when the submitted window is invalid (zero span,
    i.e. ``start == end``); the transient keys are then left in *user_input* so
    the error re-render shows the user's own values instead of resetting them.
    Returns ``None`` on success (canonical keys written) or no-op.
    """
    if (
        CONF_SUN_WINDOW_START not in user_input
        and CONF_SUN_WINDOW_END not in user_input
    ):
        return None
    start = user_input.get(CONF_SUN_WINDOW_START)
    end = user_input.get(CONF_SUN_WINDOW_END)
    if start is None or end is None:
        # Defensive: a partial submit fragment carries no usable window — drop
        # it so the transient keys can never leak into persisted options.
        user_input.pop(CONF_SUN_WINDOW_START, None)
        user_input.pop(CONF_SUN_WINDOW_END, None)
        return None
    try:
        azimuth, fov_left, fov_right = sun_window_to_canonical(start, end)
    except ValueError:
        # Translation KEY (resolved via translations' config/options ``error``
        # section), NOT a message — HA renders an unknown key verbatim.
        return {CONF_SUN_WINDOW_END: "sun_window_span"}
    user_input.pop(CONF_SUN_WINDOW_START, None)
    user_input.pop(CONF_SUN_WINDOW_END, None)
    user_input[CONF_AZIMUTH] = azimuth
    user_input[CONF_FOV_LEFT] = fov_left
    user_input[CONF_FOV_RIGHT] = fov_right
    return None


def _inject_sun_window_display(suggested: dict[str, Any]) -> dict[str, Any]:
    """Add the transient sun-window display values to *suggested* (in place).

    Derives start/end from the stored canonical azimuth/fov keys, falling back
    to the schema defaults when a key is absent (fresh create flow). When the
    transient keys are already present (the zero-span error re-render, where
    ``_apply_sun_window_submit`` left them in the submitted values on purpose)
    they win, so the user sees their own rejected input rather than a reset.
    """
    if CONF_SUN_WINDOW_START in suggested and CONF_SUN_WINDOW_END in suggested:
        return suggested
    azimuth = suggested.get(CONF_AZIMUTH)
    fov_left = suggested.get(CONF_FOV_LEFT)
    fov_right = suggested.get(CONF_FOV_RIGHT)
    start, end = sun_window_from_canonical(
        DEFAULT_WINDOW_AZIMUTH if azimuth is None else azimuth,
        DEFAULT_FOV_LEFT if fov_left is None else fov_left,
        DEFAULT_FOV_RIGHT if fov_right is None else fov_right,
    )
    suggested[CONF_SUN_WINDOW_START] = start
    suggested[CONF_SUN_WINDOW_END] = end
    return suggested


def _resolve_fov_compute_submit(
    sensor_type: str | None,
    user_input: dict[str, Any],
    source_config: dict[str, Any],
) -> bool:
    """Process a sun-tracking submit for the FOV-from-measurements button (#565).

    Single home for the button logic shared by the create-flow and options-flow
    ``async_step_sun_tracking`` handlers (no-duplication guideline). The
    ``CONF_FOV_COMPUTE`` toggle is transient — always popped from *user_input*
    here so it never persists.

    When the toggle was ticked, ``fov_left``/``fov_right`` are overwritten in
    *user_input* with the angle derived from the entry's window width + reveal
    depth, and ``True`` is returned so the caller re-renders the form with the
    populated, un-ticked sliders (the "button press"). Otherwise ``False`` is
    returned and the user's typed fov values pass through to the save path.
    """
    pressed = bool(user_input.pop(CONF_FOV_COMPUTE, False))
    if not pressed or not _fov_compute_supported(sensor_type):
        return False

    width = float(source_config.get(CONF_WINDOW_WIDTH) or 0.0)
    depth = float(source_config.get(CONF_WINDOW_DEPTH) or 0.0)
    derived = round(fov_from_reveal(width, depth))
    user_input[CONF_FOV_LEFT] = derived
    user_input[CONF_FOV_RIGHT] = derived
    return True


def _get_sun_tracking_schema(
    sensor_type: str | None,
    hass: HomeAssistant | None = None,
) -> vol.Schema:
    """Return the sun-tracking schema for *sensor_type*.

    Adds the glare-zones toggle for cover types that support it, and routes the
    FOV-field shaping (the "Generate FOV from measurements" button, #565)
    through the cover-type policy so no cover-type string branching leaks here.
    """
    base = sun_tracking_schema(hass) if hass is not None else SUN_TRACKING_SCHEMA
    if sensor_type in POLICY_REGISTRY:
        base = get_policy(sensor_type).fov_compute_schema(base)
    return base


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle ConfigFlow."""

    VERSION = 3
    # 3.6 (issue #719): the v3.5→v3.6 block enables the weather override for every
    # pre-existing entry so upgrades keep firing weather safety overrides; new
    # installs default to off via the schema.
    # 3.5 (issue #693): formerly seeded the now-removed CONF_SHOW_WEATHER_RETRACTION
    # toggle. The toggle is gone (retraction pickers are always shown), so the
    # v3.4→v3.5 block is a no-op minor bump kept to advance stale entries.
    # 3.4 (issue #591/#606): MINOR_VERSION raised so HA triggers
    # async_migrate_entry for entries below 3.4.  The v3.3→v3.4 block enables
    # position matching for every pre-existing entry so upgrades keep the old
    # reconcile/chase behavior; new installs default to off via the schema.
    # 3.3 (issue #563 trailing defect): copy legacy custom_position_sensor_N
    # into the new list key.
    # 3.7: repair values the entry's own schema now rejects — clamp numbers that
    # fall outside their field's declared range (ranges were tightened without
    # migrating stored values), and drop templates that never finish rendering
    # (heals entries poisoned before the write-path cost gate shipped; this runs
    # before async_setup_entry, so it is what breaks that boot loop).
    # Rollback-safe: every migration block is additive (existing keys retained)
    # or value-level (3.7), and HA lets older code load a higher minor version.
    MINOR_VERSION = 7

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self.type_blind: str | None = None
        self.config: dict[str, Any] = {}
        self.mode: str = "basic"
        self.selected_source_entry_id: str | None = None
        self._has_device_options: bool = False
        self._cover_devices: dict[str, str] = {}

    def optional_entities(self, keys: list, user_input: dict[str, Any]) -> None:
        """Set value to None if key does not exist in user_input."""
        for key in keys:
            if key not in user_input:
                user_input[key] = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step — straight to the cover-entity form.

        Condensed flow (docs/CONFIG_FLOW_REWORK.md): no create-menu (the
        building-profile and duplicate-existing entry points died in stage 4)
        and no name/type step — the louvered roof is the only cover type this
        integration ships, so there is nothing to choose, and the name is
        derived from the selected cover's device in ``async_step_cover_entities``.
        The lean path is: cover → geometry → sun window → positions → summary;
        everything else is configured later via the options menu.
        """
        self.type_blind = CoverType.LOUVERED_ROOF
        self.config = {}
        return await self.async_step_cover_entities(user_input)

    async def async_step_cover_entities(self, user_input: dict[str, Any] | None = None):
        """Select cover entities and optionally link to a physical device.

        Pass 1 (entities only): user selects cover entities; if they have associated
        physical devices the form is re-rendered with a device selector appended.
        Pass 2 (combined, only when devices exist): both fields are submitted together
        and the flow proceeds to geometry.
        """
        if user_input is not None:
            if self._has_device_options:
                # Pass 2: process entity + device selection
                self.config.update(user_input)
                device_id = user_input.get(CONF_DEVICE_ID, _STANDALONE_SENTINEL)
                if device_id and device_id != _STANDALONE_SENTINEL:
                    self.config[CONF_DEVICE_ID] = device_id
                else:
                    self.config.pop(CONF_DEVICE_ID, None)
                self.config[CONF_ENABLE_PROXY_COVER] = True
                return await self.async_step_geometry()

            # Pass 1: store entities, auto-name, check for associated devices
            self.config.update(user_input)
            # The create flow always ships the proxy cover — it is the entity
            # the dashboard drives, so there is no toggle to read back.
            self.config[CONF_ENABLE_PROXY_COVER] = True
            if CONF_ENTITIES in user_input and user_input[CONF_ENTITIES]:
                first_entity_id = user_input[CONF_ENTITIES][0]
                entity_reg = er.async_get(self.hass)
                entity_entry = entity_reg.async_get(first_entity_id)
                if entity_entry and not self.config.get("name"):
                    device_name = await _get_device_name_for_entity(
                        self.hass, first_entity_id
                    )
                    if device_name:
                        self.config["name"] = device_name
                        self.config["_title_is_device_name"] = True
                    else:
                        entity_name = (
                            entity_entry.original_name
                            or entity_entry.name
                            or first_entity_id.split(".")[-1].replace("_", " ").title()
                        )
                        self.config["name"] = f"Adaptive {entity_name}"
            # No name step any more, so nothing else can supply one: fall back
            # when the user picked no cover (or an unregistered one).
            self.config.setdefault("name", _DEFAULT_INSTANCE_NAME)

            entity_ids = self.config.get(CONF_ENTITIES, [])
            devices = await _get_devices_from_entities(self.hass, entity_ids)
            if devices:
                self._has_device_options = True
                self._cover_devices = devices
                schema = _build_cover_entity_schema(
                    self.type_blind,
                    devices=devices,
                    attach_device_by_default=True,
                    include_proxy_toggle=False,
                )
                return self.async_show_form(
                    step_id="cover_entities",
                    data_schema=self.add_suggested_values_to_schema(
                        schema, self.config
                    ),
                    description_placeholders={
                        "learn_more": "https://github.com/B4S71/adaptive-pergola"
                    },
                )
            return await self.async_step_geometry()

        schema = _build_cover_entity_schema(self.type_blind, include_proxy_toggle=False)
        return self.async_show_form(
            step_id="cover_entities",
            data_schema=schema,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_geometry(self, user_input: dict[str, Any] | None = None):
        """Configure cover geometry dimensions."""
        length_keys, slat_keys = _geometry_unit_keys(self.type_blind)
        if user_input is not None:
            canonical = user_input_to_canonical(
                self.hass, user_input, length_keys=length_keys, slat_keys=slat_keys
            )
            self.config.update(canonical)
            return await self.async_step_sun_tracking()

        schema = _get_geometry_schema(self.type_blind, self.hass, self.config)
        return self.async_show_form(
            step_id="geometry",
            data_schema=schema,
            description_placeholders={
                "geometry_wiki_link": _geometry_wiki_link(self.type_blind)
            },
        )

    async def async_step_sun_tracking(self, user_input: dict[str, Any] | None = None):
        """Configure sun tracking parameters."""
        if user_input is not None:
            self.optional_entities([CONF_MIN_ELEVATION, CONF_MAX_ELEVATION], user_input)
            # Transient sun-window fields → canonical azimuth/fov keys, before
            # any canonicalisation/validation (docs/CONFIG_FLOW_REWORK.md, st. 2).
            # On a zero-span window the transient keys stay in *user_input* and
            # the form re-renders below with the field error.
            window_errors = _apply_sun_window_submit(user_input)
            pressed = _resolve_fov_compute_submit(
                self.type_blind, user_input, self.config
            )
            # Canonicalize once: ``_show_sun_tracking_form`` re-displays via
            # ``options_to_display``, so feeding it raw (already display-unit)
            # input would convert metres->inches a second time and the value
            # would compound on every rerender (#565). Canonical here keeps the
            # rerender re-feed symmetric with the initial render and save path.
            canonical = user_input_to_canonical(
                self.hass, user_input, length_keys=_SUN_TRACKING_LENGTH_KEYS
            )
            if window_errors:
                # Zero-span sun window (start == end) — re-render with the
                # user's values (the transient keys survived the failed apply).
                return self._show_sun_tracking_form(canonical, errors=window_errors)
            if pressed:
                # The button was ticked → re-render with the derived fov values
                # filled in and the toggle reset, for the user to edit/confirm.
                return self._show_sun_tracking_form(canonical)
            if (
                user_input.get(CONF_MAX_ELEVATION) is not None
                and user_input.get(CONF_MIN_ELEVATION) is not None
                and user_input[CONF_MAX_ELEVATION] <= user_input[CONF_MIN_ELEVATION]
            ):
                return self._show_sun_tracking_form(
                    canonical,
                    errors={
                        CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
                    },
                )
            self.config.update(canonical)
            # L1 physical setup complete → L2 positions.
            return await self.async_step_position()
        return self._show_sun_tracking_form(self.config)

    def _show_sun_tracking_form(
        self,
        values: dict[str, Any] | None = None,
        *,
        errors: dict | None = None,
    ):
        """Render the create-flow sun-tracking form."""
        schema = _get_sun_tracking_schema(self.type_blind, self.hass)
        suggested = _inject_sun_window_display(
            options_to_display(
                self.hass, values or self.config, length_keys=_SUN_TRACKING_LENGTH_KEYS
            )
        )
        return self.async_show_form(
            step_id="sun_tracking",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders=_sun_tracking_placeholders(
                self.type_blind, self.config
            ),
        )

    async def async_step_position(self, user_input: dict[str, Any] | None = None):
        """Configure position settings."""
        if user_input is not None:
            self.optional_entities(_POSITION_OPTIONAL_KEYS, user_input)
            self.config.update(user_input)
            # Quick setup: skip optional screens, go straight to summary
            # Condensed flow: position is the last create step — behavior and
            # every handler are configured later via the options menu.
            return await self.async_step_summary()
        return self.async_show_form(
            step_id="position",
            data_schema=POSITION_SCHEMA,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_behavior(self, user_input: dict[str, Any] | None = None):
        """Configure L2b timing & threshold behavior."""
        if user_input is not None:
            self.optional_entities(_BEHAVIOR_OPTIONAL_KEYS, user_input)
            self.config.update(user_input)
            # The L3 handler steps begin in pipeline-priority order (weather = 90).
            return await self.async_step_weather_override()
        return self.async_show_form(
            step_id="behavior",
            data_schema=_behavior_schema(self.config),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
                "position_matching_wiki": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_automation(self, user_input: dict[str, Any] | None = None):
        """Manage automation options."""
        if user_input is not None:
            self.optional_entities(
                [CONF_START_ENTITY, CONF_END_ENTITY, CONF_RESYNC_TRAVEL_THRESHOLD],
                user_input,
            )
            self.config.update(user_input)
            # L4 global motion constraints are the final config step → summary.
            return await self.async_step_summary()
        return self.async_show_form(
            step_id="automation",
            data_schema=AUTOMATION_SCHEMA,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_manual_override(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure manual override settings."""
        if user_input is not None:
            self.optional_entities([CONF_MANUAL_THRESHOLD], user_input)
            self.config.update(user_input)
            return await self.async_step_custom_position()
        return self.async_show_form(
            step_id="manual_override",
            data_schema=MANUAL_OVERRIDE_SCHEMA,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_custom_position(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure custom position sensors."""
        if user_input is not None:
            self.optional_entities(_CUSTOM_POSITION_OPTIONAL_KEYS, user_input)
            self.config.update(user_input)
            # Mirror on the merged dict so a cleared slot can null a stale
            # legacy key carried over from a copied/source entry.
            mirror_legacy_slot_sensor_keys(self.config)
            return await self.async_step_motion_override()
        schema = vol.Schema(
            _build_custom_position_schema_dict(sensor_type=self.type_blind)
        )
        return self.async_show_form(
            step_id="custom_position",
            data_schema=schema,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
                "priority_scale": _render_priority_scale(
                    self.config, get_policy(self.type_blind)
                ),
            },
        )

    async def async_step_motion_override(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure motion/occupancy-based control."""
        if user_input is not None:
            self.config.update(user_input)
            # L3 priority 75 → 60 (cloud / light).
            return await self.async_step_light_cloud()
        return self.async_show_form(
            step_id="motion_override",
            data_schema=MOTION_OVERRIDE_SCHEMA,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_weather_override(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure weather-based safety overrides."""
        if user_input is not None:
            self.optional_entities(_WEATHER_OVERRIDE_OPTIONAL_KEYS, user_input)
            self.config.update(user_input)
            # L3 priority 90 → 80 (manual override).
            return await self.async_step_manual_override()
        return self.async_show_form(
            step_id="weather_override",
            data_schema=weather_override_schema(self.hass, self.config),
            description_placeholders=_weather_override_placeholders(
                self.hass, self.config
            ),
        )

    async def async_step_light_cloud(self, user_input: dict[str, Any] | None = None):
        """Configure light sensors, weather conditions, and cloud suppression."""
        if user_input is not None:
            self.optional_entities(_LIGHT_CLOUD_OPTIONAL_KEYS, user_input)
            self.config.update(user_input)
            return await self.async_step_temperature_climate()
        return self.async_show_form(
            step_id="light_cloud",
            data_schema=light_cloud_schema(self.hass, self.config),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_temperature_climate(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure temperature-based climate mode."""
        if user_input is not None:
            self.optional_entities(_TEMPERATURE_CLIMATE_OPTIONAL_KEYS, user_input)
            if user_input.get(CONF_CLIMATE_MODE) and not user_input.get(
                CONF_TEMP_ENTITY
            ):
                return self.async_show_form(
                    step_id="temperature_climate",
                    data_schema=temperature_climate_schema(self.hass, user_input),
                    errors={CONF_TEMP_ENTITY: "Required when climate mode is enabled"},
                    description_placeholders={
                        "learn_more": "https://github.com/B4S71/adaptive-pergola"
                    },
                )
            self.config.update(user_input)
            # L3 priority 50 → L4 automation.
            return await self.async_step_automation()
        return self.async_show_form(
            step_id="temperature_climate",
            data_schema=temperature_climate_schema(self.hass, self.config),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None):
        """Manage weather conditions."""
        if user_input is not None:
            self.config.update(user_input)
            return await self.async_step_summary()
        return self.async_show_form(
            step_id="weather",
            data_schema=WEATHER_OPTIONS,
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_summary(self, user_input: dict[str, Any] | None = None):
        """Show a read-only summary of all collected configuration before creating the entry."""
        if user_input is not None:
            return await self.async_step_update()
        sun_times = await _compute_todays_sun_times(self.hass, self.config)
        labels = await _load_summary_labels(
            self.hass, self.context.get("language", "en")
        )
        summary_text = _build_config_summary(
            self.config, self.type_blind, self.hass, sun_times, labels=labels
        )
        return self.async_show_form(
            step_id="summary",
            data_schema=vol.Schema({}),
            description_placeholders={"summary": summary_text},
        )

    async def async_step_update(self, user_input: dict[str, Any] | None = None):
        """Create entry."""
        if self.type_blind is None:
            msg = "type_blind must be set before calling async_step_update"
            raise ValueError(msg)

        if self.config.pop("_title_is_device_name", False):
            title = self.config["name"]
        else:
            title = f"{_cover_type_label(self.type_blind)} {self.config['name']}"

        # Build options from the full accumulated config dict, mirroring the
        # options-flow contract (data=self.options).  Strip only the data-level
        # keys that belong in entry.data rather than entry.options; override
        # CONF_MODE (which holds the cover-type string in self.config) with the
        # strategy-mode value stored on self.mode.
        _DATA_KEYS = {"name", CONF_SENSOR_TYPE}
        options = {k: v for k, v in self.config.items() if k not in _DATA_KEYS}
        # CONF_MODE in self.config is the cover-type selector value (CoverType.*).
        # entry.options["mode"] must carry the strategy mode ("basic" / "advanced").
        options[CONF_MODE] = self.mode

        # The condensed flow skips some steps (e.g. automation) leaving critical
        # keys absent from self.config.  Apply constant-backed defaults so the
        # coordinator never receives None for gating values (issue #133).
        options.setdefault(CONF_DELTA_POSITION, DEFAULT_DELTA_POSITION)
        options.setdefault(CONF_DELTA_TIME, DEFAULT_DELTA_TIME)
        options.setdefault(
            CONF_MANUAL_OVERRIDE_DURATION, DEFAULT_MANUAL_OVERRIDE_DURATION
        )
        options.setdefault(CONF_MOTION_SENSORS, [])
        options.setdefault(CONF_MOTION_TIMEOUT, DEFAULT_MOTION_TIMEOUT)
        options.setdefault(
            CONF_ENABLE_POSITION_MATCHING, DEFAULT_ENABLE_POSITION_MATCHING
        )

        return self.async_create_entry(
            title=title,
            data={
                "name": self.config["name"],
                CONF_SENSOR_TYPE: self.type_blind,
            },
            options=options,
        )


class OptionsFlowHandler(OptionsFlow):
    """Options to adjust parameters."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self.current_config: dict = dict(config_entry.data)
        self.options = dict(config_entry.options)
        self.sensor_type: CoverType = (  # type: ignore[misc]
            self.current_config.get(CONF_SENSOR_TYPE) or CoverType.BLIND
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        # Ordered by the 4-layer pipeline model (#613): physical setup →
        # positions → handlers in priority order → global motion constraints.

        # ── Layer 1: What am I? (physical setup) ─────────────────────
        keys = [
            "cover_entities",
            "geometry",
            "sun_tracking",
        ]
        # Condensed flow (docs/CONFIG_FLOW_REWORK.md): the heritage
        # building-profile, blind-spot and interpolation steps were deleted
        # in stage 4.

        # ── Layer 2: Where can I go? / how do I behave? ──────────────
        keys.append("position")  # L2a positions (% values)
        keys.append("behavior")  # L2b timing & thresholds

        # ── Layer 3: How do I decide? (handlers, priority high → low) ─
        keys.extend(
            [
                "weather_override",  # Priority 90
                "manual_override",  # Priority 80
                "custom_position",  # Priority 1-100 per slot (100 = safety)
                "motion_override",  # Priority 75
                "light_cloud",  # Cloud suppression, priority 60
                "temperature_climate",  # Climate, priority 50
            ]
        )
        # Condensed flow: the heritage glare-zone and multi-cover sync steps
        # were deleted in stage 4.

        # Re-order the whole handler chain (built-in priority overrides).
        keys.append("pipeline_priorities")

        # ── Layer 4: How do I move? (global motion constraints) ──────
        keys.append("automation")

        # ── Admin ────────────────────────────────────────────────────
        keys.extend(["summary", "debug", "done"])

        # Use a list so HA translates labels client-side using the user's language preference.
        # Icons are embedded directly in each translation string (e.g. "🪟 Covers & Device").
        menu_options: list[str] = keys

        return self.async_show_menu(  # type: ignore[return-value]
            step_id="init",
            menu_options=menu_options,
            description_placeholders={
                "instance_name": self.config_entry.title,
            },
        )

    async def async_step_cover_entities(self, user_input: dict[str, Any] | None = None):
        """Adjust cover entities and device association on a single combined form."""
        entity_ids = self.options.get(CONF_ENTITIES, [])
        devices = await _get_devices_from_entities(self.hass, entity_ids)

        if user_input is not None:
            self.options.update(user_input)
            device_id = user_input.get(CONF_DEVICE_ID, _STANDALONE_SENTINEL)
            if device_id and device_id != _STANDALONE_SENTINEL:
                self.options[CONF_DEVICE_ID] = device_id
            else:
                self.options.pop(CONF_DEVICE_ID, None)
            return await self.async_step_init()

        current_device = self.options.get(CONF_DEVICE_ID) or _STANDALONE_SENTINEL
        schema = _build_cover_entity_schema(self.sensor_type, devices=devices or None)
        suggested = dict(self.options)
        if devices:
            suggested.setdefault(CONF_DEVICE_ID, current_device)
        return self.async_show_form(
            step_id="cover_entities",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_geometry(self, user_input: dict[str, Any] | None = None):
        """Adjust geometry parameters."""
        length_keys, slat_keys = _geometry_unit_keys(self.sensor_type)
        if user_input is not None:
            canonical = user_input_to_canonical(
                self.hass, user_input, length_keys=length_keys, slat_keys=slat_keys
            )
            self.options.update(canonical)
            return await self.async_step_init()

        schema = _get_geometry_schema(self.sensor_type, self.hass, self.options)
        suggested = options_to_display(
            self.hass,
            user_input or self.options,
            length_keys=length_keys,
            slat_keys=slat_keys,
        )
        return self.async_show_form(
            step_id="geometry",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            description_placeholders={
                "geometry_wiki_link": _geometry_wiki_link(self.sensor_type)
            },
        )

    async def async_step_sun_tracking(self, user_input: dict[str, Any] | None = None):
        """Adjust sun tracking parameters."""
        if user_input is not None:
            self.optional_entities([CONF_MIN_ELEVATION, CONF_MAX_ELEVATION], user_input)
            # Transient sun-window fields → canonical azimuth/fov keys, before
            # any canonicalisation/validation (docs/CONFIG_FLOW_REWORK.md, st. 2).
            # On a zero-span window the transient keys stay in *user_input* and
            # the form re-renders below with the field error.
            window_errors = _apply_sun_window_submit(user_input)
            pressed = _resolve_fov_compute_submit(
                self.sensor_type, user_input, self.options
            )
            # Canonicalize once: ``_show_sun_tracking_form`` re-displays via
            # ``options_to_display``, so feeding it raw (already display-unit)
            # input would convert metres->inches a second time and the value
            # would compound on every rerender (#565). Canonical here keeps the
            # rerender re-feed symmetric with the initial render and save path.
            canonical = user_input_to_canonical(
                self.hass, user_input, length_keys=_SUN_TRACKING_LENGTH_KEYS
            )
            if window_errors:
                # Zero-span sun window (start == end) — re-render with the
                # user's values (the transient keys survived the failed apply).
                return self._show_sun_tracking_form(canonical, errors=window_errors)
            if pressed:
                # The button was ticked → re-render with the derived fov values
                # filled in and the toggle reset, for the user to edit/confirm.
                return self._show_sun_tracking_form(canonical)
            if (
                user_input.get(CONF_MAX_ELEVATION) is not None
                and user_input.get(CONF_MIN_ELEVATION) is not None
                and user_input[CONF_MAX_ELEVATION] <= user_input[CONF_MIN_ELEVATION]
            ):
                return self._show_sun_tracking_form(
                    canonical,
                    errors={
                        CONF_MAX_ELEVATION: "Must be greater than 'Minimal Elevation'"
                    },
                )
            # Drop the legacy ``fov_mode`` key from entries created before the
            # button replaced the mode selector (#565) — it is inert and no
            # longer written.
            self.options.pop("fov_mode", None)
            self.options.update(canonical)
            return await self.async_step_init()
        return self._show_sun_tracking_form(self.options)

    def _show_sun_tracking_form(
        self,
        values: dict[str, Any],
        *,
        errors: dict | None = None,
    ):
        """Render the sun-tracking form."""
        schema = _get_sun_tracking_schema(self.sensor_type, self.hass)
        suggested = _inject_sun_window_display(
            options_to_display(self.hass, values, length_keys=_SUN_TRACKING_LENGTH_KEYS)
        )
        return self.async_show_form(
            step_id="sun_tracking",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders=_sun_tracking_placeholders(
                self.sensor_type, self.options
            ),
        )

    async def async_step_position(self, user_input: dict[str, Any] | None = None):
        """Adjust position settings."""
        if user_input is not None:
            self.optional_entities(_POSITION_OPTIONAL_KEYS, user_input)
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="position",
            data_schema=self.add_suggested_values_to_schema(
                POSITION_SCHEMA, user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_behavior(self, user_input: dict[str, Any] | None = None):
        """Manage L2b timing & threshold behavior options."""
        if user_input is not None:
            self.optional_entities(_BEHAVIOR_OPTIONAL_KEYS, user_input)
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="behavior",
            data_schema=self.add_suggested_values_to_schema(
                _behavior_schema(self.options), user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
                "position_matching_wiki": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_automation(self, user_input: dict[str, Any] | None = None):
        """Manage automation options."""
        if user_input is not None:
            self.optional_entities(
                [CONF_START_ENTITY, CONF_END_ENTITY, CONF_RESYNC_TRAVEL_THRESHOLD],
                user_input,
            )
            # A cleared TimeSelector either omits the key or coerces to the blank
            # sentinel "00:00:00". Treat both as "unset": drop the key from the
            # submission and from any previously-stored option so it never
            # persists as a literal midnight window (issue #492).
            for time_key in (CONF_START_TIME, CONF_END_TIME):
                if user_input.get(time_key) in (None, BLANK_TIME):
                    user_input.pop(time_key, None)
                    self.options.pop(time_key, None)
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="automation",
            data_schema=self.add_suggested_values_to_schema(
                AUTOMATION_SCHEMA, user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_manual_override(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage manual override options."""
        if user_input is not None:
            self.optional_entities([CONF_MANUAL_THRESHOLD], user_input)
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="manual_override",
            data_schema=self.add_suggested_values_to_schema(
                MANUAL_OVERRIDE_SCHEMA, user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_custom_position(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage custom position sensors."""
        if user_input is not None:
            self.optional_entities(_CUSTOM_POSITION_OPTIONAL_KEYS, user_input)
            self.options.update(user_input)
            # Mirror on the merged options so a cleared slot nulls its stale
            # legacy single-sensor key (rollback fidelity, issue #563).
            mirror_legacy_slot_sensor_keys(self.options)
            return await self.async_step_init()
        sensor_type = self._config_entry.data.get(CONF_SENSOR_TYPE)
        schema = vol.Schema(_build_custom_position_schema_dict(sensor_type=sensor_type))
        return self.async_show_form(
            step_id="custom_position",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
                "priority_scale": _render_priority_scale(
                    self.options, get_policy(sensor_type)
                ),
            },
        )

    async def async_step_motion_override(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage motion/occupancy-based control."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="motion_override",
            data_schema=self.add_suggested_values_to_schema(
                MOTION_OVERRIDE_SCHEMA, user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_weather_override(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage weather-based safety overrides."""
        if user_input is not None:
            # Profile-owned pickers are shown (inherit/override model), so they
            # are present in user_input; null any cleared field as usual.
            self.optional_entities(_WEATHER_OVERRIDE_OPTIONAL_KEYS, user_input)
            self.options.update(user_input)
            return await self.async_step_init()
        suggested = _stringify_templatable(self.options)
        placeholders = dict(_weather_override_placeholders(self.hass, self.options))
        return self.async_show_form(
            step_id="weather_override",
            data_schema=self.add_suggested_values_to_schema(
                weather_override_schema(self.hass, suggested), suggested
            ),
            description_placeholders=placeholders,
        )

    async def async_step_pipeline_priorities(
        self, user_input: dict[str, Any] | None = None
    ):
        """Re-order the built-in handler decision chain (priority overrides)."""
        if user_input is not None:
            # A cleared slider is omitted; null it so the handler reverts to its
            # class-default priority instead of keeping the stale override.
            self.optional_entities(_PIPELINE_PRIORITY_OPTIONAL_KEYS, user_input)
            self.options.update(user_input)
            return await self.async_step_init()
        sensor_type = self._config_entry.data.get(CONF_SENSOR_TYPE)
        return self.async_show_form(
            step_id="pipeline_priorities",
            data_schema=self.add_suggested_values_to_schema(
                config_fields.pipeline_priorities_schema(), user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
                "priority_scale": _render_priority_scale(
                    self.options, get_policy(sensor_type)
                ),
            },
        )

    async def async_step_light_cloud(self, user_input: dict[str, Any] | None = None):
        """Manage light sensors, weather conditions, and cloud suppression."""
        suggested = _stringify_templatable(user_input or self.options)
        if user_input is not None:
            self.optional_entities(_LIGHT_CLOUD_OPTIONAL_KEYS, user_input)
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="light_cloud",
            data_schema=self.add_suggested_values_to_schema(
                light_cloud_schema(self.hass, suggested), suggested
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_temperature_climate(
        self, user_input: dict[str, Any] | None = None
    ):
        """Manage temperature-based climate mode."""
        suggested = _stringify_templatable(user_input or self.options)
        if user_input is not None:
            self.optional_entities(_TEMPERATURE_CLIMATE_OPTIONAL_KEYS, user_input)
            if user_input.get(CONF_CLIMATE_MODE) and not user_input.get(
                CONF_TEMP_ENTITY
            ):
                return self.async_show_form(
                    step_id="temperature_climate",
                    data_schema=self.add_suggested_values_to_schema(
                        temperature_climate_schema(self.hass, suggested), suggested
                    ),
                    errors={CONF_TEMP_ENTITY: "Required when climate mode is enabled"},
                    description_placeholders={
                        "learn_more": "https://github.com/B4S71/adaptive-pergola",
                    },
                )
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="temperature_climate",
            data_schema=self.add_suggested_values_to_schema(
                temperature_climate_schema(self.hass, suggested), suggested
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_weather(self, user_input: dict[str, Any] | None = None):
        """Manage weather conditions."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="weather",
            data_schema=self.add_suggested_values_to_schema(
                WEATHER_OPTIONS, user_input or self.options
            ),
            description_placeholders={
                "learn_more": "https://github.com/B4S71/adaptive-pergola"
            },
        )

    async def async_step_summary(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show a read-only summary of the current configuration."""
        if user_input is not None:
            return await self.async_step_init()
        sun_times = await _compute_todays_sun_times(self.hass, self.options)
        labels = await _load_summary_labels(
            self.hass, self.context.get("language", "en")
        )
        summary_text = _build_config_summary(
            self.options, self.sensor_type, self.hass, sun_times, labels=labels
        )
        return self.async_show_form(
            step_id="summary",
            data_schema=vol.Schema({}),
            description_placeholders={"summary": summary_text},
        )

    async def async_step_debug(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Debug & Diagnostics options."""
        if user_input is not None:
            self.options.update(user_input)
            return await self.async_step_init()
        caps_text = _build_cover_capabilities_text(
            self.options, self.sensor_type, self.hass
        )
        return self.async_show_form(
            step_id="debug",
            data_schema=self.add_suggested_values_to_schema(
                DEBUG_SCHEMA, user_input or self.options
            ),
            description_placeholders={
                "cover_capabilities": caps_text,
                "learn_more": "https://github.com/B4S71/adaptive-pergola",
            },
        )

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Save and exit the options flow."""
        return await self._update_options()

    async def _update_options(self) -> FlowResult:
        """Update config entry options."""
        return self.async_create_entry(title="", data=self.options)  # type: ignore[return-value]

    def optional_entities(self, keys: list, user_input: dict[str, Any]):
        """Set value to None if key does not exist."""
        for key in keys:
            if key not in user_input:
                user_input[key] = None
