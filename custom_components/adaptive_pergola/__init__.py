"""Adaptive Pergola integration."""

from __future__ import annotations

from collections.abc import Mapping

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
	CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
	CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
	CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
	CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
	CONF_AXIS_AZIMUTH_DEG,
	CONF_CLOSED_ANGLE_DEG,
	CONF_COMMAND_MODE,
	CONF_HAS_ADDITIONAL_PROTECTED_AREA,
	CONF_HAS_SHADOW_CASTING_WALL,
	CONF_MANUAL_IGNORE_INTERMEDIATE,
	CONF_MANUAL_OVERRIDE_DURATION,
	CONF_MANUAL_OVERRIDE_RESET,
	CONF_NAME,
	CONF_OPEN_ACTUATOR_PERCENT,
	CONF_OPEN_ANGLE_DEG,
	CONF_OPENING_AZIMUTH_DEG,
	CONF_SHADOW_CASTING_WALL_HEIGHT_M,
	CONF_SHADOW_CASTING_WALL_LENGTH_M,
	CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
	CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
	CONF_MAX_TRAVEL_ANGLE_DEG,
	CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG,
	CONF_SLAT_AXIS_AZIMUTH_DEG,
	CONF_TARGET_ENTITY,
	CONF_WIND_SPEED_SENSOR,
	CONF_RAIN_SENSOR,
	CONF_IS_RAINING_SENSOR,
	CONF_IS_WINDY_SENSOR,
	CONF_SEVERE_SENSORS,
	DEFAULT_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
	DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
	DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
	DEFAULT_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
	DEFAULT_HAS_ADDITIONAL_PROTECTED_AREA,
	DEFAULT_HAS_SHADOW_CASTING_WALL,
	DEFAULT_MANUAL_IGNORE_INTERMEDIATE,
	DEFAULT_MANUAL_OVERRIDE_DURATION,
	DEFAULT_MANUAL_OVERRIDE_RESET,
	DEFAULT_SHADOW_CASTING_WALL_HEIGHT_M,
	DEFAULT_SHADOW_CASTING_WALL_LENGTH_M,
	DEFAULT_SHADOW_CASTING_WALL_OFFSET_EAST_M,
	DEFAULT_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
	DOMAIN,
	PLATFORMS,
	SUN_ENTITY_ID,
)
from .coordinator import AdaptivePergolaCoordinator
from .geometry_config import strip_legacy_geometry_keys
from .models import derived_open_actuator_percent

CONFIG_SCHEMA = vol.Schema(
	{
		DOMAIN: vol.All(
			cv.ensure_list,
			[
				vol.Schema(
					{
						vol.Required(CONF_NAME): cv.string,
						vol.Required(CONF_TARGET_ENTITY): cv.entity_id,
						vol.Required(CONF_COMMAND_MODE): cv.string,
					},
					extra=vol.ALLOW_EXTRA,
				)
			],
		)
	},
	extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: Mapping) -> bool:
	"""Set up Adaptive Pergola from YAML for live/demo testing."""
	hass.data.setdefault(DOMAIN, {})
	for item in config.get(DOMAIN, []):
		hass.async_create_task(
			hass.config_entries.flow.async_init(
				DOMAIN,
				context={"source": SOURCE_IMPORT},
				data=dict(item),
			)
		)
	return True


def _tracked_entities(entry: ConfigEntry) -> list[str]:
	"""Return sensor and target entities that should trigger an immediate refresh."""
	config = {**entry.data, **entry.options}
	tracked = [SUN_ENTITY_ID]
	target_entity = config.get(CONF_TARGET_ENTITY)
	if target_entity:
		tracked.append(target_entity)
	for key in [
		CONF_WIND_SPEED_SENSOR,
		CONF_RAIN_SENSOR,
		CONF_IS_RAINING_SENSOR,
		CONF_IS_WINDY_SENSOR,
	]:
		entity_id = config.get(key)
		if entity_id:
			tracked.append(entity_id)
	tracked.extend(config.get(CONF_SEVERE_SENSORS, []))
	return tracked


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Set up Adaptive Pergola from a config entry."""
	coordinator = AdaptivePergolaCoordinator(hass, entry)
	hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

	entry.async_on_unload(
		async_track_state_change_event(
			hass,
			_tracked_entities(entry),
			coordinator.async_handle_state_change,
		)
	)
	entry.async_on_unload(entry.add_update_listener(_async_update_listener))

	await coordinator.async_config_entry_first_refresh()
	await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
	return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload Adaptive Pergola."""
	unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
	if unload_ok:
		hass.data[DOMAIN].pop(entry.entry_id, None)
	return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
	"""Reload entry when options change."""
	await hass.config_entries.async_reload(entry.entry_id)


