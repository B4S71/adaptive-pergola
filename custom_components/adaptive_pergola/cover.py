"""Opt-in proxy cover platform for Adaptive Pergola.

When ``CONF_ENABLE_PROXY_COVER`` is True, one ``AdaptiveProxyCover`` entity is
created per source cover in ``CONF_ENTITIES``. The proxy mirrors source state
verbatim (no inverse-state transform) and routes user commands through
``Coordinator.async_apply_user_position`` so min-mode custom-position floors
are honoured. ``stop_cover`` forwards directly to the source.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import slugify

from .const import (
    CONF_ENABLE_PROXY_COVER,
    CONF_ENTITIES,
    DEFAULT_ENABLE_PROXY_COVER,
    TRIGGER_PROXY_CLOSE,
    TRIGGER_PROXY_OPEN,
    TRIGGER_PROXY_POSITION,
    TRIGGER_PROXY_TILT,
)
from .cover_types.base import (
    CAP_HAS_SET_TILT_POSITION,
    STATE_ATTR_POSITION,
    STATE_ATTR_TILT_POSITION,
    caps_get,
)
from .entity_base import _SENTINEL, AdaptivePergolaBaseEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import Event, HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AdaptiveConfigEntry, AdaptiveDataUpdateCoordinator


_LOGGER = logging.getLogger(__name__)

# Position-driven slat icons served by frontend.py. Each stop is a tilt
# percentage whose glyph is drawn at the matching louvred-roof angle along the
# pergola's non-linear travel curve (0/15/50/75/100 % -> 0/18/60/90/135 deg).
# The mirrored tilt position snaps to the nearest stop.
_SLAT_ICON_STOPS = (0, 15, 50, 75, 100)


def _slat_icon_for_tilt(tilt: int) -> str:
    """Return the ``acp`` iconset name for the nearest slat-position stop."""
    nearest = min(_SLAT_ICON_STOPS, key=lambda stop: abs(stop - tilt))
    return f"acp:pergola-slats-{nearest}"


# Safety net for the synthesized opening/closing feedback: if the source never
# publishes a settling update (Somfy IO via Tahoma can drop the post-move state),
# clear the moving indicator after this many seconds so the entity can't get
# stuck showing "opening"/"closing". Tilt moves complete in well under this.
_MOVE_FEEDBACK_TIMEOUT = 40
# Tolerance (in tilt %) for treating a source update as "arrived at target".
_MOVE_ARRIVE_TOLERANCE = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdaptiveConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up proxy cover entities for an ACP config entry."""
    if not entry.options.get(CONF_ENABLE_PROXY_COVER, DEFAULT_ENABLE_PROXY_COVER):
        return

    sources: list[str] = list(entry.options.get(CONF_ENTITIES) or [])
    if not sources:
        return

    coordinator: AdaptiveDataUpdateCoordinator = entry.runtime_data
    multi = len(sources) > 1

    entities: list[AdaptiveProxyCover] = [
        AdaptiveProxyCover(
            entry_id=entry.entry_id,
            hass=hass,
            config_entry=entry,
            coordinator=coordinator,
            source_entity_id=src,
            multi=multi,
        )
        for src in sources
    ]
    async_add_entities(entities)


def _source_friendly_label(hass: HomeAssistant, entity_id: str) -> str:
    """Return a human label for a source entity_id (registry > object_id)."""
    reg = er.async_get(hass)
    entry = reg.async_get(entity_id)
    if entry and (entry.original_name or entry.name):
        return entry.name or entry.original_name
    state = hass.states.get(entity_id)
    if state is not None:
        friendly = state.attributes.get("friendly_name")
        if friendly:
            return friendly
    return entity_id.split(".", 1)[-1].replace("_", " ").title()


