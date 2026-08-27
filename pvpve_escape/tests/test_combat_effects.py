"""角色、配件與視覺效果資料流測試。"""

from __future__ import annotations

import unittest

from pvpve_escape.characters import (
    create_primary_action,
    create_tactical_action,
    create_ultimate_action,
)
from pvpve_escape.controllers import InputState
from pvpve_escape.models import CharacterId, TacticalId, Vector2
from pvpve_escape.world import _apply_action, create_match, update_world


PRIMARY_EFFECTS = {
    CharacterId.BREACHER: "breach_cone",
    CharacterId.SNIPER: "sniper_line",
    CharacterId.GUARDIAN: "guardian_arc",
    CharacterId.HUNTER: "boomerang",
    CharacterId.CONTROLLER: "mine",
    CharacterId.SIPHONER: "beam",
}

ULTIMATE_EFFECTS = {
    CharacterId.BREACHER: "breach_burst",
    CharacterId.SNIPER: "sniper_ultimate_line",
    CharacterId.GUARDIAN: "guardian_guard",
    CharacterId.HUNTER: "hunter_dash",
    CharacterId.CONTROLLER: "gravity_cage",
    CharacterId.SIPHONER: "siphon_burst",
}

TACTICAL_EFFECTS = {
    TacticalId.DASH: "dash",
    TacticalId.SHIELD: "shield",
    TacticalId.CONTROL: "control_zone",
}


