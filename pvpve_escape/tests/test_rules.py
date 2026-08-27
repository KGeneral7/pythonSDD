"""PvPvE 純規則與初始化測試。"""

import unittest
import math

from pvpve_escape import config
from pvpve_escape.aiming import build_aim_guide
from pvpve_escape.controllers import InputState
from pvpve_escape.characters import (
    calculate_attack_damage,
    calculate_control_duration,
    create_primary_action,
    create_tactical_action,
    create_ultimate_action,
    get_character_definition,
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
    primary_attack_active,
    recover_ammo,
    respawn_player,
    update_player_timers,
    update_extraction_progress,
    resolve_extraction_winner,
    resolve_match_timeout,
)
from pvpve_escape.world import _apply_action, apply_damage, clamp_position, create_match, update_monsters, update_world


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

    def test_diagonal_boomerang_uses_the_same_bounded_ray_as_its_aim_guide(self) -> None:
        match = create_match(CharacterId.HUNTER)
        owner = match.players[0]
        owner.position = Vector2(2380, 700)
        owner.spawn_position = owner.position.copy()
        for other in match.players[1:]:
            other.alive = False

        guide = build_aim_guide(owner, "primary", Vector2(1, 1))
        action = create_primary_action(owner, Vector2(1, 1))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        effect = next(effect for effect in match.effects if effect.kind == "boomerang")

        update_world(match, {0: InputState()}, 0.05)

        self.assertAlmostEqual(effect.max_distance, owner.position.distance_to(guide.end), places=5)
        self.assertTrue(effect.returning)
        self.assertEqual(effect.position.tuple(), guide.end.tuple())

    def test_diagonal_dash_and_control_land_on_the_preview_endpoint(self) -> None:
        dash_match = create_match(selected_tactical=TacticalId.DASH)
        dash_owner = dash_match.players[0]
        dash_owner.position = Vector2(2380, 700)
        dash_guide = build_aim_guide(dash_owner, "tactical", Vector2(1, 1))
        update_world(
            dash_match,
            {0: InputState(aim_direction=Vector2(1, 1), tactical_released=True)},
            0.01,
        )
        self.assertEqual(dash_owner.position.tuple(), dash_guide.end.tuple())

        control_match = create_match(selected_tactical=TacticalId.CONTROL)
        control_owner = control_match.players[0]
        control_owner.position = Vector2(2380, 700)
        control_guide = build_aim_guide(control_owner, "tactical", Vector2(1, 1))
        update_world(
            control_match,
            {0: InputState(aim_direction=Vector2(1, 1), tactical_released=True)},
            0.01,
        )
        control_effect = next(effect for effect in control_match.effects if effect.kind == "control_zone")
        self.assertEqual(control_effect.position.tuple(), control_guide.end.tuple())

    def test_dash_preview_uses_move_direction_when_it_is_available(self) -> None:
        match = create_match(selected_tactical=TacticalId.DASH)
        owner = match.players[0]
        guide = build_aim_guide(
            owner,
            "tactical",
            Vector2(1, 0),
            move_direction=Vector2(0, 1),
        )
        action = create_tactical_action(owner, Vector2(1, 0), Vector2(0, 1))

        self.assertIsNotNone(action)
        self.assertEqual(guide.direction.tuple(), action.direction.tuple())

    def test_instant_attack_visuals_stay_at_their_cast_position(self) -> None:
        for role, effect_kind in (
            (CharacterId.BREACHER, "breach_cone"),
            (CharacterId.GUARDIAN, "guardian_arc"),
        ):
            match = create_match(role)
            match.monsters = []
            owner = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            action = create_primary_action(owner, Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            effect = next(effect for effect in match.effects if effect.kind == effect_kind)
            cast_position = effect.position.copy()
            owner.position = owner.position + Vector2(200, 100)

            update_world(match, {0: InputState()}, 0.05)

            if role == CharacterId.BREACHER:
                self.assertEqual(effect.origin.tuple(), cast_position.tuple(), role)
            else:
                self.assertEqual(effect.position.tuple(), cast_position.tuple(), role)


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

    def test_primary_attack_active_covers_hold_charge_and_cooldown(self) -> None:
        player = create_match().players[0]
        self.assertFalse(primary_attack_active(player))
        self.assertTrue(primary_attack_active(player, primary_held=True))
        player.primary_charge = 0.1
        self.assertTrue(primary_attack_active(player))
        player.primary_charge = 0.0
        player.primary_cooldown = 0.1
        self.assertTrue(primary_attack_active(player))
        player.alive = False
        self.assertFalse(primary_attack_active(player, primary_held=True))

    def test_blocked_ammo_recovery_resets_timer_and_waits_after_release(self) -> None:
        player = create_match().players[0]
        player.ammo = player.ammo_capacity - 1
        player.ammo_recovery_timer = 0.19

        recover_ammo(player, 0.50, 0.20, blocked=True)

        self.assertEqual(player.ammo, player.ammo_capacity - 1)
        self.assertEqual(player.ammo_recovery_timer, 0.0)
        recover_ammo(player, 0.19, 0.20)
        self.assertEqual(player.ammo, player.ammo_capacity - 1)
        recover_ammo(player, 0.01, 0.20)
        self.assertEqual(player.ammo, player.ammo_capacity)

    def test_full_ammo_and_dead_player_keep_recovery_timer_zero(self) -> None:
        player = create_match().players[0]
        player.ammo_recovery_timer = 0.4
        recover_ammo(player, 0.5, 0.2)
        self.assertEqual(player.ammo_recovery_timer, 0.0)
        player.ammo = 0
        player.ammo_recovery_timer = 0.4
        player.alive = False
        recover_ammo(player, 1.0, 0.2)
        self.assertEqual(player.ammo, 0)
        self.assertEqual(player.ammo_recovery_timer, 0.0)

    def test_energy_is_capped_and_upgrade_is_capped(self) -> None:
        match = create_match()
        player = match.players[0]
        add_ultimate_energy(player, 150)
        self.assertEqual(player.ultimate_energy, 100.0)
        for _ in range(20):
            apply_monster_kill_upgrade(player)
        self.assertEqual(player.upgrade_stacks, 10)
        self.assertEqual(calculate_upgrade_multiplier(player.upgrade_stacks), 1.3)
        self.assertAlmostEqual(player.max_health, 143.0)

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

    def test_monster_kill_removes_owned_effects_in_the_same_update(self) -> None:
        match = create_match(CharacterId.GUARDIAN)
        match.monsters = [match.monsters[0]]
        owner = match.players[0]
        monster = match.monsters[0]
        monster.position = owner.position.copy()
        owner.health = config.MONSTER_CONTACT_DAMAGE

        action = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        effect = next(effect for effect in match.effects if effect.kind == "guardian_arc")

        update_world(match, {0: InputState()}, 0.05)

        self.assertFalse(owner.alive)
        self.assertNotIn(effect, match.effects)

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
            if role == CharacterId.SIPHONER:
                update_world(
                    match,
                    {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True)},
                    0.05,
                )
            else:
                update_world(
                    match,
                    {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True)},
                    0.05,
                )
                update_world(
                    match,
                    {0: InputState(aim_direction=Vector2(1, 0), primary_released=True)},
                    0.05,
                )
            fired = expected_effect in {effect.kind for effect in match.effects}
            self.assertTrue(fired, role)

    def test_sniper_quick_click_fires_but_siphoner_quick_click_does_not_channel(self) -> None:
        match = create_match(CharacterId.SNIPER)
        match.monsters = []
        for other in match.players[1:]:
            other.alive = False
        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_released=True)},
            0.05,
        )
        self.assertIn("sniper_line", {effect.kind for effect in match.effects})

        match = create_match(CharacterId.SIPHONER)
        match.monsters = []
        for other in match.players[1:]:
            other.alive = False
        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_released=True)},
            0.05,
        )
        self.assertNotIn("beam", {effect.kind for effect in match.effects})

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
        sniper.auto_aim_enabled = False
        near_health = near_target.health
        far_health = far_target.health

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        self.assertEqual(near_target.health, near_health)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
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
        sniper.auto_aim_enabled = False
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
        sniper.auto_aim_enabled = False
        target_health = target.health
        target.shield_remaining = 100.0
        target.shield_timer = 2.0

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
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
        sniper.auto_aim_enabled = False

        update_world(
            match,
            {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True)},
            0.05,
        )
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
        update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.05)
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


