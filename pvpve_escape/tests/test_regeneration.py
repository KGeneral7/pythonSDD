"""戰鬥計時與玩家生命恢復規則測試。"""

from __future__ import annotations

import unittest

from pvpve_escape import config
from pvpve_escape.characters import create_primary_action, create_tactical_action
from pvpve_escape.controllers import InputState
from pvpve_escape.models import CharacterId, TacticalId, Vector2
from pvpve_escape.rules import (
    apply_damage_to_player,
    handle_player_death,
    mark_player_attack,
    mark_player_hit,
    regenerate_player_health,
    respawn_player,
    update_player_timers,
)
from pvpve_escape.world import _apply_action, create_match, update_world


class PlayerRegenerationRuleTests(unittest.TestCase):
    def test_regeneration_does_not_start_before_five_seconds(self) -> None:
        for _ in range(20):
            player = create_match().players[0]
            player.health = player.max_health / 2
            player.last_damage_time = config.PLAYER_REGEN_DELAY - 0.1
            player.last_attack_time = config.PLAYER_REGEN_DELAY

            regenerate_player_health(player, 1.0)

            self.assertEqual(player.health, player.max_health / 2)

    def test_exact_five_second_boundary_starts_regeneration(self) -> None:
        for _ in range(20):
            player = create_match().players[0]
            player.health = player.max_health / 2
            player.last_damage_time = config.PLAYER_REGEN_DELAY - 0.1
            player.last_attack_time = config.PLAYER_REGEN_DELAY
            update_player_timers(player, 0.1)
            before = player.health

            regenerate_player_health(player, 1.0)

            self.assertAlmostEqual(
                player.health - before,
                player.max_health * config.PLAYER_REGEN_RATE,
                places=6,
            )

    def test_regeneration_scales_with_delta_time_and_clamps_to_maximum(self) -> None:
        for _ in range(20):
            player = create_match().players[0]
            player.health = player.max_health - 10.0
            player.last_damage_time = config.PLAYER_REGEN_DELAY
            player.last_attack_time = config.PLAYER_REGEN_DELAY

            regenerate_player_health(player, 0.25)
            self.assertAlmostEqual(player.health, player.max_health - 10.0 + player.max_health * 0.10 * 0.25)
            regenerate_player_health(player, 1.0)
            self.assertEqual(player.health, player.max_health)

    def test_hit_and_attack_markers_reset_independent_timers(self) -> None:
        player = create_match().players[0]
        player.last_damage_time = 8.0
        player.last_attack_time = 9.0

        mark_player_hit(player)
        self.assertEqual(player.last_damage_time, 0.0)
        self.assertEqual(player.last_attack_time, 9.0)
        mark_player_attack(player)
        self.assertEqual(player.last_damage_time, 0.0)
        self.assertEqual(player.last_attack_time, 0.0)

    def test_shield_or_invulnerability_hit_still_restarts_damage_wait(self) -> None:
        for _ in range(20):
            player = create_match().players[0]
            player.health = player.max_health / 2
            player.last_damage_time = config.PLAYER_REGEN_DELAY
            player.last_attack_time = config.PLAYER_REGEN_DELAY
            player.shield_remaining = 100.0
            player.shield_timer = 2.0
            apply_damage_to_player(player, 10.0)
            self.assertEqual(player.health, player.max_health / 2)
            self.assertEqual(player.last_damage_time, 0.0)
            self.assertEqual(player.last_attack_time, config.PLAYER_REGEN_DELAY)

            player.last_damage_time = config.PLAYER_REGEN_DELAY
            player.invulnerability_timer = 1.0
            apply_damage_to_player(player, 10.0)
            self.assertEqual(player.last_damage_time, 0.0)

    def test_control_hit_restarts_damage_wait_even_without_direct_damage(self) -> None:
        from pvpve_escape.rules import apply_slow

        for _ in range(20):
            player = create_match().players[0]
            player.last_damage_time = config.PLAYER_REGEN_DELAY

            apply_slow(player, 0.6, 1.5)

            self.assertEqual(player.last_damage_time, 0.0)

    def test_dead_player_never_regenerates_and_new_life_resets_timers(self) -> None:
        for _ in range(20):
            match = create_match()
            player = match.players[0]
            player.health = player.max_health / 2
            player.last_damage_time = 20.0
            player.last_attack_time = 20.0
            handle_player_death(player)
            regenerate_player_health(player, 1.0)
            self.assertEqual(player.health, 0.0)
            self.assertEqual(player.last_damage_time, 0.0)
            self.assertEqual(player.last_attack_time, 0.0)

            respawn_player(player, player.spawn_position)
            self.assertEqual(player.health, player.max_health)
            self.assertEqual(player.last_damage_time, 0.0)
            self.assertEqual(player.last_attack_time, 0.0)

    def test_dead_player_timers_do_not_accumulate_during_respawn_wait(self) -> None:
        for _ in range(20):
            player = create_match().players[0]
            player.alive = False
            player.last_damage_time = 20.0
            player.last_attack_time = 20.0

            update_player_timers(player, 1.0)

            self.assertEqual(player.last_damage_time, 0.0)
            self.assertEqual(player.last_attack_time, 0.0)

    def test_world_updates_regeneration_after_same_frame_hit_and_attack_resolution(self) -> None:
        for _ in range(20):
            match = create_match(CharacterId.SNIPER)
            match.monsters = []
            owner = match.players[0]
            owner.health = owner.max_health / 2
            owner.last_damage_time = config.PLAYER_REGEN_DELAY - 0.05
            owner.last_attack_time = config.PLAYER_REGEN_DELAY

            update_world(match, {0: InputState()}, 0.05)
            update_world(match, {0: InputState()}, 0.05)

            self.assertAlmostEqual(owner.health, owner.max_health / 2 + owner.max_health * 0.10 * 0.1)

    def test_attack_action_restarts_attack_timer_but_dash_and_shield_do_not(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        owner = match.players[0]
        owner.last_attack_time = 8.0
        attack = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(attack)
        _apply_action(match, attack)
        self.assertEqual(owner.last_attack_time, 0.0)

        for tactical_id in (TacticalId.DASH, TacticalId.SHIELD):
            tactical_match = create_match(CharacterId.SNIPER, tactical_id)
            tactical_match.monsters = []
            tactical_owner = tactical_match.players[0]
            tactical_owner.last_attack_time = 8.0
            tactical = create_tactical_action(tactical_owner, Vector2(1, 0), Vector2(1, 0))
            self.assertIsNotNone(tactical)
            _apply_action(tactical_match, tactical)
            self.assertEqual(tactical_owner.last_attack_time, 8.0, tactical_id)

        control_match = create_match(CharacterId.SNIPER, TacticalId.CONTROL)
        control_match.monsters = []
        control_owner = control_match.players[0]
        control_owner.last_attack_time = 8.0
        control = create_tactical_action(control_owner, Vector2(1, 0), Vector2())
        self.assertIsNotNone(control)
        _apply_action(control_match, control)
        self.assertEqual(control_owner.last_attack_time, 0.0)

    def test_non_attack_dash_can_regenerate_on_the_next_update(self) -> None:
        match = create_match(CharacterId.SNIPER, TacticalId.DASH)
        match.monsters = []
        owner = match.players[0]
        owner.health = owner.max_health / 2
        owner.last_damage_time = config.PLAYER_REGEN_DELAY
        owner.last_attack_time = config.PLAYER_REGEN_DELAY
        action = create_tactical_action(owner, Vector2(1, 0), Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        before = owner.health

        update_world(match, {0: InputState()}, 0.1)

        self.assertGreater(owner.health, before)

    def test_world_control_effect_counts_as_a_hit_for_a_player_target(self) -> None:
        for _ in range(20):
            match = create_match(CharacterId.CONTROLLER, TacticalId.CONTROL)
            match.monsters = []
            owner = match.players[0]
            target = match.players[1]
            owner.position = Vector2(500, 500)
            target.position = Vector2(600, 500)
            target.health = target.max_health / 2
            target.last_damage_time = config.PLAYER_REGEN_DELAY
            target.last_attack_time = config.PLAYER_REGEN_DELAY
            for other in match.players[2:]:
                other.alive = False

            update_world(
                match,
                {0: InputState(aim_direction=Vector2(1, 0), tactical_pressed=True)},
                0.05,
            )

            self.assertEqual(target.last_damage_time, 0.0)
            self.assertEqual(target.health, target.max_health / 2)

if __name__ == "__main__":
    unittest.main()
