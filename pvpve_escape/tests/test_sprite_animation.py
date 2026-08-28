"""破陣者素材、方向量化與動畫狀態測試。"""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, sprites
from pvpve_escape.models import Vector2
from pvpve_escape.world import create_match


class BreacherSpriteAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        sprites.clear_breacher_sprite_cache()

    def test_all_72_assets_have_the_required_shape_and_transparency(self) -> None:
        asset_root = Path(__file__).resolve().parents[1] / "assets" / "characters" / "breacher"
        files = list(asset_root.rglob("*.png"))
        self.assertEqual(len(files), 72)

        for direction_index, direction_name in enumerate(sprites.BREACHER_DIRECTION_NAMES):
            idle = sprites.load_breacher_sprite("idle", direction_index, 0)
            self.assertIsNotNone(idle, direction_name)
            self.assertEqual(idle.get_size(), (config.BREACHER_SPRITE_SOURCE_SIZE,) * 2)
            self._assert_valid_canvas(idle)

            for visual_state in ("move", "attack"):
                for frame_index in range(config.BREACHER_ANIMATION_FRAME_COUNT):
                    frame = sprites.load_breacher_sprite(visual_state, direction_index, frame_index)
                    self.assertIsNotNone(frame, f"{visual_state}/{direction_name}/{frame_index}")
                    self.assertEqual(frame.get_size(), (config.BREACHER_SPRITE_SOURCE_SIZE,) * 2)
                    self._assert_valid_canvas(frame)

    def test_direction_quantization_uses_eight_stable_sectors(self) -> None:
        directions = (
            (Vector2(1, 0), 0),
            (Vector2(1, 1), 1),
            (Vector2(0, 1), 2),
            (Vector2(-1, 1), 3),
            (Vector2(-1, 0), 4),
            (Vector2(-1, -1), 5),
            (Vector2(0, -1), 6),
            (Vector2(1, -1), 7),
            (Vector2(), 0),
        )
        for vector, expected in directions:
            self.assertEqual(sprites.quantize_sprite_direction(vector), expected)

    def test_animation_frame_request_uses_attack_priority_and_four_frame_ranges(self) -> None:
        player = create_match().players[0]
        player.aim_direction = Vector2(-1, 0)

        sprites.update_player_animation(player, Vector2(-1, 0), 0.10)
        self.assertEqual(player.animation_state.facing_direction_index, 4)
        self.assertTrue(player.animation_state.moving)
        self.assertEqual(sprites.current_sprite_request(player), ("move", 4, 1))

        sprites.start_or_refresh_attack_animation(player)
        self.assertEqual(sprites.current_sprite_request(player), ("attack", 4, 0))
        sprites.update_player_animation(player, Vector2(-1, 0), 0.06)
        self.assertEqual(sprites.current_sprite_request(player), ("attack", 4, 1))

        elapsed_before_refresh = player.animation_state.attack_elapsed
        sprites.start_or_refresh_attack_animation(player)
        self.assertEqual(player.animation_state.attack_elapsed, elapsed_before_refresh)
        self.assertTrue(player.animation_state.attack_hold >= config.BREACHER_ATTACK_DURATION)

        sprites.update_player_animation(player, Vector2(), config.BREACHER_ATTACK_DURATION)
        self.assertEqual(sprites.current_sprite_request(player), ("idle", 4, 0))

    def test_invalid_queries_return_unavailable_result_and_record_error(self) -> None:
        for query in (
            ("unknown", 0, 0),
            ("idle", 0, 1),
            ("move", 0, 4),
            ("attack", 8, 0),
            ("attack", -1, 0),
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self.assertIsNone(sprites.load_breacher_sprite(*query))
            self.assertIsNotNone(sprites.breacher_sprite_error(*query))

    def test_valid_asset_is_scaled_with_cache_identity(self) -> None:
        with patch.object(pygame.image, "load", wraps=pygame.image.load) as image_load:
            first = sprites.load_breacher_sprite("idle", 0, 0, display_size=72)
            second = sprites.load_breacher_sprite("idle", 0, 0, display_size=72)

        self.assertIsNotNone(first)
        self.assertIs(first, second)
        self.assertEqual(first.get_size(), (72, 72))
        self.assertEqual(image_load.call_count, 1)

    def test_displayed_assets_normalize_visible_extent_to_requested_canvas(self) -> None:
        requests = (
            ("idle", 0, 0),
            ("idle", 2, 0),
            ("move", 4, 1),
            ("attack", 1, 2),
            ("attack", 6, 3),
        )
        for visual_state, direction_index, frame_index in requests:
            sprite = sprites.load_breacher_sprite(
                visual_state,
                direction_index,
                frame_index,
                display_size=config.BREACHER_SPRITE_DISPLAY_SIZE,
            )
            self.assertIsNotNone(sprite)
            self.assertEqual(sprite.get_size(), (50, 50))
            bounds = sprite.get_bounding_rect(min_alpha=16)
            self.assertEqual(max(bounds.width, bounds.height), 50)
            self.assertLessEqual(abs(bounds.centerx - 25), 1)
            self.assertLessEqual(abs(bounds.centery - 25), 1)

    def test_clearing_sprite_cache_forces_each_image_to_be_read_again(self) -> None:
        with patch.object(pygame.image, "load", wraps=pygame.image.load) as image_load:
            first = sprites.load_breacher_sprite("idle", 0, 0, display_size=50)
            sprites.clear_breacher_sprite_cache()
            second = sprites.load_breacher_sprite("idle", 0, 0, display_size=50)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(image_load.call_count, 2)

    def test_preload_reads_and_extracts_all_72_images_once(self) -> None:
        with patch.object(pygame.image, "load", wraps=pygame.image.load) as image_load:
            loaded_count = sprites.preload_breacher_sprites(50)

        self.assertEqual(loaded_count, 72)
        self.assertEqual(image_load.call_count, 72)
        displayed = [
            surface
            for (visual_state, direction_index, frame_index, size), surface in sprites._SPRITE_CACHE.items()
            if size == (50, 50)
        ]
        self.assertEqual(len(displayed), 72)
        for surface in displayed:
            self.assertEqual(max(surface.get_bounding_rect(min_alpha=16).size), 50)

    def test_failed_asset_is_cached_and_not_reloaded_every_frame(self) -> None:
        missing_path = Path("missing-breacher-frame.png")
        with patch.object(sprites, "_path_for_request", return_value=missing_path):
            with patch.object(pygame.image, "load", side_effect=OSError("missing")) as image_load:
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter("always")
                    self.assertIsNone(sprites.load_breacher_sprite("move", 0, 0))
                    self.assertIsNone(sprites.load_breacher_sprite("move", 0, 0))
        self.assertEqual(image_load.call_count, 0)
        self.assertIsNotNone(sprites.breacher_sprite_error("move", 0, 0))
        self.assertEqual(len(captured), 1)
        self.assertIn("幾何 fallback", str(captured[0].message))

    def test_invalid_dimensions_and_opaque_backgrounds_return_unavailable_result(self) -> None:
        source_path = Path(__file__)
        invalid_surfaces = (
            pygame.Surface((64, 64), pygame.SRCALPHA),
            pygame.Surface((config.BREACHER_SPRITE_SOURCE_SIZE,) * 2),
        )
        invalid_surfaces[-1].fill((24, 24, 24))

        for fake_surface in invalid_surfaces:
            sprites.clear_breacher_sprite_cache()
            with patch.object(sprites, "_path_for_request", return_value=source_path):
                with patch.object(pygame.image, "load", return_value=fake_surface):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)
                        self.assertIsNone(sprites.load_breacher_sprite("move", 0, 0))
            self.assertIsNotNone(sprites.breacher_sprite_error("move", 0, 0))

    def test_death_and_respawn_clear_animation_progress_without_changing_facing(self) -> None:
        from pvpve_escape.rules import handle_player_death, respawn_player

        player = create_match().players[0]
        player.animation_state.facing_direction_index = 6
        player.animation_state.moving = True
        player.animation_state.move_elapsed = 0.19
        player.animation_state.attack_elapsed = 0.12
        player.animation_state.attack_hold = 0.24

        handle_player_death(player)
        self.assertEqual(player.animation_state.facing_direction_index, 6)
        self.assertFalse(player.animation_state.moving)
        self.assertEqual(player.animation_state.move_elapsed, 0.0)
        self.assertEqual(player.animation_state.attack_elapsed, 0.0)
        self.assertEqual(player.animation_state.attack_hold, 0.0)

        respawn_player(player, player.spawn_position)
        self.assertEqual(player.animation_state.facing_direction_index, 6)
        self.assertFalse(player.animation_state.attack_active)

    def test_breacher_actions_start_attack_visual_state(self) -> None:
        from pvpve_escape.characters import create_primary_action
        from pvpve_escape.world import _apply_action

        match = create_match()
        owner = match.players[0]
        for player in match.players[1:]:
            player.alive = False
        action = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        self.assertTrue(owner.animation_state.attack_active)
        self.assertEqual(owner.animation_state.attack_elapsed, 0.0)

    @staticmethod
    def _assert_valid_canvas(surface: pygame.Surface) -> None:
        corners = (
            surface.get_at((0, 0)).a,
            surface.get_at((surface.get_width() - 1, 0)).a,
            surface.get_at((0, surface.get_height() - 1)).a,
            surface.get_at((surface.get_width() - 1, surface.get_height() - 1)).a,
        )
        assert corners == (0, 0, 0, 0), corners
        bounds = surface.get_bounding_rect(min_alpha=1)
        assert bounds.width > 0 and bounds.height > 0
        assert bounds.left > 0 and bounds.top > 0
        assert bounds.right < surface.get_width() and bounds.bottom < surface.get_height()
        center_x = (bounds.left + bounds.right - 1) / 2
        center_y = (bounds.top + bounds.bottom - 1) / 2
        assert abs(center_x - 511.5) <= 16
        assert abs(center_y - 511.5) <= 16


if __name__ == "__main__":
    unittest.main()
