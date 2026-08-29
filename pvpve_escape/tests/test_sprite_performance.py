"""像素角色預載入後的 headless 繪製效能驗證。"""

from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, sprites
from pvpve_escape.models import CharacterId, Vector2
from pvpve_escape.rendering import draw_player_visual
from pvpve_escape.world import create_match


class SniperSpritePerformanceTests(unittest.TestCase):
    """用十秒模擬時間檢查預載入後繪製不再讀檔。"""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_headless_ten_second_sprite_rendering_has_no_runtime_image_reads(self) -> None:
        sprites.clear_character_sprite_cache()
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        player = create_match(CharacterId.SNIPER).players[0]
        player.aim_direction = Vector2(1, 0)

        with patch.object(pygame.image, "load", wraps=pygame.image.load) as image_load:
            self.assertEqual(
                sprites.preload_character_sprites(
                    CharacterId.BREACHER,
                    display_sizes=(50, 54, 24),
                ),
                72,
            )
            self.assertEqual(
                sprites.preload_character_sprites(
                    CharacterId.SNIPER,
                    display_sizes=(50, 54, 24),
                ),
                72,
            )
            self.assertEqual(image_load.call_count, 144)
            image_load.reset_mock()

            frame_count = 600
            simulated_delta = 1.0 / 60.0
            intervals: list[float] = []
            started = time.perf_counter()
            previous = started
            for frame_index in range(frame_count):
                now = time.perf_counter()
                intervals.append(now - previous)
                previous = now
                if frame_index % 180 == 0:
                    sprites.start_or_refresh_attack_animation(player)
                sprites.update_player_animation(player, Vector2(1, 0), simulated_delta)
                surface.fill(config.GROUND_COLOR)
                draw_player_visual(surface, player, (320, 240), config.ACCENT_COLOR)
            elapsed = time.perf_counter() - started

            average_fps = frame_count / max(elapsed, 1e-9)
            maximum_frame_interval_ms = max(intervals, default=0.0) * 1000.0
            runtime_image_loads = image_load.call_count

        print(
            "SPRITE_PERFORMANCE "
            f"simulated_seconds={frame_count * simulated_delta:.2f} "
            f"average_fps={average_fps:.2f} "
            f"max_frame_interval_ms={maximum_frame_interval_ms:.2f} "
            f"runtime_image_loads={runtime_image_loads}"
        )
        self.assertGreaterEqual(average_fps, 60.0)
        self.assertLessEqual(maximum_frame_interval_ms, 100.0)
        self.assertEqual(runtime_image_loads, 0)


if __name__ == "__main__":
    unittest.main()
