"""Pytest configuration for Adaptive Pergola."""

pytest_plugins = ["pytest_homeassistant_custom_component"]

import pytest


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(request):
    """Enable discovery of local custom_components for integration-style tests."""
    if request.node.get_closest_marker("integration"):
        request.getfixturevalue("enable_custom_integrations")