class AimAndProjectileRuleTests(unittest.TestCase):
    def _solo_match(self, role: CharacterId, tactical: TacticalId = TacticalId.DASH):
        match = create_match(role, tactical)
        match.monsters = []
        # 角色投射物速度／技能數值的單元測試不依賴固定地圖阻擋；地形路徑另由
        # test_terrain 與 feature 004 整合測試覆蓋。
        match.obstacles = []
        for other in match.players[1:]:
            other.alive = False
        match.players[0].position = Vector2(500, 500)
        match.players[0].spawn_position = Vector2(500, 500)
        match.players[0].ability_input_blocked = False
        match.players[0].auto_aim_enabled = False
        return match

    def _target_match(self, role: CharacterId, target_offset: Vector2):
        match = create_match(role)
        match.monsters = []
        # 固定 TTK 夾具要量測技能本身，不讓新地圖牆體改變距離命中結果。
        match.obstacles = []
        owner = match.players[0]
        target = match.players[1]
        owner.position = Vector2(500, 500)
        owner.spawn_position = owner.position.copy()
        target.position = owner.position + target_offset
        target.max_health = 120.0
        target.health = 120.0
        target.radius = 40.0
        owner.auto_aim_enabled = False
        for other in match.players[2:]:
            other.alive = False
        return match, owner, target

    def test_character_and_monster_balance_table_is_centralized(self) -> None:
        expected = {
            CharacterId.BREACHER: (110.0, 7.0, 200.0, config.BREACH_PROJECTILE_SPEED),
            CharacterId.SNIPER: (80.0, 50.0, 1000.0, config.SNIPER_PROJECTILE_SPEED),
            CharacterId.GUARDIAN: (115.0, 30.0, 125.0, 0.0),
            CharacterId.HUNTER: (95.0, 24.0, 340.0, config.HUNTER_PROJECTILE_SPEED),
            CharacterId.CONTROLLER: (90.0, 20.0, 460.0, config.MINE_PROJECTILE_SPEED),
            CharacterId.SIPHONER: (105.0, 6.0, 280.0, 0.0),
        }
        for role, values in expected.items():
            definition = get_character_definition(role)
            self.assertEqual(
                (definition.base_health, definition.primary_damage, definition.primary_range, definition.projectile_speed),
                values,
            )
            player = create_match(role).players[0]
            expected_health = values[0] * (1.2 if role == CharacterId.GUARDIAN else 1.0)
            self.assertEqual(player.max_health, expected_health)

        self.assertEqual(config.MONSTER_HEALTH, 85.0)
        self.assertEqual(config.MONSTER_SPEED, 95.0)
        self.assertEqual(config.MONSTER_CONTACT_DAMAGE, 12.0)
        self.assertEqual(config.MONSTER_ATTACK_INTERVAL, 0.8)
        self.assertEqual(config.MONSTER_RADIUS, 16.0)
        self.assertEqual(config.MONSTER_RESPAWN_DELAY, 6.0)
        self.assertEqual(len(create_match().monsters), config.MONSTER_CAMP_COUNT * config.MONSTERS_PER_CAMP)

    def test_non_channel_primary_only_casts_on_release(self) -> None:
        expected_effects = {
            CharacterId.BREACHER: "breach_cone",
            CharacterId.SNIPER: "sniper_line",
            CharacterId.GUARDIAN: "guardian_arc",
            CharacterId.HUNTER: "boomerang",
            CharacterId.CONTROLLER: "mine",
        }
        for role, expected_effect in expected_effects.items():
            match = self._solo_match(role)
            owner = match.players[0]
            ammo_before = owner.ammo
            cooldown_before = owner.primary_cooldown
            update_world(
                match,
                {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True)},
                0.10,
            )
            self.assertEqual(match.effects, [], role)
            self.assertEqual(owner.ammo, ammo_before, role)
            self.assertEqual(owner.primary_cooldown, cooldown_before, role)

            update_world(
                match,
                {0: InputState(aim_direction=Vector2(1, 0), primary_released=True)},
                0.01,
            )
            self.assertIn(expected_effect, {effect.kind for effect in match.effects}, role)
            self.assertEqual(owner.ammo, ammo_before - 1, role)
            self.assertGreater(owner.primary_cooldown, 0.0, role)

    def test_non_channel_slots_and_quick_taps_are_single_casts(self) -> None:
        expected = {
            "primary": {
                CharacterId.BREACHER: "breach_cone",
                CharacterId.SNIPER: "sniper_line",
                CharacterId.GUARDIAN: "guardian_arc",
                CharacterId.HUNTER: "boomerang",
                CharacterId.CONTROLLER: "mine",
            },
            "ultimate": {
                role: kind
                for role, kind in {
                    CharacterId.BREACHER: "breach_burst",
                    CharacterId.SNIPER: "sniper_ultimate_line",
                    CharacterId.GUARDIAN: "guardian_guard",
                    CharacterId.HUNTER: "hunter_dash",
                    CharacterId.CONTROLLER: "gravity_cage",
                    CharacterId.SIPHONER: "siphon_burst",
                }.items()
            },
            "tactical": {
                CharacterId.BREACHER: "dash",
                CharacterId.SNIPER: "dash",
                CharacterId.GUARDIAN: "dash",
                CharacterId.HUNTER: "dash",
                CharacterId.CONTROLLER: "dash",
                CharacterId.SIPHONER: "dash",
            },
        }
        fields = {
            "primary": ("primary_pressed", "primary_released"),
            "ultimate": ("ultimate_pressed", "ultimate_released"),
            "tactical": ("tactical_pressed", "tactical_released"),
        }
        for slot, role_effects in expected.items():
            for role, expected_effect in role_effects.items():
                for _ in range(20):
                    tactical = TacticalId.DASH
                    match = self._solo_match(role, tactical)
                    owner = match.players[0]
                    if slot == "ultimate":
                        owner.ultimate_energy = 100.0
                    pressed, released = fields[slot]
                    input_state = InputState(
                        aim_direction=Vector2(1, 0),
                        **{pressed: True, released: True},
                    )
                    update_world(match, {0: input_state}, 0.01)
                    self.assertIn(expected_effect, {effect.kind for effect in match.effects}, (slot, role, _))
                    if slot == "ultimate":
                        self.assertEqual(owner.ultimate_energy, 0.0)
                    elif slot == "tactical":
                        self.assertEqual(owner.tactical_cooldown, 12.0)

    def test_hold_release_resource_checks_and_siphoner_channel(self) -> None:
        # 大招與配件按住只預覽，放開才建立效果並消耗資源。
        for role in CharacterId:
            for slot in ("ultimate", "tactical"):
                match = self._solo_match(role)
                owner = match.players[0]
                owner.ultimate_energy = 100.0
                held = InputState(
                    aim_direction=Vector2(1, 0),
                    ultimate_pressed=slot == "ultimate",
                    ultimate_held=slot == "ultimate",
                    tactical_pressed=slot == "tactical",
                    tactical_held=slot == "tactical",
                )
                update_world(match, {0: held}, 0.05)
                self.assertEqual(match.effects, [], (role, slot))
                self.assertEqual(owner.ultimate_energy, 100.0, (role, slot))
                self.assertEqual(owner.tactical_cooldown, 0.0, (role, slot))
                released = InputState(
                    aim_direction=Vector2(1, 0),
                    ultimate_released=slot == "ultimate",
                    tactical_released=slot == "tactical",
                )
                update_world(match, {0: released}, 0.01)
                self.assertTrue(match.effects, (role, slot))

        for _ in range(20):
            match = self._target_match(CharacterId.SIPHONER, Vector2(100, 0))[0]
            owner, target = match.players[0], match.players[1]
            health_before = target.health
            update_world(
                match,
                {0: InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True)},
                0.05,
            )
            for _ in range(23):
                update_world(match, {0: InputState(aim_direction=Vector2(1, 0), primary_held=True)}, 0.05)
            self.assertLess(target.health, health_before)
            self.assertFalse(any(effect.kind == "beam" for effect in match.effects))
            update_world(match, {0: InputState(primary_released=True)}, 0.01)
            self.assertFalse(any(effect.kind == "beam" for effect in match.effects))

        focus_match = self._target_match(CharacterId.SIPHONER, Vector2(100, 0))[0]
        update_world(focus_match, {0: InputState(primary_held=True)}, 0.05)
        self.assertTrue(any(effect.kind == "beam" for effect in focus_match.effects))
        update_world(focus_match, {0: InputState(focus_lost=True)}, 0.01)
        self.assertFalse(any(effect.kind == "beam" for effect in focus_match.effects))

        death_match = self._target_match(CharacterId.SIPHONER, Vector2(100, 0))[0]
        update_world(death_match, {0: InputState(primary_held=True)}, 0.05)
        apply_damage(death_match, 1, "player", 0, 999.0)
        update_world(death_match, {0: InputState(primary_held=True)}, 0.01)
        self.assertFalse(any(effect.kind == "beam" for effect in death_match.effects))

    def test_siphoner_full_channel_has_eight_ticks_in_1_2_seconds(self) -> None:
        match = create_match(CharacterId.SIPHONER)
        match.monsters = []
        owner, target = match.players[0], match.players[1]
        owner.position = Vector2(500, 500)
        target.position = Vector2(600, 500)
        target.max_health = 1000.0
        target.health = 1000.0
        for other in match.players[2:]:
            other.alive = False

        for frame in range(24):
            update_world(
                match,
                {
                    0: InputState(
                        aim_direction=Vector2(1, 0),
                        primary_pressed=frame == 0,
                        primary_held=True,
                    )
                },
                0.05,
            )

        self.assertEqual(target.health, 952.0)
        self.assertFalse(any(effect.kind == "beam" for effect in match.effects))

    def test_insufficient_resources_never_cast_on_release(self) -> None:
        match = self._solo_match(CharacterId.BREACHER)
        owner = match.players[0]
        owner.ammo = 0
        update_world(match, {0: InputState(primary_released=True)}, 0.01)
        self.assertEqual(match.effects, [])
        self.assertEqual(owner.ammo, 0)
        self.assertEqual(owner.primary_cooldown, 0.0)

        owner.ultimate_energy = 99.0
        update_world(match, {0: InputState(ultimate_released=True)}, 0.01)
        self.assertEqual(match.effects, [])
        self.assertEqual(owner.ultimate_energy, 99.0)

        owner.tactical_cooldown = 1.0
        cooldown_before = owner.tactical_cooldown
        update_world(match, {0: InputState(tactical_released=True)}, 0.01)
        self.assertEqual(match.effects, [])
        self.assertLess(owner.tactical_cooldown, cooldown_before)
        self.assertGreater(owner.tactical_cooldown, 0.0)

    def test_projectile_speed_snapshots_and_non_flying_effects(self) -> None:
        expected_speed = {
            CharacterId.BREACHER: config.BREACH_PROJECTILE_SPEED,
            CharacterId.SNIPER: config.SNIPER_PROJECTILE_SPEED,
            CharacterId.GUARDIAN: 0.0,
            CharacterId.HUNTER: config.HUNTER_PROJECTILE_SPEED,
            CharacterId.CONTROLLER: config.MINE_PROJECTILE_SPEED,
            CharacterId.SIPHONER: 0.0,
        }
        expected_kind = {
            CharacterId.BREACHER: "breach_pellet",
            CharacterId.SNIPER: "sniper_line",
            CharacterId.GUARDIAN: "guardian_arc",
            CharacterId.HUNTER: "boomerang",
            CharacterId.CONTROLLER: "mine",
            CharacterId.SIPHONER: "beam",
        }
        for role in CharacterId:
            match = self._solo_match(role)
            action = create_primary_action(match.players[0], Vector2(1, 0))
            self.assertIsNotNone(action)
            self.assertEqual(action.projectile_speed, expected_speed[role])
            _apply_action(match, action)
            effects = [effect for effect in match.effects if effect.kind == expected_kind[role]]
            self.assertTrue(effects, role)
            if role == CharacterId.BREACHER:
                self.assertEqual(len(effects), 5)
                self.assertTrue(all(effect.projectile_speed == config.BREACH_PROJECTILE_SPEED for effect in effects))
            else:
                self.assertEqual(effects[0].projectile_speed, expected_speed[role])
            self.assertTrue(all(not hasattr(effect, "speed") for effect in effects))
            self.assertTrue(all("speed" not in effect.metadata for effect in effects))
            if role == CharacterId.CONTROLLER:
                self.assertFalse(effects[0].armed)

    def test_projectiles_move_at_configured_speed_for_ten_frames(self) -> None:
        expected = {
            CharacterId.BREACHER: (config.BREACH_PROJECTILE_SPEED, "breach_pellet"),
            CharacterId.SNIPER: (config.SNIPER_PROJECTILE_SPEED, "sniper_line"),
            CharacterId.HUNTER: (config.HUNTER_PROJECTILE_SPEED, "boomerang"),
            CharacterId.CONTROLLER: (config.MINE_PROJECTILE_SPEED, "mine"),
        }
        for role, (speed, kind) in expected.items():
            match = self._solo_match(role)
            action = create_primary_action(match.players[0], Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            effect = next(effect for effect in match.effects if effect.kind == kind)
            start = effect.position.copy()
            for frame in range(1, 11):
                update_world(match, {0: InputState()}, 0.05)
                expected_distance = min(speed * 0.05 * frame, effect.max_distance)
                self.assertAlmostEqual(start.distance_to(effect.position), expected_distance, delta=0.5, msg=(role, frame))
                if role == CharacterId.CONTROLLER and frame < 10:
                    self.assertFalse(effect.armed)

    def test_four_flying_roles_hold_speed_within_five_percent_for_twenty_runs(self) -> None:
        expected = {
            CharacterId.BREACHER: (config.BREACH_PROJECTILE_SPEED, "breach_pellet"),
            CharacterId.SNIPER: (config.SNIPER_PROJECTILE_SPEED, "sniper_line"),
            CharacterId.HUNTER: (config.HUNTER_PROJECTILE_SPEED, "boomerang"),
            CharacterId.CONTROLLER: (config.MINE_PROJECTILE_SPEED, "mine"),
        }
        delta_time = 0.05
        for role, (speed, kind) in expected.items():
            for _ in range(20):
                match = self._solo_match(role)
                action = create_primary_action(match.players[0], Vector2(1, 0))
                self.assertIsNotNone(action)
                assert action is not None
                _apply_action(match, action)
                effect = next(effect for effect in match.effects if effect.kind == kind)
                expected_intervals = min(10, math.ceil(effect.max_distance / (speed * delta_time)))
                observed_intervals = 0
                for _ in range(expected_intervals):
                    before = effect.position.copy()
                    remaining = max(0.0, effect.max_distance - effect.distance_travelled)
                    update_world(match, {0: InputState()}, delta_time)
                    actual_step = before.distance_to(effect.position)
                    expected_step = min(speed * delta_time, remaining)
                    tolerance = max(0.5, expected_step * 0.05)
                    self.assertAlmostEqual(actual_step, expected_step, delta=tolerance, msg=(role, observed_intervals))
                    observed_intervals += 1
                    if remaining <= 0.0 or effect.distance_travelled >= effect.max_distance - 0.001:
                        break
                self.assertEqual(observed_intervals, expected_intervals, role)

    def test_projectile_sweeps_and_controller_mine_only_arms_at_landing(self) -> None:
        for role in (CharacterId.BREACHER, CharacterId.SNIPER, CharacterId.HUNTER):
            for _ in range(20):
                match, owner, target = self._target_match(role, Vector2(50, 0))
                health_before = target.health
                action = create_primary_action(owner, Vector2(1, 0))
                self.assertIsNotNone(action)
                _apply_action(match, action)
                for _ in range(4):
                    update_world(match, {0: InputState()}, 0.05)
                self.assertLess(target.health, health_before, role)

        for _ in range(20):
            match, owner, target = self._target_match(CharacterId.CONTROLLER, Vector2(100, 0))
            health_before = target.health
            action = create_primary_action(owner, Vector2(1, 0))
            self.assertIsNotNone(action)
            _apply_action(match, action)
            update_world(match, {0: InputState()}, 0.10)
            mine = next(effect for effect in match.effects if effect.kind == "mine")
            self.assertFalse(mine.armed)
            self.assertEqual(target.health, health_before)
            self.assertEqual(target.slow_multiplier, 1.0)

            # 目標不在地雷中心，但在落地後 100 半徑控制區內；
            # 這能區分「投射物碰撞半徑」與「落地效果半徑」。
            target.position = owner.position + Vector2(540, 0)
            for _ in range(26):
                update_world(match, {0: InputState()}, 0.05)
            self.assertLess(target.health, health_before)
            self.assertLess(target.slow_multiplier, 1.0)

    def test_boomerang_can_damage_the_same_target_once_on_each_direction(self) -> None:
        match, owner, target = self._target_match(CharacterId.HUNTER, Vector2(100, 0))
        action = create_primary_action(owner, Vector2(1, 0))
        self.assertIsNotNone(action)
        _apply_action(match, action)
        for _ in range(5):
            update_world(match, {0: InputState()}, 0.05)
        health_after_outbound = target.health
        self.assertLess(health_after_outbound, target.max_health)

        for _ in range(50):
            update_world(match, {0: InputState()}, 0.05)
        self.assertLess(target.health, health_after_outbound)

    def test_damage_order_applies_shield_then_reduction_and_final_clamp(self) -> None:
        match = create_match(CharacterId.SNIPER)
        target = match.players[1]
        target.max_health = 100.0
        target.health = 100.0
        target.shield_remaining = 30.0
        target.shield_timer = 2.0
        target.damage_reduction = 0.5
        target.damage_reduction_timer = 2.0
        event = apply_damage(match, 0, "player", target.player_id, 100.0)
        self.assertIsNotNone(event)
        self.assertEqual(event.effective_damage, 35.0)
        self.assertEqual(target.health, 65.0)
        self.assertEqual(target.shield_remaining, 0.0)

    def test_fixed_ttk_ranges_use_the_new_role_values(self) -> None:
        def run_burst(role: CharacterId, distance: float, step: float, repeat: int) -> int:
            match, owner, target = self._target_match(role, Vector2(distance, 0))
            projectile_speed = get_character_definition(role).projectile_speed
            effective_step = max(
                step,
                distance / projectile_speed + 0.10 if projectile_speed > 0.0 else step,
            )
            for hit in range(1, repeat + 1):
                owner.ammo = owner.ammo_capacity
                owner.primary_cooldown = 0.0
                # 固定 TTK 夾具每次都把目標放回指定距離，排除守衛者
                # 弧形攻擊的擊退對「全部命中」條件造成干擾。
                target.position = owner.position + Vector2(distance, 0)
                action = create_primary_action(owner, Vector2(1, 0))
                self.assertIsNotNone(action)
                _apply_action(match, action)
                if role != CharacterId.GUARDIAN:
                    for _ in range(max(1, round(effective_step / 0.05))):
                        update_world(match, {0: InputState()}, 0.05)
                if not target.alive:
                    return hit
                match.effects.clear()
            return repeat + 1

        sniper_hits = run_burst(CharacterId.SNIPER, 500.0, 0.40, 5)
        breacher_hits = run_burst(CharacterId.BREACHER, 50.0, 0.25, 5)
        guardian_hits = run_burst(CharacterId.GUARDIAN, 50.0, 0.01, 5)
        hunter_hits = run_burst(CharacterId.HUNTER, 100.0, 0.30, 5)
        self.assertIn(sniper_hits, (2, 3))
        self.assertIn(breacher_hits, (3, 4, 5))
        self.assertIn(guardian_hits, (3, 4, 5))
        self.assertIn(hunter_hits, (3, 4, 5))

        match, owner, target = self._target_match(CharacterId.SIPHONER, Vector2(100, 0))
        channels = 0
        while target.alive and channels < 5:
            owner.ammo = owner.ammo_capacity
            owner.primary_cooldown = 0.0
            match.effects.clear()
            for frame in range(24):
                update_world(
                    match,
                    {0: InputState(primary_pressed=frame == 0, primary_held=True, aim_direction=Vector2(1, 0))},
                    0.05,
                )
            update_world(match, {0: InputState(primary_released=True)}, 0.01)
            channels += 1
        self.assertIn(channels, (2, 3, 4))


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

    def test_extraction_uses_only_time_after_activation_and_before_timeout(self) -> None:
        activation_match = create_match()
        activation_match.monsters = []
        activation_player = activation_match.players[0]
        activation_player.position = activation_match.extraction_zone.center.copy()
        activation_match.elapsed_time = 209.99

        update_world(activation_match, {0: InputState()}, 0.05)

        self.assertAlmostEqual(activation_player.extraction_progress, 0.04, places=5)

        timeout_match = create_match()
        timeout_match.monsters = []
        timeout_player = timeout_match.players[0]
        timeout_player.position = timeout_match.extraction_zone.center.copy()
        timeout_player.extraction_progress = 9.97
        timeout_match.elapsed_time = 239.98

        update_world(timeout_match, {0: InputState()}, 0.05)

        self.assertEqual(timeout_match.phase, MatchPhase.NO_WINNER)
        self.assertAlmostEqual(timeout_player.extraction_progress, 9.99, places=5)


if __name__ == "__main__":
    unittest.main()
