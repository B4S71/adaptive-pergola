"""Tests for the accumulated-travel end-stop re-sync feature.

Covers the drift-compensation cycle (CONF_RESYNC_TRAVEL_THRESHOLD): motors
that execute many small tracking steps drift, so once the cumulative
commanded travel since the last end-stop visit exceeds the threshold, the
next mid-range move detours via the nearest mechanical end stop before
continuing to the target.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.adaptive_pergola.managers.cover_command import (
    CoverCommandService,
    PositionContext,
)

MOD = "custom_components.adaptive_pergola.managers.cover_command"


@pytest.fixture
def mock_hass():
    """Return a mock Home Assistant instance with an awaitable service call."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def svc(mock_hass):
    """Return a CoverCommandService for a tilt cover (the pergola case)."""
    return CoverCommandService(
        hass=mock_hass,
        logger=MagicMock(),
        cover_type="cover_tilt",
        grace_mgr=MagicMock(),
        open_close_threshold=50,
    )


def _ctx(threshold: int | None) -> PositionContext:
    """PositionContext that passes every gate, with the resync threshold set."""
    return PositionContext(
        auto_control=True,
        manual_override=False,
        sun_just_appeared=False,
        min_change=1,
        time_threshold=0,
        special_positions=[0, 100],
        resync_travel_threshold=threshold,
    )


def _stub_state(mock_hass, position: int) -> None:
    state = MagicMock()
    state.state = "open"
    state.attributes = {"current_tilt_position": position}
    mock_hass.states.get.return_value = state


async def _apply(svc, mock_hass, *, current, target, threshold, service_name="set_cover_tilt_position"):
    """Run apply_position with all gates green and a stubbed service route."""
    _stub_state(mock_hass, current)
    with (
        patch.object(svc, "_get_current_position", return_value=current),
        patch.object(svc, "_check_position_delta", return_value=True),
        patch.object(svc, "_check_time_delta", return_value=True),
        patch.object(
            svc,
            "_prepare_service_call",
            return_value=(
                service_name,
                {"entity_id": "cover.test", "tilt_position": target},
                True,
            ),
        ),
        patch(f"{MOD}.asyncio.sleep", new=AsyncMock()),
    ):
        return await svc.apply_position("cover.test", target, "solar", _ctx(threshold))


# --- travel accounting -------------------------------------------------------


@pytest.mark.asyncio
async def test_midrange_moves_accumulate_travel(svc, mock_hass):
    """Mid-range → mid-range legs add |target − current| to the counter."""
    outcome, _ = await _apply(svc, mock_hass, current=40, target=50, threshold=None)
    assert outcome == "sent"
    assert svc.state("cover.test").travel_since_resync == 10

    outcome, _ = await _apply(svc, mock_hass, current=50, target=44, threshold=None)
    assert outcome == "sent"
    assert svc.state("cover.test").travel_since_resync == 16


@pytest.mark.asyncio
async def test_endpoint_target_resets_counter(svc, mock_hass):
    """Commanding 0/100 (the nightly close) is a free re-sync."""
    svc.state("cover.test").travel_since_resync = 55
    outcome, _ = await _apply(svc, mock_hass, current=40, target=100, threshold=None)
    assert outcome == "sent"
    assert svc.state("cover.test").travel_since_resync == 0


@pytest.mark.asyncio
async def test_leg_departing_endstop_resets_counter(svc, mock_hass):
    """A move starting AT an end stop re-references — reset, don't count.

    Counting it would re-trigger a detour on every move that follows a
    re-sync cycle (the end-stop → target leg is often > threshold).
    """
    svc.state("cover.test").travel_since_resync = 15
    outcome, _ = await _apply(svc, mock_hass, current=0, target=37, threshold=None)
    assert outcome == "sent"
    assert svc.state("cover.test").travel_since_resync == 0


# --- detour trigger ----------------------------------------------------------


