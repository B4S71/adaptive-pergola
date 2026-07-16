"""Diagnostics package for Adaptive Pergola."""

from __future__ import annotations

import datetime as dt

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import (
    CONF_DAYTIME_GATE_SENSORS,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_FORCE_OVERRIDE_SENSORS,
    CONF_MANUAL_OVERRIDE_INPUT_ENTITIES,
    CONF_MOTION_MEDIA_PLAYERS,
    CONF_MOTION_SENSORS,
    CONF_PRESENCE_ENTITY,
    CUSTOM_POSITION_SLOTS,
)
from .builder import DiagnosticContext, DiagnosticsBuilder

__all__ = [
    "DiagnosticContext",
    "DiagnosticsBuilder",
    "async_get_config_entry_diagnostics",
]


def _build_redaction_keys() -> frozenset[str]:
    """Config-option keys withheld from the diagnostics download.

    HA diagnostics are routinely pasted into public GitHub issues, so anything
    that identifies household members or their movements is redacted (ACP-006):

    * entities that name people or track presence/occupancy,
    * every custom-position slot's trigger sensors,
    * every ``*_template`` field — user Jinja that can embed URLs or tokens,
    * the user-chosen ``name`` (e.g. "Kids Room").

    Coordinates are never emitted directly, but note they remain *derivable*
    from the exact sunrise/sunset and sun-vector values elsewhere in the dump;
    coarsening those is a separate change.
    """
    keys = {
        "name",
        # user_id / context id carried by manual-override events (ACP-007).
        "context_user_id",
        "context_id",
        CONF_PRESENCE_ENTITY,
        CONF_MOTION_SENSORS,
        CONF_MOTION_MEDIA_PLAYERS,
        CONF_ENTITIES,
        CONF_MANUAL_OVERRIDE_INPUT_ENTITIES,
        CONF_DAYTIME_GATE_SENSORS,
        CONF_FORCE_OVERRIDE_SENSORS,
        CONF_DEVICE_ID,
    }
    # Per-slot custom-position trigger sensors + condition templates.
    for slot in CUSTOM_POSITION_SLOTS.values():
        keys.add(slot["sensor"])
        keys.add(slot["sensors"])
        keys.add(slot["template"])
    # Every remaining templatable field — presence/is-sunny/weather/motion/
    # daytime-gate condition templates. These are raw user Jinja.
    from .. import const  # noqa: PLC0415

    for name in dir(const):
        if name.startswith("CONF_") and name.endswith("_TEMPLATE"):
            keys.add(getattr(const, name))
    return frozenset(keys)


TO_REDACT: frozenset[str] = _build_redaction_keys()


def _jsonify(obj):
    """Recursively convert non-JSON-serializable types to serializable equivalents.

    This is a *type* conversion (datetime → isoformat, enum → value, numpy →
    .item()), NOT a privacy control — it redacts nothing. The name matters:
    ``_sanitize`` read like a redaction step during review, which it never was.
    Redaction is ``async_redact_data(..., TO_REDACT)`` at the call sites.
    """
    import dataclasses  # noqa: PLC0415
    import enum  # noqa: PLC0415

    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_jsonify(v) for v in obj]
    if isinstance(obj, set | frozenset):
        return sorted(_jsonify(v) for v in obj)
    if isinstance(obj, dt.datetime | dt.date | dt.time):
        return obj.isoformat()
    if isinstance(obj, enum.Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _jsonify(dataclasses.asdict(obj))
    # numpy scalars (numpy not imported at module level — check by duck-typing)
    if hasattr(obj, "item") and hasattr(obj, "dtype"):
        return obj.item()
    return obj


# Backwards-compatible alias: _sanitize was the historical name. Kept so the
# diagnostics service and existing tests keep importing it; new code uses
# _jsonify, which no longer reads as a privacy control.
_sanitize = _jsonify


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
):
    """Return config entry diagnostics."""
    from custom_components.adaptive_pergola.const import (
        DIAG_CACHE_KEY,
    )  # noqa: PLC0415

    # The coordinator lives on entry.runtime_data (the registry every platform
    # reads). Virtual Building-Profile entries have no coordinator, so this is
    # legitimately None for them.
    coordinator = getattr(config_entry, "runtime_data", None)
    if coordinator is not None:
        if coordinator.data is None:
            # Diagnostics requested before the first completed update cycle (e.g.
            # right after a restart/reload). Trigger one refresh so the download
            # captures a full snapshot instead of an empty marker. Scoped to the
            # data-is-None case, so a normal download (data already present) never
            # triggers an extra update cycle or cover commands.
            await coordinator.async_refresh()

        if coordinator.data is not None:
            coordinator_diagnostics = _sanitize(coordinator.data.diagnostics)
        else:
            # The refresh did not yield data (first cycle still failing). Surface
            # an explicit marker (not a bare None) and include the event buffer so
            # there is still a timeline to triage from.
            marker = {
                "status": "unavailable",
                "reason": "no completed update cycle yet — coordinator.data is None",
            }
            event_buffer = getattr(coordinator, "_event_buffer", None)
            if event_buffer is not None:
                timeline = _sanitize(event_buffer.snapshot())
                marker["event_timeline"] = timeline
                marker["data_window"] = DiagnosticsBuilder._compute_data_window(
                    timeline
                )
            coordinator_diagnostics = marker
    else:
        # No live coordinator — typically a reload window (entry.runtime_data is
        # briefly unset) or a not-yet-loaded entry. Fall back to the last-good
        # snapshot cached in hass.data so the download is still useful, annotated
        # as stale so the reader knows it is not live.
        cached = hass.data.get(DIAG_CACHE_KEY, {}).get(config_entry.entry_id)
        if cached is not None:
            snapshot = _sanitize(cached["diagnostics"])
            age_seconds = (dt.datetime.now(dt.UTC) - cached["ts"]).total_seconds()
            cache_status = {
                "stale": True,
                "captured_at": cached["ts"].isoformat(),
                "age_seconds": round(age_seconds, 1),
            }
            coordinator_diagnostics = (
                {**snapshot, "cache_status": cache_status}
                if isinstance(snapshot, dict)
                else {"cache_status": cache_status, "snapshot": snapshot}
            )
        else:
            coordinator_diagnostics = {
                "status": "unavailable",
                "reason": "coordinator missing — the integration is not set up for this entry",
            }

    return {
        "title": "Adaptive Pergola Configuration",
        "type": "config_entry",
        "identifier": config_entry.entry_id,
        # Envelope triage fields HA core's diagnostics wrapper does not provide.
        # Always present, so even a marker-only download states whether the entry
        # is set up and which migration schema it is on.
        "config_entry_state": config_entry.state.value,
        "config_entry_version": config_entry.version,
        "config_entry_minor_version": config_entry.minor_version,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "config_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "config_options": async_redact_data(dict(config_entry.options), TO_REDACT),
        "diagnostics": coordinator_diagnostics,
    }
