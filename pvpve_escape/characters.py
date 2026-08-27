"""六種角色、三種戰術配件與其動作資料。"""

from __future__ import annotations

from . import config
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
        primary_damage=7.0,
        primary_range=config.BREACH_CONE_RANGE,
        passive_text="200 內傷害 +20%",
        ultimate_text="半徑 190 爆發並擊退",
        base_health=110.0,
        projectile_speed=config.BREACH_PROJECTILE_SPEED,
        passive_multiplier=1.2,
        passive_condition="close",
        parameters={"pellets": float(config.BREACH_PELLET_COUNT), "angle": config.BREACH_CONE_ANGLE_DEGREES, "passive_range": config.BREACH_CONE_RANGE, "ultimate_damage": 55.0, "ultimate_radius": 190.0, "ultimate_knockback": 120.0},
    ),
    CharacterId.SNIPER: CharacterDefinition(
        character_id=CharacterId.SNIPER,
        display_name="狙擊者",
        primary_kind="0.6 秒蓄力直線射擊",
        ammo_capacity=2,
        ammo_recovery_interval=0.80,
        primary_cooldown=1.25,
        primary_damage=50.0,
        primary_range=1000.0,
        passive_text="超過 450 距離傷害 +20%",
        ultimate_text="射程 1100 的穿透線",
        base_health=80.0,
        projectile_speed=config.SNIPER_PROJECTILE_SPEED,
        passive_multiplier=1.2,
        passive_condition="far",
        parameters={"charge": 0.6, "passive_range": 450.0, "ultimate_range": 1100.0, "ultimate_damage": 90.0},
    ),
    CharacterId.GUARDIAN: CharacterDefinition(
        character_id=CharacterId.GUARDIAN,
        display_name="守衛者",
        primary_kind="前方弧形盾牌衝擊",
        ammo_capacity=2,
        ammo_recovery_interval=0.60,
        primary_cooldown=0.80,
        primary_damage=30.0,
        primary_range=125.0,
        passive_text="最大生命值 +20%",
        ultimate_text="4 秒減傷 70%",
        base_health=115.0,
        projectile_speed=0.0,
        parameters={"angle": 100.0, "knockback": 120.0, "ultimate_duration": 4.0, "reduction": 0.7},
    ),
    CharacterId.HUNTER: CharacterDefinition(
        character_id=CharacterId.HUNTER,
        display_name="追獵者",
        primary_kind="往返回旋飛刃",
        ammo_capacity=3,
        ammo_recovery_interval=0.35,
        primary_cooldown=0.85,
        primary_damage=24.0,
        primary_range=340.0,
        passive_text="移動速度 +15%",
        ultimate_text="突進 360、免傷並傷害路徑",
        base_health=95.0,
        projectile_speed=config.HUNTER_PROJECTILE_SPEED,
        parameters={"ultimate_distance": 360.0, "ultimate_invulnerability": 0.5, "ultimate_damage": 50.0},
    ),
    CharacterId.CONTROLLER: CharacterDefinition(
        character_id=CharacterId.CONTROLLER,
        display_name="控場者",
        primary_kind="重力地雷",
        ammo_capacity=2,
        ammo_recovery_interval=0.55,
        primary_cooldown=0.90,
        primary_damage=20.0,
        primary_range=460.0,
        passive_text="控制時間 +50%",
        ultimate_text="半徑 190 重力牢籠",
        base_health=90.0,
        projectile_speed=config.MINE_PROJECTILE_SPEED,
        passive_multiplier=1.5,
        parameters={"mine_radius": 100.0, "slow": 0.5, "slow_duration": 1.5, "max_mines": 2.0, "ultimate_radius": 190.0, "ultimate_slow": 0.7, "ultimate_root": 0.75, "ultimate_duration": 3.0},
    ),
    CharacterId.SIPHONER: CharacterDefinition(
        character_id=CharacterId.SIPHONER,
        display_name="吸能者",
        primary_kind="持續吸能光束",
        ammo_capacity=4,
        ammo_recovery_interval=0.20,
        primary_cooldown=0.15,
        primary_damage=6.0,
        primary_range=280.0,
        passive_text="對怪物能量 +25%",
        ultimate_text="半徑 220 傷害並吸血",
        base_health=105.0,
        projectile_speed=0.0,
        parameters={"beam_tick": 0.15, "beam_duration": 1.2, "energy_multiplier": 1.25, "ultimate_radius": 220.0, "ultimate_damage": 60.0, "heal_ratio": 0.5},
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
    passive_range = float(definition.parameters.get("passive_range", 180.0))
    if definition.passive_condition == "close" and distance <= passive_range:
        damage *= definition.passive_multiplier
    elif definition.passive_condition == "far" and distance >= passive_range:
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
            projectile_speed=definition.projectile_speed,
            metadata={
                "pellets": int(definition.parameters.get("pellets", config.BREACH_PELLET_COUNT)),
                "angle": definition.parameters.get("angle", config.BREACH_CONE_ANGLE_DEGREES),
                "visual": "cone_and_pellet_trails",
                "impact": "authoritative_cone_sweep",
            },
        )
    if player.character_id == CharacterId.SNIPER:
        return CombatAction(
            kind="sniper_line", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            projectile_speed=definition.projectile_speed,
            metadata={"charge": primary_charge, "piercing": 0, "visual": "projectile_line", "impact": "first_target"},
        )
    if player.character_id == CharacterId.GUARDIAN:
        return CombatAction(
            kind="guardian_arc", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            metadata={"angle": definition.parameters.get("angle", 100.0), "knockback": definition.parameters.get("knockback", 120.0), "visual": "shield_arc", "impact": "arc_area"},
        )
    if player.character_id == CharacterId.HUNTER:
        return CombatAction(
            kind="boomerang", owner_id=player.player_id, origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range, max_distance=definition.primary_range,
            projectile_speed=definition.projectile_speed,
            metadata={"visual": "returning_blade", "impact": "outbound_and_return"},
        )
    if player.character_id == CharacterId.CONTROLLER:
        return CombatAction(
            kind="mine", owner_id=player.player_id,
            origin=origin, direction=direction,
            damage=definition.primary_damage, range=definition.primary_range,
            radius=definition.parameters.get("mine_radius", 100.0), duration=12.0,
            max_distance=definition.primary_range,
            projectile_speed=definition.projectile_speed,
            metadata={"slow": definition.parameters.get("slow", 0.5), "slow_duration": definition.parameters.get("slow_duration", 1.5), "visual": "landing_mine", "impact": "armed_area"},
        )
    return CombatAction(
        kind="beam", owner_id=player.player_id, origin=origin, direction=direction,
        damage=definition.primary_damage, range=definition.primary_range,
        duration=definition.parameters.get("beam_duration", 1.2),
        metadata={"tick": definition.parameters.get("beam_tick", 0.15), "visual": "channel_beam", "impact": "periodic_line"},
    )


