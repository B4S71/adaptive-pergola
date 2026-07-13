"""Test-only stand-in policies for the cover types removed in the pergola split.

Adaptive Pergola ships only the louvered-roof policy (plus the virtual
Building Profile), but the test suite inherited from Adaptive Cover Pro
exercises the SHARED infrastructure — coordinator cycle, cover-command
service, manual-override detection, pipeline handlers — through configs
that say ``cover_blind`` / ``cover_awning`` / ``cover_tilt``. That coverage
is still valuable here: the same shared code paths ship in this integration.

These compat policies reproduce just enough of the removed policies (axes,
calc-engine dispatch, glare-zone support) for those tests to keep meaning
what they meant upstream. They are registered into ``POLICY_REGISTRY`` at
conftest import — i.e. in TESTS ONLY, never in the shipped integration.

They carry just enough config-flow surface (geometry schemas, unit keys,
disallowed-field lists) for the SHARED create/options-flow machinery tests
to walk their steps. Behavioural tests of the removed types themselves were
deleted in the split; the production registry test pins that the shipped
integration registers only the pergola types.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

import voluptuous as vol
from homeassistant.helpers import selector

from custom_components.adaptive_pergola.const import (
    CONF_AWNING_ANGLE,
    CONF_HEIGHT_WIN,
    CONF_LENGTH_AWNING,
    CONF_SILL_HEIGHT,
    CONF_TILT_DEPTH,
    CONF_TILT_DISTANCE,
    CONF_TILT_MODE,
    CONF_WINDOW_DEPTH,
    CONF_WINDOW_WIDTH,
    DEFAULT_AWNING_LENGTH,
    DEFAULT_WINDOW_HEIGHT,
    MAX_AWNING_ANGLE,
    MAX_WINDOW_DEPTH,
)
from custom_components.adaptive_pergola.cover_types._summary_labels import (
    COVER_TYPE_LABELS_EN,
)
from custom_components.adaptive_pergola.cover_types._tilt_math import (
    TILT_CAPABLE_ENTITY_FILTER,
)
from custom_components.adaptive_pergola.unit_system import (
    length_default,
    length_selector,
    slat_default,
    slat_selector,
)
from custom_components.adaptive_pergola.cover_types.base import (
    POSITION_AXIS,
    POSITION_AXIS_OPEN_BLOCKS_SUN,
    TILT_AXIS,
    CoverAxis,
    CoverTypePolicy,
)
from custom_components.adaptive_pergola.engine.covers import (
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.adaptive_pergola.engine.covers import (
        AdaptiveGeneralCover,
    )


# Geometry schemas ported verbatim from the removed policies so create/options
# flow tests that walk the geometry step with window/awning/slat inputs keep
# working. Keys whose stored value is canonical metres / centimetres are
# listed per policy in ``geometry_length_keys`` / ``geometry_slat_keys``.
VERTICAL_LENGTH_KEYS: tuple[str, ...] = (
    CONF_HEIGHT_WIN,
    CONF_WINDOW_WIDTH,
    CONF_WINDOW_DEPTH,
    CONF_SILL_HEIGHT,
)
HORIZONTAL_LENGTH_KEYS: tuple[str, ...] = (CONF_LENGTH_AWNING, CONF_HEIGHT_WIN)
TILT_SLAT_KEYS: tuple[str, ...] = (CONF_TILT_DEPTH, CONF_TILT_DISTANCE)


def geometry_vertical_schema(hass: HomeAssistant | None = None) -> vol.Schema:
    """Vertical-blind geometry schema. ``hass=None`` → metric labels."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HEIGHT_WIN,
                default=length_default(DEFAULT_WINDOW_HEIGHT, hass),
            ): length_selector(hass, min_m=0.1, max_m=50, metric_step=0.01),
            vol.Optional(
                CONF_WINDOW_WIDTH, default=length_default(1.0, hass)
            ): length_selector(hass, min_m=0.1, max_m=50, metric_step=0.01),
            vol.Optional(
                CONF_WINDOW_DEPTH, default=length_default(0.0, hass)
            ): length_selector(
                hass,
                min_m=0.0,
                max_m=MAX_WINDOW_DEPTH,
                metric_step=0.01,
                mode=selector.NumberSelectorMode.SLIDER,
            ),
            vol.Optional(
                CONF_SILL_HEIGHT, default=length_default(0.0, hass)
            ): length_selector(hass, min_m=0.0, max_m=50, metric_step=0.01),
        }
    )


GEOMETRY_VERTICAL_SCHEMA = geometry_vertical_schema()


