"""破陣者素材、方向量化與動畫狀態測試。"""

from __future__ import annotations

from dataclasses import replace
import math
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, sprites
from pvpve_escape.models import CharacterId, TacticalId, Vector2
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


class SniperSpriteAssetTests(unittest.TestCase):
    """狙擊者正式素材應能透過角色中立入口被完整索引。"""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        sprites.clear_character_sprite_cache()

    def test_all_72_sniper_assets_have_the_required_shape_and_transparency(self) -> None:
        asset_root = Path(__file__).resolve().parents[1] / "assets" / "characters" / "sniper"
        self.assertEqual(len(list(asset_root.rglob("*.png"))), 72)

        for direction_index, direction_name in enumerate(sprites.SNIPER_DIRECTION_NAMES):
            idle = sprites.load_sniper_sprite("idle", direction_index, 0)
            self.assertIsNotNone(idle, direction_name)
            self.assertEqual(idle.get_size(), (config.SNIPER_SPRITE_SOURCE_SIZE,) * 2)
            self._assert_valid_canvas(idle)

            for visual_state in ("move", "attack"):
                for frame_index in range(config.SNIPER_ANIMATION_FRAME_COUNT):
                    frame = sprites.load_sniper_sprite(visual_state, direction_index, frame_index)
                    self.assertIsNotNone(frame, f"{visual_state}/{direction_name}/{frame_index}")
                    self.assertEqual(frame.get_size(), (config.SNIPER_SPRITE_SOURCE_SIZE,) * 2)
                    self._assert_valid_canvas(frame)

    def test_sniper_direction_indexes_follow_the_shared_eight_sector_contract(self) -> None:
        self.assertEqual(
            sprites.SNIPER_DIRECTION_NAMES,
            ("right", "down_right", "down", "down_left", "left", "up_left", "up", "up_right"),
        )
        for vector, expected in (
            (Vector2(1, 0), 0),
            (Vector2(0, 1), 2),
            (Vector2(-1, 0), 4),
            (Vector2(0, -1), 6),
        ):
            self.assertEqual(sprites.quantize_sprite_direction(vector), expected)

    def test_invalid_sniper_queries_return_unavailable_result_and_record_error(self) -> None:
        for query in (
            ("unknown", 0, 0),
            ("idle", 0, 1),
            ("move", 0, 4),
            ("attack", 8, 0),
            ("attack", -1, 0),
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                self.assertIsNone(sprites.load_sniper_sprite(*query))
            self.assertIsNotNone(sprites.sniper_sprite_error(*query))

    def test_character_loader_keeps_role_in_cache_and_normalizes_display_sizes(self) -> None:
        with patch.object(pygame.image, "load", wraps=pygame.image.load) as image_load:
            sniper = sprites.load_character_sprite(
                CharacterId.SNIPER, "idle", 0, 0, display_size=50
            )
            sniper_again = sprites.load_sniper_sprite("idle", 0, 0, display_size=50)
            sniper_roster = sprites.load_sniper_sprite("idle", 0, 0, display_size=24)
            breacher = sprites.load_breacher_sprite("idle", 0, 0, display_size=50)

        self.assertIsNotNone(sniper)
        self.assertIs(sniper, sniper_again)
        self.assertEqual(sniper.get_size(), (50, 50))
        self.assertEqual(sniper_roster.get_size(), (24, 24))
        self.assertEqual(breacher.get_size(), (50, 50))
        self.assertEqual(image_load.call_count, 2)
        self.assertIn(
            (CharacterId.SNIPER, "idle", 0, 0, (50, 50)),
            sprites._CHARACTER_SPRITE_CACHE,
        )
        self.assertIn(
            (CharacterId.BREACHER, "idle", 0, 0, (50, 50)),
            sprites._CHARACTER_SPRITE_CACHE,
        )

    def test_sniper_display_uses_fixed_direction_source_canvas_fit(self) -> None:
        requests = [
            ("idle", direction_index, 0)
            for direction_index in range(len(sprites.SNIPER_DIRECTION_NAMES))
        ]
        requests.extend(
            (visual_state, direction_index, frame_index)
            for visual_state, frame_index in (("move", 1), ("attack", 2))
            for direction_index in range(len(sprites.SNIPER_DIRECTION_NAMES))
        )

        with patch.object(
            sprites,
            "_fit_source_canvas",
            wraps=sprites._fit_source_canvas,
        ) as source_canvas_fit:
            with patch.object(
                sprites,
                "_fit_visible_sprite",
                wraps=sprites._fit_visible_sprite,
            ) as visible_extent_fit:
                displayed = [
                    sprites.load_sniper_sprite(
                        visual_state,
                        direction_index,
                        frame_index,
                        display_size=config.SNIPER_SPRITE_DISPLAY_SIZE,
                    )
                    for visual_state, direction_index, frame_index in requests
                ]

        self.assertEqual(source_canvas_fit.call_count, len(requests))
        visible_extent_fit.assert_not_called()
        for request, sprite in zip(requests, displayed):
            self.assertIsNotNone(sprite)
            self.assertEqual(sprite.get_size(), (50, 50))
            bounds = sprite.get_bounding_rect(min_alpha=64)
            self.assertGreater(bounds.width, 0, f"{request}: {bounds}")
            self.assertGreater(bounds.height, 0, f"{request}: {bounds}")
            self.assertLessEqual(bounds.right, 50, f"{request}: {bounds}")
            self.assertLessEqual(bounds.bottom, 50, f"{request}: {bounds}")
            # 固定比例後仍允許動畫姿勢在格內自然位移；這裡驗證的是不出界，
            # 不是把每一幀重新置中（否則會破壞走路與攻擊的動作感）。
            self.assertLessEqual(abs(bounds.centerx - 25), 6, f"{request}: {bounds}")
            self.assertLessEqual(abs(bounds.centery - 25), 6, f"{request}: {bounds}")

    def test_preload_sniper_warms_all_sources_and_three_display_sizes(self) -> None:
        with patch.object(pygame.image, "load", wraps=pygame.image.load) as image_load:
            loaded_count = sprites.preload_sniper_sprites()

        self.assertEqual(loaded_count, 72)
        self.assertEqual(image_load.call_count, 72)
        for size in ((50, 50), (54, 54), (24, 24)):
            displayed = [
                surface
                for (character_id, _state, _direction, _frame, cached_size), surface
                in sprites._CHARACTER_SPRITE_CACHE.items()
                if character_id == CharacterId.SNIPER and cached_size == size
            ]
            self.assertEqual(len(displayed), 72)
            self.assertTrue(all(surface is not None for surface in displayed))

    def test_preload_default_uses_the_character_spec_display_sizes(self) -> None:
        current_spec = sprites.CHARACTER_SPRITE_SPECS[CharacterId.SNIPER]
        custom_spec = replace(current_spec, preload_display_sizes=(31, 17))
        with patch.dict(
            sprites.CHARACTER_SPRITE_SPECS,
            {CharacterId.SNIPER: custom_spec},
        ):
            with patch.object(
                sprites, "load_character_sprite", return_value=object()
            ) as load:
                self.assertEqual(
                    sprites.preload_character_sprites(CharacterId.SNIPER),
                    72,
                )

        requested_sizes = {
            call.args[4]
            for call in load.call_args_list
            if call.args[4] is not None
        }
        self.assertEqual(requested_sizes, {31, 17})

    def test_sniper_failed_asset_is_cached_and_warned_once(self) -> None:
        missing_path = Path("missing-sniper-frame.png")
        with patch.object(sprites, "_path_for_character_request", return_value=missing_path):
            with patch.object(pygame.image, "load", side_effect=OSError("missing")) as image_load:
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter("always")
                    self.assertIsNone(sprites.load_sniper_sprite("move", 0, 0))
                    self.assertIsNone(sprites.load_sniper_sprite("move", 0, 0))

        self.assertEqual(image_load.call_count, 0)
        self.assertIsNotNone(sprites.sniper_sprite_error("move", 0, 0))
        self.assertEqual(len(captured), 1)
        self.assertIn("幾何 fallback", str(captured[0].message))

    def test_sniper_direction_boundaries_use_the_clockwise_sector(self) -> None:
        boundary = math.pi / 8
        exact = Vector2(math.cos(boundary), math.sin(boundary))
        before = Vector2(math.cos(boundary - 1e-6), math.sin(boundary - 1e-6))
        self.assertEqual(sprites.quantize_sprite_direction(exact), 1)
        self.assertEqual(sprites.quantize_sprite_direction(before), 0)

    def test_sniper_animation_cycles_move_frames_and_attack_has_priority(self) -> None:
        player = create_match(CharacterId.SNIPER).players[0]
        player.aim_direction = Vector2(-1, 0)

        sprites.update_player_animation(player, Vector2(-1, 0), 0.10)
        self.assertEqual(player.animation_state.facing_direction_index, 4)
        self.assertEqual(sprites.current_sprite_request(player), ("move", 4, 1))

        sprites.start_or_refresh_attack_animation(player)
        self.assertEqual(sprites.current_sprite_request(player), ("attack", 4, 0))
        sprites.update_player_animation(player, Vector2(-1, 0), 0.12)
        self.assertEqual(sprites.current_sprite_request(player), ("attack", 4, 2))
        elapsed_before_refresh = player.animation_state.attack_elapsed
        sprites.start_or_refresh_attack_animation(player)
        self.assertEqual(player.animation_state.attack_elapsed, elapsed_before_refresh)
        self.assertGreaterEqual(player.animation_state.attack_hold, config.SNIPER_ATTACK_DURATION)

        sprites.update_player_animation(player, Vector2(), config.SNIPER_ATTACK_DURATION)
        self.assertEqual(sprites.current_sprite_request(player), ("idle", 4, 0))

    def test_sniper_successful_primary_tactical_and_ultimate_start_attack_state(self) -> None:
        from pvpve_escape.characters import create_primary_action, create_tactical_action, create_ultimate_action
        from pvpve_escape.world import _apply_action

        action_builders = (
            lambda player: create_primary_action(player, Vector2(1, 0), primary_charge=0.6),
            lambda player: create_tactical_action(player, Vector2(1, 0), Vector2(1, 0)),
            lambda player: create_ultimate_action(player, Vector2(1, 0)),
        )
        for build_action in action_builders:
            match = create_match(CharacterId.SNIPER, TacticalId.DASH)
            owner = match.players[0]
            owner.ultimate_energy = 100.0
            action = build_action(owner)
            self.assertIsNotNone(action)
            _apply_action(match, action)
            self.assertTrue(owner.animation_state.attack_active)
            self.assertEqual(owner.animation_state.attack_elapsed, 0.0)

    def test_sniper_animation_does_not_start_from_incomplete_or_unavailable_input(self) -> None:
        player = create_match(CharacterId.SNIPER).players[0]
        player.primary_charge = 0.2
        player.primary_cooldown = 1.0
        player.ammo = 0
        sprites.update_player_animation(player, Vector2(), 0.24)
        self.assertFalse(player.animation_state.attack_active)

    def test_sniper_death_and_respawn_clear_animation_progress_without_changing_facing(self) -> None:
        from pvpve_escape.rules import handle_player_death, respawn_player

        player = create_match(CharacterId.SNIPER).players[0]
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

    def test_invalid_sniper_dimensions_alpha_and_bounds_use_the_same_quality_gate(self) -> None:
        source_path = Path(__file__)
        transparent_but_empty = pygame.Surface(
            (config.SNIPER_SPRITE_SOURCE_SIZE,) * 2, pygame.SRCALPHA
        )
        transparent_but_empty.set_at((512, 512), (255, 255, 255, 1))
        boundary_pixel = pygame.Surface(
            (config.SNIPER_SPRITE_SOURCE_SIZE,) * 2, pygame.SRCALPHA
        )
        boundary_pixel.set_at((0, 512), (255, 255, 255, 1))
        invalid_surfaces = (
            pygame.Surface((64, 64), pygame.SRCALPHA),
            transparent_but_empty,
            boundary_pixel,
        )

        for fake_surface in invalid_surfaces:
            sprites.clear_character_sprite_cache()
            with patch.object(
                sprites, "_path_for_character_request", return_value=source_path
            ):
                with patch.object(pygame.image, "load", return_value=fake_surface):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)
                        self.assertIsNone(
                            sprites.load_sniper_sprite("move", 0, 0, display_size=50)
                        )
            self.assertIsNotNone(sprites.sniper_sprite_error("move", 0, 0))

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
