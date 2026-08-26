"""PvPvE 純規則與初始化測試。"""

import unittest

from pvpve_escape.controllers import InputState
from pvpve_escape.characters import (
    calculate_attack_damage,
    calculate_control_duration,
    create_primary_action,
    create_tactical_action,
    create_ultimate_action,
    get_all_character_definitions,
)
from pvpve_escape.models import CharacterId, MatchPhase, TacticalId, Vector2
from pvpve_escape.rules import (
    add_ultimate_energy,
    apply_damage_to_monster,
    apply_damage_to_player,
    apply_monster_kill_upgrade,
    calculate_upgrade_multiplier,
    handle_player_death,
    recover_ammo,
    respawn_player,
    update_player_timers,
    update_extraction_progress,
    resolve_extraction_winner,
    resolve_match_timeout,
)
from pvpve_escape.world import apply_damage, clamp_position, create_match, update_monsters, update_world


class PlayerSetupTests(unittest.TestCase):
    def test_match_has_six_unique_players_and_all_tactics(self) -> None:
        match = create_match(CharacterId.SNIPER, TacticalId.CONTROL)

        self.assertEqual(len(match.players), 6)
        self.assertEqual({player.player_id for player in match.players}, set(range(6)))
        self.assertEqual(match.players[0].character_id, CharacterId.SNIPER)
        self.assertEqual(match.players[0].tactical_id, TacticalId.CONTROL)
        self.assertEqual({player.character_id for player in match.players}, set(CharacterId))
        self.assertTrue(all(player.tactical_id in set(TacticalId) for player in match.players))
        self.assertEqual(sum(player.controller_type.value == "HUMAN" for player in match.players), 1)
        self.assertEqual(sum(player.controller_type.value == "DUMMY" for player in match.players), 5)
        self.assertEqual(len({player.spawn_position.tuple() for player in match.players}), 6)


class WorldBoundaryTests(unittest.TestCase):
    def test_player_position_is_clamped_inside_world(self) -> None:
        self.assertEqual(clamp_position(Vector2(-100, -20), 18).tuple(), (18, 18))
        self.assertEqual(clamp_position(Vector2(9999, 9999), 18).tuple(), (2382, 1382))

    def test_camera_is_clamped_after_following_target(self) -> None:
        match = create_match()
        match.players[0].position = Vector2(2399, 1399)
        match.camera.follow(match.players[0].position)
        self.assertEqual(match.camera.position.tuple(), (1120, 680))


class RestartTests(unittest.TestCase):
    def test_new_match_does_not_keep_previous_player_state(self) -> None:
        first = create_match()
        first.players[0].upgrade_stacks = 10
        first.players[0].ultimate_energy = 100
        second = create_match()
        self.assertEqual(second.elapsed_time, 0.0)
        self.assertEqual(second.players[0].upgrade_stacks, 0)
        self.assertEqual(second.players[0].ultimate_energy, 0.0)


