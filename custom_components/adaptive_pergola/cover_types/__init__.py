"""Per-cover-type policy registry.

The coordinator selects a single ``CoverTypePolicy`` instance at startup
and routes every cover-type-specific decision through it, so the shared
code paths (coordinator update cycle, cover command service, manual
override detection, config flow) never branch on cover type.

Adaptive Pergola ships only the louvered-roof (pergola) cover type plus
the virtual Building Profile entry type. The other Adaptive Cover Pro
policies (blind, awning, tilt, venetian, …) were removed in the pergola
split; the shared calc engine under ``engine/covers/`` is retained.
"""

from __future__ import annotations

from .base import POLICY_REGISTRY, CoverTypePolicy

# Importing each policy module triggers its ``register=True`` auto-registration
# in ``POLICY_REGISTRY`` (see ``CoverTypePolicy.__init_subclass__``). Import
# order sets the cover-type picker order. A new cover type is added simply by
# creating its module and importing it here.
from .louvered_roof import LouveredRoofPolicy


def get_policy(cover_type) -> CoverTypePolicy:
    """Return a policy instance for the given cover-type identifier.

    Accepts a plain string, a ``CoverType`` ``StrEnum`` member, or any value
    with a ``.value`` attribute. Raises ``ValueError`` for unknown types —
    preserves the failure mode of the previous if/elif chain in
    ``coordinator.get_blind_data``.
    """
    key: str | None
    if cover_type is None:
        key = None
    elif hasattr(cover_type, "value"):
        key = cover_type.value
    else:
        key = cover_type
    cls = POLICY_REGISTRY.get(key) if key is not None else None
    if cls is None:
        msg = f"Unsupported cover type: {cover_type!r}"
        raise ValueError(msg)
    return cls()


__all__ = [
    "POLICY_REGISTRY",
    "CoverTypePolicy",
    "LouveredRoofPolicy",
    "get_policy",
]
