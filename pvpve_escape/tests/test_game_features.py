"""新玩法：歷史位置自動瞄準、怪物種類與介紹頁回歸測試。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.auto_aim import resolve_auto_aim
from pvpve_escape.characters import create_ultimate_action
from pvpve_escape.controllers import HumanController, InputState
from pvpve_escape.models import (
    AppScreen,
    BushState,
    CharacterId,
    MonsterType,
    MonsterBehavior,
    ObstacleKind,
    ObstacleState,
    TacticalId,
    Vector2,
    WorldRect,
)
from pvpve_escape.monsters import get_monster_definition
from pvpve_escape.terrain import circle_intersects_rect
from pvpve_escape.world import (
    _apply_action,
    _choose_wander_target,
    create_match,
    update_monsters,
    update_world,
)


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

    def test_monsters_start_in_wander_without_shared_navigation_state(self) -> None:
        match = create_match()

        self.assertTrue(all(monster.behavior == MonsterBehavior.WANDER for monster in match.monsters))
        self.assertTrue(all(monster.target_player_id is None for monster in match.monsters))
        self.assertTrue(all(not monster.navigation_path for monster in match.monsters))
        self.assertEqual(len({id(monster.navigation_path) for monster in match.monsters}), len(match.monsters))

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


class MonsterNavigationIntegrationTests(unittest.TestCase):
    def _prepare_wall_chase(self, monster_type: MonsterType):
        match = create_match()
        target = match.players[0]
        target.position = Vector2(460, 500)
        for player in match.players[1:]:
            player.alive = False

        monster = next(item for item in match.monsters if item.monster_type == monster_type)
        monster.position = Vector2(420, 500)
        monster.spawn_position = monster.position.copy()
        monster.attack_timer = 999.0
        match.monsters = [monster]
        match.obstacles = []

        update_monsters(match, 0.05)
        self.assertEqual(monster.target_player_id, target.player_id)

        target.position = Vector2(800, 500)
        match.obstacles = [
            ObstacleState(
                obstacle_id=1,
                kind=ObstacleKind.THICK_WALL,
                bounds=WorldRect(600, 480, 40, 40),
            )
        ]
        return match, monster, target, match.obstacles[0]

    def test_each_monster_type_reaches_a_wall_blocked_target_without_jumping(self) -> None:
        for _ in range(20):
            for monster_type in MonsterType:
                match, monster, target, wall = self._prepare_wall_chase(monster_type)
                saw_navigation_path = False
                previous_position = monster.position.copy()

                for _ in range(200):
                    update_monsters(match, 0.05)
                    saw_navigation_path = saw_navigation_path or bool(monster.navigation_path)
                    displacement = previous_position.distance_to(monster.position)
                    self.assertLessEqual(
                        displacement,
                        monster.move_speed * 0.05 * monster.slow_multiplier
                        + config.TERRAIN_GEOMETRY_EPSILON,
                    )
                    self.assertFalse(circle_intersects_rect(monster.position, monster.radius, wall.bounds))
                    previous_position = monster.position.copy()

                self.assertTrue(saw_navigation_path)
                definition = get_monster_definition(monster_type)
                interaction_distance = (
                    definition.attack_range
                    if monster_type == MonsterType.SHOOTER
                    else monster.radius + target.radius
                )
                self.assertLessEqual(
                    monster.position.distance_to(target.position),
                    interaction_distance + config.TERRAIN_GEOMETRY_EPSILON,
                )

    def test_shooter_does_not_stall_when_preferred_position_is_inside_a_wall_corner(self) -> None:
        match = create_match()
        target = match.players[0]
        for player in match.players[1:]:
            player.alive = False

        shooter = next(monster for monster in match.monsters if monster.monster_type == MonsterType.SHOOTER)
        shooter.position = Vector2(820, 540)
        shooter.spawn_position = shooter.position.copy()
        shooter.attack_timer = 999.0
        match.monsters = [shooter]
        target.position = Vector2(1200, 600)

        # 先在無牆視線下取得目標，再建立牆體，重現已鎖定目標繞牆的情境。
        match.obstacles = []
        update_monsters(match, 0.05)
        self.assertEqual(shooter.target_player_id, target.player_id)
        match.obstacles = [
            ObstacleState(
                obstacle_id=1,
                kind=ObstacleKind.THICK_WALL,
                bounds=WorldRect(900, 500, 100, 160),
            )
        ]

        positions = [shooter.position.copy()]
        for _ in range(200):
            update_monsters(match, 0.05)
            positions.append(shooter.position.copy())
            self.assertFalse(
                circle_intersects_rect(shooter.position, shooter.radius, match.obstacles[0].bounds)
            )

        self.assertGreater(
            max(previous.distance_to(current) for previous, current in zip(positions, positions[1:])),
            config.TERRAIN_GEOMETRY_EPSILON,
        )
        self.assertLessEqual(
            shooter.position.distance_to(target.position),
            get_monster_definition(MonsterType.SHOOTER).preferred_range
            + 36.0
            + config.TERRAIN_GEOMETRY_EPSILON,
        )

    def test_shooter_can_leave_the_navigation_clearance_at_a_long_wall_corner(self) -> None:
        match = create_match()
        target = match.players[0]
        for player in match.players[1:]:
            player.alive = False

        shooter = next(monster for monster in match.monsters if monster.monster_type == MonsterType.SHOOTER)
        shooter.position = Vector2(100, 600)
        shooter.spawn_position = shooter.position.copy()
        shooter.attack_timer = 999.0
        match.monsters = [shooter]
        target.position = Vector2(600, 600)

        match.obstacles = []
        update_monsters(match, 0.05)
        self.assertEqual(shooter.target_player_id, target.player_id)
        match.obstacles = [
            ObstacleState(
                obstacle_id=1,
                kind=ObstacleKind.THIN_WALL,
                bounds=WorldRect(300, 400, 100, 600),
            )
        ]

        positions = [shooter.position.copy()]
        for _ in range(200):
            update_monsters(match, 0.05)
            positions.append(shooter.position.copy())
            self.assertFalse(
                circle_intersects_rect(shooter.position, shooter.radius, match.obstacles[0].bounds)
            )

        self.assertGreater(
            max(previous.distance_to(current) for previous, current in zip(positions, positions[1:])),
            config.TERRAIN_GEOMETRY_EPSILON,
        )
        self.assertLessEqual(
            shooter.position.distance_to(target.position),
            get_monster_definition(MonsterType.SHOOTER).preferred_range
            + 36.0
            + config.TERRAIN_GEOMETRY_EPSILON,
        )

    def test_shooter_falls_back_to_reachable_target_when_preferred_area_is_sealed(self) -> None:
        match = create_match()
        target = match.players[0]
        for player in match.players[1:]:
            player.alive = False

        shooter = next(monster for monster in match.monsters if monster.monster_type == MonsterType.SHOOTER)
        shooter.position = Vector2(460, 470)
        shooter.spawn_position = shooter.position.copy()
        shooter.attack_timer = 999.0
        match.monsters = [shooter]
        target.position = Vector2(950, 470)

        # 先取得目標，再用四面厚牆封住安全的偏好距離點，重現「目標可繞行、
        # 但 300px 偏好點本身不可達」的情境。
        match.obstacles = []
        update_monsters(match, 0.05)
        self.assertEqual(shooter.target_player_id, target.player_id)
        match.obstacles = [
            ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(500, 320, 100, 300)),
            ObstacleState(2, ObstacleKind.THICK_WALL, WorldRect(700, 320, 100, 300)),
            ObstacleState(3, ObstacleKind.THICK_WALL, WorldRect(500, 320, 300, 100)),
            ObstacleState(4, ObstacleKind.THICK_WALL, WorldRect(500, 520, 300, 100)),
        ]

        positions = [shooter.position.copy()]
        for _ in range(200):
            update_monsters(match, 0.05)
            positions.append(shooter.position.copy())
            self.assertTrue(
                all(
                    not circle_intersects_rect(shooter.position, shooter.radius, obstacle.bounds)
                    for obstacle in match.obstacles
                )
            )

        self.assertGreater(
            max(previous.distance_to(current) for previous, current in zip(positions, positions[1:])),
            config.TERRAIN_GEOMETRY_EPSILON,
        )
        self.assertLessEqual(
            shooter.position.distance_to(target.position),
            get_monster_definition(MonsterType.SHOOTER).preferred_range
            + 36.0
            + config.TERRAIN_GEOMETRY_EPSILON,
        )


class MonsterWanderIntegrationTests(unittest.TestCase):
    @staticmethod
    def _isolated_monster(monster_type: MonsterType):
        match = create_match()
        for player in match.players:
            player.alive = False
        monster = next(item for item in match.monsters if item.monster_type == monster_type)
        match.monsters = [monster]
        monster.attack_timer = 0.0
        match.obstacles = []
        return match, monster

    def test_each_monster_type_reaches_two_safe_distinct_wander_points_at_half_speed(self) -> None:
        for _ in range(20):
            for monster_type in MonsterType:
                match, monster = self._isolated_monster(monster_type)
                camp = config.MONSTER_CAMP_POINTS[monster.spawn_zone_id]
                completed_points: list[Vector2] = []
                pause_elapsed: float | None = None
                delta_time = 0.25

                for _ in range(180):
                    previous_position = monster.position.copy()
                    previous_behavior = monster.behavior
                    previous_target = monster.wander_target
                    previous_pause = monster.wander_pause_timer
                    update_monsters(match, delta_time)
                    displacement = previous_position.distance_to(monster.position)

                    if previous_behavior == MonsterBehavior.WANDER and previous_target is not None and previous_pause <= 0.0:
                        self.assertLessEqual(
                            displacement,
                            monster.move_speed
                            * delta_time
                            * config.MONSTER_WANDER_SPEED_RATIO
                            * monster.slow_multiplier
                            + config.TERRAIN_GEOMETRY_EPSILON,
                        )
                    if previous_target is not None and monster.wander_target is None and monster.wander_pause_timer > 0.0:
                        completed_points.append(previous_target.copy())
                        pause_elapsed = 0.0
                    elif pause_elapsed is not None and previous_pause > 0.0:
                        pause_elapsed += delta_time
                        if monster.wander_pause_timer <= 0.0:
                            self.assertAlmostEqual(
                                pause_elapsed,
                                config.MONSTER_WANDER_PAUSE,
                                delta=delta_time,
                            )
                            pause_elapsed = None

                    if monster.wander_target is not None:
                        self.assertLessEqual(
                            monster.wander_target.distance_to(camp),
                            config.MONSTER_WANDER_RADIUS + config.TERRAIN_GEOMETRY_EPSILON,
                        )
                    if len(completed_points) >= 2:
                        break

                self.assertGreaterEqual(len(completed_points), 2)
                self.assertGreater(
                    completed_points[0].distance_to(completed_points[1]),
                    config.MONSTER_NAVIGATION_NODE_ARRIVAL_TOLERANCE,
                )
                self.assertTrue(all(point.distance_to(camp) <= config.MONSTER_WANDER_RADIUS for point in completed_points[:2]))
                self.assertFalse(match.monster_projectiles)

    def test_wander_candidates_use_the_expanded_700px_radius(self) -> None:
        match = create_match()
        match.obstacles = []
        monster = match.monsters[0]
        camp = config.MONSTER_CAMP_POINTS[monster.spawn_zone_id]

        candidate_distances = []
        for _ in range(32):
            candidate = _choose_wander_target(monster, match.obstacles)
            self.assertIsNotNone(candidate)
            candidate_distances.append(candidate.distance_to(camp))

        self.assertGreater(max(candidate_distances), 600.0)
        self.assertLessEqual(max(candidate_distances), config.MONSTER_WANDER_RADIUS)

    def test_monster_returns_to_camp_before_wandering_and_does_not_attack(self) -> None:
        match, monster = self._isolated_monster(MonsterType.CHASER)
        camp = config.MONSTER_CAMP_POINTS[monster.spawn_zone_id]
        monster.position = camp + Vector2(760, 0)
        monster.spawn_position = monster.position.copy()
        health_before = [player.health for player in match.players]

        for _ in range(120):
            update_monsters(match, 0.25)
            if monster.behavior == MonsterBehavior.WANDER:
                break

        self.assertEqual(monster.behavior, MonsterBehavior.WANDER)
        self.assertLessEqual(
            monster.position.distance_to(camp),
            config.MONSTER_CAMP_ARRIVAL_RADIUS + config.TERRAIN_GEOMETRY_EPSILON,
        )
        self.assertEqual(health_before, [player.health for player in match.players])
        self.assertFalse(match.monster_projectiles)

    def test_respawn_clears_chase_wander_and_navigation_state(self) -> None:
        match, monster = self._isolated_monster(MonsterType.BRUTE)
        monster.alive = False
        monster.respawn_timer = 0.0
        monster.position = Vector2(1200, 700)
        monster.behavior = MonsterBehavior.RETURN
        monster.target_player_id = 4
        monster.navigation_path = [Vector2(100, 100)]
        monster.navigation_goal = Vector2(100, 100)
        monster.navigation_obstacle_signature = ((7, ObstacleKind.THICK_WALL, WorldRect(100, 100, 40, 40)),)
        monster.navigation_repath_timer = 4.0
        monster.wander_target = Vector2(200, 200)
        monster.wander_index = 12
        monster.wander_pause_timer = 0.5

        update_monsters(match, 0.05)

        self.assertTrue(monster.alive)
        self.assertEqual(monster.behavior, MonsterBehavior.WANDER)
        self.assertIsNone(monster.target_player_id)
        self.assertFalse(monster.navigation_path)
        self.assertIsNone(monster.navigation_goal)
        self.assertEqual(monster.navigation_obstacle_signature, ())
        self.assertEqual(monster.navigation_repath_timer, 0.0)
        self.assertIsNone(monster.wander_target)
        self.assertEqual(monster.wander_index, 0)
        self.assertEqual(monster.wander_pause_timer, 0.0)
        self.assertEqual(monster.position.tuple(), monster.spawn_position.tuple())


class MonsterCombatRegressionTests(unittest.TestCase):
    @staticmethod
    def _isolated_monster(monster_type: MonsterType):
        match = create_match()
        target = match.players[0]
        target.position = Vector2(500, 500)
        for player in match.players[1:]:
            player.alive = False
        monster = next(item for item in match.monsters if item.monster_type == monster_type)
        match.monsters = [monster]
        match.obstacles = []
        monster.attack_timer = 0.0
        monster.behavior = MonsterBehavior.CHASE
        monster.target_player_id = target.player_id
        return match, monster, target

    def test_chaser_and_brute_keep_contact_attack_only(self) -> None:
        for monster_type, contact_distance in (
            (MonsterType.CHASER, config.MONSTER_RADIUS + config.PLAYER_RADIUS),
            (MonsterType.BRUTE, config.MONSTER_BRUTE_RADIUS + config.PLAYER_RADIUS),
        ):
            match, monster, target = self._isolated_monster(monster_type)
            monster.position = target.position - Vector2(contact_distance, 0)
            health_before = target.health

            update_monsters(match, 0.05)

            definition = get_monster_definition(monster_type)
            self.assertEqual(target.health, health_before - definition.attack_damage)
            self.assertFalse(match.monster_projectiles)

    def test_shooter_keeps_attack_range_preferred_range_and_slow_projectile(self) -> None:
        match, monster, target = self._isolated_monster(MonsterType.SHOOTER)
        definition = get_monster_definition(MonsterType.SHOOTER)
        monster.position = target.position - Vector2(definition.preferred_range, 0)

        update_monsters(match, 0.05)

        self.assertEqual(len(match.monster_projectiles), 1)
        projectile = match.monster_projectiles[0]
        self.assertEqual(projectile.projectile_speed, definition.projectile_speed)
        self.assertEqual(projectile.max_distance, definition.projectile_range)
        self.assertLess(projectile.projectile_speed, config.MONSTER_SHOOTER_PROJECTILE_BASE_SPEED)

        match.monster_projectiles.clear()
        monster.attack_timer = 0.0
        monster.position = target.position - Vector2(definition.attack_range + 10.0, 0)
        before = monster.position.copy()
        update_monsters(match, 0.05)

        self.assertFalse(match.monster_projectiles)
        self.assertGreater(monster.position.x, before.x)

    def test_wander_and_return_never_attack(self) -> None:
        match, monster, target = self._isolated_monster(MonsterType.CHASER)
        target.position = Vector2(1200, 1300)
        monster.behavior = MonsterBehavior.WANDER
        monster.target_player_id = None
        monster.position = config.MONSTER_CAMP_POINTS[monster.spawn_zone_id].copy()
        monster.spawn_position = monster.position.copy()
        monster.attack_timer = 0.0
        health_before = target.health
        update_monsters(match, 0.05)
        self.assertEqual(target.health, health_before)
        self.assertFalse(match.monster_projectiles)

        monster.behavior = MonsterBehavior.RETURN
        monster.target_player_id = None
        monster.wander_target = None
        monster.position = config.MONSTER_CAMP_POINTS[monster.spawn_zone_id] + Vector2(220, 0)
        monster.attack_timer = 0.0
        update_monsters(match, 0.05)
        self.assertEqual(target.health, health_before)
        self.assertFalse(match.monster_projectiles)


class TerrainSkillIntegrationTests(unittest.TestCase):
    def test_breacher_ultimate_breaks_only_intersecting_formal_cells(self) -> None:
        match = create_match(CharacterId.BREACHER, TacticalId.DASH)
        match.monsters = []
        owner = match.players[0]
        owner.position = Vector2(500, 500)
        owner.ultimate_energy = 100.0
        match.obstacles = [
            ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(500, 400, 100, 100)),
            ObstacleState(2, ObstacleKind.THIN_WALL, WorldRect(600, 400, 100, 100)),
            ObstacleState(3, ObstacleKind.THIN_WALL, WorldRect(800, 400, 100, 100)),
            ObstacleState(4, ObstacleKind.THICK_WALL, WorldRect(500, 600, 100, 100)),
        ]
        match.bushes = [
            BushState(1, WorldRect(500, 300, 100, 100)),
            BushState(2, WorldRect(600, 300, 100, 100)),
            BushState(3, WorldRect(800, 300, 100, 100)),
        ]

        action = create_ultimate_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)

        self.assertTrue(match.obstacles[0].destroyed)
        self.assertTrue(match.obstacles[1].destroyed)
        self.assertFalse(match.obstacles[2].destroyed)
        self.assertFalse(match.obstacles[3].destroyed)
        self.assertFalse(match.bushes[0].active)
        self.assertFalse(match.bushes[1].active)
        self.assertTrue(match.bushes[2].active)


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
