"""Regressions reproduced against the 0.7.0 beta on the Dev HA instance."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.adaptive_pergola.const import CoverType, DOMAIN
from tests.test_services_integration import _setup


pytestmark = pytest.mark.integration


async def setup_roof(hass):
    hass.states.async_set(
        "cover.test_blind",
        "open",
        {
            "current_tilt_position": 31,
            "supported_features": int(
                CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT
            ),
        },
    )
    entry = await _setup(hass, cover_type=CoverType.LOUVERED_ROOF)
    return entry.runtime_data


@pytest.mark.parametrize("service", ["integration_disable", "emergency_stop"])
async def test_global_shutdown_blocks_force_and_updates_switch_immediately(
    hass, service
):
    coord = await setup_roof(hass)
    stop_calls = []
    move_calls = []

    async def stop(call):
        # The hard gate has to be closed BEFORE the stop can yield.
        assert coord._cmd_svc.enabled is False
        stop_calls.append(call)

    async def move(call):
        move_calls.append(call)

    hass.services.async_register("cover", "stop_cover_tilt", stop)
    hass.services.async_register("cover", "set_cover_tilt_position", move)
    coord._cmd_svc.set_target("cover.test_blind", 70)
    coord._cmd_svc.set_waiting("cover.test_blind", True)
    await hass.services.async_call(DOMAIN, service, {}, blocking=True)
    await hass.services.async_call(
        DOMAIN,
        "set_tilt",
        {
            "entity_id": "cover.test_blind",
            "tilt": 83,
            "force": True,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert len(stop_calls) == 1
    assert not move_calls
    assert coord.enabled_toggle is False
    switch = next(
        s
        for s in hass.states.async_all("switch")
        if s.entity_id.endswith("integration_enabled")
    )
    assert switch.state == "off"
    assert coord._cmd_svc.state("cover.test_blind").target is None
    await hass.services.async_call(DOMAIN, "integration_enable", {}, blocking=True)
    await hass.async_block_till_done()
    assert coord._cmd_svc.enabled is True
    assert hass.states.get(switch.entity_id).state == "on"
    assert not move_calls  # enabling alone never moves


async def test_stop_uses_supported_tilt_axis_and_propagates_failure(hass):
    coord = await setup_roof(hass)
    calls = []

    async def stop(call):
        calls.append(call)
        assert coord._cmd_svc.was_acp_stop_context(call.context.id)

    hass.services.async_register("cover", "stop_cover_tilt", stop)
    await hass.services.async_call(
        DOMAIN, "stop", {"entity_id": "cover.test_blind"}, blocking=True
    )
    assert len(calls) == 1

    async def failed_stop(call):
        raise HomeAssistantError("actuator offline")

    hass.services.async_register("cover", "stop_cover_tilt", failed_stop)
    with pytest.raises(HomeAssistantError, match="actuator offline"):
        await coord.async_apply_user_stop("cover.test_blind", trigger="test")


async def test_unsupported_stop_reports_validation_error(hass):
    coord = await setup_roof(hass)
    hass.states.async_set("cover.test_blind", "open", {"supported_features": 0})
    with pytest.raises(ServiceValidationError, match="no supported stop"):
        await coord.async_apply_user_stop("cover.test_blind", trigger="test")


@pytest.mark.parametrize(
    "service,patch_data,expected",
    [
        ("set_weather_safety", {"weather_enabled": True}, {"weather_enabled": True}),
        ("set_light_cloud", {"cloudy_position": 25}, {"cloudy_position": 25}),
        ("set_light_cloud", {"cloudy_position": None}, {"cloudy_position": None}),
        (
            "set_option",
            {"option": "weather_enabled", "value": False},
            {"weather_enabled": False},
        ),
        (
            "set_option",
            {"option": "cloudy_position", "value": 42},
            {"cloudy_position": 42},
        ),
    ],
)
async def test_previously_missing_options_persist_via_services(
    hass, service, patch_data, expected
):
    coord = await setup_roof(hass)
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        await hass.services.async_call(
            DOMAIN,
            service,
            {
                "entity_id": "cover.test_blind",
                **patch_data,
            },
            blocking=True,
        )
        await hass.async_block_till_done()
    for key, value in expected.items():
        assert coord.config_entry.options.get(key) == value


async def test_emergency_failure_still_disables_and_stops_other_covers(hass):
    coord = await setup_roof(hass)
    other = "cover.other_roof"
    hass.states.async_set(
        other,
        "open",
        {
            "current_tilt_position": 50,
            "supported_features": int(
                CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.STOP_TILT
            ),
        },
    )
    calls = []

    async def stop(call):
        entity = call.data["entity_id"]
        calls.append(entity)
        if entity == "cover.test_blind":
            raise HomeAssistantError("actuator offline")

    hass.services.async_register("cover", "stop_cover_tilt", stop)
    with patch.object(coord, "entities", ["cover.test_blind", other]):
        with pytest.raises(HomeAssistantError, match="Failed to stop covers"):
            await hass.services.async_call(DOMAIN, "emergency_stop", {}, blocking=True)
    assert calls == ["cover.test_blind", other]
    assert coord.enabled_toggle is False
    assert coord._cmd_svc.enabled is False