@pytest.mark.asyncio
async def test_no_detour_below_threshold(svc, mock_hass):
    """Accumulated + planned below the threshold: one direct service call."""
    svc.state("cover.test").travel_since_resync = 5
    outcome, _ = await _apply(svc, mock_hass, current=90, target=92, threshold=20)
    assert outcome == "sent"
    assert mock_hass.services.async_call.await_count == 1


@pytest.mark.asyncio
async def test_detour_fires_at_threshold_via_nearest_endstop(svc, mock_hass):
    """Over threshold: end stop nearest the target is visited first."""
    svc.state("cover.test").travel_since_resync = 19
    with patch.object(svc, "_at_target", return_value=True):
        outcome, _ = await _apply(svc, mock_hass, current=90, target=92, threshold=20)
    assert outcome == "sent"
    assert mock_hass.services.async_call.await_count == 2
    first, second = mock_hass.services.async_call.await_args_list
    assert first.args[2]["tilt_position"] == 100  # target 92 → nearest stop 100
    assert second.args[2]["tilt_position"] == 92
    # end-stop → target leg does not count as new travel
    assert svc.state("cover.test").travel_since_resync == 0


@pytest.mark.asyncio
async def test_detour_uses_low_endstop_for_low_targets(svc, mock_hass):
    """Targets below 50 detour via the 0 end stop."""
    svc.state("cover.test").travel_since_resync = 30
    with patch.object(svc, "_at_target", return_value=True):
        outcome, _ = await _apply(svc, mock_hass, current=45, target=40, threshold=20)
    assert outcome == "sent"
    first, second = mock_hass.services.async_call.await_args_list
    assert first.args[2]["tilt_position"] == 0
    assert second.args[2]["tilt_position"] == 40


@pytest.mark.asyncio
async def test_no_detour_when_disabled(svc, mock_hass):
    """threshold None/0: never detours regardless of accumulated travel."""
    svc.state("cover.test").travel_since_resync = 500
    outcome, _ = await _apply(svc, mock_hass, current=90, target=92, threshold=None)
    assert outcome == "sent"
    assert mock_hass.services.async_call.await_count == 1


@pytest.mark.asyncio
async def test_no_detour_departing_from_endstop(svc, mock_hass):
    """Origin at a hard stop is freshly referenced: no detour, counter reset."""
    svc.state("cover.test").travel_since_resync = 50
    outcome, _ = await _apply(svc, mock_hass, current=100, target=92, threshold=20)
    assert outcome == "sent"
    assert mock_hass.services.async_call.await_count == 1
    assert svc.state("cover.test").travel_since_resync == 0


@pytest.mark.asyncio
async def test_detour_counter_resets_even_on_wait_timeout(svc, mock_hass):
    """The counter resets on the attempt so a slow cover can't loop detours."""
    svc.state("cover.test").travel_since_resync = 25
    with (
        patch.object(svc, "_at_target", return_value=False),
        patch(f"{MOD}.monotonic", side_effect=[0, 100, 200]),
    ):
        outcome, _ = await _apply(svc, mock_hass, current=90, target=92, threshold=20)
    assert outcome == "sent"
    assert mock_hass.services.async_call.await_count == 2
    assert svc.state("cover.test").travel_since_resync == 0


@pytest.mark.asyncio
async def test_planned_travel_counts_toward_threshold(svc, mock_hass):
    """A single large move (the far-side flip) can trigger the detour alone."""
    svc.state("cover.test").travel_since_resync = 0
    with patch.object(svc, "_at_target", return_value=True):
        outcome, _ = await _apply(svc, mock_hass, current=48, target=94, threshold=20)
    assert outcome == "sent"
    assert mock_hass.services.async_call.await_count == 2
    first, _second = mock_hass.services.async_call.await_args_list
    assert first.args[2]["tilt_position"] == 100


@pytest.mark.asyncio
async def test_snapshot_exposes_travel_counter(svc, mock_hass):
    """Diagnostics snapshot carries the counter."""
    outcome, _ = await _apply(svc, mock_hass, current=40, target=50, threshold=None)
    assert outcome == "sent"
    snap = svc.get_entity_state_snapshot("cover.test")
    assert snap["travel_since_resync"] == 10
