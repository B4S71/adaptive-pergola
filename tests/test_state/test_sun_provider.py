"""Tests for the SunProvider state provider."""

from unittest.mock import MagicMock, patch

import pytest
from astral import Observer

from custom_components.adaptive_pergola.state.sun_provider import SunProvider
from custom_components.adaptive_pergola.sun import SunData

_GET_OBSERVER = (
    "custom_components.adaptive_pergola.state.sun_provider.get_astral_observer"
)


@pytest.fixture
def mock_hass():
    """Return a mock HomeAssistant instance."""
    return MagicMock()


class TestSunProvider:
    """Tests for SunProvider.

    HA deprecated ``get_astral_location`` (removal in 2027.7) in favour of
    ``get_astral_observer``, which returns a single ``astral.Observer``
    carrying latitude/longitude/elevation instead of a
    ``(Location, elevation)`` pair.
    """

    def test_create_sun_data_returns_sun_data(self, mock_hass):
        """SunProvider.create_sun_data returns a SunData wrapping HA's observer."""
        observer = Observer(48.0, 14.0, 100.0)
        with patch(_GET_OBSERVER, return_value=observer) as mock_get_obs:
            provider = SunProvider(hass=mock_hass)
            result = provider.create_sun_data("Europe/Berlin")

            assert isinstance(result, SunData)
            assert result.timezone == "Europe/Berlin"
            assert result.observer is observer
            # Elevation now travels inside the observer.
            assert result.observer.elevation == 100.0
            mock_get_obs.assert_called_once_with(mock_hass)

    def test_create_sun_data_passes_hass_to_get_astral_observer(self, mock_hass):
        """SunProvider passes its hass instance to get_astral_observer."""
        with patch(_GET_OBSERVER, return_value=Observer(0.0, 0.0, 0.0)) as mock_get_obs:
            provider = SunProvider(hass=mock_hass)
            provider.create_sun_data("UTC")

            mock_get_obs.assert_called_once_with(mock_hass)

    def test_create_sun_data_different_timezones(self, mock_hass):
        """SunProvider can create SunData with different timezones."""
        with patch(_GET_OBSERVER, return_value=Observer(48.0, 14.0, 50.0)):
            provider = SunProvider(hass=mock_hass)

            utc_data = provider.create_sun_data("UTC")
            assert utc_data.timezone == "UTC"

            berlin_data = provider.create_sun_data("Europe/Berlin")
            assert berlin_data.timezone == "Europe/Berlin"

    def test_sun_data_no_hass_dependency(self):
        """SunData itself has no HomeAssistant dependency."""
        observer = Observer(48.0, 14.0, 42.0)
        sun_data = SunData("UTC", observer)

        assert sun_data.timezone == "UTC"
        assert sun_data.observer is observer
        assert sun_data.observer.elevation == 42.0