def _with_protected_area_defaults(config: Mapping) -> dict:
	"""Return config data with defaults for the optional additional protected area."""
	normalized = strip_legacy_geometry_keys(config)
	normalized.setdefault(
		CONF_MANUAL_OVERRIDE_DURATION,
		dict(DEFAULT_MANUAL_OVERRIDE_DURATION),
	)
	normalized.setdefault(CONF_MANUAL_OVERRIDE_RESET, DEFAULT_MANUAL_OVERRIDE_RESET)
	normalized.setdefault(
		CONF_MANUAL_IGNORE_INTERMEDIATE,
		DEFAULT_MANUAL_IGNORE_INTERMEDIATE,
	)
	if CONF_OPEN_ACTUATOR_PERCENT not in normalized:
		normalized[CONF_OPEN_ACTUATOR_PERCENT] = derived_open_actuator_percent(
			float(normalized.get(CONF_CLOSED_ANGLE_DEG, 0.0)),
			float(normalized.get(CONF_OPEN_ANGLE_DEG, 90.0)),
			float(normalized.get(CONF_MAX_TRAVEL_ANGLE_DEG, 135.0)),
		)
	normalized.setdefault(CONF_HAS_ADDITIONAL_PROTECTED_AREA, DEFAULT_HAS_ADDITIONAL_PROTECTED_AREA)
	normalized.setdefault(
		CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
		DEFAULT_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
	)
	normalized.setdefault(
		CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
		DEFAULT_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
	)
	normalized.setdefault(
		CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
		DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
	)
	normalized.setdefault(
		CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
		DEFAULT_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
	)
	normalized.setdefault(CONF_HAS_SHADOW_CASTING_WALL, DEFAULT_HAS_SHADOW_CASTING_WALL)
	normalized.setdefault(
		CONF_SHADOW_CASTING_WALL_LENGTH_M,
		DEFAULT_SHADOW_CASTING_WALL_LENGTH_M,
	)
	normalized.setdefault(
		CONF_SHADOW_CASTING_WALL_HEIGHT_M,
		DEFAULT_SHADOW_CASTING_WALL_HEIGHT_M,
	)
	normalized.setdefault(
		CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M,
		DEFAULT_SHADOW_CASTING_WALL_OFFSET_EAST_M,
	)
	normalized.setdefault(
		CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
		DEFAULT_SHADOW_CASTING_WALL_OFFSET_NORTH_M,
	)
	return normalized


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Migrate legacy geometry settings to the explicit azimuth model."""
	if entry.version > 6:
		return False

	data = dict(entry.data)
	options = dict(entry.options)
	needs_update = entry.version < 6
	for source in (data, options):
		if CONF_AXIS_AZIMUTH_DEG in source:
			needs_update = True
		if CONF_SLAT_AXIS_AZIMUTH_DEG not in source:
			needs_update = True
		if CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG not in source:
			needs_update = True
		if CONF_OPENING_AZIMUTH_DEG not in source:
			needs_update = True
		if CONF_OPEN_ACTUATOR_PERCENT not in source:
			needs_update = True
		if CONF_HAS_ADDITIONAL_PROTECTED_AREA not in source:
			needs_update = True
		if CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M not in source:
			needs_update = True
		if CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M not in source:
			needs_update = True
		if CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M not in source:
			needs_update = True
		if CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M not in source:
			needs_update = True
		if CONF_HAS_SHADOW_CASTING_WALL not in source:
			needs_update = True
		if CONF_SHADOW_CASTING_WALL_LENGTH_M not in source:
			needs_update = True
		if CONF_SHADOW_CASTING_WALL_HEIGHT_M not in source:
			needs_update = True
		if CONF_SHADOW_CASTING_WALL_OFFSET_EAST_M not in source:
			needs_update = True
		if CONF_SHADOW_CASTING_WALL_OFFSET_NORTH_M not in source:
			needs_update = True
		if CONF_MANUAL_OVERRIDE_DURATION not in source:
			needs_update = True
		if CONF_MANUAL_OVERRIDE_RESET not in source:
			needs_update = True
		if CONF_MANUAL_IGNORE_INTERMEDIATE not in source:
			needs_update = True

	if not needs_update:
		return True

	hass.config_entries.async_update_entry(
		entry,
		data=_with_protected_area_defaults(data),
		options=_with_protected_area_defaults(options),
		version=6,
	)
	return True


__all__ = ["DOMAIN"]