def create_ultimate_action(player: PlayerState, aim_direction: Vector2) -> CombatAction | None:
    """大招消耗 100 能量後立即歸零；各角色效果完全不同。"""

    if not player.alive or player.ultimate_energy < 100.0:
        return None
    player.ultimate_energy = 0.0
    direction = _safe_direction(aim_direction)
    player.aim_direction = direction
    definition = get_character_definition(player.character_id)
    parameters = definition.parameters
    if player.character_id == CharacterId.BREACHER:
        return CombatAction("breach_burst", player.player_id, player.position.copy(), direction, parameters.get("ultimate_damage", 55.0), radius=parameters.get("ultimate_radius", 190.0), metadata={"knockback": parameters.get("ultimate_knockback", 120.0), "visual": "radial_burst", "impact": "radial_damage"})
    if player.character_id == CharacterId.SNIPER:
        return CombatAction("sniper_ultimate_line", player.player_id, player.position.copy(), direction, parameters.get("ultimate_damage", 90.0), range=parameters.get("ultimate_range", 1100.0), metadata={"piercing": 1, "visual": "piercing_line", "impact": "all_targets_in_line"})
    if player.character_id == CharacterId.GUARDIAN:
        return CombatAction("guardian_guard", player.player_id, player.position.copy(), direction, duration=parameters.get("ultimate_duration", 4.0), metadata={"reduction": parameters.get("reduction", 0.7), "visual": "defense_ring", "impact": "self_reduction"})
    if player.character_id == CharacterId.HUNTER:
        return CombatAction("hunter_dash", player.player_id, player.position.copy(), direction, damage=parameters.get("ultimate_damage", 50.0), max_distance=parameters.get("ultimate_distance", 360.0), duration=parameters.get("ultimate_invulnerability", 0.5), metadata={"visual": "dash_trail", "impact": "path_damage"})
    if player.character_id == CharacterId.CONTROLLER:
        control_duration = calculate_control_duration(player, parameters.get("ultimate_duration", 3.0))
        return CombatAction("gravity_cage", player.player_id, player.position.copy(), direction, max_distance=220.0, radius=parameters.get("ultimate_radius", 190.0), duration=control_duration, metadata={"slow": parameters.get("ultimate_slow", 0.7), "root": calculate_control_duration(player, parameters.get("ultimate_root", 0.75)), "visual": "gravity_cage", "impact": "slow_and_root"})
    return CombatAction("siphon_burst", player.player_id, player.position.copy(), direction, damage=parameters.get("ultimate_damage", 60.0), radius=parameters.get("ultimate_radius", 220.0), metadata={"heal_ratio": parameters.get("heal_ratio", 0.5), "visual": "siphon_burst", "impact": "damage_and_heal"})


def create_tactical_action(player: PlayerState, aim_direction: Vector2, move_direction: Vector2) -> CombatAction | None:
    """建立位移、防禦或控場配件動作；開局即可用，固定 12 秒冷卻。"""

    if not player.alive or player.tactical_cooldown > 0:
        return None
    definition = get_tactical_definition(player.tactical_id)
    player.tactical_cooldown = definition.cooldown
    # 衝刺沿移動方向操作；需要落點的控場配件則固定沿瞄準方向，
    # 讓預覽端點與實際控制區中心在同一個世界座標。
    if player.tactical_id == TacticalId.DASH:
        direction = _safe_direction(move_direction if move_direction.length() else aim_direction)
    else:
        direction = _safe_direction(aim_direction)
    if player.tactical_id == TacticalId.DASH:
        return CombatAction("tactical_dash", player.player_id, player.position.copy(), direction, max_distance=definition.parameters.get("distance", 220.0), duration=definition.parameters.get("invulnerability", 0.2), projectile_speed=0.0)
    if player.tactical_id == TacticalId.SHIELD:
        return CombatAction("tactical_shield", player.player_id, player.position.copy(), direction, duration=definition.parameters.get("duration", 2.0), projectile_speed=0.0, metadata={"absorb": definition.parameters.get("absorb", 60.0)})
    radius = definition.parameters.get("radius", 100.0)
    return CombatAction("tactical_control", player.player_id, player.position.copy(), direction, radius=radius, max_distance=radius, duration=calculate_control_duration(player, definition.parameters.get("duration", 1.5)), projectile_speed=0.0, metadata={"slow": definition.parameters.get("slow", 0.6)})
