"""破陣者五顆獨立散彈的命中與傷害測試。"""

from __future__ import annotations

import math
import unittest

from pvpve_escape import config
from pvpve_escape.characters import create_primary_action
from pvpve_escape.controllers import InputState
from pvpve_escape.models import CharacterId, Vector2
from pvpve_escape.world import _apply_action, create_match, update_world


def _prepare_target(angle_degrees: float, distance: float):
    match = create_match(CharacterId.BREACHER)
    match.monsters = []
    # 這個檔案只驗證散彈命中幾何；地形阻擋由 feature 004 的整合測試專責覆蓋。
    match.obstacles = []
    owner = match.players[0]
    target = match.players[1]
    for other in match.players[2:]:
        other.alive = False
    owner.position = Vector2(600.0, 600.0)
    owner.spawn_position = owner.position.copy()
    radians = math.radians(angle_degrees)
    target.position = owner.position + Vector2(math.cos(radians) * distance, math.sin(radians) * distance)
    target.max_health = 1000.0
    target.health = target.max_health
    action = create_primary_action(owner, Vector2(1, 0))
    assert action is not None
    _apply_action(match, action)
    return match, owner, target


def _finish_pellets(match, steps: int = 8, delta_time: float = 0.05):
    for _ in range(steps):
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, delta_time)


class BreachPelletRuleTests(unittest.TestCase):
    def test_center_edges_and_partially_intersecting_pellet_paths_are_hit(self) -> None:
        for angle in (0.0, -config.BREACH_CONE_ANGLE_DEGREES / 2.0, config.BREACH_CONE_ANGLE_DEGREES / 2.0):
            match, _, target = _prepare_target(angle, 120.0)
            before = target.health
            _finish_pellets(match)
            self.assertLess(target.health, before, angle)

        # 中心在最外側散彈附近，但玩家碰撞圓仍部分進入該散彈路徑，應視為命中。
        match, _, target = _prepare_target(32.0, 120.0)
        before = target.health
        _finish_pellets(match)
        self.assertLess(target.health, before)

    def test_completely_outside_pellet_paths_and_range_are_not_hit(self) -> None:
        for angle, distance in ((50.0, 120.0), (0.0, config.BREACH_CONE_RANGE + 40.0)):
            match, _, target = _prepare_target(angle, distance)
            before = target.health
            _finish_pellets(match, steps=12)
            self.assertEqual(target.health, before, (angle, distance))

    def test_targets_near_origin_and_multiple_targets_are_resolved(self) -> None:
        match, owner, first = _prepare_target(0.0, 150.0)
        second = match.players[2]
        second.alive = True
        second.max_health = 1000.0
        second.health = second.max_health
        second.position = owner.position + Vector2(
            math.cos(math.radians(30.0)) * 150.0,
            math.sin(math.radians(30.0)) * 150.0,
        )
        _finish_pellets(match)
        self.assertAlmostEqual(first.max_health - first.health, 7.0 * 1.2, places=5)
        self.assertAlmostEqual(second.max_health - second.health, 7.0 * 1.2, places=5)

    def test_damage_equals_the_number_of_hit_pellets(self) -> None:
        one_match, _, one_target = _prepare_target(0.0, 150.0)
        _finish_pellets(one_match, steps=30, delta_time=1.0 / 60.0)
        self.assertAlmostEqual(one_target.max_health - one_target.health, 7.0 * 1.2, places=5)

        two_match, _, two_target = _prepare_target(7.5, config.BREACH_CONE_RANGE)
        _finish_pellets(two_match, steps=30, delta_time=1.0 / 60.0)
        self.assertAlmostEqual(two_target.max_health - two_target.health, 2.0 * 7.0 * 1.2, places=5)

        five_match, _, five_target = _prepare_target(0.0, 1.0)
        _finish_pellets(five_match, steps=30, delta_time=1.0 / 60.0)
        self.assertAlmostEqual(five_target.max_health - five_target.health, 5.0 * 7.0 * 1.2, places=5)

    def test_each_target_gets_at_most_five_pellet_hits_across_frames(self) -> None:
        match, _, target = _prepare_target(0.0, 1.0)
        _finish_pellets(match, steps=60, delta_time=1.0 / 60.0)
        self.assertAlmostEqual(target.max_health - target.health, 42.0, places=5)

    def test_front_sweep_hits_when_target_is_crossed_between_updates(self) -> None:
        match, _, target = _prepare_target(0.0, 150.0)
        before = target.health
        for _ in range(2):
            update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        self.assertEqual(target.health, before)
        for _ in range(3):
            update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        self.assertAlmostEqual(before - target.health, 7.0 * 1.2, places=5)

    def test_cone_origin_is_fixed_even_when_owner_moves_after_cast(self) -> None:
        match, owner, _ = _prepare_target(0.0, 120.0)
        cone = next(effect for effect in match.effects if effect.kind == "breach_cone")
        origin = cone.origin.copy()
        owner.position = owner.position + Vector2(300.0, 100.0)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        self.assertEqual(cone.origin.tuple(), origin.tuple())

    def test_pellet_boundaries_are_stable_across_repeated_runs(self) -> None:
        hit_positions = (
            (0.0, 120.0),
            (-config.BREACH_CONE_ANGLE_DEGREES / 2.0, 120.0),
            (config.BREACH_CONE_ANGLE_DEGREES / 2.0, 120.0),
            (32.0, 120.0),
        )
        miss_positions = ((50.0, 120.0), (0.0, config.BREACH_CONE_RANGE + 40.0))
        for _ in range(20):
            for angle, distance in hit_positions:
                match, _, target = _prepare_target(angle, distance)
                before = target.health
                _finish_pellets(match)
                self.assertLess(target.health, before, (angle, distance))
            for angle, distance in miss_positions:
                match, _, target = _prepare_target(angle, distance)
                before = target.health
                _finish_pellets(match, steps=12)
                self.assertEqual(target.health, before, (angle, distance))

    def test_dead_target_stops_remaining_pellet_events(self) -> None:
        match, _, target = _prepare_target(0.0, 1.0)
        target.health = 10.0
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        impacted_pellets = [
            effect
            for effect in match.effects
            if effect.kind == "breach_pellet"
            and effect.metadata.get("impact_target_id") == target.player_id
        ]
        self.assertFalse(target.alive)
        self.assertEqual(len(impacted_pellets), 2)
        health_after = target.health
        _finish_pellets(match, steps=10)
        self.assertEqual(target.health, health_after)

    def test_widened_pellets_cover_every_gap_at_max_range(self) -> None:
        for angle in (-22.5, -7.5, 7.5, 22.5):
            match, _, target = _prepare_target(angle, config.BREACH_CONE_RANGE)
            before = target.health
            _finish_pellets(match, steps=30, delta_time=1.0 / 60.0)
            self.assertLess(target.health, before, angle)


if __name__ == "__main__":
    unittest.main()
