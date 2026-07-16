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


async def _apply(
    svc,
    mock_hass,
    *,
    current,
    target,
    threshold,
    service_name="set_cover_tilt_position",
):
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


# --- last_resync_at timestamp / diagnostics accessor --------------------------


@pytest.mark.asyncio
async def test_endpoint_command_stamps_last_resync(svc, mock_hass):
    """Landing on an end stop records the reference time."""
    assert svc.resync_diagnostics("cover.test")["last_resync_time"] is None
    await _apply(svc, mock_hass, current=40, target=100, threshold=None)
    d = svc.resync_diagnostics("cover.test")
    assert d["last_resync_time"] is not None
    assert d["travel_since_resync"] == 0


@pytest.mark.asyncio
async def test_detour_stamps_last_resync(svc, mock_hass):
    """A re-sync detour records the reference time."""
    svc.state("cover.test").travel_since_resync = 25
    with patch.object(svc, "_at_target", return_value=True):
        await _apply(svc, mock_hass, current=90, target=92, threshold=20)
    assert svc.resync_diagnostics("cover.test")["last_resync_time"] is not None


@pytest.mark.asyncio
async def test_midrange_move_does_not_stamp_last_resync(svc, mock_hass):
    """A plain mid-range move is not an end-stop reference."""
    await _apply(svc, mock_hass, current=40, target=50, threshold=None)
    d = svc.resync_diagnostics("cover.test")
    assert d["last_resync_time"] is None
    assert d["travel_since_resync"] == 10


@pytest.mark.asyncio
async def test_snapshot_exposes_last_resync_time(svc, mock_hass):
    """Diagnostics snapshot carries the iso-formatted reference time."""
    await _apply(svc, mock_hass, current=40, target=100, threshold=None)
    snap = svc.get_entity_state_snapshot("cover.test")
    assert snap["last_resync_time"] is not None


# --- manual-override protection of the detour legs -----------------------------


@pytest.mark.asyncio
async def test_detour_records_endstop_target_and_grace(svc, mock_hass, monkeypatch):
    """During the detour the live target is the END STOP (not the final pose).

    Without this, the classifier sees the cover moving away from the recorded
    final target once the 5 s grace expires and engages manual override.
    After the detour, the target points back at the final pose with a fresh
    grace period.
    """
    svc.state("cover.test").travel_since_resync = 25
    seen_targets: list[int | None] = []

    async def _fake_wait(entity_id, target, *, timeout=None):
        seen_targets.append(svc.state("cover.test").target)
        return True

    monkeypatch.setattr(svc, "wait_for_position", _fake_wait)
    outcome, _ = await _apply(svc, mock_hass, current=90, target=92, threshold=20)

    assert outcome == "sent"
    assert seen_targets == [100]  # end stop was the live target during the wait
    assert svc.state("cover.test").target == 92  # restored for the return leg
    assert svc.state("cover.test").waiting is True
    # detour leg + final-leg restore each (re)started a grace period
    assert svc._grace_mgr.start_command_grace_period.call_count >= 2


@pytest.mark.asyncio
async def test_wait_for_position_reached(svc, mock_hass):
    """wait_for_position returns True once the cover reports the target."""
    with (
        patch.object(svc, "_get_current_position", side_effect=[50, 98]),
        patch(f"{MOD}.asyncio.sleep", new=AsyncMock()),
    ):
        assert await svc.wait_for_position("cover.test", 100) is True


@pytest.mark.asyncio
async def test_wait_for_position_timeout(svc, mock_hass):
    """wait_for_position returns False when the deadline passes."""
    with (
        patch.object(svc, "_get_current_position", return_value=50),
        patch(f"{MOD}.asyncio.sleep", new=AsyncMock()),
        patch(f"{MOD}.monotonic", side_effect=[0, 100, 200]),
    ):
        assert await svc.wait_for_position("cover.test", 100) is False


# --- manual re-sync cycle (button) ---------------------------------------------


def _make_cycle_coordinator(current_position=93):
    """MagicMock coordinator with the real async_run_resync_cycle bound."""
    from custom_components.adaptive_pergola.coordinator import (
        AdaptiveDataUpdateCoordinator,
    )

    coord = MagicMock()
    coord.entities = ["cover.test"]
    coord.config_entry.options = {}
    coord._cmd_svc.get_current_position.return_value = current_position
    coord._cmd_svc.apply_position = AsyncMock(return_value=("sent", "svc"))
    coord._cmd_svc.wait_for_position = AsyncMock(return_value=True)
    coord._build_position_context.return_value = _ctx(None)
    coord.async_run_resync_cycle = (
        AdaptiveDataUpdateCoordinator.async_run_resync_cycle.__get__(coord)
    )
    return coord


@pytest.mark.asyncio
async def test_resync_cycle_closes_then_returns():
    """The cycle sends 0 first, waits, then restores the captured pose."""
    coord = _make_cycle_coordinator(current_position=93)
    cycled = await coord.async_run_resync_cycle()

    assert cycled == ["cover.test"]
    calls = coord._cmd_svc.apply_position.await_args_list
    assert [c.args[1] for c in calls] == [0, 93]
    assert all(c.args[2] == "resync_button" for c in calls)
    coord._cmd_svc.wait_for_position.assert_awaited_once_with("cover.test", 0)
    # both legs bypass gates so the cycle works during manual override too
    assert coord._build_position_context.call_count == 2
    for kwargs in (c.kwargs for c in coord._build_position_context.call_args_list):
        assert kwargs["force"] is True
        assert kwargs["bypass_auto_control"] is True


@pytest.mark.asyncio
async def test_resync_cycle_skips_unreadable_cover():
    """No readable position → cover skipped, nothing sent."""
    coord = _make_cycle_coordinator(current_position=None)
    cycled = await coord.async_run_resync_cycle()
    assert cycled == []
    coord._cmd_svc.apply_position.assert_not_awaited()


@pytest.mark.asyncio
async def test_resync_cycle_already_closed_counts_as_referenced():
    """Cover already at 0: close leg skips as same_position, no return leg."""
    coord = _make_cycle_coordinator(current_position=0)
    coord._cmd_svc.apply_position = AsyncMock(return_value=("skipped", "same_position"))
    cycled = await coord.async_run_resync_cycle()
    assert cycled == ["cover.test"]
    assert coord._cmd_svc.apply_position.await_count == 1
    coord._cmd_svc.wait_for_position.assert_not_awaited()


@pytest.mark.asyncio
async def test_resync_button_delegates_to_cycle():
    """The button press runs the coordinator cycle."""
    from custom_components.adaptive_pergola.button import AdaptivePergolaResyncButton

    coord = MagicMock()
    coord.async_run_resync_cycle = AsyncMock(return_value=["cover.test"])
    button = AdaptivePergolaResyncButton.__new__(AdaptivePergolaResyncButton)
    button.coordinator = coord
    await button.async_press()
    coord.async_run_resync_cycle.assert_awaited_once()
