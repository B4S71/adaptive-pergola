from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import azimuth, elevation

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.simulate_target_angles import _build_control, _load_profiles
from custom_components.adaptive_pergola.engine import (
    _east_north_offset_to_local,
    _full_sun_penetration_depth,
    _projected_elevation_magnitude_deg,
    _roof_normal_azimuth_deg,
    _shadow_casting_wall_polygon,
    _sun_patch_rect,
    _width_axis_azimuth_deg,
    light_angle_for_sun,
)
from custom_components.adaptive_pergola.models import ShadowCastingWallConfig, SunPosition
from custom_components.adaptive_pergola.sun import signed_angle_delta


def _panel_xy(
    x: float,
    y: float,
    *,
    min_x: float,
    max_y: float,
    scale: float,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    panel_x = origin_x + 38 + (x - min_x) * scale
    panel_y = origin_y + 36 + (max_y - y) * scale
    return (panel_x, panel_y)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "simulation_exports"
    out_dir.mkdir(exist_ok=True)

    item = _load_profiles(root, "config_entries", "Adaptive Pergola", None)[0]
    control = _build_control(item)
    geometry = control.geometry
    core = json.loads((root / "config" / ".storage" / "core.config").read_text())["data"]

    tz = ZoneInfo(core["time_zone"])
    observer = Observer(
        latitude=core["latitude"],
        longitude=core["longitude"],
        elevation=core["elevation"],
    )

    # Skizzennahe Interpretation: Mauer links neben der Pergola, parallel zur Pergola-Lange.
    wall = ShadowCastingWallConfig(
        enabled=True,
        length_m=3.0,
        height_m=2.8,
        offset_east_m=0.0,
        offset_north_m=2.0,
    )

    sample_times = [
        "09:30",
        "10:00",
        "10:30",
        "11:00",
        "11:30",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
    ]

    panels: list[dict] = []
    for time_label in sample_times:
        hour, minute = map(int, time_label.split(":"))
        when = datetime(2026, 4, 29, hour, minute, tzinfo=tz)
        sun_pos = SunPosition(
            azimuth_deg=azimuth(observer, when),
            elevation_deg=elevation(observer, when),
        )
        light_angle = light_angle_for_sun(geometry, control.actuator, sun_pos)
        front_delta = signed_angle_delta(_roof_normal_azimuth_deg(geometry), sun_pos.azimuth_deg)
        width_delta = signed_angle_delta(_width_axis_azimuth_deg(geometry), sun_pos.azimuth_deg)
        front_full_depth = _full_sun_penetration_depth(
            geometry,
            _projected_elevation_magnitude_deg(sun_pos.elevation_deg, front_delta),
        )
        width_full_depth = _full_sun_penetration_depth(
            geometry,
            _projected_elevation_magnitude_deg(sun_pos.elevation_deg, width_delta),
        )
        panels.append(
            {
                "time": time_label,
                "sun": sun_pos,
                "light_angle": light_angle,
                "sun_patch": _sun_patch_rect(
                    geometry,
                    sun_pos,
                    front_full_depth,
                    width_full_depth,
                ),
                "wall_shadow": _shadow_casting_wall_polygon(geometry, sun_pos, wall),
            }
        )

    all_x = [-6.5, 10.0]
    all_y = [-7.5, 9.5]
    for panel in panels:
        patch = panel["sun_patch"]
        all_x.extend([patch.start_x_m, patch.end_x_m])
        all_y.extend([patch.start_y_m, patch.end_y_m])
        for point_x, point_y in panel["wall_shadow"]:
            all_x.append(point_x)
            all_y.append(point_y)

    min_x = min(all_x) - 0.6
    max_x = max(all_x) + 0.6
    min_y = min(all_y) - 0.6
    max_y = max(all_y) + 0.6

    panel_w = 360
    panel_h = 300
    cols = 3
    rows = (len(panels) + cols - 1) // cols
    svg_w = cols * panel_w + 48
    svg_h = rows * panel_h + 72
    scale = min((panel_w - 70) / (max_x - min_x), (panel_h - 90) / (max_y - min_y))

    house_left = -6.0
    house_right = 8.0
    house_bottom = -7.0
    house_top = 0.0
    pergola_left = 0.0
    pergola_right = geometry.pergola_length_m
    pergola_bottom = 0.0
    pergola_top = geometry.pergola_width_m
    protected_left = geometry.pergola_length_m
    protected_right = geometry.pergola_length_m + control.additional_protected_area.length_m
    protected_bottom = control.additional_protected_area.offset_north_m
    protected_top = protected_bottom + control.additional_protected_area.width_m
    wall_start_x, wall_start_y = _east_north_offset_to_local(
        geometry,
        wall.offset_east_m,
        wall.offset_north_m,
    )
    wall_end_x = wall_start_x + wall.length_m
    wall_thickness = 0.22

    svg: list[str] = []
    append = svg.append
    append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}">'
    )
    append(
        '<style>'
        'text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #111827; } '
        '.title { font-size: 24px; font-weight: 700; } '
        '.subtitle { font-size: 13px; fill: #374151; } '
        '.panel-title { font-size: 15px; font-weight: 700; } '
        '.small { font-size: 11px; fill: #4b5563; } '
        '.label { font-size: 12px; font-weight: 600; } '
        '.grid { stroke: #e5e7eb; stroke-width: 1; } '
        '</style>'
    )
    append('<rect width="100%" height="100%" fill="#f8fafc" />')
    append('<text x="24" y="30" class="title">Adaptive Pergola - Schattenverlauf mit Seitenmauer</text>')
    append('<text x="24" y="50" class="subtitle">Skizzennahe Draufsicht: Grau = Haus, Weiss = Pergola, Rosa = Protected Area, Blau = direkter Sonnenfleck, rot gestrichelt = Mauer-Schatten.</text>')

    for index, panel in enumerate(panels):
        row = index // cols
        col = index % cols
        origin_x = 16 + col * panel_w
        origin_y = 62 + row * panel_h
        append(
            f'<rect x="{origin_x}" y="{origin_y}" width="{panel_w - 12}" height="{panel_h - 16}" '
            'rx="12" fill="#ffffff" stroke="#d1d5db" />'
        )
        append(f'<text x="{origin_x + 16}" y="{origin_y + 24}" class="panel-title">{panel["time"]}</text>')
        append(
            f'<text x="{origin_x + 84}" y="{origin_y + 24}" class="small">'
            f'Sonne {panel["sun"].azimuth_deg:.1f}° / {panel["sun"].elevation_deg:.1f}°'
            '</text>'
        )

        for grid_x in range(int(min_x), int(max_x) + 1):
            x1, y1 = _panel_xy(grid_x, min_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
            x2, y2 = _panel_xy(grid_x, max_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
            append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="grid" />')
        for grid_y in range(int(min_y), int(max_y) + 1):
            x1, y1 = _panel_xy(min_x, grid_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
            x2, y2 = _panel_xy(max_x, grid_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
            append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="grid" />')

        hx1, hy1 = _panel_xy(house_left, house_bottom, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        hx2, hy2 = _panel_xy(house_right, house_top, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        append(
            f'<rect x="{hx1:.1f}" y="{hy2:.1f}" width="{(hx2 - hx1):.1f}" height="{(hy1 - hy2):.1f}" '
            'fill="#e5e7eb" stroke="#111827" stroke-width="1.5" />'
        )
        append(f'<text x="{(hx1 + hx2) / 2:.1f}" y="{(hy1 + hy2) / 2:.1f}" text-anchor="middle" class="label">Haus</text>')

        px1, py1 = _panel_xy(pergola_left, pergola_bottom, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        px2, py2 = _panel_xy(pergola_right, pergola_top, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        append(
            f'<rect x="{px1:.1f}" y="{py2:.1f}" width="{(px2 - px1):.1f}" height="{(py1 - py2):.1f}" '
            'fill="#ffffff" stroke="#111827" stroke-width="1.8" />'
        )
        append(f'<text x="{(px1 + px2) / 2:.1f}" y="{(py1 + py2) / 2:.1f}" text-anchor="middle" class="label">Pergola</text>')

        pr1x, pr1y = _panel_xy(protected_left, protected_bottom, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        pr2x, pr2y = _panel_xy(protected_right, protected_top, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        append(
            f'<rect x="{pr1x:.1f}" y="{pr2y:.1f}" width="{(pr2x - pr1x):.1f}" height="{(pr1y - pr2y):.1f}" '
            'fill="#fee2e2" fill-opacity="0.75" stroke="#dc2626" stroke-width="1.4" stroke-dasharray="6 4" />'
        )
        append(
            f'<text x="{(pr1x + pr2x) / 2:.1f}" y="{(pr1y + pr2y) / 2:.1f}" text-anchor="middle" class="label">'
            'Protected Area</text>'
        )

        wx1, wy1 = _panel_xy(wall_start_x - wall_thickness, wall_start_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        wx2, wy2 = _panel_xy(wall_start_x, wall_end_x, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        wall_rect_x = min(wx1, wx2)
        wall_rect_y = min(wy1, wy2)
        wall_rect_w = abs(wx2 - wx1)
        wall_rect_h = abs(wy2 - wy1)
        append(
            f'<rect x="{wall_rect_x:.1f}" y="{wall_rect_y:.1f}" width="{wall_rect_w:.1f}" height="{wall_rect_h:.1f}" '
            'fill="#b91c1c" fill-opacity="0.75" stroke="#7f1d1d" stroke-width="1.2" />'
        )
        append(f'<text x="{wall_rect_x - 4:.1f}" y="{wall_rect_y + 12:.1f}" text-anchor="end" class="small">Mauer</text>')

        patch = panel["sun_patch"]
        patch_points = [
            (patch.start_x_m, patch.start_y_m),
            (patch.end_x_m, patch.start_y_m),
            (patch.end_x_m, patch.end_y_m),
            (patch.start_x_m, patch.end_y_m),
        ]
        patch_svg = []
        for point_x, point_y in patch_points:
            panel_x, panel_y = _panel_xy(point_x, point_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
            patch_svg.append(f'{panel_x:.1f},{panel_y:.1f}')
        patch_points_text = ' '.join(patch_svg)
        append(
            f'<polygon points="{patch_points_text}" fill="#93c5fd" fill-opacity="0.45" '
            'stroke="#2563eb" stroke-width="1.2" />'
        )

        if panel["wall_shadow"]:
            wall_shadow_svg = []
            for point_x, point_y in panel["wall_shadow"]:
                panel_x, panel_y = _panel_xy(point_x, point_y, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
                wall_shadow_svg.append(f'{panel_x:.1f},{panel_y:.1f}')
            wall_shadow_points_text = ' '.join(wall_shadow_svg)
            append(
                f'<polygon points="{wall_shadow_points_text}" fill="#7f1d1d" fill-opacity="0.18" '
                'stroke="#991b1b" stroke-width="1.1" stroke-dasharray="4 3" />'
            )

        append(
            f'<defs><marker id="arrow-{index}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            '<polygon points="0,0 8,4 0,8" fill="#f59e0b" /></marker></defs>'
        )
        arrow_start_x, arrow_start_y = _panel_xy(-4.8, 8.2, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        arrow_end_x, arrow_end_y = _panel_xy(-3.6, 7.0, min_x=min_x, max_y=max_y, scale=scale, origin_x=origin_x, origin_y=origin_y)
        append(
            f'<line x1="{arrow_start_x:.1f}" y1="{arrow_start_y:.1f}" x2="{arrow_end_x:.1f}" y2="{arrow_end_y:.1f}" '
            f'stroke="#f59e0b" stroke-width="2.4" marker-end="url(#arrow-{index})" />'
        )
        append(f'<text x="{arrow_start_x - 2:.1f}" y="{arrow_start_y - 6:.1f}" class="small">Sonne</text>')

        info_y = origin_y + panel_h - 32
        append(f'<text x="{origin_x + 16}" y="{info_y:.1f}" class="small">Light-Winkel: {panel["light_angle"]:.1f}°</text>')
        append(f'<text x="{origin_x + 150}" y="{info_y:.1f}" class="small">Mauer: 3.0 m x 2.8 m</text>')

    append('</svg>')
    output_path = out_dir / 'adaptive_pergola_wall_shadow_timeline.svg'
    output_path.write_text('\n'.join(svg), encoding='utf-8')
    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())