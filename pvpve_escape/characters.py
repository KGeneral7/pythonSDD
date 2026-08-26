"""六種角色、三種戰術配件與其動作資料。"""

from __future__ import annotations

from .models import (
    CharacterDefinition,
    CharacterId,
    CombatAction,
    PlayerState,
    TacticalDefinition,
    TacticalId,
    Vector2,
)
from .rules import calculate_upgrade_multiplier, consume_ammo


CHARACTER_DEFINITIONS: dict[CharacterId, CharacterDefinition] = {
    CharacterId.BREACHER: CharacterDefinition(
        character_id=CharacterId.BREACHER,
        display_name="破陣者",
        primary_kind="60° 扇形散射",
        ammo_capacity=3,
        ammo_recovery_interval=0.45,
        primary_cooldown=0.75,
        primary_damage=8.0,
        primary_range=180.0,
        passive_text="180 內傷害 +20%",
        ultimate_text="半徑 180 爆發並擊退",
        passive_multiplier=1.2,
        passive_condition="close",
        parameters={"pellets": 5.0, "angle": 60.0, "ultimate_radius": 180.0, "ultimate_knockback": 120.0},
    ),
    CharacterId.SNIPER: CharacterDefinition(
        character_id=CharacterId.SNIPER,
        display_name="狙擊者",
        primary_kind="0.6 秒蓄力直線射擊",
        ammo_capacity=2,
        ammo_recovery_interval=0.80,
        primary_cooldown=1.25,
        primary_damage=45.0,
        primary_range=900.0,
        passive_text="超過 450 距離傷害 +20%",
        ultimate_text="射程 1000 的穿透線",
        passive_multiplier=1.2,
        passive_condition="far",
        parameters={"charge": 0.6, "passive_range": 450.0, "ultimate_range": 1000.0, "ultimate_damage": 80.0},
    ),
    CharacterId.GUARDIAN: CharacterDefinition(
        character_id=CharacterId.GUARDIAN,
        display_name="守衛者",
        primary_kind="前方弧形盾牌衝擊",
        ammo_capacity=2,
        ammo_recovery_interval=0.60,
        primary_cooldown=0.80,
        primary_damage=25.0,
        primary_range=105.0,
        passive_text="最大生命值 +20%",
        ultimate_text="4 秒減傷 70%",
        parameters={"angle": 100.0, "knockback": 120.0, "ultimate_duration": 4.0, "reduction": 0.7},
    ),
    CharacterId.HUNTER: CharacterDefinition(
        character_id=CharacterId.HUNTER,
        display_name="追獵者",
        primary_kind="往返回旋飛刃",
        ammo_capacity=3,
        ammo_recovery_interval=0.35,
        primary_cooldown=0.85,
        primary_damage=18.0,
        primary_range=300.0,
        passive_text="移動速度 +15%",
        ultimate_text="突進、免傷並傷害路徑",
        parameters={"projectile_speed": 520.0, "ultimate_distance": 320.0, "ultimate_invulnerability": 0.5, "ultimate_damage": 40.0},
    ),
    CharacterId.CONTROLLER: CharacterDefinition(
        character_id=CharacterId.CONTROLLER,
        display_name="控場者",
        primary_kind="重力地雷",
        ammo_capacity=2,
        ammo_recovery_interval=0.55,
        primary_cooldown=0.90,
        primary_damage=18.0,
        primary_range=420.0,
        passive_text="控制時間 +50%",
        ultimate_text="半徑 170 重力牢籠",
        passive_multiplier=1.5,
        parameters={"mine_radius": 100.0, "slow": 0.5, "slow_duration": 1.5, "max_mines": 2.0, "ultimate_radius": 170.0, "ultimate_slow": 0.7, "ultimate_root": 0.75, "ultimate_duration": 3.0},
    ),
    CharacterId.SIPHONER: CharacterDefinition(
        character_id=CharacterId.SIPHONER,
        display_name="吸能者",
        primary_kind="持續吸能光束",
        ammo_capacity=4,
        ammo_recovery_interval=0.20,
        primary_cooldown=0.15,
        primary_damage=7.0,
        primary_range=260.0,
        passive_text="對怪物能量 +25%",
        ultimate_text="半徑 200 傷害並吸血",
        parameters={"beam_tick": 0.15, "beam_duration": 1.2, "energy_multiplier": 1.25, "ultimate_radius": 200.0, "ultimate_damage": 50.0, "heal_ratio": 0.5},
    ),
}


TACTICAL_DEFINITIONS: dict[TacticalId, TacticalDefinition] = {
    TacticalId.DASH: TacticalDefinition(
        tactical_id=TacticalId.DASH,
        display_name="短距離衝刺",
        cooldown=12.0,
        description="朝移動或瞄準方向移動 220，免傷 0.2 秒",
        parameters={"distance": 220.0, "invulnerability": 0.2},
    ),
    TacticalId.SHIELD: TacticalDefinition(
        tactical_id=TacticalId.SHIELD,
        display_name="短時間護盾",
        cooldown=12.0,
        description="吸收最多 60 點傷害，持續 2 秒",
        parameters={"absorb": 60.0, "duration": 2.0},
    ),
    TacticalId.CONTROL: TacticalDefinition(
        tactical_id=TacticalId.CONTROL,
        display_name="範圍控場",
        cooldown=12.0,
        description="半徑 100，減速 60%，持續 1.5 秒",
        parameters={"radius": 100.0, "slow": 0.6, "duration": 1.5},
    ),
}


def get_character_definition(character_id: CharacterId) -> CharacterDefinition:
    return CHARACTER_DEFINITIONS[character_id]


def get_all_character_definitions() -> list[CharacterDefinition]:
    return [CHARACTER_DEFINITIONS[character_id] for character_id in CharacterId]


