from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import time as time_module
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import azimuth, elevation, sun
import yaml

from custom_components.adaptive_pergola.const import (
    CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M,
    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M,
    CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M,
    CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M,
    CONF_CLOSES_AGAIN_AFTER_OPEN,
    CONF_CLOSED_ANGLE_DEG,
    CONF_COMMAND_MODE,
    CONF_COMMAND_VALUE_MAX,
    CONF_COMMAND_VALUE_MIN,
    CONF_HAS_ADDITIONAL_PROTECTED_AREA,
    CONF_HAS_HOUSE_ATTACHMENT,
    CONF_HOUSE_EXTENDS_LEFT_M,
    CONF_HOUSE_EXTENDS_RIGHT_M,
    CONF_HOUSE_HEIGHT_M,
    CONF_MAX_DIRECT_SUN_DEPTH_M,
    CONF_MAX_TRAVEL_ANGLE_DEG,
    CONF_NAME,
    CONF_OPEN_ANGLE_DEG,
    CONF_OPEN_ACTUATOR_PERCENT,
    CONF_OPENING_AZIMUTH_DEG,
    CONF_OPEN_BEFORE_SUNRISE_MINUTES,
    CONF_PERGOLA_LENGTH_M,
    CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG,
    CONF_PERGOLA_WIDTH_M,
    CONF_PREOPEN_ACTUATOR_PERCENT,
    CONF_RAIN_THRESHOLD,
    CONF_SLAT_AXIS_AZIMUTH_DEG,
    CONF_SEVERE_SENSORS,
    CONF_SLAT_AXIS_HEIGHT_M,
    CONF_SLAT_AXIS_SPACING_M,
    CONF_SLAT_THICKNESS_M,
    CONF_SLAT_WIDTH_M,
    CONF_TARGET_ENTITY,
    CONF_TRACKING_MODE,
    CONF_WEATHER_OVERRIDE_POSITION,
    CONF_WIND_SPEED_THRESHOLD,
)
from custom_components.adaptive_pergola.engine import compute_tracking_decision
from custom_components.adaptive_pergola.geometry_config import normalize_geometry_config
from custom_components.adaptive_pergola.models import (
    ActuatorConfig,
    AdditionalProtectedAreaConfig,
    CommandTarget,
    ControlConfig,
    HouseAttachment,
    PergolaGeometry,
    SunPosition,
    TrackingConfig,
    WeatherConfig,
    WeatherReadings,
)


def _load_profiles(root: Path, source: str, name_filter: str | None, entry_id_filter: str | None) -> list[dict]:
    config_items: list[dict] = []

    if source in {"auto", "yaml"}:
        config = yaml.safe_load((root / "config" / "configuration.yaml").read_text()) or {}
        config_items = list(config.get("adaptive_pergola", []))
        if config_items or source == "yaml":
            return _filter_profiles(config_items, name_filter, entry_id_filter=None)

    storage = json.loads((root / "config" / ".storage" / "core.config_entries").read_text())
    entries = storage["data"]["entries"]
    config_items = []
    for entry in entries:
        if entry.get("domain") != "adaptive_pergola" or entry.get("disabled_by"):
            continue
        item = {**entry.get("data", {}), **entry.get("options", {})}
        item["__entry_id"] = entry["entry_id"]
        config_items.append(item)
    return _filter_profiles(config_items, name_filter, entry_id_filter)


def _filter_profiles(items: list[dict], name_filter: str | None, entry_id_filter: str | None) -> list[dict]:
    filtered = items
    if name_filter:
        lowered = name_filter.casefold()
        filtered = [item for item in filtered if str(item.get(CONF_NAME, "")).casefold() == lowered]
    if entry_id_filter:
        filtered = [item for item in filtered if item.get("__entry_id") == entry_id_filter]
    return filtered


