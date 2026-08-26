"""Pygame 文字繪製回歸測試。"""

import os
import unittest

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
        target_health = target.health

        state = controller.collect(
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
            match.camera.position,
            sniper.position,
            MatchPhase.PLAYING,
        )
        state.aim_direction = Vector2(1, 0)
        update_match(match, state, 0.05)
        update_match(match, state.__class__(aim_direction=Vector2(1, 0)), 0.05)

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


if __name__ == "__main__":
    unittest.main()
