"""地圖編輯器的單格布局載入與保存測試。"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pvpve_escape import config, map_editor
from pvpve_escape.tests.test_helpers import headless_pygame


class MapEditorTerrainTests(unittest.TestCase):
    def make_editor(self) -> map_editor.MapEditor:
        editor = map_editor.MapEditor.__new__(map_editor.MapEditor)
        editor.status_message = ""
        editor.status_until = 0
        return editor

    def test_loading_old_rectangles_normalizes_to_single_priority_cells(self) -> None:
        old_layout = {
            "world_width": config.WORLD_WIDTH,
            "world_height": config.WORLD_HEIGHT,
            "items": [
                {"kind": "thin_wall", "left": 40, "top": 40, "width": 220, "height": 120},
                {"kind": "bush", "left": 100, "top": 0, "width": 100, "height": 100},
                {"kind": "thick_wall", "left": 0, "top": 0, "width": 100, "height": 100},
            ],
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "old-layout.json"
            path.write_text(json.dumps(old_layout), encoding="utf-8")
            editor = self.make_editor()
            with patch.object(map_editor, "SAVE_PATH", path):
                items = editor._load_items()

        self.assertEqual(
            [(item.kind, item.left, item.top) for item in items],
            [
                ("thick_wall", 0, 0),
                ("thin_wall", 100, 0),
                ("thin_wall", 200, 0),
                ("thin_wall", 0, 100),
                ("thin_wall", 100, 100),
                ("thin_wall", 200, 100),
            ],
        )

    def test_save_writes_only_aligned_100px_items_after_normalization(self) -> None:
        editor = self.make_editor()
        editor.items = [
            map_editor.LayoutItem("thin_wall", 40, 40, 220, 120),
            map_editor.LayoutItem("bush", 100, 0, 100, 100),
            map_editor.LayoutItem("thick_wall", 0, 0, 100, 100),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory, headless_pygame():
            path = Path(temporary_directory) / "saved-layout.json"
            with patch.object(map_editor, "SAVE_PATH", path):
                editor.save()
            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(len(saved["items"]), 6)
        self.assertTrue(
            all(
                item["width"] == config.TERRAIN_CELL_SIZE
                and item["height"] == config.TERRAIN_CELL_SIZE
                and item["left"] % config.TERRAIN_CELL_SIZE == 0
                and item["top"] % config.TERRAIN_CELL_SIZE == 0
                for item in saved["items"]
            )
        )
        self.assertEqual(
            {(item["left"], item["top"]) for item in saved["items"]},
            {(0, 0), (100, 0), (200, 0), (0, 100), (100, 100), (200, 100)},
        )


if __name__ == "__main__":
    unittest.main()
