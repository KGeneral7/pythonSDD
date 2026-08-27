"""Pygame 文字繪製回歸測試。"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.characters import create_primary_action, create_tactical_action, create_ultimate_action
from pvpve_escape.controllers import HumanController, InputState
from pvpve_escape.models import CharacterId, MatchPhase, TacticalId, Vector2
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

    def test_human_player_marker_is_visible_when_match_starts(self) -> None:
        match = create_match()
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        rendering.draw_match(surface, match)

        player = match.players[0]
        point = (
            round(player.position.x - match.camera.position.x),
            round(player.position.y - match.camera.position.y),
        )
        player_color = config.PLAYER_COLORS[0]
        visible_pixels = sum(
            surface.get_at((x, y))[:3] == player_color
            for x in range(point[0] - config.PLAYER_DRAW_RADIUS, point[0] + config.PLAYER_DRAW_RADIUS + 1)
            for y in range(point[1] - config.PLAYER_DRAW_RADIUS, point[1] + config.PLAYER_DRAW_RADIUS + 1)
            if 0 <= x < surface.get_width() and 0 <= y < surface.get_height()
        )
        self.assertGreater(visible_pixels, 20)

    def test_all_confirmed_walls_and_bushes_are_rendered_on_the_map_layer(self) -> None:
        match = create_match()
        match.camera.position = Vector2()
        surface = pygame.Surface((config.WORLD_WIDTH, config.WORLD_HEIGHT))
        surface.fill(config.GROUND_COLOR)

        rendering.draw_terrain(surface, match)

        for kind, left, top, width, height in config.OBSTACLE_LAYOUT:
            point = (left + width // 2, top + height // 2)
            expected_color = (
                config.THICK_WALL_COLOR
                if kind == "thick_wall"
                else config.THIN_WALL_COLOR
            )
            self.assertEqual(
                surface.get_at(point)[:3],
                expected_color,
                f"{kind} at {point} should be visible with its configured fill color",
            )

        for left, top, width, height in config.BUSH_LAYOUT:
            point = (left + width // 2, top + height // 2)
            self.assertEqual(
                surface.get_at(point)[:3],
                config.BUSH_COLOR,
                f"bush at {point} should be visible with its configured fill color",
            )

    def test_confirmed_terrain_is_visible_in_the_actual_game_viewport_after_camera_moves(self) -> None:
        """正式 1280×720 畫面移到不同世界區域時，牆與草叢都能被取樣。"""

        match = create_match()
        # 移除會遮住取樣點的生物，只驗證 draw_match 的正式地圖繪製鏈。
        match.players = []
        match.monsters = []
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        for _ in range(20):
            # 開場左上視角：這兩個點位於第一個視窗內，且不在 HUD 區域。
            match.camera.position = Vector2(0, 0)
            rendering.draw_match(surface, match)
            self.assertEqual(surface.get_at((1030, 450))[:3], config.THICK_WALL_COLOR)
            self.assertEqual(surface.get_at((970, 280))[:3], config.BUSH_COLOR)

            # 移到地圖右下區域：確認世界座標不是只在開場畫面硬編碼繪製。
            match.camera.position = Vector2(1200, 700)
            rendering.draw_match(surface, match)
            self.assertEqual(surface.get_at((860, 550))[:3], config.THIN_WALL_COLOR)
            self.assertEqual(surface.get_at((770, 30))[:3], config.BUSH_COLOR)

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
        surface.fill(config.GROUND_COLOR)

        rendering.draw_terrain(surface, match)

        self.assertEqual(surface.get_at(wall_center)[:3], config.GROUND_COLOR)
        self.assertEqual(surface.get_at(bush_center)[:3], config.GROUND_COLOR)

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
        self.assertEqual(sniper_effect.previous_position.tuple(), (500.0, 260.0))
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


if __name__ == "__main__":
    unittest.main()
