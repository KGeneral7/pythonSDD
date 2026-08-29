"""Pygame 文字繪製回歸測試。"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.characters import create_primary_action, create_tactical_action, create_ultimate_action
from pvpve_escape.controllers import HumanController, InputState
from pvpve_escape.models import CharacterId, MatchPhase, ObstacleKind, ObstacleState, TacticalId, Vector2, WorldRect
from pvpve_escape.world import _apply_action, create_match, update_match


class TraditionalChineseFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def test_traditional_chinese_uses_a_system_cjk_font(self) -> None:
        font_path = rendering.get_text_font_path()

        self.assertIsNotNone(font_path)
        self.assertNotEqual(os.path.basename(font_path).lower(), "freesansbold.ttf")

    def test_traditional_chinese_text_is_drawn(self) -> None:
        background = (7, 8, 9)
        surface = pygame.Surface((240, 60))
        surface.fill(background)

        rendering.draw_text(surface, "撤離區", (8, 8), 24, (255, 255, 255))

        changed_pixels = sum(
            surface.get_at((x, y))[:3] != background
            for x in range(surface.get_width())
            for y in range(surface.get_height())
        )
        self.assertGreater(changed_pixels, 0)

    def test_mouse_and_space_events_trigger_skill_input_flags(self) -> None:
        controller = HumanController()
        mouse_state = controller.collect(
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3)],
            Vector2(),
            Vector2(500, 500),
            MatchPhase.PLAYING,
        )
        space_state = controller.collect(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)],
            Vector2(),
            Vector2(500, 500),
            MatchPhase.PLAYING,
        )

        self.assertTrue(mouse_state.ultimate_pressed)
        self.assertTrue(space_state.tactical_pressed)

    def test_controller_exposes_press_hold_release_and_focus_loss_edges(self) -> None:
        controller = HumanController()
        player_position = Vector2(500, 500)

        with patch("pygame.mouse.get_pressed", return_value=(True, False, False)):
            pressed = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )
            held = controller.collect([], Vector2(), player_position, MatchPhase.PLAYING)
        with patch("pygame.mouse.get_pressed", return_value=(False, False, False)):
            released = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )

        self.assertTrue(pressed.primary_pressed)
        self.assertTrue(pressed.primary_held)
        self.assertFalse(pressed.primary_released)
        self.assertTrue(held.primary_held)
        self.assertFalse(held.primary_pressed)
        self.assertTrue(released.primary_released)
        self.assertFalse(released.primary_held)

        with patch("pygame.mouse.get_pressed", return_value=(True, False, False)):
            controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )
        focus_lost = controller.collect(
            [pygame.event.Event(pygame.WINDOWFOCUSLOST)],
            Vector2(),
            player_position,
            MatchPhase.PLAYING,
        )
        self.assertTrue(focus_lost.focus_lost)
        self.assertFalse(focus_lost.primary_held)
        self.assertFalse(focus_lost.primary_released)

        with patch("pygame.mouse.get_pressed", return_value=(False, False, False)):
            after_focus_release = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )
        self.assertFalse(after_focus_release.primary_pressed)
        self.assertFalse(after_focus_release.primary_released)

    def test_non_playing_phase_blocks_held_skill_until_a_new_press(self) -> None:
        controller = HumanController()
        player_position = Vector2(500, 500)

        with patch("pygame.mouse.get_pressed", return_value=(True, False, False)):
            initial = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )
            self.assertTrue(initial.primary_held)

            controller.collect([], Vector2(), player_position, MatchPhase.CHARACTER_SELECT)
            blocked = controller.collect([], Vector2(), player_position, MatchPhase.PLAYING)

        self.assertFalse(blocked.primary_pressed)
        self.assertFalse(blocked.primary_held)

        with patch("pygame.mouse.get_pressed", return_value=(False, False, False)):
            controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )

        with patch("pygame.mouse.get_pressed", return_value=(True, False, False)):
            resumed = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
                Vector2(),
                player_position,
                MatchPhase.PLAYING,
            )

        self.assertTrue(resumed.primary_pressed)
        self.assertTrue(resumed.primary_held)

    def test_live_skill_input_changes_ultimate_and_control_state(self) -> None:
        controller = HumanController()

        ultimate_match = create_match(CharacterId.BREACHER)
        ultimate_match.monsters = []
        ultimate_owner = ultimate_match.players[0]
        ultimate_target = ultimate_match.players[1]
        for other in ultimate_match.players[2:]:
            other.alive = False
        ultimate_owner.ultimate_energy = 100.0
        ultimate_target.position = ultimate_owner.position + Vector2(120, 0)
        ultimate_state = controller.collect(
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3)],
            ultimate_match.camera.position,
            ultimate_owner.position,
            MatchPhase.PLAYING,
        )
        ultimate_state.aim_direction = Vector2(1, 0)
        update_match(ultimate_match, ultimate_state, 0.05)
        ultimate_release = InputState(aim_direction=Vector2(1, 0), ultimate_released=True)
        update_match(ultimate_match, ultimate_release, 0.05)

        control_match = create_match(selected_tactical=TacticalId.CONTROL)
        control_match.monsters = []
        control_owner = control_match.players[0]
        control_target = control_match.players[1]
        for other in control_match.players[2:]:
            other.alive = False
        control_target.position = control_owner.position + Vector2(100, 0)
        control_state = controller.collect(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)],
            control_match.camera.position,
            control_owner.position,
            MatchPhase.PLAYING,
        )
        control_state.aim_direction = Vector2(1, 0)
        update_match(control_match, control_state, 0.05)
        control_release = InputState(aim_direction=Vector2(1, 0), tactical_released=True)
        update_match(control_match, control_release, 0.05)

        self.assertLess(ultimate_target.health, ultimate_target.max_health)
        self.assertEqual(control_target.slow_multiplier, 0.6)

    def test_live_sniper_mouse_input_reaches_the_same_collision_path_as_direct_input(self) -> None:
        controller = HumanController()
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        sniper = match.players[0]
        target = match.players[1]
        for other in match.players[2:]:
            other.alive = False
        sniper.position = Vector2(500, 260)
        target.position = Vector2(650, 260)
        sniper.auto_aim_enabled = False
        target_health = target.health

        with patch("pygame.mouse.get_pressed", side_effect=[(True, False, False), (False, False, False)]):
            state = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
                match.camera.position,
                sniper.position,
                MatchPhase.PLAYING,
            )
            state.aim_direction = Vector2(1, 0)
            update_match(match, state, 0.05)
            release = controller.collect(
                [pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)],
                match.camera.position,
                sniper.position,
                MatchPhase.PLAYING,
            )
        release.aim_direction = Vector2(1, 0)
        update_match(match, release, 0.05)
        update_match(match, InputState(aim_direction=Vector2(1, 0)), 0.05)
        update_match(match, InputState(aim_direction=Vector2(1, 0)), 0.05)
        update_match(match, InputState(aim_direction=Vector2(1, 0)), 0.05)

        self.assertLess(target.health, target_health)
        impact = next(effect for effect in match.effects if effect.kind == "sniper_line")
        self.assertGreater(impact.metadata.get("impact_effective_damage", 0.0), 0.0)

    def test_sniper_ultimate_line_stays_at_its_cast_position(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        for other in match.players[1:]:
            other.alive = False
        owner.ultimate_energy = 100.0
        cast_position = owner.position.copy()

        action = create_ultimate_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        effect = next(effect for effect in match.effects if effect.kind == "sniper_ultimate_line")
        owner.position = Vector2(700, 600)
        update_match(match, InputState(aim_direction=Vector2(1, 0)), 0.05)

        self.assertEqual(effect.position.tuple(), cast_position.tuple())

    def test_human_player_is_rendered_without_a_base_circle_when_match_starts(self) -> None:
        match = create_match()
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        player = match.players[0]
        point = (
            round(player.position.x - match.camera.position.x),
            round(player.position.y - match.camera.position.y),
        )
        with patch.object(rendering.pygame.draw, "circle", wraps=pygame.draw.circle) as draw_circle:
            rendering.draw_match(surface, match)

        player_circle_calls = [
            call
            for call in draw_circle.call_args_list
            if len(call.args) >= 3 and call.args[2] == point
        ]
        self.assertEqual(player_circle_calls, [])
        self.assertTrue(any(surface.get_at((x, y)).a for x in range(point[0] - 20, point[0] + 21) for y in range(point[1] - 20, point[1] + 21)))

    def test_all_confirmed_walls_and_bushes_are_rendered_on_the_map_layer(self) -> None:
        match = create_match()
        match.camera.position = Vector2()
        surface = pygame.Surface((config.WORLD_WIDTH, config.WORLD_HEIGHT))
        surface.fill(config.GROUND_COLOR)

        rendering.draw_terrain(surface, match)

        for obstacle in match.obstacles:
            asset = rendering.load_map_asset(obstacle.kind.value)
            self.assertIsNotNone(asset)
            point = (round(obstacle.bounds.left + 50), round(obstacle.bounds.top + 50))
            self.assertEqual(
                surface.get_at(point)[:3],
                asset.get_at((50, 50))[:3],
                f"{obstacle.kind.value} at {point} should use its tile pixels",
            )

        bush_asset = rendering.load_map_asset("bush")
        self.assertIsNotNone(bush_asset)
        for bush in match.bushes:
            point = (round(bush.bounds.left + 50), round(bush.bounds.top + 50))
            self.assertEqual(
                surface.get_at(point)[:3],
                bush_asset.get_at((50, 50))[:3],
                f"bush at {point} should use its tile pixels",
            )

    def test_formal_terrain_and_ground_use_100px_tile_pixels(self) -> None:
        match = create_match()
        match.players = []
        match.monsters = []
        match.camera.position = Vector2()
        surface = pygame.Surface((config.WORLD_WIDTH, config.WORLD_HEIGHT))

        rendering.draw_world(surface, match)
        ground_asset = rendering.load_map_asset("ground")
        self.assertIsNotNone(ground_asset)
        self.assertEqual(surface.get_at((50, 50))[:3], ground_asset.get_at((50, 50))[:3])

        surface.fill(config.GROUND_COLOR)
        rendering.draw_terrain(surface, match)
        for obstacle in match.obstacles:
            asset = rendering.load_map_asset(obstacle.kind.value)
            self.assertEqual(
                surface.get_at((round(obstacle.bounds.left + 50), round(obstacle.bounds.top + 50)))[:3],
                asset.get_at((50, 50))[:3],
            )
        for bush in match.bushes:
            asset = rendering.load_map_asset("bush")
            self.assertEqual(
                surface.get_at((round(bush.bounds.left + 50), round(bush.bounds.top + 50)))[:3],
                asset.get_at((50, 50))[:3],
            )

    def test_confirmed_terrain_is_visible_in_the_actual_game_viewport_after_camera_moves(self) -> None:
        """正式 1280×720 畫面移到不同世界區域時，牆與草叢都能被取樣。"""

        match = create_match()
        # 移除會遮住取樣點的生物，只驗證 draw_match 的正式地圖繪製鏈。
        match.players = []
        match.monsters = []
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        for _ in range(20):
            # 開場左上視角：正式格的圖片應以世界左上角投影。
            match.camera.position = Vector2(0, 0)
            rendering.draw_match(surface, match)
            thick = next(item for item in match.obstacles if item.kind.value == "thick_wall" and item.bounds.left < config.WINDOW_WIDTH and item.bounds.top < config.WINDOW_HEIGHT)
            bush = next(item for item in match.bushes if item.bounds.left < config.WINDOW_WIDTH and item.bounds.top < config.WINDOW_HEIGHT)
            thick_asset = rendering.load_map_asset("thick_wall")
            bush_asset = rendering.load_map_asset("bush")
            self.assertEqual(surface.get_at((round(thick.bounds.left + 50), round(thick.bounds.top + 50)))[:3], thick_asset.get_at((50, 50))[:3])
            self.assertEqual(surface.get_at((round(bush.bounds.left + 50), round(bush.bounds.top + 50)))[:3], bush_asset.get_at((50, 50))[:3])

            # 移到地圖右下區域：確認世界座標不是只在開場畫面硬編碼繪製。
            match.camera.position = Vector2(1200, 700)
            rendering.draw_match(surface, match)
            thin = next(item for item in match.obstacles if item.kind.value == "thin_wall" and 1200 <= item.bounds.left < 2400 and 700 <= item.bounds.top < 1400)
            bush = next(item for item in match.bushes if 1200 <= item.bounds.left < 2400 and 700 <= item.bounds.top < 1400)
            thin_asset = rendering.load_map_asset("thin_wall")
            bush_asset = rendering.load_map_asset("bush")
            thin_point = (round(thin.bounds.left - match.camera.position.x + 50), round(thin.bounds.top - match.camera.position.y + 50))
            bush_point = (round(bush.bounds.left - match.camera.position.x + 50), round(bush.bounds.top - match.camera.position.y + 50))
            self.assertEqual(surface.get_at(thin_point)[:3], thin_asset.get_at((50, 50))[:3])
            self.assertEqual(surface.get_at(bush_point)[:3], bush_asset.get_at((50, 50))[:3])

    def test_destroyed_terrain_is_removed_from_the_next_map_draw(self) -> None:
        match = create_match()
        match.camera.position = Vector2()
        surface = pygame.Surface((config.WORLD_WIDTH, config.WORLD_HEIGHT))

        wall = match.obstacles[4]
        bush = match.bushes[0]
        wall_center = (round(wall.bounds.center.x), round(wall.bounds.center.y))
        bush_center = (round(bush.bounds.center.x), round(bush.bounds.center.y))
        wall.destroyed = True
        bush.active = False

        match.players = []
        match.monsters = []
        rendering.draw_world(surface, match)

        ground_asset = rendering.load_map_asset("ground")
        self.assertEqual(surface.get_at(wall_center)[:3], ground_asset.get_at((50, 50))[:3])
        self.assertEqual(surface.get_at(bush_center)[:3], ground_asset.get_at((50, 50))[:3])

    def test_destroying_one_cell_leaves_neighbor_and_thick_wall_tiles_visible(self) -> None:
        match = create_match()
        match.players = []
        match.monsters = []
        match.camera.position = Vector2()
        thin = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(100, 0, 100, 100))
        neighbor = ObstacleState(2, ObstacleKind.THIN_WALL, WorldRect(200, 0, 100, 100))
        thick = ObstacleState(3, ObstacleKind.THICK_WALL, WorldRect(300, 0, 100, 100))
        match.obstacles = [thin, neighbor, thick]
        surface = pygame.Surface((config.WORLD_WIDTH, config.WORLD_HEIGHT))
        thin.destroyed = True

        rendering.draw_world(surface, match)

        ground_asset = rendering.load_map_asset("ground")
        thin_asset = rendering.load_map_asset("thin_wall")
        thick_asset = rendering.load_map_asset("thick_wall")
        self.assertEqual(surface.get_at((150, 50))[:3], ground_asset.get_at((50, 50))[:3])
        self.assertEqual(surface.get_at((250, 50))[:3], thin_asset.get_at((50, 50))[:3])
        self.assertEqual(surface.get_at((350, 50))[:3], thick_asset.get_at((50, 50))[:3])

    def test_camera_positions_keep_tile_pixels_aligned_and_clip_partial_tiles_naturally(self) -> None:
        camera_cases = (
            (Vector2(0, 0), Vector2(100, 100), (150, 150)),
            (Vector2(560, 340), Vector2(600, 400), (90, 110)),
            (Vector2(1120, 680), Vector2(1200, 700), (130, 70)),
        )

        for camera, world_tile, expected_center in camera_cases:
            match = create_match()
            match.players = []
            match.monsters = []
            match.obstacles = [ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(world_tile.x, world_tile.y, 100, 100))]
            match.bushes = []
            match.camera.position = camera
            surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

            rendering.draw_world(surface, match)

            wall_asset = rendering.load_map_asset("thick_wall")
            self.assertEqual(surface.get_at(expected_center)[:3], wall_asset.get_at((50, 50))[:3])

        match = create_match()
        match.players = []
        match.monsters = []
        match.obstacles = [ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(0, 0, 100, 100))]
        match.bushes = []
        match.camera.position = Vector2(50, 50)
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        rendering.draw_world(surface, match)

        wall_asset = rendering.load_map_asset("thick_wall")
        self.assertEqual(surface.get_at((49, 49))[:3], wall_asset.get_at((99, 99))[:3])

    def test_every_role_primary_and_ultimate_creates_a_visual_effect(self) -> None:
        expected_primary = {
            CharacterId.BREACHER: "breach_cone",
            CharacterId.SNIPER: "sniper_line",
            CharacterId.GUARDIAN: "guardian_arc",
            CharacterId.HUNTER: "boomerang",
            CharacterId.CONTROLLER: "mine",
            CharacterId.SIPHONER: "beam",
        }
        expected_ultimate = {
            CharacterId.BREACHER: "breach_burst",
            CharacterId.SNIPER: "sniper_ultimate_line",
            CharacterId.GUARDIAN: "guardian_guard",
            CharacterId.HUNTER: "hunter_dash",
            CharacterId.CONTROLLER: "gravity_cage",
            CharacterId.SIPHONER: "siphon_burst",
        }

        for role in CharacterId:
            match = create_match(role)
            match.monsters = []
            for other in match.players[1:]:
                other.alive = False
            player = match.players[0]
            player.primary_cooldown = 0.0
            primary = create_primary_action(player, Vector2(1, 0), 1.0)
            self.assertIsNotNone(primary)
            _apply_action(match, primary)
            self.assertIn(expected_primary[role], {effect.kind for effect in match.effects})

            player.ultimate_energy = 100.0
            ultimate = create_ultimate_action(player, Vector2(1, 0))
            self.assertIsNotNone(ultimate)
            _apply_action(match, ultimate)
            self.assertIn(expected_ultimate[role], {effect.kind for effect in match.effects})
            rendering.draw_match(pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), match)

    def test_every_tactical_action_creates_a_visual_effect(self) -> None:
        expected = {
            TacticalId.DASH: "dash",
            TacticalId.SHIELD: "shield",
            TacticalId.CONTROL: "control_zone",
        }

        for tactical in TacticalId:
            match = create_match(selected_tactical=tactical)
            match.monsters = []
            for other in match.players[1:]:
                other.alive = False
            action = create_tactical_action(match.players[0], Vector2(1, 0), Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            self.assertIn(expected[tactical], {effect.kind for effect in match.effects})
            rendering.draw_match(pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), match)

    def test_active_control_and_defense_states_are_visible_on_their_targets(self) -> None:
        match = create_match(CharacterId.GUARDIAN, TacticalId.CONTROL)
        match.players[0].position = Vector2(1200, 700)
        match.players[0].damage_reduction_timer = 4.0
        match.players[0].damage_reduction = 0.7
        monster = match.monsters[0]
        monster.position = Vector2(900, 700)
        monster.slow_timer = 1.0
        monster.slow_multiplier = 0.6
        match.camera.follow(match.players[0].position)
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        rendering.draw_match(surface, match)

        player_point = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        monster_point = (player_point[0] - 300, player_point[1])
        self.assertEqual(surface.get_at((player_point[0], player_point[1] - 25))[:3], config.TEXT_COLOR)
        self.assertEqual(surface.get_at((monster_point[0] + 19, monster_point[1]))[:3], config.WARNING_COLOR)

    def test_hold_preview_is_visible_for_each_role_without_mutating_match(self) -> None:
        for role in CharacterId:
            match = create_match(role)
            for other in match.players[1:]:
                other.alive = False
            owner = match.players[0]
            before = (owner.ammo, owner.primary_cooldown, owner.ultimate_energy, len(match.effects))
            surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
            rendering.draw_match(
                surface,
                match,
                InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True),
            )
            guide_pixels = sum(
                surface.get_at((x, y))[:3] in {config.AIM_GUIDE_COLOR, config.AIM_GUIDE_SECONDARY_COLOR}
                for x in range(surface.get_width())
                for y in range(surface.get_height())
            )
            self.assertGreater(guide_pixels, 0, role)
            self.assertEqual((owner.ammo, owner.primary_cooldown, owner.ultimate_energy, len(match.effects)), before, role)

    def test_preview_priority_and_invalid_state_are_observable(self) -> None:
        match = create_match(CharacterId.BREACHER)
        owner = match.players[0]
        owner.ammo = 0
        owner.ultimate_energy = 0.0
        input_state = InputState(
            aim_direction=Vector2(1, 0),
            primary_held=True,
            tactical_held=True,
            ultimate_held=True,
        )
        self.assertEqual(rendering._preview_slot(input_state), "ultimate")
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        rendering.draw_match(surface, match, input_state)
        invalid_pixels = sum(
            surface.get_at((x, y))[:3] == config.AIM_GUIDE_INVALID_COLOR
            for x in range(surface.get_width())
            for y in range(surface.get_height())
        )
        self.assertGreater(invalid_pixels, 0)
        self.assertEqual(match.effects, [])

    def test_control_preview_endpoint_matches_released_control_zone(self) -> None:
        match = create_match(CharacterId.CONTROLLER, TacticalId.CONTROL)
        owner = match.players[0]
        owner.position = Vector2(500, 500)
        guide = rendering.build_aim_guide(owner, "tactical", Vector2(1, 0))
        update_match(
            match,
            InputState(aim_direction=Vector2(1, 0), tactical_released=True),
            0.01,
        )
        effect = next(effect for effect in match.effects if effect.kind == "control_zone")
        self.assertEqual(effect.position.tuple(), guide.end.tuple())
        self.assertEqual(effect.projectile_speed, 0.0)

    def test_flying_effect_render_data_uses_previous_position_and_mine_arming(self) -> None:
        match = create_match(CharacterId.SNIPER)
        owner = match.players[0]
        for other in match.players[1:]:
            other.alive = False
        action = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        update_match(match, InputState(), 0.05)
        sniper_effect = next(effect for effect in match.effects if effect.kind == "sniper_line")
        self.assertEqual(sniper_effect.previous_position.tuple(), (300.0, 180.0))
        self.assertNotEqual(sniper_effect.position.tuple(), sniper_effect.previous_position.tuple())
        rendering.draw_match(pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), match)

        mine_match = create_match(CharacterId.CONTROLLER)
        mine_owner = mine_match.players[0]
        for other in mine_match.players[1:]:
            other.alive = False
        mine_action = create_primary_action(mine_owner, Vector2(1, 0))
        self.assertIsNotNone(mine_action)
        _apply_action(mine_match, mine_action)
        update_match(mine_match, InputState(), 0.05)
        mine = next(effect for effect in mine_match.effects if effect.kind == "mine")
        self.assertFalse(mine.armed)
        for _ in range(26):
            update_match(mine_match, InputState(), 0.05)
        self.assertTrue(mine.armed)
        rendering.draw_match(pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), mine_match)

    def test_all_combat_effect_states_render_without_external_assets(self) -> None:
        """六角色、三配件與命中狀態均可在無頭 surface 上繪製。"""

        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        for role in CharacterId:
            match = create_match(role)
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            owner.primary_cooldown = 0.0
            primary = create_primary_action(owner, Vector2(1, 0), 0.6)
            self.assertIsNotNone(primary)
            _apply_action(match, primary)
            owner.ultimate_energy = 100.0
            ultimate = create_ultimate_action(owner, Vector2(1, 0))
            self.assertIsNotNone(ultimate)
            _apply_action(match, ultimate)
            for effect in match.effects:
                effect.metadata.setdefault("impact_status", "命中")
            rendering.draw_match(surface, match, InputState(aim_direction=Vector2(1, 0)))

        for tactical in TacticalId:
            match = create_match(selected_tactical=tactical)
            owner = match.players[0]
            action = create_tactical_action(owner, Vector2(1, 0), Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            rendering.draw_match(surface, match, InputState(aim_direction=Vector2(1, 0)))

    def test_gui_panels_use_local_alpha_without_fading_world_or_text(self) -> None:
        background = (90, 100, 110)
        for opacity in (50, 78, 90, 49, 91):
            surface = pygame.Surface((240, 160))
            surface.fill(background)
            panel = pygame.Rect(20, 20, 120, 80)
            rendering.draw_panel(surface, panel, opacity_percent=opacity)
            inside = surface.get_at((70, 60))[:3]
            outside = surface.get_at((5, 5))[:3]
            self.assertEqual(outside, background)
            self.assertNotEqual(inside, background)
            self.assertNotEqual(inside, config.PANEL_COLOR)

            rendering.draw_text(surface, "清晰", (34, 38), 20, config.TEXT_COLOR)
            text_pixels = sum(
                surface.get_at((x, y))[:3] == config.TEXT_COLOR
                for x in range(20, 140)
                for y in range(20, 100)
            )
            self.assertGreater(text_pixels, 0)

    def test_selection_and_result_panels_render_at_all_supported_opacities(self) -> None:
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        match = create_match()
        for opacity in (50, 78, 90, 49, 91):
            with patch.object(config, "GUI_OPACITY_PERCENT", opacity):
                rendering.draw_selection(surface, 0, 0)
                rendering.draw_result(surface, match)

    def test_repeated_ability_rendering_smoke_runs_twenty_times_per_slot(self) -> None:
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        for role in CharacterId:
            for _ in range(20):
                match = create_match(role)
                owner = match.players[0]
                for other in match.players[1:]:
                    other.alive = False
                owner.primary_cooldown = 0.0
                primary = create_primary_action(owner, Vector2(1, 0), 0.6)
                self.assertIsNotNone(primary)
                _apply_action(match, primary)
                owner.ultimate_energy = 100.0
                ultimate = create_ultimate_action(owner, Vector2(1, 0))
                self.assertIsNotNone(ultimate)
                _apply_action(match, ultimate)
                rendering.draw_match(surface, match, InputState(aim_direction=Vector2(1, 0)))

        for tactical in TacticalId:
            for _ in range(20):
                match = create_match(selected_tactical=tactical)
                action = create_tactical_action(match.players[0], Vector2(1, 0), Vector2(1, 0))
                self.assertIsNotNone(action)
                _apply_action(match, action)
                rendering.draw_match(surface, match, InputState(aim_direction=Vector2(1, 0)))


class OverheadRenderingTests(unittest.TestCase):
    """頭頂 HUD 的可觀察繪製測試；不依賴視窗、滑鼠或完整遊戲迴圈。"""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        # 只清理本 fixture 可能建立的顯示資源；保留共用字型初始化，
        # 避免同模組後續既有渲染測試使用已失效的 Font 物件。
        pygame.display.quit()

    def make_surface(self) -> pygame.Surface:
        """建立所有頭頂 HUD 測試共用的 headless surface。"""

        return pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

    def capture_texts(self, draw_call) -> list[tuple[str, tuple[int, int], tuple[object, ...], dict[str, object]]]:
        calls: list[tuple[str, tuple[int, int], tuple[object, ...], dict[str, object]]] = []

        def capture(_surface, text, position, *args, **kwargs) -> None:
            calls.append((text, position, args, kwargs))

        with patch.object(rendering, "draw_text", side_effect=capture):
            draw_call()
        return calls

    def capture_overlay(
        self,
        player,
        point: tuple[int, int] = (640, 360),
        *,
        show_private_info: bool,
    ) -> tuple[
        list[tuple[str, tuple[int, int], tuple[object, ...], dict[str, object]]],
        list[tuple[tuple[object, ...], dict[str, object]]],
        list[tuple[tuple[object, ...], dict[str, object]]],
        list[tuple[tuple[object, ...], dict[str, object]]],
    ]:
        text_calls: list[tuple[str, tuple[int, int], tuple[object, ...], dict[str, object]]] = []
        circle_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        rect_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        health_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def capture_text(_surface, text, position, *args, **kwargs) -> None:
            text_calls.append((text, position, args, kwargs))

        def capture_circle(*args, **kwargs) -> None:
            circle_calls.append((args, kwargs))

        def capture_rect(*args, **kwargs) -> None:
            rect_calls.append((args, kwargs))

        def capture_health(*args, **kwargs) -> None:
            health_calls.append((args, kwargs))

        with (
            patch.object(rendering, "draw_text", side_effect=capture_text),
            patch.object(rendering, "_draw_health_bar", side_effect=capture_health),
            patch.object(rendering.pygame.draw, "circle", side_effect=capture_circle),
            patch.object(rendering.pygame.draw, "rect", side_effect=capture_rect),
        ):
            rendering._draw_player_overlay(
                self.make_surface(),
                player,
                point,
                show_private_info=show_private_info,
            )
        return text_calls, circle_calls, rect_calls, health_calls

    def test_local_overhead_shows_public_and_private_state(self) -> None:
        match = create_match()
        player = match.players[0]
        player.ammo = 0
        player.ultimate_energy = 0.0
        player.upgrade_stacks = 0
        player.tactical_cooldown = 2.0

        texts, circles, rects, _ = self.capture_overlay(player, show_private_info=True)
        values = [call[0] for call in texts]
        self.assertTrue(any(value.startswith("0 ") for value in values))
        self.assertIn(f"{player.health:.0f}/{player.max_health:.0f}", values)
        self.assertIn(f"彈藥 0/{player.ammo_capacity}", values)
        self.assertIn("大招 0%", values)
        self.assertIn(f"強化 0/{config.MAX_UPGRADE_STACKS}", values)
        self.assertIn(config.PANEL_BORDER_COLOR, [args[1] for args, _ in rects if len(args) > 1])
        self.assertIn(config.PANEL_BORDER_COLOR, [args[1] for args, _ in circles if len(args) > 1])

        player.ammo = player.ammo_capacity
        player.ultimate_energy = 100.0
        player.upgrade_stacks = config.MAX_UPGRADE_STACKS
        player.tactical_cooldown = 0.0
        texts, circles, _, _ = self.capture_overlay(player, show_private_info=True)
        values = [call[0] for call in texts]
        self.assertIn(f"彈藥 {player.ammo_capacity}/{player.ammo_capacity}", values)
        self.assertIn("大招 100%", values)
        self.assertIn(f"強化 {config.MAX_UPGRADE_STACKS}/{config.MAX_UPGRADE_STACKS}", values)
        self.assertIn(config.EXTRACTION_COLOR, [args[1] for args, _ in circles if len(args) > 1])

    def test_local_overhead_clamps_resources_and_health_boundaries_repeatedly(self) -> None:
        match = create_match()
        player = match.players[0]
        for index in range(20):
            at_max = index % 2 == 1
            player.health = player.max_health + 500.0 if at_max else -500.0
            player.ammo = player.ammo_capacity + 5 if at_max else -5
            player.ultimate_energy = 500.0 if at_max else -500.0
            player.upgrade_stacks = config.MAX_UPGRADE_STACKS + 5 if at_max else -5

            texts, _, _, _ = self.capture_overlay(player, show_private_info=True)
            values = [call[0] for call in texts]
            expected_health = f"{player.max_health:.0f}/{player.max_health:.0f}" if at_max else f"0/{player.max_health:.0f}"
            expected_ammo = f"彈藥 {player.ammo_capacity}/{player.ammo_capacity}" if at_max else f"彈藥 0/{player.ammo_capacity}"
            expected_energy = "大招 100%" if at_max else "大招 0%"
            expected_upgrade = (
                f"強化 {config.MAX_UPGRADE_STACKS}/{config.MAX_UPGRADE_STACKS}"
                if at_max
                else f"強化 0/{config.MAX_UPGRADE_STACKS}"
            )
            self.assertIn(expected_health, values)
            self.assertIn(expected_ammo, values)
            self.assertIn(expected_energy, values)
            self.assertIn(expected_upgrade, values)

    def test_local_overhead_gadget_color_updates_for_ready_cooldown_and_death(self) -> None:
        match = create_match()
        player = match.players[0]
        states = ((True, 0.0, config.EXTRACTION_COLOR), (True, 1.0, config.PANEL_BORDER_COLOR), (False, 0.0, config.PANEL_BORDER_COLOR))
        for alive, cooldown, expected_color in states:
            for _ in range(20):
                player.alive = alive
                player.tactical_cooldown = cooldown
                _, circles, _, _ = self.capture_overlay(player, show_private_info=True)
                colors = [args[1] for args, _ in circles if len(args) > 1]
                self.assertIn(expected_color, colors)
                if not alive:
                    self.assertNotIn(config.EXTRACTION_COLOR, colors)
        player.alive = True

    def test_local_overhead_follows_player_screen_coordinates_twenty_times(self) -> None:
        match = create_match()
        player = match.players[0]
        observed_points: list[tuple[int, int]] = []
        for index in range(20):
            match.camera.position = Vector2(100.0 + index * 3.0, 40.0 + index * 2.0)
            player.position = Vector2(500.0 + index * 8.0, 300.0 + index * 4.0)
            expected_point = rendering._screen_point(match, player.position)
            _, _, _, health_calls = self.capture_overlay(player, expected_point, show_private_info=True)
            self.assertEqual(len(health_calls), 1)
            observed_point = health_calls[0][0][1]
            self.assertEqual(observed_point, expected_point)
            observed_points.append(observed_point)
        self.assertEqual(len(set(observed_points)), 20)

    def test_overhead_edge_clamp_and_long_identity_use_shared_layout_rules(self) -> None:
        from types import SimpleNamespace

        match = create_match()
        player = match.players[0]
        long_definition = SimpleNamespace(display_name="這是一個非常非常長的角色名稱，用來驗證省略號", character_id=player.character_id)
        surface = self.make_surface()
        with patch.object(rendering, "get_character_definition", return_value=long_definition):
            left_texts, _, _, left_health = self.capture_overlay(player, (0, 360), show_private_info=False)
            right_texts, _, _, right_health = self.capture_overlay(
                player,
                (surface.get_width(), 360),
                show_private_info=False,
            )

        left_identity = next(call for call in left_texts if call[0].startswith(f"{player.player_id} "))
        right_identity = next(call for call in right_texts if call[0].startswith(f"{player.player_id} "))
        self.assertTrue(left_identity[0].endswith("…"))
        self.assertTrue(right_identity[0].endswith("…"))
        self.assertEqual(left_health[0][0][1][0], 8 + rendering._OVERHEAD_MAX_WIDTH // 2)
        self.assertEqual(right_health[0][0][1][0], surface.get_width() - 8 - rendering._OVERHEAD_MAX_WIDTH // 2)
        self.assertGreaterEqual(left_identity[1][0] - rendering._OVERHEAD_MAX_WIDTH // 2, 8)
        self.assertLessEqual(right_identity[1][0] + rendering._OVERHEAD_MAX_WIDTH // 2, surface.get_width() - 8)

    def test_overhead_vertical_clamp_keeps_the_information_block_on_screen(self) -> None:
        match = create_match()
        player = match.players[0]
        surface = self.make_surface()
        identity_font_height = rendering._get_text_font(14).get_height()

        for point in ((surface.get_width() // 2, 0), (surface.get_width() // 2, surface.get_height())):
            panel_calls: list[pygame.Rect] = []

            def capture_panel(_surface, rect, *args, **kwargs) -> None:
                panel_calls.append(rect.copy())

            with patch.object(rendering, "draw_panel", side_effect=capture_panel):
                texts, _, _, health_calls = self.capture_overlay(player, point, show_private_info=True)
            identity = next(call for call in texts if call[0].startswith(f"{player.player_id} "))
            private_row = next(rect for rect in panel_calls if rect.height == rendering._OVERHEAD_PRIVATE_ROW_HEIGHT)
            health_center = health_calls[0][0][1]

            self.assertGreaterEqual(identity[1][1] - identity_font_height // 2, 8)
            self.assertGreaterEqual(health_center[1] + rendering._OVERHEAD_HEALTH_BAR_Y_OFFSET, 8)
            self.assertGreaterEqual(private_row.top, 8)
            self.assertLessEqual(private_row.bottom, surface.get_height() - 8)

    def test_other_player_overhead_only_contains_public_information(self) -> None:
        match = create_match()
        player = match.players[1]
        player.alive = False
        player.ammo = 0
        player.ultimate_energy = 100.0
        player.upgrade_stacks = config.MAX_UPGRADE_STACKS
        player.tactical_cooldown = 0.0
        player.death_timer = 4.0

        for _ in range(20):
            texts, circles, rects, _ = self.capture_overlay(player, show_private_info=False)
            values = [call[0] for call in texts]
            self.assertTrue(any(value.startswith(f"{player.player_id} ") for value in values))
            self.assertIn(f"{player.health:.0f}/{player.max_health:.0f}", values)
            for private_label in ("彈藥", "大招", "強化", "配件", "死亡"):
                self.assertFalse(any(private_label in value for value in values))
            self.assertEqual(circles, [])
            self.assertEqual(rects, [])

    def test_draw_world_centralizes_private_visibility_for_all_six_players(self) -> None:
        match = create_match()
        match.bushes = []
        match.monsters = []
        match.effects = []
        match.monster_projectiles = []
        match.camera.position = Vector2()
        for index, player in enumerate(match.players):
            player.position = Vector2(
                100.0 + (index % 3) * 400.0,
                150.0 + (index // 3) * 350.0,
            )
        match.players[3].alive = False
        observed: list[tuple[int, bool]] = []

        def capture_overlay(_surface, player, _point, *, show_private_info) -> None:
            observed.append((player.player_id, show_private_info))

        with patch.object(rendering, "_draw_player_overlay", side_effect=capture_overlay):
            rendering.draw_world(self.make_surface(), match, viewer_id=0)

        self.assertEqual({player_id for player_id, _ in observed}, set(range(6)))
        self.assertEqual({player_id for player_id, private in observed if private}, {0})
        self.assertEqual({player_id for player_id, private in observed if not private}, set(range(1, 6)))

    def test_other_player_overlay_is_culled_outside_viewport_and_returns_when_visible(self) -> None:
        match = create_match()
        match.bushes = []
        match.monsters = []
        match.effects = []
        match.monster_projectiles = []
        surface = self.make_surface()
        match.camera.position = Vector2()
        match.players[0].position = Vector2(640.0, 360.0)
        match.players[1].position = Vector2(900.0, 360.0)

        observed: list[int] = []

        def capture_overlay(_surface, player, _point, *, show_private_info) -> None:
            observed.append(player.player_id)

        def draw_and_capture() -> None:
            observed.clear()
            with patch.object(rendering, "_draw_player_overlay", side_effect=capture_overlay):
                rendering.draw_world(surface, match, viewer_id=0)

        draw_and_capture()
        self.assertIn(1, observed)
        self.assertIn(0, observed)

        offscreen_positions = (
            Vector2(-1.0, 360.0),
            Vector2(surface.get_width(), 360.0),
            Vector2(640.0, -1.0),
            Vector2(640.0, surface.get_height()),
        )
        for _ in range(5):
            for position in offscreen_positions:
                match.players[1].position = position
                draw_and_capture()
                self.assertNotIn(1, observed)
                self.assertIn(0, observed)

        match.players[1].position = Vector2(900.0, 360.0)
        draw_and_capture()
        self.assertIn(1, observed)
        self.assertIn(0, observed)

        match.players[1].alive = False
        match.players[1].position = Vector2(-1.0, 360.0)
        draw_and_capture()
        self.assertNotIn(1, observed)
        self.assertIn(0, observed)

    def test_selection_page_contains_role_attack_and_operation_hints(self) -> None:
        from pvpve_escape.characters import get_all_character_definitions

        for selected_index in range(len(CharacterId)):
            calls = self.capture_texts(
                lambda selected_index=selected_index: rendering.draw_selection(
                    self.make_surface(), selected_index, 0
                )
            )
            values = [call[0] for call in calls]
            for definition in get_all_character_definitions():
                self.assertIn(definition.primary_kind, values)
            self.assertTrue(any("左鍵" in value for value in values))
            self.assertTrue(any("右鍵" in value for value in values))
            self.assertTrue(any("Space" in value for value in values))
            self.assertTrue(any("蓄力" in value for value in values))
            self.assertTrue(any("持續引導" in value for value in values))

    def test_battle_hud_no_longer_contains_fixed_attack_prompts(self) -> None:
        match = create_match()
        panels: list[pygame.Rect] = []

        def capture_panel(_surface, rect, *args, **kwargs) -> None:
            panels.append(rect.copy())

        with patch.object(rendering, "draw_panel", side_effect=capture_panel):
            calls = self.capture_texts(lambda: rendering.draw_hud(self.make_surface(), match))
        values = [call[0] for call in calls]
        for removed_prompt in ("左鍵普攻", "右鍵大招", "Space 配件", "普攻提示"):
            self.assertFalse(any(removed_prompt in value for value in values))
        self.assertTrue(any("WASD 移動" in value for value in values))
        self.assertTrue(any("Tab" in value for value in values))
        self.assertTrue(any("F1" in value for value in values))
        self.assertNotIn(pygame.Rect(16, 16, 470, 310), panels)

    def test_local_death_countdown_uses_large_centered_pygame_font_text(self) -> None:
        match = create_match()
        player = match.players[0]
        player.alive = False
        player.death_timer = 4.6

        calls = self.capture_texts(lambda: rendering.draw_hud(self.make_surface(), match))
        countdown_calls = [call for call in calls if call[0] == "死亡倒數 4.6s"]

        self.assertEqual(len(countdown_calls), 1)
        _, position, args, _ = countdown_calls[0]
        self.assertEqual(position, (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2))
        self.assertGreaterEqual(args[0], 48)
        self.assertTrue(args[2])

    def test_death_countdown_is_private_to_the_current_viewer(self) -> None:
        match = create_match()
        match.players[1].alive = False
        match.players[1].death_timer = 4.0

        other_player_view = self.capture_texts(
            lambda: rendering.draw_hud(self.make_surface(), match, viewer_id=0)
        )
        self.assertFalse(any(call[0].startswith("死亡倒數") for call in other_player_view))

        local_dead_view = self.capture_texts(
            lambda: rendering.draw_hud(self.make_surface(), match, viewer_id=1)
        )
        self.assertTrue(any(call[0] == "死亡倒數 4.0s" for call in local_dead_view))


class BreacherVisualRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        # 只清理可能建立的顯示資源，保留共用字型與 Pygame 初始化。
        pygame.display.quit()

    @staticmethod
    def make_surface() -> pygame.Surface:
        return pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)

    def test_common_player_visual_selects_attack_over_move(self) -> None:
        player = create_match().players[0]
        player.animation_state.facing_direction_index = 2
        player.animation_state.moving = True
        player.animation_state.move_elapsed = config.BREACHER_MOVE_FRAME_TIME
        player.animation_state.attack_elapsed = config.BREACHER_ATTACK_FRAME_TIME * 2
        player.animation_state.attack_hold = config.BREACHER_ATTACK_FRAME_TIME
        fake_sprite = pygame.Surface((config.BREACHER_SPRITE_DISPLAY_SIZE,) * 2, pygame.SRCALPHA)

        with patch.object(rendering, "load_breacher_sprite", return_value=fake_sprite) as loader:
            rendering.draw_player_visual(self.make_surface(), player, (300, 300), config.ACCENT_COLOR)

        loader.assert_called_once_with("attack", 2, 2, config.BREACHER_SPRITE_DISPLAY_SIZE)

    def test_selection_and_roster_use_idle_sprite_but_other_roles_keep_geometry(self) -> None:
        fake_sprite = pygame.Surface((config.BREACHER_SELECTION_SPRITE_SIZE,) * 2, pygame.SRCALPHA)
        with patch.object(rendering, "load_breacher_sprite", return_value=fake_sprite) as loader:
            rendering.draw_selection(self.make_surface(), 0, 0)
        self.assertTrue(any(call.args[:3] == ("idle", 0, 0) for call in loader.call_args_list))

        match = create_match()
        with patch.object(rendering, "load_breacher_sprite", return_value=fake_sprite) as loader:
            rendering._draw_player_roster(self.make_surface(), match)
        self.assertTrue(any(call.args[0] == "idle" for call in loader.call_args_list))

    def test_unavailable_breacher_sprite_falls_back_to_existing_geometry(self) -> None:
        player = create_match().players[0]
        with patch.object(rendering, "load_breacher_sprite", return_value=None):
            with patch.object(rendering, "_draw_role_shape") as geometry:
                rendering.draw_player_visual(self.make_surface(), player, (300, 300), config.ACCENT_COLOR)
        geometry.assert_called_once()

    def test_world_uses_common_visual_entry_for_live_players(self) -> None:
        match = create_match()
        match.monsters = []
        match.bushes = []
        match.effects = []
        match.monster_projectiles = []
        surface = self.make_surface()
        with patch.object(rendering, "draw_player_visual") as draw_visual:
            rendering.draw_world(surface, match)
        self.assertTrue(any(call.args[1] is match.players[0] for call in draw_visual.call_args_list))

    def test_qwe_update_selected_tactical_index(self) -> None:
        from pvpve_escape.main import GameApplication

        controller = HumanController()
        application = GameApplication.__new__(GameApplication)
        application.selected_character_index = 0
        application.selected_tactical_index = 0
        for key, expected_index in ((pygame.K_q, 0), (pygame.K_w, 1), (pygame.K_e, 2)):
            state = controller.collect(
                [pygame.event.Event(pygame.KEYDOWN, key=key)],
                Vector2(),
                Vector2(),
                MatchPhase.CHARACTER_SELECT,
            )
            application._update_selection(state)
            self.assertEqual(application.selected_tactical_index, expected_index)


if __name__ == "__main__":
    unittest.main()
