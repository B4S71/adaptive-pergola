"""Verify CoverTypePolicy.build_calc_engine returns the right concrete engine.

After PR #33's refactor, the coordinator no longer branches on cover-type
strings — it routes through ``self._policy.build_calc_engine(...)``. These
tests pin the dispatch table so a future policy refactor can't silently
mis-route a cover type to the wrong calc engine.

Adaptive Pergola ships a single physical cover type (louvered roof) plus the
virtual Building Profile entry type, so the registry surface is deliberately
small — these tests also pin that nothing else is registered.
"""

from unittest.mock import MagicMock

import pytest

from custom_components.adaptive_pergola.config_types import CoverConfig
from custom_components.adaptive_pergola.cover_types import (
    POLICY_REGISTRY,
    BuildingProfilePolicy,
    CoverTypePolicy,
    LouveredRoofPolicy,
    get_policy,
)
from custom_components.adaptive_pergola.engine.covers import (
    AdaptiveLouveredRoofCover,
)

from .stub_policy import StubDualAxisPolicy, StubSingleAxisPolicy


def _common_cover_config() -> CoverConfig:
    return CoverConfig(
        win_azi=180,
        fov_left=90,
        fov_right=90,
        h_def=0,
        sunset_pos=None,
        sunset_off=0,
        sunrise_off=0,
        max_pos=100,
        min_pos=0,
        max_pos_sun_only=False,
        min_pos_sun_only=False,
        blind_spot_left=None,
        blind_spot_right=None,
        blind_spot_elevation=None,
        blind_spot_on=False,
        min_elevation=None,
        max_elevation=None,
    )


@pytest.fixture
def fake_config_service():
    svc = MagicMock()
    svc.get_glare_zones_config.return_value = None
    return svc


@pytest.fixture
def calc_kwargs(mock_sun_data, mock_logger, fake_config_service):
    return {
        "logger": mock_logger,
        "sol_azi": 180.0,
        "sol_elev": 45.0,
        "sun_data": mock_sun_data,
        "config": _common_cover_config(),
        "config_service": fake_config_service,
        "options": {},
    }


@pytest.mark.unit
class TestRegistry:
    """Verify the policy registry maps cover-type strings to the right class."""

    def test_louvered_roof_policy_registered(self):
        assert POLICY_REGISTRY["cover_louvered_roof"] is LouveredRoofPolicy

    def test_building_profile_policy_registered(self):
        assert POLICY_REGISTRY["cover_building_profile"] is BuildingProfilePolicy

    def test_only_pergola_types_registered_by_integration(self):
        # The pergola split ships exactly one physical cover type plus the
        # virtual building profile. Anything else in the registry must come
        # from the test-only compat shims (tests/compat_policies.py), never
        # from the integration package itself.
        for key, cls in POLICY_REGISTRY.items():
            if key in ("cover_louvered_roof", "cover_building_profile"):
                assert cls.__module__.startswith("custom_components.")
            else:
                assert cls.__module__ == "tests.compat_policies", (
                    f"{key} registered by {cls.__module__} — the integration "
                    "must only register the pergola types"
                )

    def test_get_policy_returns_instance(self):
        assert isinstance(get_policy("cover_louvered_roof"), LouveredRoofPolicy)
        assert isinstance(get_policy("cover_building_profile"), BuildingProfilePolicy)

    def test_get_policy_raises_for_unknown(self):
        with pytest.raises(ValueError, match="Unsupported cover type"):
            get_policy("cover_nonexistent")

    def test_get_policy_raises_for_removed_types(self):
        # The non-pergola Adaptive Cover Pro types are gone on purpose
        # (cover_blind/awning/tilt have test-only shims; these three don't).
        for removed in (
            "cover_venetian",
            "cover_roof_window",
            "cover_oscillating_awning",
        ):
            with pytest.raises(ValueError, match="Unsupported cover type"):
                get_policy(removed)

    def test_get_policy_raises_for_none(self):
        with pytest.raises(ValueError, match="Unsupported cover type"):
            get_policy(None)

    def test_all_subclasses_implement_required_methods(self):
        for policy_cls in POLICY_REGISTRY.values():
            assert issubclass(policy_cls, CoverTypePolicy)
            assert hasattr(policy_cls, "cover_type")
            assert hasattr(policy_cls, "build_calc_engine")


@pytest.mark.unit
class TestBuildCalcEngine:
    """``build_calc_engine`` returns the right concrete cover for each policy."""

    def test_louvered_roof_returns_louvered_cover(self, calc_kwargs):
        engine = LouveredRoofPolicy().build_calc_engine(**calc_kwargs)
        assert isinstance(engine, AdaptiveLouveredRoofCover)

    def test_strenum_input(self, calc_kwargs):
        from custom_components.adaptive_pergola.const import CoverType

        policy = get_policy(CoverType.LOUVERED_ROOF)
        assert isinstance(policy, LouveredRoofPolicy)
        engine = policy.build_calc_engine(**calc_kwargs)
        assert isinstance(engine, AdaptiveLouveredRoofCover)


@pytest.mark.unit
class TestDefaultHooks:
    """Default hook implementations on ``CoverTypePolicy`` are no-ops."""

    @pytest.mark.parametrize(
        "policy_cls", [StubSingleAxisPolicy, StubDualAxisPolicy]
    )
    def test_post_pipeline_resolve_is_identity(self, policy_cls, calc_kwargs):
        result = MagicMock()
        out = policy_cls().post_pipeline_resolve(result, **calc_kwargs)
        assert out is result

    @pytest.mark.parametrize(
        "policy_cls", [StubSingleAxisPolicy, StubDualAxisPolicy]
    )
    def test_position_context_overrides_empty(self, policy_cls):
        assert policy_cls().position_context_overrides(MagicMock()) == {}

    @pytest.mark.parametrize(
        "policy_cls", [StubSingleAxisPolicy, StubDualAxisPolicy]
    )
    def test_secondary_axis_check_none(self, policy_cls):
        assert policy_cls().secondary_axis_check(MagicMock(), MagicMock()) is None

    @pytest.mark.parametrize(
        "policy_cls", [StubSingleAxisPolicy, StubDualAxisPolicy]
    )
    @pytest.mark.asyncio
    async def test_after_position_command_returns_none(self, policy_cls):
        out = await policy_cls().after_position_command(
            MagicMock(),
            "cover.x",
            service="set_cover_position",
            position=50,
            context=MagicMock(),
            reason="test",
        )
        assert out is None