class CombatRuleTests(unittest.TestCase):
    def test_ammo_capacity_and_continuous_recovery(self) -> None:
        match = create_match()
        for player in match.players:
            self.assertIn(player.ammo_capacity, (2, 3, 4))
            player.ammo = 1
            recover_ammo(player, 1.0, 0.2)
            self.assertEqual(player.ammo, player.ammo_capacity)

    def test_energy_is_capped_and_upgrade_is_capped(self) -> None:
        match = create_match()
        player = match.players[0]
        add_ultimate_energy(player, 150)
        self.assertEqual(player.ultimate_energy, 100.0)
        for _ in range(20):
            apply_monster_kill_upgrade(player)
        self.assertEqual(player.upgrade_stacks, 10)
        self.assertEqual(calculate_upgrade_multiplier(player.upgrade_stacks), 1.3)
        self.assertAlmostEqual(player.max_health, 130.0)

    def test_damage_adds_energy_and_final_monster_hit_gives_only_one_upgrade(self) -> None:
        match = create_match()
        monster = match.monsters[0]
        first = apply_damage(match, 1, "monster", monster.monster_id, 10.0)
        self.assertIsNotNone(first)
        self.assertEqual(match.players[1].ultimate_energy, 10.0)
        apply_damage(match, 0, "monster", monster.monster_id, 100.0)
        self.assertFalse(monster.alive)
        self.assertEqual(match.players[0].upgrade_stacks, 1)
        self.assertEqual(match.players[1].upgrade_stacks, 0)

    def test_death_clears_state_and_respawn_restores_basic_state(self) -> None:
        match = create_match()
        player = match.players[0]
        player.upgrade_stacks = 5
        player.ultimate_energy = 80
        player.extraction_progress = 4
        apply_damage_to_player(player, player.health + 1)
        self.assertFalse(player.alive)
        self.assertEqual(player.upgrade_stacks, 0)
        self.assertEqual(player.ultimate_energy, 0)
        self.assertEqual(player.extraction_progress, 0)
        respawn_player(player, Vector2(170, 170))
        self.assertTrue(player.alive)
        self.assertEqual(player.health, player.max_health)
        self.assertEqual(player.ammo, player.ammo_capacity)

    def test_tactical_cooldown_is_fixed_and_resets_after_time(self) -> None:
        match = create_match()
        player = match.players[0]
        action = create_tactical_action(player, Vector2(1, 0), Vector2(1, 0))
        self.assertIsNotNone(action)
        self.assertEqual(player.tactical_cooldown, 12.0)
        self.assertIsNone(create_tactical_action(player, Vector2(1, 0), Vector2(1, 0)))
        update_player_timers(player, 12.0)
        self.assertIsNotNone(create_tactical_action(player, Vector2(1, 0), Vector2(1, 0)))

    def test_monster_respawns_after_fixed_delay(self) -> None:
        match = create_match()
        monster = match.monsters[0]
        apply_damage_to_monster(monster, 999)
        self.assertFalse(monster.alive)
        update_monsters(match, 5.9)
        self.assertFalse(monster.alive)
        update_monsters(match, 0.1)
        self.assertTrue(monster.alive)
        self.assertEqual(monster.health, monster.max_health)


