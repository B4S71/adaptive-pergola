"""Tests for template render safety (ACP-004, ACP-019, ACP-020).

ACP-004 is the worst finding in the audit: a template that *parses* clean but
never finishes *rendering* is persisted to the config entry and then rendered
during setup, freezing the event loop so Home Assistant never starts. Recovery
needed hand-editing .storage/core.config_entries.
"""

from __future__ import annotations

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceValidationError

from custom_components.adaptive_pergola.services.options_service import (
    _check_template_syntax,
    async_validate_template_cost,
)
from custom_components.adaptive_pergola.templates import render_condition_or_none

pytestmark = pytest.mark.unit

# An unbounded render that HA's sandbox does NOT stop.
#
# The audit's proposed payload was `{% for i in range(100000000) %}`, but HA's
# ImmutableSandboxedEnvironment caps a single range at MAX_RANGE (100000) and
# raises OverflowError, so that exact template never hangs — it fails fast.
# MAX_RANGE bounds one range, not total work: two nested loops each *under* the
# cap multiply to 10^10 iterations and hang with no sandbox complaint. Verified
# both ways; see test_audit_poc_is_blocked_by_ha_sandbox below.
_UNBOUNDED = "{% for i in range(100000) %}{% for j in range(100000) %}{% endfor %}{% endfor %}500"


# --- ACP-004 -------------------------------------------------------------


async def test_unbounded_template_is_rejected(hass: HomeAssistant):
    """An unbounded render must be rejected before it can be persisted.

    jinja2.parse() proves syntax and says nothing about cost, so this template
    passed validation, reached config_entry.options, and then hung the event
    loop in the coordinator constructor on every subsequent boot.
    """
    with pytest.raises(ServiceValidationError, match="took longer than"):
        await async_validate_template_cost(
            hass, {"lux_threshold": _UNBOUNDED}, timeout=1.0
        )


async def test_unbounded_template_still_parses_clean(hass: HomeAssistant):
    """Shows *why* the cost gate is needed: syntax validation accepts it."""
    assert _check_template_syntax(_UNBOUNDED) == _UNBOUNDED


async def test_audit_poc_is_blocked_by_ha_sandbox(hass: HomeAssistant):
    """Records that a single oversized range is stopped by HA, not by us.

    Pins the boundary the nested-loop payload above works around: if HA ever
    bounds total render work (not just range size), this test tells the next
    reader which half of the protection changed.
    """
    with pytest.raises(ServiceValidationError, match="failed to render"):
        await async_validate_template_cost(
            hass,
            {"lux_threshold": "{% for i in range(100000000) %}{% endfor %}500"},
            timeout=5,
        )


async def test_cheap_template_passes(hass: HomeAssistant):
    """A realistic threshold template is unaffected."""
    hass.states.async_set("sensor.t", "21.5")
    await async_validate_template_cost(
        hass, {"lux_threshold": "{{ states('sensor.t') | float(0) * 2 }}"}
    )


async def test_non_template_values_are_ignored(hass: HomeAssistant):
    """Plain values are not rendered."""
    await async_validate_template_cost(
        hass, {"lux_threshold": "500", "fov_left": 45, "motion_sensors": []}
    )


async def test_broken_template_reports_cleanly(hass: HomeAssistant):
    """A template that raises at render time gives a ServiceValidationError."""
    with pytest.raises(ServiceValidationError):
        await async_validate_template_cost(
            hass, {"lux_threshold": "{{ 1 / 0 }}"}, timeout=5
        )


# --- ACP-019 -------------------------------------------------------------


def test_loopcontrols_template_is_accepted():
    """{% break %} renders fine in HA, so validation must not reject it.

    HA's TemplateEnvironment enables jinja2.ext.loopcontrols; a bare
    jinja2.Environment() does not, so this was a false reject on a valid
    template.
    """
    tpl = "{% for i in range(10) %}{% if i > 2 %}{% break %}{% endif %}{% endfor %}1"
    assert _check_template_syntax(tpl) == tpl


def test_genuinely_broken_syntax_still_rejected():
    """The loopcontrols extension must not weaken syntax checking."""
    with pytest.raises(vol.Invalid):
        _check_template_syntax("{% for i in range(3) %}{{ i }}")


# --- ACP-020 -------------------------------------------------------------


async def test_render_condition_or_none_handles_nondeterministic(hass: HomeAssistant):
    """A random template renders fine and must not be reported as failed.

    The old implementation rendered twice with opposing defaults and compared;
    a nondeterministic template disagreed across the two renders and was
    misreported as "render failed" -> None.
    """
    results = {
        render_condition_or_none(hass, "{{ [true, false] | random }}")
        for _ in range(25)
    }
    assert results <= {True, False}, "must never report None for a working template"
    assert None not in results


async def test_render_condition_or_none_still_returns_none_on_failure(
    hass: HomeAssistant,
):
    """A genuinely broken template still yields no opinion."""
    assert render_condition_or_none(hass, "{{ 1 / 0 }}") is None


async def test_render_condition_or_none_renders_once(hass: HomeAssistant):
    """The template is evaluated exactly once per call."""
    hass.states.async_set("input_boolean.x", "on")
    assert render_condition_or_none(hass, "{{ is_state('input_boolean.x','on') }}")
    assert (
        render_condition_or_none(hass, "{{ is_state('input_boolean.x','off') }}")
        is False
    )


async def test_render_condition_or_none_ignores_non_templates(hass: HomeAssistant):
    """Non-template values give no opinion."""
    assert render_condition_or_none(hass, "") is None
    assert render_condition_or_none(hass, None) is None
    assert render_condition_or_none(hass, "just a string") is None