def _build_control(item: dict) -> ControlConfig:
    item = normalize_geometry_config(item)
    house = None
    if item.get(CONF_HAS_HOUSE_ATTACHMENT):
        house = HouseAttachment(
            height_m=float(item.get(CONF_HOUSE_HEIGHT_M, 0.0)),
            extends_left_m=float(item.get(CONF_HOUSE_EXTENDS_LEFT_M, 0.0)),
            extends_right_m=float(item.get(CONF_HOUSE_EXTENDS_RIGHT_M, 0.0)),
        )

    weather = WeatherConfig(
        override_actuator_percent=int(item.get(CONF_WEATHER_OVERRIDE_POSITION, 0)),
        wind_speed_threshold=float(item.get(CONF_WIND_SPEED_THRESHOLD, 0.0)),
        rain_threshold=float(item.get(CONF_RAIN_THRESHOLD, 0.0)),
        severe_binary_enabled=bool(item.get(CONF_SEVERE_SENSORS, [])),
    )

    return ControlConfig(
        geometry=PergolaGeometry(
            slat_width_m=float(item[CONF_SLAT_WIDTH_M]),
            slat_thickness_m=float(item[CONF_SLAT_THICKNESS_M]),
            slat_axis_spacing_m=float(item[CONF_SLAT_AXIS_SPACING_M]),
            slat_axis_height_m=float(item[CONF_SLAT_AXIS_HEIGHT_M]),
            pergola_length_m=float(item[CONF_PERGOLA_LENGTH_M]),
            pergola_width_m=float(item[CONF_PERGOLA_WIDTH_M]),
            slat_axis_azimuth_deg=float(item[CONF_SLAT_AXIS_AZIMUTH_DEG]),
            pergola_orientation_azimuth_deg=float(item[CONF_PERGOLA_ORIENTATION_AZIMUTH_DEG]),
            opening_azimuth_deg=float(item[CONF_OPENING_AZIMUTH_DEG]),
            house_attachment=house,
        ),
        actuator=ActuatorConfig(
            closed_angle_deg=float(item[CONF_CLOSED_ANGLE_DEG]),
            open_angle_deg=float(item[CONF_OPEN_ANGLE_DEG]),
            max_travel_angle_deg=float(item[CONF_MAX_TRAVEL_ANGLE_DEG]),
            open_actuator_percent=(
                float(item[CONF_OPEN_ACTUATOR_PERCENT])
                if CONF_OPEN_ACTUATOR_PERCENT in item
                else None
            ),
            closes_again_after_open=bool(item.get(CONF_CLOSES_AGAIN_AFTER_OPEN, False)),
        ),
        target=CommandTarget(
            entity_id=item[CONF_TARGET_ENTITY],
            mode=item[CONF_COMMAND_MODE],
            value_min=float(item.get(CONF_COMMAND_VALUE_MIN, 0.0)),
            value_max=float(item.get(CONF_COMMAND_VALUE_MAX, 100.0)),
        ),
        tracking=TrackingConfig(
            strategy=item[CONF_TRACKING_MODE],
            max_direct_sun_depth_m=float(item[CONF_MAX_DIRECT_SUN_DEPTH_M]),
            open_before_sunrise_minutes=int(item[CONF_OPEN_BEFORE_SUNRISE_MINUTES]),
            preopen_actuator_percent=int(item[CONF_PREOPEN_ACTUATOR_PERCENT]),
        ),
        weather=weather,
        additional_protected_area=AdditionalProtectedAreaConfig(
            enabled=bool(item.get(CONF_HAS_ADDITIONAL_PROTECTED_AREA, False)),
            length_m=float(item.get(CONF_ADDITIONAL_PROTECTED_AREA_LENGTH_M, 0.0)),
            width_m=float(item.get(CONF_ADDITIONAL_PROTECTED_AREA_WIDTH_M, 0.0)),
            offset_east_m=float(item.get(CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_EAST_M, 0.0)),
            offset_north_m=float(item.get(CONF_ADDITIONAL_PROTECTED_AREA_OFFSET_NORTH_M, 0.0)),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--step-minutes", type=int, default=15)
    parser.add_argument("--step-hours", type=float, default=1.0)
    parser.add_argument("--seconds-per-step", type=float, default=60.0)
    parser.add_argument("--playback", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--name")
    parser.add_argument("--entry-id")
    parser.add_argument("--source", choices=["auto", "yaml", "config_entries"], default="auto")
    parser.add_argument(
        "--config-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    args = parser.parse_args()

    root = Path(args.config_root)
    config_items = _load_profiles(root, args.source, args.name, args.entry_id)
    if not config_items:
        raise SystemExit("No Adaptive Pergola profiles found for the selected source/filter.")

    core_config = json.loads((root / "config" / ".storage" / "core.config").read_text())["data"]

    tz = ZoneInfo(core_config["time_zone"])
    day = date.fromisoformat(args.date)
    observer = Observer(
        latitude=core_config["latitude"],
        longitude=core_config["longitude"],
        elevation=core_config["elevation"],
    )
    solar_times = sun(observer, date=day, tzinfo=tz)
    weather = WeatherReadings(wind_speed=0.0, rain_rate=0.0, is_raining=False, is_windy=False, severe=False)
    start = datetime.combine(day, time(0, 0), tz)
    end = start + timedelta(days=1)
    step = timedelta(hours=args.step_hours) if args.playback else timedelta(minutes=args.step_minutes)
    profiles = [(item[CONF_NAME], item.get("__entry_id"), _build_control(item)) for item in config_items]

    print(f"Location: {core_config['latitude']:.6f}, {core_config['longitude']:.6f} ({core_config['time_zone']})")
    print(f"Date: {day.isoformat()}")
    print(f"Sunrise: {solar_times['sunrise'].strftime('%H:%M:%S %Z')}")
    print(f"Sunset:  {solar_times['sunset'].strftime('%H:%M:%S %Z')}")
    if args.playback:
        print(
            f"Playback: {args.step_hours:.2f} simulated hours per step, "
            f"{args.seconds_per_step:.2f} real seconds between steps"
        )
    print()

    for name, entry_id, control in profiles:
        print(f"=== {name} ===")
        if entry_id:
            print(f"entry_id={entry_id}")
        previous = None
        cursor = start
        while cursor < end:
            sun_position = SunPosition(
                azimuth_deg=azimuth(observer, cursor),
                elevation_deg=elevation(observer, cursor),
            )
            decision = compute_tracking_decision(
                control,
                sun_position,
                weather,
                now=cursor,
                next_sunrise=solar_times["sunrise"],
            )
            snapshot = (
                round(decision.target_angle_deg, 2),
                decision.strategy_used,
                bool(decision.hits_house_wall),
            )
            if args.playback or args.full or snapshot != previous:
                print(
                    f"{cursor.strftime('%H:%M')} angle={decision.target_angle_deg:6.2f}deg "
                    f"strategy={decision.strategy_used:>21} depth={decision.direct_sun_depth_m:4.2f}m "
                    f"house_hit={str(decision.hits_house_wall):5} sun_elev={sun_position.elevation_deg:6.2f}deg "
                    f"reason={decision.reason}"
                )
                previous = snapshot
                if args.playback and args.seconds_per_step > 0 and cursor + step < end:
                    time_module.sleep(args.seconds_per_step)
            cursor += step
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())