class CharacterDefinitionTests(unittest.TestCase):
    def test_six_roles_have_distinct_primary_passive_and_ultimate_data(self) -> None:
        definitions = get_all_character_definitions()
        self.assertEqual(len(definitions), 6)
        self.assertEqual(len({definition.primary_kind for definition in definitions}), 6)
        self.assertEqual(len({definition.passive_text for definition in definitions}), 6)
        self.assertEqual(len({definition.ultimate_text for definition in definitions}), 6)

    def test_each_role_can_create_primary_and_ultimate_actions(self) -> None:
        match = create_match()
        for player in match.players:
            player.primary_cooldown = 0
            player.primary_charge = 0.6
            primary = create_primary_action(player, Vector2(1, 0), player.primary_charge)
            self.assertIsNotNone(primary, player.character_id)
            player.ultimate_energy = 100.0
            ultimate = create_ultimate_action(player, Vector2(1, 0))
            self.assertIsNotNone(ultimate, player.character_id)
            self.assertEqual(player.ultimate_energy, 0.0)

    def test_each_role_can_fire_primary_through_gameplay_input(self) -> None:
        expected_effects = {
            CharacterId.BREACHER: "breach_cone",
            CharacterId.SNIPER: "sniper_line",
            CharacterId.GUARDIAN: "guardian_arc",
            CharacterId.HUNTER: "boomerang",
            CharacterId.CONTROLLER: "mine",
            CharacterId.SIPHONER: "beam",
        }

        for role, expected_effect in expected_effects.items():
            match = create_match(role)
            match.monsters = []
            for other in match.players[1:]:
                other.alive = False
            input_state = InputState(
                aim_direction=Vector2(1, 0),
                primary_pressed=True,
                primary_held=True,
            )
            fired = False
            for _ in range(15):
                update_world(match, {0: input_state}, 0.05)
                fired = fired or expected_effect in {effect.kind for effect in match.effects}
            self.assertTrue(fired, role)

    def test_sniper_and_siphoner_can_fire_from_a_single_click(self) -> None:
        expected_effects = {
            CharacterId.SNIPER: "sniper_line",
            CharacterId.SIPHONER: "beam",
        }

        for role, expected_effect in expected_effects.items():
            match = create_match(role)
            match.monsters = []
            for other in match.players[1:]:
                other.alive = False
            update_world(
                match,
                {
                    0: InputState(
                        aim_direction=Vector2(1, 0),
                        primary_pressed=True,
                        primary_held=False,
                    )
                },
                0.05,
            )
            self.assertIn(expected_effect, {effect.kind for effect in match.effects}, role)

    def test_sniper_projectile_hits_the_first_target_on_its_visible_path(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        sniper = match.players[0]
        near_target = match.players[1]
        far_target = match.players[2]
        for other in match.players[3:]:
            other.alive = False
        sniper.position = Vector2(500, 260)
        near_target.position = Vector2(650, 260)
        far_target.position = Vector2(800, 260)
        near_health = near_target.health
        far_health = far_target.health

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        self.assertEqual(near_target.health, near_health)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)

        self.assertLess(near_target.health, near_health)
        self.assertEqual(far_target.health, far_health)
        self.assertTrue(any(effect.metadata.get("impacted") for effect in match.effects))

    def test_sniper_projectile_does_not_damage_a_target_off_its_visible_path(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        sniper = match.players[0]
        target = match.players[1]
        for other in match.players[2:]:
            other.alive = False
        sniper.position = Vector2(500, 260)
        target.position = Vector2(650, 300)
        target_health = target.health

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        for _ in range(20):
            update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)

        self.assertEqual(target.health, target_health)

    def test_sniper_projectile_records_a_blocked_hit_when_shield_absorbs_damage(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        sniper = match.players[0]
        target = match.players[1]
        for other in match.players[2:]:
            other.alive = False
        sniper.position = Vector2(500, 260)
        target.position = Vector2(650, 260)
        target_health = target.health
        target.shield_remaining = 100.0
        target.shield_timer = 2.0

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)

        impact = next(effect for effect in match.effects if effect.kind == "sniper_line")
        self.assertEqual(target.health, target_health)
        self.assertLess(target.shield_remaining, 100.0)
        self.assertEqual(impact.metadata.get("impact_effective_damage"), 0.0)
        self.assertEqual(impact.metadata.get("impact_status"), "護盾")
        self.assertTrue(impact.metadata.get("impact_blocked"))

    def test_sniper_impact_marker_stays_at_the_position_where_damage_was_applied(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        sniper = match.players[0]
        target = match.players[1]
        for other in match.players[2:]:
            other.alive = False
        sniper.position = Vector2(500, 260)
        target.position = Vector2(650, 260)

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        impact = next(effect for effect in match.effects if effect.kind == "sniper_line")
        damage_position = impact.position.copy()
        health_after_hit = target.health

        target.position = Vector2(720, 320)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)

        self.assertEqual(impact.position.tuple(), damage_position.tuple())
        self.assertEqual(target.health, health_after_hit)

    def test_each_ultimate_applies_a_gameplay_effect_to_a_world_target(self) -> None:
        damage_roles = {
            CharacterId.BREACHER,
            CharacterId.SNIPER,
            CharacterId.HUNTER,
            CharacterId.SIPHONER,
        }

        for role in CharacterId:
            match = create_match(role)
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            match.monsters = [match.monsters[0]]
            monster = match.monsters[0]
            owner.position = Vector2(500, 500)
            monster.position = Vector2(720 if role == CharacterId.CONTROLLER else 620, 500)
            monster_health = monster.health
            owner.health = owner.max_health - 40
            owner_health = owner.health
            owner.ultimate_energy = 100.0

            update_world(
                match,
                {0: InputState(aim_direction=Vector2(1, 0), ultimate_pressed=True)},
                0.05,
            )

            if role in damage_roles:
                self.assertLess(monster.health, monster_health, role)
            elif role == CharacterId.GUARDIAN:
                self.assertEqual(owner.damage_reduction, 0.7)
                self.assertGreater(owner.damage_reduction_timer, 0.0)
            else:
                self.assertLess(monster.slow_multiplier, 1.0)
                self.assertGreater(monster.slow_timer, 0.0)
                self.assertGreater(monster.root_timer, 0.0)
            if role == CharacterId.SIPHONER:
                self.assertGreater(owner.health, owner_health)

    def test_control_tactical_slows_and_releases_monsters(self) -> None:
        match = create_match(selected_tactical=TacticalId.CONTROL)
        owner = match.players[0]
        for other in match.players[1:]:
            other.alive = False
        match.monsters = [match.monsters[0]]
        monster = match.monsters[0]
        owner.position = Vector2(500, 500)
        monster.position = Vector2(600, 500)

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), tactical_pressed=True)},
            0.05,
        )

        self.assertEqual(owner.tactical_cooldown, 12.0)
        self.assertEqual(monster.slow_multiplier, 0.6)
        self.assertGreater(monster.slow_timer, 0.0)
        slowed_position = monster.position.x

        for _ in range(35):
            update_world(match, {0: InputState()}, 0.05)

        self.assertEqual(monster.slow_multiplier, 1.0)
        self.assertEqual(monster.slow_timer, 0.0)
        self.assertLess(monster.position.x, slowed_position)

    def test_conditional_passives_change_damage_or_control_duration(self) -> None:
        breacher = create_match(CharacterId.BREACHER).players[0]
        self.assertGreater(calculate_attack_damage(breacher, 100), calculate_attack_damage(breacher, 220))
        sniper = create_match(CharacterId.SNIPER).players[0]
        self.assertGreater(calculate_attack_damage(sniper, 600), calculate_attack_damage(sniper, 200))
        controller = create_match(CharacterId.CONTROLLER).players[0]
        self.assertEqual(calculate_control_duration(controller, 2.0), 3.0)


