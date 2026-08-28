"""地形資料、碰撞、路徑與破壞政策的純 Python 測試。"""

from __future__ import annotations

import unittest

from pvpve_escape import config
from pvpve_escape.characters import create_primary_action, create_tactical_action, create_ultimate_action
from pvpve_escape.controllers import InputState
from pvpve_escape.models import (
    BushState,
    CharacterId,
    ControllerType,
    MonsterBehavior,
    ObstacleKind,
    ObstacleState,
    PlayerState,
    TerrainInteraction,
    TacticalId,
    Vector2,
    WorldRect,
)
from pvpve_escape.terrain import (
    build_terrain,
    circle_intersects_rect,
    destroy_bushes_on_segment,
    destroy_terrain_in_radius,
    destroy_thin_wall_on_path,
    first_obstacle_on_segment,
    is_player_in_bush,
    is_player_visible_to_viewer,
    move_circle_with_obstacles,
    resolve_path_endpoint,
    snapshot_obstacles,
)
from pvpve_escape.world import _apply_action, _knockback, create_match, update_monsters, update_player_movement, update_world


class TerrainGeometryTests(unittest.TestCase):
    def test_world_rect_exposes_edges_center_and_contains(self) -> None:
        rect = WorldRect(10, 20, 30, 40)

        self.assertEqual(rect.right, 40)
        self.assertEqual(rect.bottom, 60)
        self.assertEqual(rect.center.tuple(), (25, 40))
        self.assertTrue(rect.contains(Vector2(10, 20)))
        self.assertTrue(rect.contains(Vector2(40, 60)))
        self.assertFalse(rect.contains(Vector2(41, 60)))

    def test_circle_rectangle_boundary_and_corner_contact_are_consistent(self) -> None:
        rect = WorldRect(100, 100, 40, 40)

        self.assertTrue(circle_intersects_rect(Vector2(90, 120), 10, rect))
        self.assertTrue(circle_intersects_rect(Vector2(90, 90), 14.15, rect))
        self.assertFalse(circle_intersects_rect(Vector2(89, 89), 14.0, rect))

    def test_first_wall_path_returns_the_nearest_wall_and_radius_adjusted_point(self) -> None:
        wall = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(100, 80, 20, 80))

        hit = first_obstacle_on_segment(Vector2(0, 120), Vector2(240, 120), [wall], radius=10)

        self.assertTrue(hit.blocked)
        self.assertIs(hit.obstacle, wall)
        self.assertAlmostEqual(hit.distance, 90.0)
        self.assertAlmostEqual(hit.position.x, 90.0)
        self.assertAlmostEqual(hit.position.y, 120.0)

    def test_path_can_leave_a_wall_boundary_without_a_false_block(self) -> None:
        wall = ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(100, 80, 20, 80))

        leaving = first_obstacle_on_segment(
            Vector2(90, 120),
            Vector2(0, 120),
            [wall],
            radius=10,
        )
        entering = first_obstacle_on_segment(
            Vector2(90, 120),
            Vector2(240, 120),
            [wall],
            radius=10,
        )

        self.assertFalse(leaving.blocked)
        self.assertEqual(leaving.position.tuple(), (0.0, 120.0))
        self.assertTrue(entering.blocked)
        self.assertAlmostEqual(entering.position.x, 90.0)

    def test_path_endpoint_keeps_requested_end_when_no_wall_exists(self) -> None:
        result = resolve_path_endpoint(Vector2(30, 30), Vector2(3, 4), 50, [])

        self.assertFalse(result.blocked)
        self.assertIsNone(result.obstacle)
        self.assertEqual(result.position.tuple(), (60.0, 70.0))
        self.assertAlmostEqual(result.distance, 50.0)

    def test_axis_separated_movement_stops_and_diagonal_movement_slides(self) -> None:
        wall = ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(100, 100, 40, 100))

        stopped = move_circle_with_obstacles(Vector2(50, 150), Vector2(100, 0), 10, [wall])
        slid = move_circle_with_obstacles(Vector2(50, 150), Vector2(100, 100), 10, [wall])

        self.assertLessEqual(stopped.x, 90.0 + config.TERRAIN_GEOMETRY_EPSILON)
        self.assertAlmostEqual(slid.x, 90.0, delta=0.01)
        self.assertGreater(slid.y, 150.0)

    def test_diagonal_movement_cannot_cut_through_a_wall_corner(self) -> None:
        wall = ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(100, 100, 40, 100))

        result = move_circle_with_obstacles(Vector2(50, 90), Vector2(100, 100), 10, [wall])

        self.assertLessEqual(result.x, 90.0 + config.TERRAIN_GEOMETRY_EPSILON)

    def test_diagonal_movement_keeps_sliding_after_contact_with_a_thick_wall(self) -> None:
        wall = ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(900, 500, 100, 160))
        position = Vector2(850, 480)

        for _ in range(8):
            position = move_circle_with_obstacles(position, Vector2(10, 10), 18, [wall])

        self.assertLessEqual(position.x, 900.0 - 18.0 + config.TERRAIN_GEOMETRY_EPSILON)
        self.assertGreater(position.y, 500.0)

    def test_each_built_terrain_collection_is_independent(self) -> None:
        first_obstacles, first_bushes = build_terrain()
        second_obstacles, second_bushes = build_terrain()

        first_obstacles[0].destroyed = True
        first_bushes[0].active = False

        self.assertFalse(second_obstacles[0].destroyed)
        self.assertTrue(second_bushes[0].active)
        self.assertEqual(len(first_obstacles), 18)
        self.assertEqual(len(first_bushes), 27)
        self.assertEqual(sum(item.kind == ObstacleKind.THICK_WALL for item in first_obstacles), 12)
        self.assertEqual(sum(item.kind == ObstacleKind.THIN_WALL for item in first_obstacles), 6)

    def test_snapshot_keeps_obstacle_identity_kind_and_bounds(self) -> None:
        obstacles, _ = build_terrain()

        snapshot = snapshot_obstacles(obstacles)

        self.assertEqual(len(snapshot), 18)
        self.assertEqual(snapshot[0][0], obstacles[0].obstacle_id)
        self.assertEqual(snapshot[0][1], obstacles[0].kind)
        self.assertEqual(snapshot[0][2], obstacles[0].bounds)

    def test_create_match_rebuilds_the_confirmed_terrain_for_every_new_round(self) -> None:
        first = create_match()
        second = create_match()

        self.assertEqual(len(first.obstacles), 18)
        self.assertEqual(len(first.bushes), 27)
        self.assertEqual(
            [(item.kind, item.bounds) for item in first.obstacles],
            [(item.kind, item.bounds) for item in second.obstacles],
        )
        self.assertIsNot(first.obstacles, second.obstacles)
        first.obstacles[0].destroyed = True
        first.bushes[0].active = False
        self.assertFalse(second.obstacles[0].destroyed)
        self.assertTrue(second.bushes[0].active)

    def test_player_movement_stays_in_front_of_a_confirmed_wall_for_repeated_steps(self) -> None:
        match = create_match()
        player = match.players[0]
        for _ in range(20):
            player.position = Vector2(850, 580)
            update_player_movement(player, Vector2(1, 0), 1.0, match.obstacles)
            self.assertLessEqual(player.position.x, 900.0 - player.radius + config.TERRAIN_GEOMETRY_EPSILON)

    def test_update_world_uses_the_same_wall_collision_for_human_input(self) -> None:
        match = create_match()
        match.monsters = []
        player = match.players[0]
        for other in match.players[1:]:
            other.alive = False

        for _ in range(20):
            player.position = Vector2(850, 580)
            update_world(match, {0: InputState(move_direction=Vector2(1, 0))}, 0.05)
            self.assertLessEqual(
                player.position.x,
                900.0 - player.radius + config.TERRAIN_GEOMETRY_EPSILON,
            )

    def test_player_diagonal_input_continues_along_a_thick_wall(self) -> None:
        match = create_match()
        player = match.players[0]
        player.position = Vector2(850, 480)
        match.obstacles = [
            ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(900, 500, 100, 160)),
        ]

        for _ in range(10):
            update_player_movement(player, Vector2(1, 1), 0.05, match.obstacles)

        self.assertLessEqual(
            player.position.x,
            900.0 - player.radius + config.TERRAIN_GEOMETRY_EPSILON,
        )
        self.assertGreater(player.position.y, 500.0)

    def test_monster_movement_also_stops_at_the_same_wall_geometry(self) -> None:
        match = create_match()
        owner = match.players[0]
        owner.position = Vector2(1050, 580)
        for player in match.players[1:]:
            player.alive = False
        monster = match.monsters[0]
        monster.position = Vector2(850, 580)
        monster.spawn_position = monster.position.copy()
        monster.move_speed = 220.0
        match.monsters = [monster]

        for _ in range(20):
            monster.position = Vector2(850, 580)
            monster.attack_timer = 999.0
            update_monsters(match, 1.0)
            self.assertLessEqual(monster.position.x, 900.0 - monster.radius + config.TERRAIN_GEOMETRY_EPSILON)

    def test_projectile_stops_at_the_first_wall_and_cannot_hit_a_wall_behind_target(self) -> None:
        for _ in range(20):
            match = create_match(CharacterId.SNIPER)
            match.monsters = []
            owner = match.players[0]
            owner.position = Vector2(800, 580)
            target = match.players[1]
            target.position = Vector2(1000, 580)
            for player in match.players[2:]:
                player.alive = False
            match.obstacles = [
                ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(900, 500, 40, 160)),
            ]

            action = create_primary_action(owner, Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            health_before = target.health
            for _ in range(20):
                update_world(match, {0: InputState()}, 0.05)

            self.assertEqual(target.health, health_before)
            self.assertFalse(any(effect.position.x > 892.0 + config.TERRAIN_GEOMETRY_EPSILON for effect in match.effects))

    def test_knockback_stops_at_a_wall_instead_of_pushing_a_target_through_it(self) -> None:
        match = create_match(CharacterId.BREACHER)
        target = match.players[1]
        target.position = Vector2(880, 580)
        match.obstacles = [
            ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(900, 500, 40, 160)),
        ]

        _knockback(match, "player", target.player_id, Vector2(800, 580), 200.0)

        self.assertLessEqual(
            target.position.x,
            900.0 - target.radius + config.TERRAIN_GEOMETRY_EPSILON,
        )

    def test_boomerang_return_does_not_cross_a_wall_if_owner_is_on_the_other_side(self) -> None:
        match = create_match(CharacterId.HUNTER)
        match.monsters = []
        owner = match.players[0]
        owner.position = Vector2(800, 580)
        for player in match.players[1:]:
            player.alive = False
        match.obstacles = [
            ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(900, 500, 40, 160)),
        ]

        action = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        boomerang = next(effect for effect in match.effects if effect.kind == "boomerang")
        for _ in range(30):
            update_world(match, {0: InputState()}, 0.05)
            if boomerang.returning:
                break

        self.assertTrue(boomerang.returning)
        owner.position = Vector2(1000, 580)
        update_world(match, {0: InputState()}, 0.05)

        self.assertLessEqual(
            boomerang.position.x,
            900.0 - config.BOOMERANG_PROJECTILE_RADIUS + config.TERRAIN_GEOMETRY_EPSILON,
        )
        self.assertEqual(boomerang.impact_status, "牆")

    def test_breacher_primary_blocks_thin_wall_without_breaking_it(self) -> None:
        for _ in range(20):
            match = create_match(CharacterId.BREACHER)
            match.monsters = []
            owner = match.players[0]
            owner.position = Vector2(800, 580)
            target = match.players[1]
            target.position = Vector2(1000, 580)
            for player in match.players[2:]:
                player.alive = False
            wall = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(900, 500, 40, 160))
            match.obstacles = [wall]
            bush = BushState(0, WorldRect(820, 550, 40, 60))
            match.bushes = [bush]

            action = create_primary_action(owner, Vector2(1, 0))
            self.assertIsNotNone(action)
            self.assertEqual(action.terrain_interaction, TerrainInteraction.BLOCK)
            _apply_action(match, action)
            health_before = target.health
            self.assertFalse(wall.destroyed)
            self.assertTrue(match.bushes[0].active)
            for _ in range(20):
                update_world(match, {0: InputState()}, 0.05)
            self.assertEqual(target.health, health_before)

    def test_breacher_ultimate_area_breaks_thin_wall_and_bush_but_not_thick_wall(self) -> None:
        match = create_match(CharacterId.BREACHER)
        owner = match.players[0]
        owner.position = Vector2(800, 580)
        thin = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(820, 550, 20, 60))
        thick = ObstacleState(2, ObstacleKind.THICK_WALL, WorldRect(840, 550, 20, 60))
        bush = BushState(0, WorldRect(820, 550, 20, 60))
        match.obstacles = [thin, thick]
        match.bushes = [bush]
        owner.ultimate_energy = 100.0

        action = create_ultimate_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)

        self.assertTrue(thin.destroyed)
        self.assertFalse(thick.destroyed)
        self.assertFalse(bush.active)

    def test_world_updates_monsters_after_player_breaks_thin_wall(self) -> None:
        match = create_match(CharacterId.BREACHER)
        owner = match.players[0]
        owner.position = Vector2(400, 500)
        owner.ultimate_energy = 100.0
        for player in match.players[1:]:
            player.alive = False

        monster = match.monsters[0]
        monster.position = Vector2(900, 500)
        monster.spawn_position = monster.position.copy()
        monster.behavior = MonsterBehavior.CHASE
        monster.target_player_id = owner.player_id
        monster.attack_timer = 999.0
        monster.navigation_path = [Vector2(1, 1)]
        thin = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(500, 450, 40, 100))
        thick = ObstacleState(2, ObstacleKind.THICK_WALL, WorldRect(700, 450, 40, 100))
        match.obstacles = [thin, thick]
        monster.navigation_obstacle_signature = snapshot_obstacles(match.obstacles)
        match.monsters = [monster]

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), ultimate_pressed=True)},
            0.01,
        )

        self.assertTrue(thin.destroyed)
        self.assertTrue(thick.solid)
        self.assertEqual(
            monster.navigation_obstacle_signature,
            snapshot_obstacles(match.obstacles),
        )
        self.assertNotIn(Vector2(1, 1), monster.navigation_path)

    def test_dash_breaks_only_the_first_thin_wall_then_stops_at_the_next_wall(self) -> None:
        for _ in range(20):
            match = create_match(CharacterId.CONTROLLER, TacticalId.DASH)
            owner = match.players[0]
            owner.position = Vector2(800, 500)
            first = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(850, 450, 20, 100))
            second = ObstacleState(2, ObstacleKind.THIN_WALL, WorldRect(1000, 450, 20, 100))
            match.obstacles = [first, second]
            bush = BushState(0, WorldRect(830, 450, 80, 100))
            match.bushes = [bush]

            action = create_tactical_action(owner, Vector2(1, 0), Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)

            self.assertTrue(first.destroyed)
            self.assertFalse(second.destroyed)
            self.assertFalse(match.bushes[0].active)
            self.assertAlmostEqual(owner.position.x, 982.0, delta=0.01)

    def test_non_qualified_primary_and_non_dash_tactical_do_not_destroy_walls_or_bushes(self) -> None:
        for role in (CharacterId.SNIPER, CharacterId.HUNTER, CharacterId.CONTROLLER):
            match = create_match(role, TacticalId.SHIELD if role == CharacterId.SNIPER else TacticalId.CONTROL)
            owner = match.players[0]
            owner.position = Vector2(800, 580)
            wall = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(900, 500, 40, 160))
            bush = BushState(0, WorldRect(820, 550, 40, 60))
            match.obstacles = [wall]
            match.bushes = [bush]
            action = create_primary_action(owner, Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            self.assertFalse(wall.destroyed, role)
            self.assertTrue(bush.active, role)

        match = create_match(CharacterId.CONTROLLER, TacticalId.CONTROL)
        owner = match.players[0]
        owner.position = Vector2(800, 580)
        wall = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(900, 500, 40, 160))
        match.obstacles = [wall]
        action = create_tactical_action(owner, Vector2(1, 0), Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        self.assertFalse(wall.destroyed)


class TerrainDestructionAndVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.obstacles, self.bushes = build_terrain()

    def test_only_first_thin_wall_on_a_path_can_be_destroyed(self) -> None:
        thick = ObstacleState(1, ObstacleKind.THICK_WALL, WorldRect(100, 0, 20, 100))
        thin = ObstacleState(2, ObstacleKind.THIN_WALL, WorldRect(160, 0, 20, 100))
        obstacles = [thick, thin]

        destroyed = destroy_thin_wall_on_path(Vector2(0, 50), Vector2(240, 50), obstacles)

        self.assertIsNone(destroyed)
        self.assertFalse(thin.destroyed)
        thick.destroyed = True
        destroyed = destroy_thin_wall_on_path(Vector2(0, 50), Vector2(240, 50), obstacles)
        self.assertIs(destroyed, thin)
        self.assertTrue(thin.destroyed)

    def test_area_and_segment_policies_remove_thin_walls_and_bushes(self) -> None:
        wall = ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(100, 100, 40, 40))
        thick = ObstacleState(2, ObstacleKind.THICK_WALL, WorldRect(150, 100, 40, 40))
        bush = self.bushes[0]
        bush.bounds = WorldRect(100, 100, 40, 40)
        obstacles = [wall, thick]

        removed_walls, removed_bushes = destroy_terrain_in_radius(Vector2(120, 120), 5, obstacles, [bush])

        self.assertEqual(removed_walls, [wall])
        self.assertEqual(removed_bushes, [bush])
        self.assertTrue(wall.destroyed)
        self.assertFalse(thick.destroyed)
        self.assertFalse(bush.active)

    def test_segment_destruction_does_not_remove_bushes_that_are_not_crossed(self) -> None:
        bush = self.bushes[0]
        bush.bounds = WorldRect(100, 100, 40, 40)

        removed = destroy_bushes_on_segment(Vector2(0, 0), Vector2(50, 50), [bush])

        self.assertEqual(removed, [])
        self.assertTrue(bush.active)

    def test_player_visibility_is_self_visible_and_otherwise_bush_dependent(self) -> None:
        player = PlayerState(
            player_id=2,
            controller_type=ControllerType.DUMMY,
            character_id=CharacterId.BREACHER,
            tactical_id=TacticalId.DASH,
            position=Vector2(1100, 540),
            spawn_position=Vector2(1100, 540),
        )
        self.assertTrue(is_player_in_bush(player, self.bushes))
        self.assertTrue(is_player_visible_to_viewer(player, 2, self.bushes))
        self.assertFalse(is_player_visible_to_viewer(player, 0, self.bushes))

        for bush in self.bushes:
            bush.active = False
        self.assertFalse(is_player_in_bush(player, self.bushes))
        self.assertTrue(is_player_visible_to_viewer(player, 0, self.bushes))

    def test_terrain_interaction_enum_has_explicit_breaking_policies(self) -> None:
        self.assertEqual(TerrainInteraction.BLOCK.value, "BLOCK")
        self.assertEqual(TerrainInteraction.BREAK_THIN_ON_PATH.value, "BREAK_THIN_ON_PATH")
        self.assertEqual(TerrainInteraction.BREAK_THIN_IN_AREA.value, "BREAK_THIN_IN_AREA")
        self.assertEqual(TerrainInteraction.DASH_BREAK_FIRST_THIN.value, "DASH_BREAK_FIRST_THIN")


if __name__ == "__main__":
    unittest.main()