def geometry_horizontal_schema(hass: HomeAssistant | None = None) -> vol.Schema:
    """Horizontal-awning geometry schema. ``hass=None`` → metric labels."""
    return vol.Schema(
        {
            vol.Required(
                CONF_LENGTH_AWNING, default=length_default(DEFAULT_AWNING_LENGTH, hass)
            ): length_selector(
                hass,
                min_m=0.3,
                max_m=6,
                metric_step=0.01,
                mode=selector.NumberSelectorMode.SLIDER,
            ),
            vol.Required(CONF_AWNING_ANGLE, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=MAX_AWNING_ANGLE,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="°",
                )
            ),
            vol.Required(
                CONF_HEIGHT_WIN, default=length_default(DEFAULT_WINDOW_HEIGHT, hass)
            ): length_selector(hass, min_m=0.1, max_m=50, metric_step=0.01),
        }
    )


GEOMETRY_HORIZONTAL_SCHEMA = geometry_horizontal_schema()


def geometry_tilt_schema(hass: HomeAssistant | None = None) -> vol.Schema:
    """Tilt-only geometry schema. ``hass=None`` → metric labels."""
    return vol.Schema(
        {
            vol.Required(
                CONF_TILT_DEPTH, default=slat_default(3.0, hass)
            ): slat_selector(hass, min_cm=0.1, max_cm=15),
            vol.Required(
                CONF_TILT_DISTANCE, default=slat_default(2.0, hass)
            ): slat_selector(hass, min_cm=0.1, max_cm=15),
            vol.Required(CONF_TILT_MODE, default="mode2"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["mode1", "mode2"], translation_key="tilt_mode"
                )
            ),
        }
    )


GEOMETRY_TILT_SCHEMA = geometry_tilt_schema()


class CompatBlindPolicy(CoverTypePolicy, register=True):
    """Vertical-blind stand-in — mirrors the removed ``BlindPolicy``."""

    cover_type = "cover_blind"
    axes: ClassVar[tuple[CoverAxis, ...]] = (POSITION_AXIS,)
    supports_glare_zones = True
    supports_return_to_default_switch = True
    supports_fov_compute = True

    def wiki_anchor(self) -> str:
        """Vertical-blind geometry page."""
        return "Configuration-Vertical"

    def display_label(self, labels: dict[str, str] | None = None) -> str:
        """User-facing label for vertical blinds."""
        L = {**COVER_TYPE_LABELS_EN, **(labels or {})}
        return L["cover_types.blind"]

    def disallowed_geometry_fields(
        self,
        *,
        vertical_only: set[str],
        awning_only: set[str],
        tilt_only: set[str],
    ) -> list[tuple[set[str], str]]:
        """Reject awning and tilt geometry fields on a vertical blind."""
        return [(awning_only, "awning"), (tilt_only, "tilt")]

    def geometry_schema(
        self,
        hass: HomeAssistant | None = None,
        options: dict | None = None,  # noqa: ARG002
    ) -> vol.Schema:
        """Return the vertical-blind geometry schema for the given locale."""
        if hass is None:
            return GEOMETRY_VERTICAL_SCHEMA
        return geometry_vertical_schema(hass)

    def geometry_length_keys(self) -> tuple[str, ...]:
        """Vertical blinds store four window dimensions in canonical metres."""
        return VERTICAL_LENGTH_KEYS

    def glare_zones_config(self, config_service, options: dict):
        """Return the glare-zones config for this cover (vertical-only feature)."""
        return config_service.get_glare_zones_config(options)

    def lift_travel_metres(self, config_service, options: dict) -> float | None:
        """Vertical blinds travel the configured window height."""
        return config_service.get_vertical_data(options).h_win

    def build_calc_engine(
        self,
        *,
        logger,
        sol_azi: float,
        sol_elev: float,
        sun_data,
        config,
        config_service,
        options: dict,
    ) -> AdaptiveGeneralCover:
        """Build an ``AdaptiveVerticalCover``, threading glare zones if any."""
        vert_config = config_service.get_vertical_data(options)
        glare_zones_cfg = config_service.get_glare_zones_config(options)
        if glare_zones_cfg is not None:
            vert_config = replace(vert_config, glare_zones=glare_zones_cfg)
        return AdaptiveVerticalCover(
            logger=logger,
            sol_azi=sol_azi,
            sol_elev=sol_elev,
            sun_data=sun_data,
            config=config,
            vert_config=vert_config,
        )