class ExtractionRuleTests(unittest.TestCase):
    def test_extraction_requires_activation_and_accumulates_per_player(self) -> None:
        match = create_match()
        zone = match.extraction_zone
        first, second = match.players[0], match.players[1]
        first.position = zone.center.copy()
        second.position = zone.center.copy()
        self.assertEqual(update_extraction_progress(first, zone, 1.0, False), 0.0)
        update_extraction_progress(first, zone, 2.0, True)
        update_extraction_progress(second, zone, 3.0, True)
        self.assertEqual(first.extraction_progress, 2.0)
        self.assertEqual(second.extraction_progress, 3.0)

    def test_leaving_resets_only_that_players_progress(self) -> None:
        match = create_match()
        zone = match.extraction_zone
        first, second = match.players[0], match.players[1]
        first.position = zone.center.copy()
        second.position = zone.center.copy()
        update_extraction_progress(first, zone, 4.0, True)
        update_extraction_progress(second, zone, 5.0, True)
        first.position = Vector2(100, 100)
        update_extraction_progress(first, zone, 0.1, True)
        update_extraction_progress(second, zone, 0.1, True)
        self.assertEqual(first.extraction_progress, 0.0)
        self.assertAlmostEqual(second.extraction_progress, 5.1)

    def test_first_completion_and_same_tick_use_lowest_player_id(self) -> None:
        match = create_match()
        match.players[2].extraction_progress = 10.0
        match.players[4].extraction_progress = 10.0
        self.assertEqual(resolve_extraction_winner(match.players), 2)

    def test_extraction_wins_before_timeout_and_timeout_has_no_winner(self) -> None:
        match = create_match()
        match.monsters = []
        match.elapsed_time = 239.99
        match.players[0].position = match.extraction_zone.center.copy()
        match.players[0].extraction_progress = 9.99
        update_world(match, {}, 0.01)
        self.assertEqual(match.phase, MatchPhase.VICTORY)
        self.assertEqual(match.winner_id, 0)

        timeout_match = create_match()
        timeout_match.elapsed_time = timeout_match.duration
        self.assertTrue(resolve_match_timeout(timeout_match))
        self.assertEqual(timeout_match.phase, MatchPhase.NO_WINNER)


if __name__ == "__main__":
    unittest.main()
