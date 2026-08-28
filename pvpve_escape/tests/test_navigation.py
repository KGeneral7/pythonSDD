"""小怪導航、路徑失效與目標選擇的純 Python 測試。"""

from __future__ import annotations

import unittest

from pvpve_escape import config

from pvpve_escape.models import MonsterBehavior, ObstacleKind, ObstacleState, Vector2, WorldRect
from pvpve_escape.navigation import find_grid_path, grid_to_world
from pvpve_escape.terrain import (
    circle_intersects_rect,
    first_obstacle_on_segment,
    snapshot_obstacles,
)
from pvpve_escape.world import create_match, update_monsters


class NavigationTestCase(unittest.TestCase):
    @staticmethod
    def wall(
        obstacle_id: int = 1,
        kind: ObstacleKind = ObstacleKind.THICK_WALL,
        left: float = 400.0,
        top: float = 300.0,
        width: float = 40.0,
        height: float = 240.0,
        destroyed: bool = False,
    ) -> ObstacleState:
        return ObstacleState(
            obstacle_id=obstacle_id,
            kind=kind,
            bounds=WorldRect(left, top, width, height),
            destroyed=destroyed,
        )

    def test_navigation_module_has_a_pure_path_entry_point(self) -> None:
        result = find_grid_path(Vector2(100, 100), Vector2(200, 100), 16.0, [])

        self.assertIsNotNone(result)
        self.assertEqual(result[-1].tuple(), (200, 100))

    def test_path_stays_inside_world_safe_boundary(self) -> None:
        radius = 16.0

        path = find_grid_path(Vector2(20, 20), Vector2(2380, 1380), radius, [])

        self.assertIsNotNone(path)
        safe_margin = radius + config.MONSTER_NAVIGATION_CLEARANCE
        for point in path or ():
            self.assertGreaterEqual(point.x, safe_margin)
            self.assertLessEqual(point.x, config.WORLD_WIDTH - safe_margin)
            self.assertGreaterEqual(point.y, safe_margin)
            self.assertLessEqual(point.y, config.WORLD_HEIGHT - safe_margin)

    def test_path_goes_around_a_rectangular_wall_with_clearance(self) -> None:
        wall = self.wall(left=560, top=360, width=40, height=280)
        start = Vector2(400, 500)
        goal = Vector2(760, 500)

        path = find_grid_path(start, goal, 16.0, [wall])

        self.assertIsNotNone(path)
        points = [start, *(path or ())]
        self.assertTrue(
            any(point.y < wall.bounds.top or point.y > wall.bounds.bottom for point in points[1:])
        )
        for point in points[1:]:
            self.assertFalse(circle_intersects_rect(point, 16.0, wall.bounds))
        for previous, current in zip(points, points[1:]):
            self.assertLessEqual(
                previous.distance_to(current),
                config.MONSTER_NAVIGATION_CELL_SIZE * 2**0.5 + config.TERRAIN_GEOMETRY_EPSILON,
            )

    def test_larger_monster_radius_cannot_use_a_narrow_corridor(self) -> None:
        top_wall = self.wall(left=0, top=400, width=config.WORLD_WIDTH, height=40)
        bottom_wall = self.wall(
            obstacle_id=2,
            left=0,
            top=480,
            width=config.WORLD_WIDTH,
            height=40,
        )
        start = Vector2(200, 460)
        goal = Vector2(800, 460)

        small_path = find_grid_path(start, goal, 8.0, [top_wall, bottom_wall])
        large_path = find_grid_path(start, goal, 16.0, [top_wall, bottom_wall])

        self.assertIsNotNone(small_path)
        self.assertIsNone(large_path)

    def test_diagonal_route_does_not_cut_through_a_wall_corner(self) -> None:
        wall = self.wall(left=400, top=400, width=40, height=40)
        start = Vector2(340, 340)
        goal = Vector2(500, 500)

        path = find_grid_path(start, goal, 8.0, [wall])

        self.assertIsNotNone(path)
        points = [start, *(path or ())]
        for previous, current in zip(points, points[1:]):
            self.assertFalse(
                circle_intersects_rect(
                    current,
                    8.0,
                    wall.bounds,
                )
            )
            self.assertFalse(
                circle_intersects_rect(
                    previous + (current - previous) * 0.5,
                    8.0,
                    wall.bounds,
                )
            )

    def test_path_segments_match_the_existing_swept_wall_collision(self) -> None:
        wall = self.wall(left=800, top=1100, width=400, height=100)
        start = Vector2(1260, 1220)
        goal = Vector2(1100, 1260)

        path = find_grid_path(start, goal, 24.0, [wall])

        self.assertIsNotNone(path)
        points = [start, *(path or ())]
        for previous, current in zip(points, points[1:]):
            self.assertFalse(
                first_obstacle_on_segment(previous, current, [wall], 24.0).blocked
            )

    def test_goal_inside_wall_returns_no_path(self) -> None:
        wall = self.wall(left=400, top=400, width=80, height=80)

        path = find_grid_path(Vector2(300, 440), Vector2(440, 440), 16.0, [wall])

        self.assertIsNone(path)

    def test_goal_touching_a_wall_can_use_the_nearest_safe_approach_cell(self) -> None:
        wall = self.wall(left=900, top=500, width=100, height=160)
        target = Vector2(882, 580)

        path = find_grid_path(
            Vector2(700, 580),
            target,
            16.0,
            [wall],
            allow_goal_fallback=True,
        )

        self.assertIsNotNone(path)
        self.assertLess(path[-1].distance_to(target), 40.0)
        self.assertFalse(circle_intersects_rect(path[-1], 16.0, wall.bounds))

    def test_full_wall_returns_no_path(self) -> None:
        wall = self.wall(left=0, top=600, width=config.WORLD_WIDTH, height=200)

        path = find_grid_path(Vector2(800, 400), Vector2(800, 1000), 16.0, [wall])

        self.assertIsNone(path)

    def test_grid_to_world_returns_cell_centers(self) -> None:
        point = grid_to_world((3, 4))

        self.assertEqual(point.tuple(), (140.0, 180.0))

    def test_wall_snapshot_invalidates_paths_for_three_behaviors_in_one_camp(self) -> None:
        match = create_match()
        target = match.players[0]
        target.position = Vector2(800, 400)
        for player in match.players[1:]:
            player.alive = False

        monsters = [monster for monster in match.monsters if monster.spawn_zone_id == 0]
        match.monsters = monsters
        thin_wall = self.wall(
            obstacle_id=1,
            kind=ObstacleKind.THIN_WALL,
            left=600,
            top=300,
            width=40,
            height=240,
        )
        thick_wall = self.wall(
            obstacle_id=2,
            kind=ObstacleKind.THICK_WALL,
            left=720,
            top=300,
            width=40,
            height=240,
        )
        match.obstacles = [thin_wall, thick_wall]
        old_signature = snapshot_obstacles(match.obstacles)
        stale_node = Vector2(1, 1)
        for monster, behavior in zip(
            monsters,
            (MonsterBehavior.WANDER, MonsterBehavior.RETURN, MonsterBehavior.CHASE),
        ):
            monster.behavior = behavior
            monster.position = Vector2(520, 400)
            monster.spawn_position = monster.position.copy()
            monster.target_player_id = target.player_id if behavior == MonsterBehavior.CHASE else None
            monster.navigation_goal = Vector2(800, 400)
            monster.navigation_path = [stale_node.copy()]
            monster.navigation_obstacle_signature = old_signature

        thin_wall.destroyed = True
        new_signature = snapshot_obstacles(match.obstacles)
        update_monsters(match, 0.05)

        self.assertNotEqual(old_signature, new_signature)
        self.assertEqual(new_signature, ((2, ObstacleKind.THICK_WALL, thick_wall.bounds),))
        for monster in monsters:
            self.assertEqual(monster.navigation_obstacle_signature, new_signature)
            self.assertNotIn(stale_node, monster.navigation_path)
        self.assertTrue(thick_wall.solid)

    def test_no_route_keeps_monster_safe_and_retries_after_terrain_changes(self) -> None:
        match = create_match()
        target = match.players[0]
        target.position = Vector2(800, 1000)
        for player in match.players[1:]:
            player.alive = False
        monster = match.monsters[0]
        monster.position = Vector2(800, 500)
        monster.spawn_position = monster.position.copy()
        monster.behavior = MonsterBehavior.CHASE
        monster.target_player_id = target.player_id
        monster.attack_timer = 999.0
        full_wall = self.wall(
            left=0,
            top=600,
            width=config.WORLD_WIDTH,
            height=200,
        )
        match.obstacles = [full_wall]
        monster.navigation_obstacle_signature = snapshot_obstacles(match.obstacles)
        monster.navigation_goal = target.position.copy()
        monster.navigation_path = []
        before = monster.position.copy()

        update_monsters(match, 0.05)

        self.assertEqual(monster.position.tuple(), before.tuple())
        self.assertFalse(circle_intersects_rect(monster.position, monster.radius, full_wall.bounds))
        self.assertFalse(monster.navigation_path)

        match.obstacles = []
        update_monsters(match, config.MONSTER_NAVIGATION_RETRY_INTERVAL)

        self.assertTrue(monster.navigation_path or monster.position.distance_to(target.position) <= monster.radius + target.radius)

    def test_monster_keeps_approaching_when_player_is_touching_a_thick_wall(self) -> None:
        match = create_match()
        target = match.players[0]
        for player in match.players[1:]:
            player.alive = False
        monster = match.monsters[0]
        match.monsters = [monster]
        monster.position = Vector2(700, 580)
        monster.spawn_position = monster.position.copy()
        monster.attack_timer = 999.0
        match.obstacles = [self.wall(left=900, top=500, width=100, height=160)]
        target.position = Vector2(850, 580)

        update_monsters(match, 0.05)
        target.position = Vector2(900 - target.radius, 580)
        before = monster.position.copy()

        update_monsters(match, 0.05)

        self.assertGreater(monster.position.x, before.x)
        self.assertEqual(monster.behavior, MonsterBehavior.CHASE)

    def test_new_target_requires_alive_player_visible_within_aggro_radius(self) -> None:
        match = create_match()
        monster = match.monsters[0]
        monster.position = Vector2(500, 450)
        monster.spawn_position = monster.position.copy()
        monster.root_timer = 999.0
        monster.attack_timer = 999.0
        match.monsters = [monster]
        target = match.players[0]
        target.position = Vector2(700, 450)
        for player in match.players[1:]:
            player.alive = False

        match.obstacles = [self.wall(left=600, top=400, width=40, height=100)]
        update_monsters(match, 0.05)

        self.assertIsNone(monster.target_player_id)
        self.assertNotEqual(monster.behavior, MonsterBehavior.CHASE)

        match.obstacles = []
        target.position = Vector2(1020, 450)
        update_monsters(match, 0.05)
        self.assertEqual(monster.target_player_id, target.player_id)
        self.assertEqual(monster.behavior, MonsterBehavior.CHASE)

        target.position = Vector2(1021, 450)
        update_monsters(match, 0.05)
        self.assertIsNone(monster.target_player_id)
        self.assertEqual(monster.behavior, MonsterBehavior.RETURN)

    def test_new_target_chooses_nearest_alive_player_then_player_id(self) -> None:
        match = create_match()
        monster = match.monsters[0]
        monster.position = Vector2(500, 450)
        monster.spawn_position = monster.position.copy()
        monster.root_timer = 999.0
        monster.attack_timer = 999.0
        match.monsters = [monster]
        for player in match.players:
            player.alive = False

        farther = match.players[0]
        nearer = match.players[1]
        farther.alive = True
        nearer.alive = True
        farther.position = Vector2(700, 450)
        nearer.position = Vector2(650, 450)
        update_monsters(match, 0.05)
        self.assertEqual(monster.target_player_id, nearer.player_id)

        monster.behavior = MonsterBehavior.WANDER
        monster.target_player_id = None
        monster.navigation_path.clear()
        monster.navigation_goal = None
        farther.position = Vector2(650, 450)
        nearer.position = Vector2(650, 450)
        update_monsters(match, 0.05)
        self.assertEqual(monster.target_player_id, min(farther.player_id, nearer.player_id))

        farther.alive = False
        monster.behavior = MonsterBehavior.WANDER
        monster.target_player_id = None
        monster.navigation_path.clear()
        monster.navigation_goal = None
        update_monsters(match, 0.05)
        self.assertEqual(monster.target_player_id, nearer.player_id)


if __name__ == "__main__":
    unittest.main()
