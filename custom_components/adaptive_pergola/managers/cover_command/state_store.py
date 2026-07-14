"""Pure data shapes for cover_command's per-entity state.

These dataclasses are the contract between the orchestrator
(:class:`CoverCommandService`) and the cover-positioning lifecycle
(reconciliation, manual override, diagnostics).

Keeping them in a leaf module — no imports from the rest of the package —
breaks any latent circular-import risk and makes it cheap for managers,
diagnostics, and tests to depend on the shapes without dragging in the
whole service.

Today this file holds the dataclasses only. The companion
``EntityStateStore`` wrapper that owns the ``dict[str, PerEntityState]``
and the typed accessor methods is still on :class:`CoverCommandService`;
extracting it is the natural follow-up once the rest of the seams have
moved.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any


@dataclasses.dataclass(slots=True)
class PerEntityState:
    """Per-entity positioning state owned by CoverCommandService.

    Replaces a fan of parallel dicts/sets keyed by entity_id. The service
    holds a single dict[str, PerEntityState]; an entity has no state until
    apply_position / send_my_position records one.

    `target` and `sent_at` use ``None`` to mean "absent" — preserving the
    "key not in dict" semantics of the previous parallel-dict design.

    """

    target: int | None = None
    sent_at: dt.datetime | None = None
    waiting: bool = False
    last_progress_at: dt.datetime | None = None
    retry_count: int = 0
    gave_up: bool = False
    is_safety: bool = False
    last_reconcile_at: dt.datetime | None = None
    # Cumulative commanded travel (percent) since the cover last visited a
    # mechanical end stop (0/100). Drives the accumulated-travel re-sync
    # detour (CONF_RESYNC_TRAVEL_THRESHOLD); reset whenever a command lands
    # on an end stop.
    travel_since_resync: float = 0.0
    # When the travel counter last reset — i.e. the last time the cover was
    # referenced at an end stop (endpoint command, endpoint-origin leg, or a
    # re-sync detour). Surfaced by the diagnostics sensors; None until the
    # first reference after startup (in-memory only).
    last_resync_at: dt.datetime | None = None


@dataclasses.dataclass
class PositionContext:
    """Context passed to apply_position() describing current coordinator state.

    The coordinator builds this each time it wants to move a cover, passing in
    all the contextual flags that govern whether the command should actually be
    sent. CoverCommandService uses these instead of reaching back into the
    coordinator.

    """

    auto_control: bool
    manual_override: bool
    sun_just_appeared: bool
    min_change: int
    time_threshold: int
    special_positions: list[int]
    # Accumulated-travel end-stop re-sync threshold (percent of travel);
    # None/0 = feature disabled. See CONF_RESYNC_TRAVEL_THRESHOLD.
    resync_travel_threshold: int | None = None
    inverse_state: bool = False
    force: bool = False  # Skip delta/time/manual_override gates (NOT auto_control)
    is_safety: bool = (
        False  # Safety-critical target (persists across window boundaries; bypasses auto_control)
    )
    bypass_auto_control: bool = (
        False  # Sanctioned one-shot bypass of auto_control gate (e.g. switch return-to-default)
    )
    use_my_position: bool = (
        False  # Route through send_my_position() on non-position-capable covers
    )
    # Secondary-axis target (e.g. tilt for venetian blinds). The owning
    # cover-type policy reads it inside ``after_position_command`` to decide
    # whether and how to chase the position command with a second service
    # call. ``None`` means "no secondary axis on this update cycle".
    tilt: int | None = None
    # The cover-type policy in effect. ``apply_position`` calls
    # ``policy.after_position_command`` once the position service has fired so
    # dual-axis covers can run their settle+tilt sequence without leaking the
    # logic into this shared service.
    policy: Any = None