class CompatAwningPolicy(CoverTypePolicy, register=True):
    """Horizontal-awning stand-in — mirrors the removed ``AwningPolicy``."""

    cover_type = "cover_awning"
    axes: ClassVar[tuple[CoverAxis, ...]] = (POSITION_AXIS_OPEN_BLOCKS_SUN,)
    supports_return_to_default_switch = True

    def wiki_anchor(self) -> str:
        """Horizontal-awning geometry page."""
        return "Configuration-Horizontal"

    def display_label(self, labels: dict[str, str] | None = None) -> str:
        """User-facing label for horizontal awnings."""
        L = {**COVER_TYPE_LABELS_EN, **(labels or {})}
        return L["cover_types.awning"]

    def disallowed_geometry_fields(
        self,
        *,
        vertical_only: set[str],
        awning_only: set[str],
        tilt_only: set[str],
    ) -> list[tuple[set[str], str]]:
        """Reject vertical-blind and tilt geometry fields on an awning cover."""
        return [(vertical_only, "vertical blind"), (tilt_only, "tilt")]

    def geometry_schema(
        self,
        hass: HomeAssistant | None = None,
        options: dict | None = None,  # noqa: ARG002
    ) -> vol.Schema:
        """Return the horizontal-awning geometry schema for the given locale."""
        if hass is None:
            return GEOMETRY_HORIZONTAL_SCHEMA
        return geometry_horizontal_schema(hass)

    def geometry_length_keys(self) -> tuple[str, ...]:
        """Awnings store awning length and window height in canonical metres."""
        return HORIZONTAL_LENGTH_KEYS

    def lift_travel_metres(self, config_service, options: dict) -> float | None:
        """Awnings travel their configured extension length."""
        return config_service.get_horizontal_data(options).awn_length

    def build_calc_engine(
        self,
        *,
        logger,
        sol_azi: float,
        sol_elev: float,
        sun_data,
        config,
        config_service,
        options: dict,
    ) -> AdaptiveGeneralCover:
        """Build an ``AdaptiveHorizontalCover`` for in/out awning geometry."""
        return AdaptiveHorizontalCover(
            logger=logger,
            sol_azi=sol_azi,
            sol_elev=sol_elev,
            sun_data=sun_data,
            config=config,
            vert_config=config_service.get_vertical_data(options),
            horiz_config=config_service.get_horizontal_data(options),
        )


class CompatTiltPolicy(CoverTypePolicy, register=True):
    """Tilt-only stand-in — mirrors the removed ``TiltPolicy``."""

    cover_type = "cover_tilt"
    axes: ClassVar[tuple[CoverAxis, ...]] = (TILT_AXIS,)

    def wiki_anchor(self) -> str:
        """Slat-tilt geometry page."""
        return "Configuration-Tilt"

    def display_label(self, labels: dict[str, str] | None = None) -> str:
        """User-facing label for tilt-only covers."""
        L = {**COVER_TYPE_LABELS_EN, **(labels or {})}
        return L["cover_types.tilt"]

    def disallowed_geometry_fields(
        self,
        *,
        vertical_only: set[str],
        awning_only: set[str],
        tilt_only: set[str],
    ) -> list[tuple[set[str], str]]:
        """Reject vertical-blind and awning geometry fields on a tilt cover."""
        return [(vertical_only, "vertical blind"), (awning_only, "awning")]

    def geometry_schema(
        self,
        hass: HomeAssistant | None = None,
        options: dict | None = None,  # noqa: ARG002
    ) -> vol.Schema:
        """Return the slat-tilt geometry schema for the given locale."""
        if hass is None:
            return GEOMETRY_TILT_SCHEMA
        return geometry_tilt_schema(hass)

    def geometry_slat_keys(self) -> tuple[str, ...]:
        """Tilt covers store slat depth/spacing in canonical centimetres."""
        return TILT_SLAT_KEYS

    def entity_selector_filter(self) -> selector.EntityFilterSelectorConfig:
        """Tilt covers require ``set_tilt_position`` on the bound entity."""
        return TILT_CAPABLE_ENTITY_FILTER

    def build_calc_engine(
        self,
        *,
        logger,
        sol_azi: float,
        sol_elev: float,
        sun_data,
        config,
        config_service,
        options: dict,
    ) -> AdaptiveGeneralCover:
        """Build an ``AdaptiveTiltCover`` for slat-only covers."""
        return AdaptiveTiltCover(
            logger=logger,
            sol_azi=sol_azi,
            sol_elev=sol_elev,
            sun_data=sun_data,
            config=config,
            tilt_config=config_service.get_tilt_data(options),
        )
