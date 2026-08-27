"""集中設定與 GUI alpha 轉換測試。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from pvpve_escape import config


EXPECTED_OBSTACLE_LAYOUT = (
    ("thick_wall", 900, 500, 100, 160),
    ("thick_wall", 900, 400, 260, 100),
    ("thick_wall", 1400, 760, 100, 160),
    ("thick_wall", 1220, 920, 280, 100),
    ("thin_wall", 680, 400, 80, 220),
    ("thin_wall", 660, 820, 100, 220),
    ("thin_wall", 1640, 420, 80, 240),
    ("thin_wall", 1640, 800, 80, 220),
    ("thin_wall", 1240, 340, 220, 60),
    ("thin_wall", 1140, 1020, 80, 80),
    ("thin_wall", 1680, 0, 80, 100),
    ("thin_wall", 2020, 1100, 80, 300),
    ("thin_wall", 2260, 920, 140, 40),
    ("thin_wall", 2020, 0, 80, 340),
    ("thin_wall", 2300, 320, 80, 40),
    ("thin_wall", 540, 140, 400, 80),
    ("thin_wall", 540, 1180, 320, 60),
    ("thin_wall", 300, 400, 80, 220),
)

EXPECTED_BUSH_LAYOUT = (
    (1000, 500, 400, 80),
    (1000, 820, 400, 80),
    (1000, 500, 100, 400),
    (1300, 500, 100, 400),
    (1480, 200, 220, 120),
    (1720, 640, 500, 180),
    (140, 620, 620, 200),
    (840, 1100, 300, 100),
    (1540, 1140, 340, 120),
    (800, 220, 340, 120),
    (240, 1040, 360, 160),
    (1900, 320, 400, 140),
    (2040, 960, 220, 140),
    (20, 140, 260, 80),
    (820, 740, 100, 240),
    (1480, 500, 100, 180),
)


class ConfigValueTests(unittest.TestCase):
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
        self.assertEqual(len(config.BUSH_LAYOUT), 16)
        self.assertEqual(
            sum(kind == "thick_wall" for kind, *_ in config.OBSTACLE_LAYOUT),
            4,
        )
        self.assertEqual(
            sum(kind == "thin_wall" for kind, *_ in config.OBSTACLE_LAYOUT),
            14,
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
            ("bush", 1540, 1140, 340, 120, "怪物區 4"),
            ("bush", 240, 1040, 360, 160, "出生點 4"),
            ("bush", 240, 1040, 360, 160, "怪物區 3"),
            ("bush", 1900, 320, 400, 140, "怪物區 2"),
            ("thin_wall", 540, 140, 400, 80, "出生點 1"),
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