class AdaptiveProxyCover(AdaptivePergolaBaseEntity, CoverEntity):
    """Proxy cover that mirrors a source and routes commands through ACP."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        *,
        entry_id: str,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinator: AdaptiveDataUpdateCoordinator,
        source_entity_id: str,
        multi: bool,
    ) -> None:
        """Initialise a proxy cover bound to ``source_entity_id``."""
        super().__init__(entry_id, hass, config_entry, coordinator)
        self._source_entity_id = source_entity_id
        self._attr_unique_id = f"{entry_id}_proxy_{slugify(source_entity_id)}"
        title = config_entry.title or config_entry.data.get("name") or "Adaptive"
        if multi:
            label = _source_friendly_label(hass, source_entity_id)
            self._attr_name = f"{title} Managed ({label})"
        else:
            self._attr_name = f"{title} Managed"
        # Render signature of the last source-mirror write. Kept separate from
        # the base-class coordinator-update gate because the proxy renders from
        # source state, not coordinator.data — the two write paths must not
        # share one cache field.
        self._proxy_source_sig: object = _SENTINEL
        # Synthesized movement feedback. The Somfy IO source reports
        # opening/closing only intermittently (and briefly), so a user command
        # issued on the proxy often shows no motion at all. When we dispatch a
        # command we drive these ourselves until the source settles.
        self._move_dir: str | None = None  # "opening" | "closing" | None
        self._move_target: int | None = None
        self._move_start_tilt: int | None = None
        self._move_unsub: Any = None

    # ---- availability + mirroring -------------------------------------- #

    def _source_state(self) -> Any:
        """Return the current HA state object for the source entity, or None."""
        return self.hass.states.get(self._source_entity_id)

    @property
    def available(self) -> bool:
        """Mirror source availability."""
        state = self._source_state()
        if state is None:
            return False
        return state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    @property
    def is_opening(self) -> bool:
        """True while the slats are opening (synthesized command feedback or source)."""
        if self._move_dir == "opening":
            return True
        state = self._source_state()
        return state is not None and state.state == CoverState.OPENING

    @property
    def is_closing(self) -> bool:
        """True while the slats are closing (synthesized command feedback or source)."""
        if self._move_dir == "closing":
            return True
        state = self._source_state()
        return state is not None and state.state == CoverState.CLOSING

    @property
    def current_cover_position(self) -> int | None:
        """Mirror source current_position verbatim (no inverse transform)."""
        state = self._source_state()
        if state is None:
            return None
        value = state.attributes.get(STATE_ATTR_POSITION)
        return int(value) if value is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Mirror source current_tilt_position verbatim."""
        state = self._source_state()
        if state is None:
            return None
        value = state.attributes.get(STATE_ATTR_TILT_POSITION)
        return int(value) if value is not None else None

    @property
    def icon(self) -> str | None:
        """Position-aware slat icon for tilt-capable (louvred-roof) sources.

        A source that reports a tilt axis is a bioclimatic-pergola slat set
        (``io:SimpleBioclimaticPergolaIOComponent`` and kin), so map the
        mirrored tilt onto one of five custom ``acp:pergola-slats-*`` glyphs.
        Non-tilt covers return None and keep Home Assistant's default icon.
        """
        tilt = self.current_cover_tilt_position
        if tilt is None:
            return None
        return _slat_icon_for_tilt(tilt)

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Advertised features, remapped for tilt-only sources.

        A bioclimatic-pergola source is tilt-only (``open/close/stop_cover_tilt``
        + ``set_cover_tilt_position``, no position axis). Home Assistant's cover
        card then issues ``cover.open_cover`` / ``close_cover`` / ``stop_cover``
        for the main buttons — which such a source rejects as unsupported, so the
        open/close/stop buttons do nothing. Present those position buttons (they
        route onto the slat/tilt axis via the policy) plus the tilt slider, so
        the standard controls all operate the slats. Position-capable sources are
        mirrored verbatim.
        """
        state = self._source_state()
        if state is None:
            return CoverEntityFeature(0)
        raw = CoverEntityFeature(int(state.attributes.get("supported_features", 0)))
        if raw & CoverEntityFeature.SET_TILT_POSITION and not (
            raw & CoverEntityFeature.SET_POSITION
        ):
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_TILT_POSITION
            )
        return raw

    @property
    def is_closed(self) -> bool | None:
        """Whether the cover is fully closed.

        Position-capable sources decide by ``current_position`` (0 = closed).
        Tilt-only sources — e.g. a bioclimatic-pergola slat set
        (``io:SimpleBioclimaticPergolaIOComponent``), which exposes an
        orientation/tilt axis and no position — have no position to read, so
        fall back to the source's own open/closed state and then to the
        mirrored tilt (0 = closed). Without this a tilt-only cover reports
        ``None`` and Home Assistant renders the entity state as ``unknown``.
        """
        pos = self.current_cover_position
        if pos is not None:
            return pos == 0
        state = self._source_state()
        if state is not None:
            if state.state == CoverState.CLOSED:
                return True
            if state.state == CoverState.OPEN:
                return False
        tilt = self.current_cover_tilt_position
        if tilt is not None:
            return tilt == 0
        return None

    # ---- synthesized movement feedback -------------------------------- #

    @callback
    def _begin_move(self, target: int) -> None:
        """Show opening/closing immediately for a proxy-issued command.

        The source publishes transitional states unreliably, so derive the
        direction from the requested target vs the current tilt and drive the
        indicator ourselves until the source settles or the safety timer fires.
        """
        current = self.current_cover_tilt_position
        if current is None or target == current:
            return
        self._move_dir = "opening" if target > current else "closing"
        self._move_target = target
        self._move_start_tilt = current
        if self._move_unsub is not None:
            self._move_unsub()
        self._move_unsub = async_call_later(
            self.hass, _MOVE_FEEDBACK_TIMEOUT, self._end_move
        )
        self.async_write_ha_state()

    @callback
    def _end_move(self, _now: Any = None) -> None:
        """Clear the synthesized movement indicator and write state."""
        was_moving = self._move_dir is not None
        self._move_dir = None
        self._move_target = None
        self._move_start_tilt = None
        if self._move_unsub is not None:
            self._move_unsub()
            self._move_unsub = None
        if was_moving:
            self.async_write_ha_state()

    @callback
    def _maybe_finish_move(self) -> None:
        """Clear synthesized movement once the source has settled at/after target."""
        if self._move_dir is None:
            return
        state = self._source_state()
        if state is None:
            return
        # Source says it is still physically moving — keep the indicator.
        if state.state in (CoverState.OPENING, CoverState.CLOSING):
            return
        tilt = self.current_cover_tilt_position
        if tilt is None:
            self._end_move()
            return
        reached = (
            self._move_target is not None
            and abs(tilt - self._move_target) <= _MOVE_ARRIVE_TOLERANCE
        )
        moved = self._move_start_tilt is not None and tilt != self._move_start_tilt
        if reached or moved:
            self._end_move()

    async def async_added_to_hass(self) -> None:
        """Subscribe to source state changes once mounted."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._handle_source_event,
            )
        )
        self.async_on_remove(self._cancel_move_timer)

    @callback
    def _cancel_move_timer(self) -> None:
        """Cancel the pending movement-feedback timeout, if any (on teardown)."""
        if self._move_unsub is not None:
            self._move_unsub()
            self._move_unsub = None

    @callback
    def _handle_source_event(self, event: Event) -> None:
        """Mirror the source cover, skipping writes that carry no new state.

        Rapid OPENING/CLOSING intermediate events often repeat the same
        observable state; writing each one floods HA with no-op updates. Gate on
        the rendered surface (state flags, position, tilt, supported features).
        Fails open so a comparison error can never stall the mirror.
        """
        # A settling source update ends any synthesized movement indicator
        # first, so the gate below sees the post-move opening/closing flags.
        self._maybe_finish_move()
        try:
            sig = (
                self.available,
                self.is_opening,
                self.is_closing,
                self.current_cover_position,
                self.current_cover_tilt_position,
                int(self.supported_features),
                self._move_dir,
            )
        except Exception:  # noqa: BLE001 - never let a signature error suppress a write
            self._proxy_source_sig = _SENTINEL
            self.async_write_ha_state()
            return
        if sig == self._proxy_source_sig:
            return
        self._proxy_source_sig = sig
        self.async_write_ha_state()

    # ---- command routing ---------------------------------------------- #

    def _source_available(self) -> bool:
        state = self.hass.states.get(self._source_entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug(
                "proxy %s: source %s unavailable — dropping command",
                self.entity_id,
                self._source_entity_id,
            )
            return False
        return True

    def _source_caps(self) -> dict[str, bool]:
        feats = int(self.supported_features)
        return {
            "has_set_position": bool(feats & CoverEntityFeature.SET_POSITION),
            "has_set_tilt_position": bool(feats & CoverEntityFeature.SET_TILT_POSITION),
            "has_open": bool(feats & CoverEntityFeature.OPEN),
            "has_close": bool(feats & CoverEntityFeature.CLOSE),
            "has_stop": bool(feats & CoverEntityFeature.STOP),
        }

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Route slider position via the floor-clamping helper."""
        if not self._source_available():
            return
        position = int(kwargs["position"])
        await self.coordinator.async_apply_user_position(
            self._source_entity_id, position, trigger=TRIGGER_PROXY_POSITION
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open command routed through the helper as position=100."""
        if not self._source_available():
            return
        self._begin_move(100)
        result = await self.coordinator.async_apply_user_position(
            self._source_entity_id, 100, trigger=TRIGGER_PROXY_OPEN
        )
        self._end_move_if_skipped(result)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close command routed through the helper (clamp applies intentionally)."""
        if not self._source_available():
            return
        self._begin_move(0)
        result = await self.coordinator.async_apply_user_position(
            self._source_entity_id, 0, trigger=TRIGGER_PROXY_CLOSE
        )
        self._end_move_if_skipped(result)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Route the requested tilt onto the dedicated tilt axis (issue #684).

        Dual-axis covers (venetian) must move only the slats — routing a tilt
        through ``async_apply_user_position`` previously drove the carriage to
        the requested value and left the slats untouched. ``async_apply_user_tilt``
        dispatches through the cover-type policy so the carriage stays put.
        """
        if not self._source_available():
            return
        if not caps_get(self._source_caps(), CAP_HAS_SET_TILT_POSITION):
            return
        tilt = int(kwargs["tilt_position"])
        self._begin_move(tilt)
        result = await self.coordinator.async_apply_user_tilt(
            self._source_entity_id, tilt, trigger=TRIGGER_PROXY_TILT
        )
        self._end_move_if_skipped(result)

    def _end_move_if_skipped(self, result: Any) -> None:
        """Back out the movement indicator when the pipeline preempted the move.

        ``async_apply_user_*`` returns ``("skipped", reason)`` when a
        higher-priority handler wins and no command is dispatched; nothing will
        physically move, so drop the synthesized opening/closing at once.
        """
        if isinstance(result, tuple) and result and result[0] == "skipped":
            self._end_move()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop forwards directly to the source (no clamp).

        Uses whichever stop the source actually exposes: ``stop_cover`` on a
        position-capable source, else ``stop_cover_tilt`` on a tilt-only
        bioclimatic pergola (which has no ``stop_cover``).
        """
        state = self._source_state()
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        self._end_move()
        raw = int(state.attributes.get("supported_features", 0))
        if raw & CoverEntityFeature.STOP:
            service = "stop_cover"
        elif raw & CoverEntityFeature.STOP_TILT:
            service = "stop_cover_tilt"
        else:
            return
        await self.hass.services.async_call(
            "cover",
            service,
            {ATTR_ENTITY_ID: self._source_entity_id},
            blocking=False,
        )