def get_tactical_definition(tactical_id: TacticalId) -> TacticalDefinition:
    return TACTICAL_DEFINITIONS[tactical_id]


def get_all_tactical_definitions() -> list[TacticalDefinition]:
    return [TACTICAL_DEFINITIONS[tactical_id] for tactical_id in TacticalId]


def _safe_direction(direction: Vector2) -> Vector2:
    return direction.normalized() if direction.length() else Vector2(1.0, 0.0)


def calculate_attack_damage(
    player: PlayerState,
    distance: float,
    target_kind: str = "player",
) -> float:
    """套用強化與條件被動；只有有效傷害才會在世界規則中轉為能量。"""

    definition = get_character_definition(player.character_id)
    damage = definition.primary_damage * calculate_upgrade_multiplier(player.upgrade_stacks)
    if definition.passive_condition == "close" and distance <= 180.0:
        damage *= definition.passive_multiplier
    elif definition.passive_condition == "far" and distance >= 450.0:
        damage *= definition.passive_multiplier
    return damage


def calculate_control_duration(player: PlayerState, duration: float) -> float:
    """套用控場者的控制時間被動，其他角色維持原始持續時間。"""

    if player.character_id == CharacterId.CONTROLLER:
        return duration * get_character_definition(player.character_id).passive_multiplier
    return duration


def create_primary_action(
    player: PlayerState,
    aim_direction: Vector2,
    primary_charge: float = 0.0,
) -> CombatAction | None:
    """在冷卻與彈藥允許時產生角色專屬普攻動作。"""

    definition = get_character_definition(player.character_id)
    if player.primary_cooldown > 0 or not consume_ammo(player):
        return None
    direction = _safe_direction(aim_direction)
    player.aim_direction = direction
    player.primary_cooldown = definition.primary_cooldown
    origin = player.position.copy()
    if player.character_id == CharacterId.BREACHER:
        return CombatAction(
            kind="breach_cone", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            metadata={"pellets": 5, "angle": 60},
        )
    if player.character_id == CharacterId.SNIPER:
        return CombatAction(
            kind="sniper_line", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            metadata={"charge": primary_charge, "piercing": 0},
        )
    if player.character_id == CharacterId.GUARDIAN:
        return CombatAction(
            kind="guardian_arc", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            metadata={"angle": 100, "knockback": 120},
        )
    if player.character_id == CharacterId.HUNTER:
        return CombatAction(
            kind="boomerang", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range, max_distance=definition.primary_range,
            metadata={"speed": 520},
        )
    if player.character_id == CharacterId.CONTROLLER:
        return CombatAction(
            kind="mine", owner_id=player.player_id,
            origin=origin + direction * 140.0, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            radius=100.0, duration=12.0,
            metadata={"slow": 0.5, "slow_duration": 1.5},
        )
    return CombatAction(
        kind="beam", owner_id=player.player_id, origin=origin, direction=direction,
        damage=definition.primary_damage, range=definition.primary_range,
        duration=1.2, metadata={"tick": 0.15},
    )


def create_ultimate_action(player: PlayerState, aim_direction: Vector2) -> CombatAction | None:
    """大招消耗 100 能量後立即歸零；各角色效果完全不同。"""

    if not player.alive or player.ultimate_energy < 100.0:
        return None
    player.ultimate_energy = 0.0
    direction = _safe_direction(aim_direction)
    player.aim_direction = direction
    if player.character_id == CharacterId.BREACHER:
        return CombatAction("breach_burst", player.player_id, player.position.copy(), direction, 50.0, radius=180.0, metadata={"knockback": 120})
    if player.character_id == CharacterId.SNIPER:
        return CombatAction("sniper_ultimate_line", player.player_id, player.position.copy(), direction, 80.0, range=1000.0, metadata={"piercing": 1})
    if player.character_id == CharacterId.GUARDIAN:
        return CombatAction("guardian_guard", player.player_id, player.position.copy(), direction, duration=4.0, metadata={"reduction": 0.7})
    if player.character_id == CharacterId.HUNTER:
        return CombatAction("hunter_dash", player.player_id, player.position.copy(), direction, damage=40.0, max_distance=320.0, duration=0.5)
    if player.character_id == CharacterId.CONTROLLER:
        control_duration = calculate_control_duration(player, 3.0)
        return CombatAction("gravity_cage", player.player_id, player.position.copy() + direction * 220.0, direction, radius=170.0, duration=control_duration, metadata={"slow": 0.7, "root": calculate_control_duration(player, 0.75)})
    return CombatAction("siphon_burst", player.player_id, player.position.copy(), direction, damage=50.0, radius=200.0, metadata={"heal_ratio": 0.5})


def create_tactical_action(player: PlayerState, aim_direction: Vector2, move_direction: Vector2) -> CombatAction | None:
    """建立位移、防禦或控場配件動作；開局即可用，固定 12 秒冷卻。"""

    if not player.alive or player.tactical_cooldown > 0:
        return None
    definition = get_tactical_definition(player.tactical_id)
    player.tactical_cooldown = definition.cooldown
    direction = _safe_direction(move_direction if move_direction.length() else aim_direction)
    if player.tactical_id == TacticalId.DASH:
        return CombatAction("tactical_dash", player.player_id, player.position.copy(), direction, max_distance=220.0, duration=0.2)
    if player.tactical_id == TacticalId.SHIELD:
        return CombatAction("tactical_shield", player.player_id, player.position.copy(), direction, duration=2.0, metadata={"absorb": 60})
    return CombatAction("tactical_control", player.player_id, player.position.copy() + direction * 100.0, direction, radius=100.0, duration=calculate_control_duration(player, 1.5), metadata={"slow": 0.6})
