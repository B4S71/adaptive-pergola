"""Fetch sun data.

`SunData` caches the day's solar timeline (`pd.date_range` plus the
per-tick azimuth/elevation lists from astral) so a single property read
doesn't pay the full ~289-call astral walk every time. The cache is
keyed on `(timezone, lat, lon, elevation, date.today())` — it
self-invalidates at midnight without any explicit refresh.

This shape exists because `position_forecast` (and any future
forecast-style consumer) reads ``solar_azimuth`` / ``solar_elevation``
in a tight loop. The plain `@property` form recomputed everything on
every access, with a nested ``for _i in self.times`` clause that
re-evaluated ``self.times`` on every iteration — pathological inside
a 49-step forecast walker. See issue #437.

The module-level ``_DAY_CACHE`` shares one fill across all ``SunData``
instances at the same location (e.g. 10 covers at the same address).
The fill runs inside ``hass.async_add_executor_job`` (off the event
loop), so the cache is guarded by a ``threading.Lock``. See issue #441.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import astral.sun
import pandas as pd

# ---------------------------------------------------------------------------
# Module-level day cache — shared across all SunData instances
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _SunDayData:
    """Module-cache value: one day's computed times/azimuth/elevation for a location."""

    times: pd.DatetimeIndex
    azi: list[float]
    ele: list[float]


_CACHE_LOCK: threading.Lock = threading.Lock()
_DAY_CACHE: dict[tuple, _SunDayData] = {}


def _cache_key(tz_name: str, observer) -> tuple[str, float, float, float, date]:
    """Module-level cache key — date.today() component self-invalidates at midnight."""
    return (
        tz_name,
        observer.latitude,
        observer.longitude,
        observer.elevation,
        date.today(),
    )


