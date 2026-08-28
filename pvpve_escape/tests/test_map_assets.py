"""正式地圖 PNG 素材的尺寸、快取與備援測試。"""

from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.tests.test_helpers import reset_rendering_test_state
from pvpve_escape.world import create_match


class MapAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        reset_rendering_test_state()
        pygame.display.quit()

    def setUp(self) -> None:
        reset_rendering_test_state()

    def test_all_runtime_tiles_exist_are_100px_and_fully_opaque(self) -> None:
        asset_root = Path(rendering.__file__).resolve().parent / "assets" / "map"

        for asset_key in rendering.MAP_ASSET_FILENAMES:
            path = asset_root / rendering.MAP_ASSET_FILENAMES[asset_key]
            self.assertTrue(path.is_file(), f"missing map asset: {path}")
            surface = pygame.image.load(str(path))
            self.assertEqual(surface.get_size(), (config.TERRAIN_CELL_SIZE,) * 2)
            self.assertTrue(
                all(
                    surface.get_at((x, y)).a == 255
                    for x in range(config.TERRAIN_CELL_SIZE)
                    for y in range(config.TERRAIN_CELL_SIZE)
                ),
                f"{asset_key} must fill its entire tile",
            )

    def test_each_tile_loads_once_and_reuses_the_cached_surface(self) -> None:
        original_load = pygame.image.load

        with patch.object(pygame.image, "load", wraps=original_load) as load:
            first = rendering.load_map_asset("ground")
            second = rendering.load_map_asset("ground")

        self.assertIsNotNone(first)
        self.assertIs(first, second)
        self.assertEqual(load.call_count, 1)

    def test_missing_wall_tile_uses_the_existing_procedural_fallback(self) -> None:
        match = create_match()
        match.camera.position.x = 0
        match.camera.position.y = 0
        obstacle = next(item for item in match.obstacles if item.kind.value == "thin_wall")
        surface = pygame.Surface((config.WORLD_WIDTH, config.WORLD_HEIGHT))
        surface.fill(config.GROUND_COLOR)

        with patch.dict(rendering.MAP_ASSET_FILENAMES, {"thin_wall": "does-not-exist.png"}):
            rendering.draw_terrain(surface, match)

        center = (round(obstacle.bounds.center.x), round(obstacle.bounds.center.y))
        self.assertEqual(surface.get_at(center)[:3], config.THIN_WALL_COLOR)


if __name__ == "__main__":
    unittest.main()
