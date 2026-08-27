"""瞄準預覽幾何的純規則測試。"""

import unittest

from pvpve_escape import config
from pvpve_escape.aiming import build_aim_guide, clamp_aim_endpoint
from pvpve_escape.models import CharacterId, ObstacleKind, ObstacleState, TacticalId, Vector2, WorldRect
from pvpve_escape.world import create_match


class AimGuideGeometryTests(unittest.TestCase):
    def test_endpoint_is_limited_to_the_world_boundary(self) -> None:
        endpoint = clamp_aim_endpoint(Vector2(2380, 700), Vector2(1, 0), 1000)

        self.assertEqual(endpoint.tuple(), (2400.0, 700.0))

    def test_primary_guides_use_the_character_specific_geometry(self) -> None:
        expected = {
            CharacterId.BREACHER: ("wedge", 200.0, 60.0),
            CharacterId.SNIPER: ("line", 1000.0, 0.0),
            CharacterId.GUARDIAN: ("wedge", 125.0, 100.0),
            CharacterId.HUNTER: ("path", 340.0, 0.0),
            CharacterId.CONTROLLER: ("circle", 460.0, 0.0),
            CharacterId.SIPHONER: ("beam", 280.0, 0.0),
        }

        for role, (shape, range_distance, angle) in expected.items():
            player = create_match(role).players[0]
            guide = build_aim_guide(player, "primary", Vector2(1, 0))

            self.assertEqual(guide.shape, shape, role)
            self.assertEqual(guide.range, range_distance, role)
            self.assertEqual(guide.angle_degrees, angle, role)
            self.assertTrue(guide.valid, role)
            self.assertEqual(guide.direction.tuple(), (1.0, 0.0), role)

        self.assertEqual(
            len(build_aim_guide(create_match(CharacterId.BREACHER).players[0], "primary", Vector2(1, 0)).path_points),
            5,
        )
        self.assertGreaterEqual(
            len(build_aim_guide(create_match(CharacterId.HUNTER).players[0], "primary", Vector2(1, 0)).path_points),
            3,
        )

    def test_breacher_preview_uses_the_authoritative_cone_constants(self) -> None:
        player = create_match(CharacterId.BREACHER).players[0]
        guide = build_aim_guide(player, "primary", Vector2(1, 0))

        self.assertEqual(guide.range, config.BREACH_CONE_RANGE)
        self.assertEqual(guide.angle_degrees, config.BREACH_CONE_ANGLE_DEGREES)
        self.assertEqual(len(guide.path_points), config.BREACH_PELLET_COUNT)
        self.assertEqual(guide.origin.tuple(), player.position.tuple())
        self.assertTrue(all(point.x <= config.WORLD_WIDTH and point.y <= config.WORLD_HEIGHT for point in guide.path_points))

    def test_ultimate_and_tactical_guides_share_the_same_boundary_rule(self) -> None:
        match = create_match(CharacterId.CONTROLLER, TacticalId.CONTROL)
        player = match.players[0]
        player.position = Vector2(2380, 700)

        ultimate = build_aim_guide(player, "ultimate", Vector2(1, 0))
        tactical = build_aim_guide(player, "tactical", Vector2(1, 0))

        self.assertLessEqual(ultimate.end.x, 2400.0)
        self.assertLessEqual(tactical.end.x, 2400.0)
        self.assertEqual(tactical.radius, 100.0)
        self.assertEqual(tactical.shape, "circle")

    def test_ultimate_guides_describe_each_role_specific_shape(self) -> None:
        expected = {
            CharacterId.BREACHER: ("circle", 0.0, 190.0),
            CharacterId.SNIPER: ("line", 1100.0, 0.0),
            CharacterId.GUARDIAN: ("circle", 0.0, 38.0),
            CharacterId.HUNTER: ("path", 360.0, 0.0),
            CharacterId.CONTROLLER: ("circle", 0.0, 190.0),
            CharacterId.SIPHONER: ("circle", 0.0, 220.0),
        }
        for role, (shape, range_distance, radius) in expected.items():
            guide = build_aim_guide(create_match(role).players[0], "ultimate", Vector2(1, 0))
            self.assertEqual(guide.shape, shape, role)
            self.assertEqual(guide.range, range_distance, role)
            self.assertEqual(guide.radius, radius, role)
            if role == CharacterId.HUNTER:
                self.assertEqual(len(guide.path_points), 2)

    def test_tactical_guides_expose_dash_shield_and_bounded_control(self) -> None:
        expected = {
            TacticalId.DASH: ("path", 220.0, 0.0),
            TacticalId.SHIELD: ("circle", 0.0, 36.0),
            TacticalId.CONTROL: ("circle", 100.0, 100.0),
        }
        for tactical, (shape, range_distance, radius) in expected.items():
            match = create_match(CharacterId.CONTROLLER, tactical)
            player = match.players[0]
            player.position = Vector2(2380, 700)
            guide = build_aim_guide(player, "tactical", Vector2(1, 0))
            self.assertEqual(guide.shape, shape, tactical)
            self.assertEqual(guide.range, range_distance, tactical)
            self.assertEqual(guide.radius, radius, tactical)
            self.assertLessEqual(guide.end.x, 2400.0, tactical)
            self.assertGreaterEqual(guide.end.x, 0.0, tactical)
            self.assertTrue(all(0.0 <= point.x <= 2400.0 for point in guide.path_points), tactical)

    def test_guides_are_read_only_and_invalid_resources_only_change_color_state(self) -> None:
        player = create_match(CharacterId.SNIPER).players[0]
        player.aim_direction = Vector2(0, 1)
        before = player.position.tuple()
        guide = build_aim_guide(player, "primary", Vector2(), valid=False)

        self.assertFalse(guide.valid)
        self.assertEqual(guide.direction.tuple(), (0.0, 1.0))
        self.assertEqual(player.position.tuple(), before)
        self.assertEqual(player.aim_direction.tuple(), (0.0, 1.0))

    def test_line_and_path_guides_stop_at_the_same_confirmed_wall_as_gameplay(self) -> None:
        match = create_match(CharacterId.SNIPER, TacticalId.DASH)
        player = match.players[0]
        player.position = Vector2(800, 580)

        for _ in range(20):
            line = build_aim_guide(player, "primary", Vector2(1, 0), obstacles=match.obstacles)
            dash = build_aim_guide(
                player,
                "tactical",
                Vector2(1, 0),
                move_direction=Vector2(1, 0),
                obstacles=match.obstacles,
            )
            self.assertAlmostEqual(line.end.x, 892.0, delta=0.01)
            self.assertAlmostEqual(dash.end.x, 882.0, delta=0.01)
            self.assertEqual(line.end.y, player.position.y)
            self.assertEqual(dash.end.y, player.position.y)

    def test_omitting_obstacles_keeps_the_legacy_preview_result(self) -> None:
        player = create_match(CharacterId.SNIPER).players[0]

        implicit = build_aim_guide(player, "primary", Vector2(1, 0))
        explicit_empty = build_aim_guide(player, "primary", Vector2(1, 0), obstacles=[])

        self.assertEqual(implicit.end.tuple(), explicit_empty.end.tuple())
        self.assertEqual(implicit.path_points, explicit_empty.path_points)

    def test_dash_preview_simulates_first_thin_wall_break_then_stops_at_next_wall(self) -> None:
        match = create_match(CharacterId.CONTROLLER, TacticalId.DASH)
        player = match.players[0]
        player.position = Vector2(800, 500)
        match.obstacles = [
            ObstacleState(1, ObstacleKind.THIN_WALL, WorldRect(850, 450, 20, 100)),
            ObstacleState(2, ObstacleKind.THICK_WALL, WorldRect(1000, 450, 20, 100)),
        ]

        for _ in range(20):
            guide = build_aim_guide(
                player,
                "tactical",
                Vector2(1, 0),
                move_direction=Vector2(1, 0),
                obstacles=match.obstacles,
            )
            self.assertAlmostEqual(guide.end.x, 982.0, delta=0.01)
            self.assertFalse(match.obstacles[0].destroyed)
            self.assertFalse(match.obstacles[1].destroyed)


if __name__ == "__main__":
    unittest.main()