class SunData:
    """Access local sun data.

    Properties are computed lazily on first access per day and memoised
    on the instance until ``date.today()`` advances. ``functools.cached_property``
    would lock to construction day, so we maintain an explicit
    `_cache_day` key instead.
    """

    def __init__(self, timezone, observer) -> None:  # noqa: D107
        # astral.Observer — carries latitude/longitude/elevation together.
        # Replaced astral.location.Location when HA deprecated
        # get_astral_location in favour of get_astral_observer (removal in HA
        # 2027.7). Location's convenience methods (solar_azimuth, sunrise, ...)
        # have no Observer equivalent, so the astral.sun module functions are
        # called directly below.
        self.observer = observer
        self.timezone = timezone
        # Day-keyed memoisation. None on first access; populated by
        # `_ensure_today()` and invalidated when `date.today()` rolls over.
        self._cache_day: date | None = None
        self._cache_times: pd.DatetimeIndex | None = None
        self._cache_azi: list[float] | None = None
        self._cache_ele: list[float] | None = None

    def _ensure_today(self) -> None:
        """Refresh the cached timeline + solar angles when the day rolls over.

        Three-tier lookup:
        1. Fast path — instance fields already populated for today.
        2. Module lookup — dict GET (no lock); assign from cached _SunDayData.
        3. Miss — acquire lock, double-check, build timeline, purge stale
           entries, store, release; then assign from the new entry.
        """
        today = date.today()
        # Tier 1: instance fast path.
        if self._cache_day == today and self._cache_times is not None:
            return

        key = _cache_key(self.timezone, self.observer)

        # Tier 2: module cache hit (no lock — CPython GIL + immutable value safe).
        cached = _DAY_CACHE.get(key)
        if cached is not None:
            self._cache_day = today
            self._cache_times = cached.times
            self._cache_azi = cached.azi
            self._cache_ele = cached.ele
            return

        # Tier 3: fill under lock.
        with _CACHE_LOCK:
            # Double-checked locking: another thread may have filled while we waited.
            cached = _DAY_CACHE.get(key)
            if cached is None:
                end_date = today + timedelta(days=1)
                times = pd.date_range(
                    start=today,
                    end=end_date,
                    freq="5min",
                    tz=self.timezone,
                    name="time",
                )
                # NB: astral.sun.* does NOT normalise a tz-aware datetime to
                # UTC — only naive ones are *assumed* UTC. Location.solar_*
                # used to do the .astimezone(utc) for us, so it must be done
                # here explicitly: passing these tz-aware (local) stamps
                # straight through silently skews the angles (measured: up to
                # 0.16° elevation / 0.06° azimuth). With the conversion the
                # results are bit-for-bit identical to the old Location calls.
                utc_times = [t.astimezone(timezone.utc) for t in times]
                azi_list = [astral.sun.azimuth(self.observer, t) for t in utc_times]
                ele_list = [astral.sun.elevation(self.observer, t) for t in utc_times]
                cached = _SunDayData(times=times, azi=azi_list, ele=ele_list)
                # Purge stale (non-today) entries to keep memory bounded.
                stale = [k for k in _DAY_CACHE if k[4] != today]
                for k in stale:
                    del _DAY_CACHE[k]
                _DAY_CACHE[key] = cached

        self._cache_day = today
        self._cache_times = cached.times
        self._cache_azi = cached.azi
        self._cache_ele = cached.ele

    @property
    def times(self) -> pd.DatetimeIndex:
        """Today's 5-minute timeline (cached per day)."""
        self._ensure_today()
        # Explicit RuntimeError instead of assert: assert is stripped under
        # optimized builds (python -O), which would turn a failed cache fill into
        # a silent None dereference instead of a clear error.
        if self._cache_times is None:
            raise RuntimeError(  # pragma: no cover
                "SunData cache fill failed: _cache_times is None after _ensure_today()"
            )
        return self._cache_times

    @property
    def solar_azimuth(self) -> list[float]:
        """Solar azimuth at each entry in :attr:`times` (cached per day)."""
        self._ensure_today()
        if self._cache_azi is None:
            raise RuntimeError(  # pragma: no cover
                "SunData cache fill failed: _cache_azi is None after _ensure_today()"
            )
        return self._cache_azi

    @property
    def solar_elevation(self) -> list[float]:
        """Solar elevation at each entry in :attr:`times` (cached per day)."""
        self._ensure_today()
        if self._cache_ele is None:
            raise RuntimeError(  # pragma: no cover
                "SunData cache fill failed: _cache_ele is None after _ensure_today()"
            )
        return self._cache_ele

    def prime_cache(self) -> None:
        """Pre-warm the day cache — call from an executor, never inline on the event loop.

        Accessing ``pd.date_range(tz=<named-tz>)`` on a system without OS-level
        IANA tz data (e.g. HAOS on Raspberry Pi) triggers
        ``importlib.import_module('tzdata')`` which HA's loop watchdog flags as
        a blocking call. This method exists so the cache fill runs in a thread
        pool worker via ``hass.async_add_executor_job(sun_data.prime_cache)``.

        If the cache is already warm for today, accessing ``self.times`` is a
        Tier 1 fast-path hit (no lock, no I/O) — so calling this unconditionally
        is safe and cheap. Issue #655.
        """
        _ = self.times  # Forces Tier 3 fill if cache is cold; no-op if warm.

    def sunset(self) -> datetime:
        """Fetch sunset time.

        Returns a far-future sentinel (midnight tonight) at polar latitudes
        during midnight sun when astral raises ValueError.
        """
        try:
            return astral.sun.sunset(self.observer, date.today())
        except (ValueError, AttributeError):
            # Polar midnight sun: sun never sets — treat as end of day
            today = date.today()
            return datetime(
                today.year, today.month, today.day, 23, 59, 59
            )  # noqa: DTZ001

    def sunrise(self) -> datetime:
        """Fetch sunrise time.

        Returns an early-morning sentinel (00:01 today) at polar latitudes
        during polar night when astral raises ValueError.
        """
        try:
            return astral.sun.sunrise(self.observer, date.today())
        except (ValueError, AttributeError):
            # Polar night: sun never rises — treat as very early morning
            today = date.today()
            return datetime(today.year, today.month, today.day, 0, 1, 0)  # noqa: DTZ001

    def next_sunrise(self) -> datetime:
        """Fetch tomorrow's sunrise time.

        Lets the forecast expose a still-upcoming event late in the evening,
        after today's sunrise/sunset/FOV events have all passed, so the
        ``position_forecast`` sensor keeps a real timestamp instead of going
        ``Unknown`` (issue #516).

        Returns an early-morning sentinel (00:01 tomorrow) at polar latitudes
        during polar night when astral raises ValueError.
        """
        tomorrow = date.today() + timedelta(days=1)
        try:
            return astral.sun.sunrise(self.observer, tomorrow)
        except (ValueError, AttributeError):
            # Polar night: sun never rises — treat as very early morning
            return datetime(
                tomorrow.year, tomorrow.month, tomorrow.day, 0, 1, 0
            )  # noqa: DTZ001