class CombatEffectDataTests(unittest.TestCase):
    def test_primary_ultimate_and_tactical_effect_kinds_are_distinct(self) -> None:
        self.assertEqual(len(set(PRIMARY_EFFECTS.values())), 6)
        self.assertEqual(len(set(ULTIMATE_EFFECTS.values())), 6)
        self.assertEqual(len(set(TACTICAL_EFFECTS.values())), 3)

    def test_primary_effects_snapshot_origin_direction_range_and_metadata(self) -> None:
        for role, expected_kind in PRIMARY_EFFECTS.items():
            match = create_match(role)
            match.monsters = []
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            action = create_primary_action(owner, Vector2(1, 0), 0.6)
            self.assertIsNotNone(action, role)
            assert action is not None
            _apply_action(match, action)
            effect = next(effect for effect in match.effects if effect.kind == expected_kind)
            self.assertEqual(effect.origin.tuple(), action.origin.tuple(), role)
            self.assertEqual(effect.direction.tuple(), (1.0, 0.0), role)
            self.assertGreaterEqual(effect.max_distance, 0.0, role)
            self.assertIsInstance(effect.metadata, dict)

    def test_every_ultimate_and_tactical_action_has_a_rule_effect(self) -> None:
        for role, expected_kind in ULTIMATE_EFFECTS.items():
            match = create_match(role)
            match.monsters = []
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            owner.ultimate_energy = 100.0
            action = create_ultimate_action(owner, Vector2(1, 0))
            self.assertIsNotNone(action, role)
            assert action is not None
            _apply_action(match, action)
            self.assertIn(expected_kind, {effect.kind for effect in match.effects}, role)

        for tactical, expected_kind in TACTICAL_EFFECTS.items():
            match = create_match(selected_tactical=tactical)
            match.monsters = []
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            action = create_tactical_action(owner, Vector2(1, 0), Vector2(1, 0))
            self.assertIsNotNone(action, tactical)
            assert action is not None
            _apply_action(match, action)
            self.assertIn(expected_kind, {effect.kind for effect in match.effects}, tactical)

    def test_visual_only_breach_trails_never_change_target_state(self) -> None:
        match = create_match(CharacterId.BREACHER)
        match.monsters = []
        owner = match.players[0]
        target = match.players[1]
        for other in match.players[2:]:
            other.alive = False
        target.position = owner.position + Vector2(100, 0)
        before_health = target.health
        action = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        assert action is not None
        _apply_action(match, action)
        cone = next(effect for effect in match.effects if effect.kind == "breach_cone")
        trails = [effect for effect in match.effects if effect.kind == "breach_pellet"]
        self.assertEqual(len(trails), 5)
        self.assertTrue(all(effect.metadata.get("visual_only") for effect in trails))
        match.effects.remove(cone)

        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)

        self.assertEqual(target.health, before_health)
        self.assertEqual(target.ultimate_energy, 0.0)

    def test_all_abilities_survive_twenty_repeated_cast_smoke_runs(self) -> None:
        """以固定資料重複施放，確保效果 kind 與繪製資料不會偶發缺失。"""

        for role, expected_kind in PRIMARY_EFFECTS.items():
            for _ in range(20):
                match = create_match(role)
                match.monsters = []
                owner = match.players[0]
                for other in match.players[1:]:
                    other.alive = False
                owner.ammo = owner.ammo_capacity
                owner.primary_cooldown = 0.0
                action = create_primary_action(owner, Vector2(1, 0), 0.6)
                self.assertIsNotNone(action, role)
                assert action is not None
                _apply_action(match, action)
                self.assertIn(expected_kind, {effect.kind for effect in match.effects}, role)

        for role, expected_kind in ULTIMATE_EFFECTS.items():
            for _ in range(20):
                match = create_match(role)
                match.monsters = []
                owner = match.players[0]
                for other in match.players[1:]:
                    other.alive = False
                owner.ultimate_energy = 100.0
                action = create_ultimate_action(owner, Vector2(1, 0))
                self.assertIsNotNone(action, role)
                assert action is not None
                _apply_action(match, action)
                self.assertIn(expected_kind, {effect.kind for effect in match.effects}, role)

        for tactical, expected_kind in TACTICAL_EFFECTS.items():
            for _ in range(20):
                match = create_match(selected_tactical=tactical)
                match.monsters = []
                owner = match.players[0]
                action = create_tactical_action(owner, Vector2(1, 0), Vector2(1, 0))
                self.assertIsNotNone(action, tactical)
                assert action is not None
                _apply_action(match, action)
                self.assertIn(expected_kind, {effect.kind for effect in match.effects}, tactical)

    def test_hit_blocked_invulnerable_and_control_feedback_repeat_twenty_times(self) -> None:
        for _ in range(20):
            hit_match = create_match(CharacterId.SNIPER)
            hit_match.monsters = []
            hit_owner = hit_match.players[0]
            hit_target = hit_match.players[1]
            for other in hit_match.players[2:]:
                other.alive = False
            hit_target.position = hit_owner.position + Vector2(100, 0)
            update_world(
                hit_match,
                {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
                0.05,
            )
            update_world(hit_match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
            self.assertLess(hit_target.health, hit_target.max_health)

            blocked_match = create_match(CharacterId.SNIPER)
            blocked_match.monsters = []
            blocked_owner = blocked_match.players[0]
            blocked_target = blocked_match.players[1]
            for other in blocked_match.players[2:]:
                other.alive = False
            blocked_target.position = blocked_owner.position + Vector2(100, 0)
            blocked_target.invulnerability_timer = 1.0
            update_world(
                blocked_match,
                {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
                0.05,
            )
            update_world(blocked_match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
            blocked_effect = next(effect for effect in blocked_match.effects if effect.kind == "sniper_line")
            self.assertTrue(blocked_effect.metadata.get("impact_blocked"))

            control_match = create_match(selected_tactical=TacticalId.CONTROL)
            control_match.monsters = []
            control_owner = control_match.players[0]
            control_target = control_match.players[1]
            for other in control_match.players[2:]:
                other.alive = False
            control_target.position = control_owner.position + Vector2(100, 0)
            action = create_tactical_action(control_owner, Vector2(1, 0), Vector2(1, 0))
            self.assertIsNotNone(action)
            assert action is not None
            _apply_action(control_match, action)
            update_world(control_match, {0: InputState()}, 0.05)
            self.assertLess(control_target.slow_multiplier, 1.0)

    def test_primary_effects_are_removed_after_their_lifecycle_ends(self) -> None:
        for role in CharacterId:
            match = create_match(role)
            match.monsters = []
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            owner.primary_cooldown = 0.0
            action = create_primary_action(owner, Vector2(1, 0), 0.6)
            self.assertIsNotNone(action, role)
            assert action is not None
            _apply_action(match, action)
            for _ in range(260):
                update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
            self.assertEqual(match.effects, [], role)


if __name__ == "__main__":
    unittest.main()
