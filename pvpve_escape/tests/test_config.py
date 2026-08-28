"""集中設定與 GUI alpha 轉換測試。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from pvpve_escape import config


EXPECTED_OBSTACLE_LAYOUT = (
    ("thick_wall", 900, 500, 100, 160),
    ("thick_wall", 900, 400, 260, 100),
    ("thick_wall", 1400, 720, 100, 280),
    ("thick_wall", 1240, 900, 180, 100),
    ("thick_wall", 700, 700, 100, 300),
    ("thick_wall", 1600, 400, 100, 300),
    ("thick_wall", 1200, 200, 400, 100),
    ("thick_wall", 800, 1100, 400, 100),
    ("thick_wall", 1600, 900, 100, 300),
    ("thick_wall", 1300, 1100, 300, 100),
    ("thick_wall", 700, 200, 100, 300),
    ("thick_wall", 800, 200, 300, 100),
    ("thin_wall", 1700, 600, 300, 100),
    ("thin_wall", 400, 700, 300, 100),
    ("thin_wall", 2000, 600, 100, 400),
    ("thin_wall", 300, 400, 100, 400),
    ("thin_wall", 2000, 200, 100, 400),
    ("thin_wall", 300, 800, 100, 400),
)

EXPECTED_BUSH_LAYOUT = (
    (1000, 500, 400, 80),
    (1000, 820, 400, 80),
    (1000, 500, 100, 400),
    (1300, 500, 100, 400),
    (1100, 580, 200, 240),
    (800, 300, 100, 100),
    (1500, 1000, 100, 100),
    (1500, 300, 100, 100),
    (800, 1000, 100, 100),
    (1600, 200, 100, 200),
    (700, 1000, 100, 200),
    (1500, 700, 200, 200),
    (700, 500, 200, 200),
    (1100, 200, 100, 100),
    (1200, 1100, 100, 100),
    (0, 400, 300, 200),
    (0, 600, 300, 200),
    (0, 800, 300, 200),
    (2100, 800, 300, 200),
    (2100, 600, 300, 200),
    (2100, 400, 300, 200),
    (2100, 300, 300, 100),
    (0, 1000, 300, 100),
    (1500, 0, 200, 200),
    (700, 0, 200, 200),
    (700, 1200, 200, 200),
    (1500, 1200, 200, 200),
)


class ConfigValueTests(unittest.TestCase):
    def test_game_frame_rate_cap_is_120_fps(self) -> None:
        self.assertEqual(config.FPS, 120)

    def test_gui_opacity_defaults_and_alpha_are_stable(self) -> None:
        self.assertEqual(config.GUI_OPACITY_PERCENT, 50)
        self.assertEqual(config.clamp_gui_opacity_percent(), 50)
        self.assertEqual(config.gui_panel_alpha(), round(255 * 0.50))

    def test_gui_opacity_accepts_inclusive_endpoints(self) -> None:
        self.assertEqual(config.clamp_gui_opacity_percent(50), 50)
        self.assertEqual(config.clamp_gui_opacity_percent(90), 90)
        self.assertEqual(config.gui_panel_alpha(50), 128)
        self.assertEqual(config.gui_panel_alpha(90), 230)

    def test_gui_opacity_clamps_out_of_range_and_invalid_values(self) -> None:
        self.assertEqual(config.clamp_gui_opacity_percent(49), 50)
        self.assertEqual(config.clamp_gui_opacity_percent(91), 90)
        self.assertEqual(config.clamp_gui_opacity_percent("not-a-number"), 50)
        self.assertGreater(config.gui_panel_alpha(49), 0)
        self.assertLess(config.gui_panel_alpha(91), 255)

    def test_confirmed_map_layout_matches_editor_submission(self) -> None:
        self.assertEqual(config.OBSTACLE_LAYOUT, EXPECTED_OBSTACLE_LAYOUT)
        self.assertEqual(config.BUSH_LAYOUT, EXPECTED_BUSH_LAYOUT)
        self.assertEqual(len(config.OBSTACLE_LAYOUT), 18)
        self.assertEqual(len(config.BUSH_LAYOUT), 27)
        self.assertEqual(
            sum(kind == "thick_wall" for kind, *_ in config.OBSTACLE_LAYOUT),
            12,
        )
        self.assertEqual(
            sum(kind == "thin_wall" for kind, *_ in config.OBSTACLE_LAYOUT),
            6,
        )

    def test_saved_editor_snapshot_matches_formal_layout_constants(self) -> None:
        snapshot_path = Path(__file__).resolve().parents[2] / "specs" / "004-obstacles-breach-bushes" / "map-layout-draft.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

        self.assertEqual(snapshot["world_width"], config.WORLD_WIDTH)
        self.assertEqual(snapshot["world_height"], config.WORLD_HEIGHT)
        self.assertEqual(
            tuple(
                (
                    item["kind"],
                    item["left"],
                    item["top"],
                    item["width"],
                    item["height"],
                )
                for item in snapshot["items"]
                if item["kind"] != "bush"
            ),
            config.OBSTACLE_LAYOUT,
        )
        self.assertEqual(
            tuple(
                (
                    item["left"],
                    item["top"],
                    item["width"],
                    item["height"],
                )
                for item in snapshot["items"]
                if item["kind"] == "bush"
            ),
            config.BUSH_LAYOUT,
        )

    def test_confirmed_map_layout_stays_inside_world_bounds(self) -> None:
        rectangles = [
            (*entry[1:],) for entry in config.OBSTACLE_LAYOUT
        ] + list(config.BUSH_LAYOUT)
        for left, top, width, height in rectangles:
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(top, 0)
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
            self.assertLessEqual(left + width, config.WORLD_WIDTH)
            self.assertLessEqual(top + height, config.WORLD_HEIGHT)

    def test_confirmed_red_overlaps_are_explicitly_retained(self) -> None:
        reserved: list[tuple[str, float, float, float, float]] = [
            (
                f"出生點 {index + 1}",
                point.x - config.TERRAIN_SPAWN_SAFE_RADIUS,
                point.y - config.TERRAIN_SPAWN_SAFE_RADIUS,
                config.TERRAIN_SPAWN_SAFE_RADIUS * 2,
                config.TERRAIN_SPAWN_SAFE_RADIUS * 2,
            )
            for index, point in enumerate(config.SPAWN_POINTS)
        ]
        reserved.extend(
            (
                f"怪物區 {index + 1}",
                point.x - config.TERRAIN_CAMP_SAFE_RADIUS,
                point.y - config.TERRAIN_CAMP_SAFE_RADIUS,
                config.TERRAIN_CAMP_SAFE_RADIUS * 2,
                config.TERRAIN_CAMP_SAFE_RADIUS * 2,
            )
            for index, point in enumerate(config.MONSTER_CAMP_POINTS)
        )
        reserved.append(
            (
                "中央撤離區",
                config.EXTRACTION_CENTER.x
                - config.EXTRACTION_RADIUS
                - config.TERRAIN_EXTRACTION_SAFE_PADDING,
                config.EXTRACTION_CENTER.y
                - config.EXTRACTION_RADIUS
                - config.TERRAIN_EXTRACTION_SAFE_PADDING,
                (config.EXTRACTION_RADIUS + config.TERRAIN_EXTRACTION_SAFE_PADDING) * 2,
                (config.EXTRACTION_RADIUS + config.TERRAIN_EXTRACTION_SAFE_PADDING) * 2,
            )
        )

        def overlaps(
            item: tuple[int, int, int, int],
            zone: tuple[str, float, float, float, float],
        ) -> bool:
            left, top, width, height = item
            _, zone_left, zone_top, zone_width, zone_height = zone
            return (
                left < zone_left + zone_width
                and left + width > zone_left
                and top < zone_top + zone_height
                and top + height > zone_top
            )

        retained: set[tuple[str, int, int, int, int, str]] = set()
        for kind, left, top, width, height in config.OBSTACLE_LAYOUT:
            for zone in reserved:
                zone_name = zone[0]
                if overlaps((left, top, width, height), zone):
                    retained.add((kind, left, top, width, height, zone_name))
        for left, top, width, height in config.BUSH_LAYOUT:
            for zone in reserved:
                zone_name = zone[0]
                if overlaps((left, top, width, height), zone):
                    retained.add(("bush", left, top, width, height, zone_name))
        expected = {
            ("bush", 1000, 500, 400, 80, "中央撤離區"),
            ("bush", 1000, 820, 400, 80, "中央撤離區"),
            ("bush", 1000, 500, 100, 400, "中央撤離區"),
            ("bush", 1300, 500, 100, 400, "中央撤離區"),
            ("bush", 1100, 580, 200, 240, "中央撤離區"),
        }
        self.assertEqual(retained, expected)

    def test_terrain_visual_and_regeneration_constants_are_stable(self) -> None:
        self.assertEqual(config.THICK_WALL_COLOR, (115, 93, 105))
        self.assertEqual(config.THIN_WALL_COLOR, (212, 143, 62))
        self.assertEqual(config.WALL_BORDER_COLOR, (235, 240, 242))
        self.assertEqual(config.BUSH_COLOR, (74, 156, 91))
        self.assertEqual(config.BUSH_HIGHLIGHT_COLOR, (144, 211, 116))
        self.assertEqual(config.PLAYER_REGEN_DELAY, 5.0)
        self.assertEqual(config.PLAYER_REGEN_RATE, 0.10)


if __name__ == "__main__":
    unittest.main()
