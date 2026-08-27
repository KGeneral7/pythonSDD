"""新玩法：歷史位置自動瞄準、怪物種類與介紹頁回歸測試。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.auto_aim import resolve_auto_aim
from pvpve_escape.controllers import HumanController, InputState
from pvpve_escape.models import (
    AppScreen,
    CharacterId,
    MonsterType,
    ObstacleKind,
    ObstacleState,
    Vector2,
    WorldRect,
)
from pvpve_escape.monsters import get_monster_definition
from pvpve_escape.world import create_match, update_world


class AutoAimHistoryTests(unittest.TestCase):
    def test_auto_aim_uses_the_configured_past_position(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        target = match.players[1]
        owner.position = Vector2(500, 500)
        target.position = Vector2(650, 650)
        for player in match.players[2:]:
            player.alive = False
        match.elapsed_time = 0.2
        match.position_history[("player", target.player_id)] = [
            (0.0, Vector2(650, 500)),
            (0.2, Vector2(650, 650)),
        ]

        result = resolve_auto_aim(match, owner, "primary", Vector2(1, 0))

        self.assertEqual(result.target_id, target.player_id)
        self.assertEqual(result.target_position.tuple(), (650, 500))
        self.assertEqual(result.direction.tuple(), (1.0, 0.0))
        self.assertEqual(result.lookback_seconds, config.AUTO_AIM_LOOKBACK_SECONDS)

    def test_lookback_number_can_be_changed_without_changing_aim_code(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        target = match.players[1]
        owner.position = Vector2(500, 500)
        target.position = Vector2(650, 650)
        for player in match.players[2:]:
            player.alive = False
        match.elapsed_time = 0.2
        match.position_history[("player", target.player_id)] = [
            (0.0, Vector2(650, 500)),
            (0.2, Vector2(650, 650)),
        ]

        with patch.object(config, "AUTO_AIM_LOOKBACK_SECONDS", 0.1):
            result = resolve_auto_aim(match, owner, "primary", Vector2(1, 0))

        self.assertEqual(result.lookback_seconds, 0.1)
        self.assertAlmostEqual(result.target_position.x, 650.0)
        self.assertAlmostEqual(result.target_position.y, 575.0)
        self.assertAlmostEqual(result.direction.y, 75.0 / (150.0**2 + 75.0**2) ** 0.5)

    def test_zero_lookback_uses_the_current_target_position(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        target = match.players[1]
        owner.position = Vector2(500, 500)
        target.position = Vector2(500, 650)
        for player in match.players[2:]:
            player.alive = False

        with patch.object(config, "AUTO_AIM_LOOKBACK_SECONDS", 0.0):
            result = resolve_auto_aim(match, owner, "primary", Vector2(0, 1))

        self.assertEqual(result.target_position.tuple(), target.position.tuple())
        self.assertEqual(result.target_distance, 150.0)

    def test_auto_aim_does_not_choose_a_target_behind_a_wall(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        target = match.players[1]
        owner.position = Vector2(500, 500)
        target.position = Vector2(700, 500)
        for player in match.players[2:]:
            player.alive = False
        match.obstacles = [
            ObstacleState(
                obstacle_id=1,
                kind=ObstacleKind.THICK_WALL,
                bounds=WorldRect(600, 450, 40, 100),
            )
        ]

        with patch.object(config, "AUTO_AIM_LOOKBACK_SECONDS", 0.0):
            result = resolve_auto_aim(
                match,
                owner,
                "primary",
                Vector2(1, 0),
                obstacles=match.obstacles,
            )

        self.assertFalse(result.has_target)

    def test_fired_projectile_keeps_the_historical_direction_and_does_not_hit_immediately(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        target = match.players[1]
        owner.position = Vector2(500, 500)
        target.position = Vector2(500, 650)
        for player in match.players[2:]:
            player.alive = False
        match.elapsed_time = 0.19
        match.position_history[("player", target.player_id)] = [
            (0.0, Vector2(650, 500)),
            (0.19, Vector2(500, 650)),
        ]
        health_before = target.health

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.01,
        )

        projectile = next(effect for effect in match.effects if effect.kind == "sniper_line")
        self.assertGreater(projectile.direction.x, 0.99)
        self.assertLess(abs(projectile.direction.y), 0.1)
        self.assertEqual(target.health, health_before)

    def test_tab_toggles_auto_aim_during_play(self) -> None:
        match = create_match()
        self.assertTrue(match.players[0].auto_aim_enabled)
        update_world(match, {0: InputState(auto_aim_toggle_pressed=True)}, 0.01)
        self.assertFalse(match.players[0].auto_aim_enabled)
        update_world(match, {0: InputState(auto_aim_toggle_pressed=True)}, 0.01)
        self.assertTrue(match.players[0].auto_aim_enabled)


class MonsterRosterTests(unittest.TestCase):
    def test_each_camp_has_one_of_each_monster_type(self) -> None:
        match = create_match()
        self.assertEqual(len(match.monsters), config.MONSTER_CAMP_COUNT * config.MONSTERS_PER_CAMP)
        for zone_id in range(config.MONSTER_CAMP_COUNT):
            types = {
                monster.monster_type
                for monster in match.monsters
                if monster.spawn_zone_id == zone_id
            }
            self.assertEqual(types, set(MonsterType))

    def test_shooter_spawns_a_slow_projectile_instead_of_contact_damage(self) -> None:
        match = create_match()
        owner = match.players[0]
        owner.position = Vector2(500, 500)
        for player in match.players[1:]:
            player.alive = False
        shooter = next(monster for monster in match.monsters if monster.monster_type == MonsterType.SHOOTER)
        shooter.position = Vector2(700, 500)
        shooter.spawn_position = shooter.position.copy()
        match.monsters = [shooter]
        health_before = owner.health

        update_world(match, {0: InputState()}, 0.05)

        self.assertEqual(len(match.monster_projectiles), 1)
        projectile = match.monster_projectiles[0]
        self.assertEqual(projectile.projectile_speed, config.MONSTER_SHOOTER_PROJECTILE_SPEED)
        self.assertLess(projectile.projectile_speed, config.MONSTER_SHOOTER_PROJECTILE_BASE_SPEED)
        self.assertEqual(owner.health, health_before)

    def test_shooter_projectile_can_be_dodged_before_it_reaches_the_player(self) -> None:
        match = create_match()
        owner = match.players[0]
        owner.position = Vector2(500, 500)
        for player in match.players[1:]:
            player.alive = False
        shooter = next(monster for monster in match.monsters if monster.monster_type == MonsterType.SHOOTER)
        shooter.position = Vector2(700, 500)
        shooter.spawn_position = shooter.position.copy()
        match.monsters = [shooter]
        health_before = owner.health

        update_world(match, {0: InputState()}, 0.05)
        self.assertEqual(len(match.monster_projectiles), 1)
        shooter.attack_timer = 99.0

        for _ in range(50):
            update_world(
                match,
                {0: InputState(move_direction=Vector2(0, 1))},
                0.05,
            )

        self.assertEqual(owner.health, health_before)


class IntroScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def test_intro_can_render_and_enter_moves_to_selection(self) -> None:
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        rendering.draw_intro(surface)
        controller = HumanController()
        state = controller.collect(
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)],
            Vector2(),
            None,
            AppScreen.INTRO,
        )
        self.assertTrue(state.intro_continue_requested)


if __name__ == "__main__":
    unittest.main()
