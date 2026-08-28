"""地圖素材快取與固定場景繪製效能基準。"""

from __future__ import annotations

import os
import platform
import sys
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.controllers import InputState
from pvpve_escape.tests.test_helpers import reset_rendering_test_state
from pvpve_escape.world import create_match, update_world


WARMUP_FRAMES = 120
MEASURED_FRAMES = 600


class MapPerformanceTests(unittest.TestCase):
    last_measurement: dict[str, object] = {}

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        reset_rendering_test_state()

    @classmethod
    def tearDownClass(cls) -> None:
        reset_rendering_test_state()

    def test_cached_map_rendering_maintains_55_fps_after_warmup(self) -> None:
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        match = create_match()
        input_state = InputState()
        fixed_delta = 1.0 / 60.0
        warmup_frames = WARMUP_FRAMES
        measured_frames = MEASURED_FRAMES

        for _ in range(warmup_frames):
            update_world(match, {0: input_state}, fixed_delta)
            rendering.draw_match(surface, match, input_state)

        cached_assets = {
            key: rendering.load_map_asset(key)
            for key in rendering.MAP_ASSET_FILENAMES
        }
        started_at = time.monotonic()
        with patch.object(pygame.image, "load", side_effect=AssertionError("PNG must not be loaded during measurement")):
            for _ in range(measured_frames):
                update_world(match, {0: input_state}, fixed_delta)
                rendering.draw_match(surface, match, input_state)
        elapsed_seconds = time.monotonic() - started_at
        average_fps = measured_frames / max(elapsed_seconds, 1e-9)

        measurement = {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "pygame": pygame.version.ver,
            "window": f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}",
            "warmup_frames": warmup_frames,
            "measured_frames": measured_frames,
            "elapsed_seconds": round(elapsed_seconds, 4),
            "average_fps": round(average_fps, 2),
        }
        self.__class__.last_measurement = measurement
        print(f"map performance: {measurement}")

        self.assertEqual(measurement["window"], "1280x720")
        self.assertEqual(measurement["warmup_frames"], WARMUP_FRAMES)
        self.assertEqual(measurement["measured_frames"], MEASURED_FRAMES)
        self.assertEqual(config.MAX_FPS, 120)
        self.assertGreaterEqual(average_fps, 55.0, measurement)
        for key, asset in cached_assets.items():
            self.assertIs(asset, rendering.load_map_asset(key))


if __name__ == "__main__":
    unittest.main()
