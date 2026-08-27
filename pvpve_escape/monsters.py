"""多種怪物的資料表與建立函式。"""

from __future__ import annotations

from . import config
from .models import MonsterDefinition, MonsterState, MonsterType, Vector2


MONSTER_DEFINITIONS: dict[MonsterType, MonsterDefinition] = {
    MonsterType.CHASER: MonsterDefinition(
        monster_type=MonsterType.CHASER,
        display_name="追獵獸",
        max_health=config.MONSTER_HEALTH,
        move_speed=config.MONSTER_SPEED,
        radius=config.MONSTER_RADIUS,
        attack_kind="contact",
        attack_damage=config.MONSTER_CONTACT_DAMAGE,
        attack_interval=config.MONSTER_ATTACK_INTERVAL,
    ),
    MonsterType.SHOOTER: MonsterDefinition(
        monster_type=MonsterType.SHOOTER,
        display_name="砲台蟲",
        max_health=config.MONSTER_SHOOTER_HEALTH,
        move_speed=config.MONSTER_SHOOTER_SPEED,
        radius=config.MONSTER_SHOOTER_RADIUS,
        attack_kind="projectile",
        attack_damage=config.MONSTER_SHOOTER_DAMAGE,
        attack_interval=config.MONSTER_SHOOTER_ATTACK_INTERVAL,
        attack_range=config.MONSTER_SHOOTER_ATTACK_RANGE,
        preferred_range=config.MONSTER_SHOOTER_PREFERRED_RANGE,
        projectile_speed=config.MONSTER_SHOOTER_PROJECTILE_SPEED,
        projectile_radius=config.MONSTER_SHOOTER_PROJECTILE_RADIUS,
        projectile_range=config.MONSTER_SHOOTER_PROJECTILE_RANGE,
    ),
    MonsterType.BRUTE: MonsterDefinition(
        monster_type=MonsterType.BRUTE,
        display_name="重裝巨獸",
        max_health=config.MONSTER_BRUTE_HEALTH,
        move_speed=config.MONSTER_BRUTE_SPEED,
        radius=config.MONSTER_BRUTE_RADIUS,
        attack_kind="contact",
        attack_damage=config.MONSTER_BRUTE_DAMAGE,
        attack_interval=config.MONSTER_BRUTE_ATTACK_INTERVAL,
    ),
}

MONSTER_SPAWN_ORDER = (
    MonsterType.CHASER,
    MonsterType.SHOOTER,
    MonsterType.BRUTE,
)


def get_monster_definition(monster_type: MonsterType) -> MonsterDefinition:
    return MONSTER_DEFINITIONS[monster_type]


def get_all_monster_definitions() -> list[MonsterDefinition]:
    return [MONSTER_DEFINITIONS[monster_type] for monster_type in MONSTER_SPAWN_ORDER]


def create_monster_state(
    monster_id: int,
    spawn_zone_id: int,
    spawn_position: Vector2,
    monster_type: MonsterType,
) -> MonsterState:
    definition = get_monster_definition(monster_type)
    return MonsterState(
        monster_id=monster_id,
        spawn_zone_id=spawn_zone_id,
        position=spawn_position.copy(),
        spawn_position=spawn_position.copy(),
        radius=definition.radius,
        max_health=definition.max_health,
        health=definition.max_health,
        move_speed=definition.move_speed,
        monster_type=monster_type,
    )
