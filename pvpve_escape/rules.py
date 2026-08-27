"""不依賴 Pygame 的數值、生命週期與撤離規則。"""

from __future__ import annotations

from . import config
from .models import (
    AbilityEffect,
    CircleZone,
    DamageEvent,
    MatchPhase,
    MatchState,
    MonsterState,
    PlayerState,
    PlayerStatus,
    Vector2,
)


def is_visual_only_effect(effect: AbilityEffect) -> bool:
    """判斷效果是否只供畫面使用，不得進入規則命中流程。"""

    return bool(effect.metadata.get("visual_only", False))


def calculate_upgrade_multiplier(stacks: int) -> float:
    """將強化層數限制在 0～10，並回傳攻擊與生命倍率。"""

    safe_stacks = max(0, min(config.MAX_UPGRADE_STACKS, int(stacks)))
    return 1.0 + config.UPGRADE_PER_STACK * safe_stacks


def recalculate_max_health(player: PlayerState) -> None:
    """依角色被動與死亡前強化重新計算最大生命值。"""

    old_max_health = max(player.max_health, 1.0)
    player.max_health = (
        player.base_max_health
        * player.health_passive_multiplier
        * calculate_upgrade_multiplier(player.upgrade_stacks)
    )
    if player.alive:
        # 讓滿血玩家在取得生命強化時仍保持滿血；受傷玩家則維持相同比例。
        player.health = min(player.max_health, player.health * player.max_health / old_max_health)


def apply_monster_kill_upgrade(player: PlayerState) -> int:
    """給最後一擊玩家增加一層死亡前有效的強化，並回傳目前層數。"""

    if not player.alive:
        return player.upgrade_stacks
    player.upgrade_stacks = min(config.MAX_UPGRADE_STACKS, player.upgrade_stacks + 1)
    recalculate_max_health(player)
    return player.upgrade_stacks


def add_ultimate_energy(player: PlayerState, effective_damage: float, multiplier: float = 1.0) -> float:
    """以有效傷害累積大招能量；吸能者的被動由 multiplier 傳入。"""

    if not player.alive or effective_damage <= 0:
        return player.ultimate_energy
    player.ultimate_energy = min(
        config.MAX_ULTIMATE_ENERGY,
        player.ultimate_energy + max(0.0, effective_damage) * max(0.0, multiplier),
    )
    return player.ultimate_energy


def primary_attack_active(player: PlayerState, primary_held: bool = False) -> bool:
    """判斷目前是否仍處於普攻按住、蓄力、引導或後搖狀態。"""

    if not player.alive:
        return False
    return bool(
        primary_held
        or player.primary_charge > 0.0
        or player.primary_cooldown > 0.0
    )


def recover_ammo(
    player: PlayerState,
    delta_time: float,
    recovery_interval: float,
    blocked: bool = False,
) -> int:
    """在未被普攻狀態阻擋時依角色間隔逐發補回彈藥。"""

    if blocked or not player.alive or player.ammo >= player.ammo_capacity:
        player.ammo_recovery_timer = 0.0
        return player.ammo

    player.ammo_recovery_timer += max(0.0, delta_time)
    interval = max(0.001, recovery_interval)
    while player.ammo < player.ammo_capacity and player.ammo_recovery_timer >= interval:
        player.ammo += 1
        player.ammo_recovery_timer -= interval
    if player.ammo >= player.ammo_capacity:
        player.ammo_recovery_timer = 0.0
    return player.ammo


def consume_ammo(player: PlayerState) -> bool:
    """消耗一發彈藥；補彈計時從射擊後重新開始。"""

    if not player.alive or player.ammo <= 0:
        return False
    player.ammo -= 1
    player.ammo_recovery_timer = 0.0
    return True


def apply_damage_to_player(player: PlayerState, raw_damage: float) -> float:
    """套用免疫、護盾與減傷後扣除生命，回傳實際傷害。"""

    if not player.alive or player.invulnerability_timer > 0:
        return 0.0
    incoming = max(0.0, raw_damage)
    if player.shield_remaining > 0:
        absorbed = min(player.shield_remaining, incoming)
        player.shield_remaining -= absorbed
        incoming -= absorbed
    effective_damage = incoming * max(0.0, 1.0 - player.damage_reduction)
    player.health = max(0.0, player.health - effective_damage)
    player.last_damage_time = 0.0
    if player.health <= 0:
        handle_player_death(player)
    return effective_damage


def apply_damage_to_monster(monster: MonsterState, raw_damage: float) -> float:
    """扣除怪物生命並回傳實際傷害；死亡交由世界更新處理重生與獎勵。"""

    if not monster.alive:
        return 0.0
    effective_damage = min(max(0.0, raw_damage), monster.health)
    monster.health = max(0.0, monster.health - effective_damage)
    if monster.health <= 0:
        monster.alive = False
        monster.respawn_timer = config.MONSTER_RESPAWN_DELAY
    return effective_damage


def make_damage_event(
    sequence: int,
    source_player_id: int | None,
    target_id: int,
    raw_damage: float,
    effective_damage: float,
    created_at: float,
    target_kind: str,
) -> DamageEvent:
    """建立可排序的傷害事件，避免最後一擊依賴集合迭代順序。"""

    return DamageEvent(
        sequence=sequence,
        source_player_id=source_player_id,
        target_id=target_id,
        raw_damage=raw_damage,
        effective_damage=effective_damage,
        created_at=created_at,
        target_kind=target_kind,
    )


def clear_player_effects(player: PlayerState) -> None:
    """清除死亡或重生時不應延續的護盾、免疫、減速與控場狀態。"""

    player.invulnerability_timer = 0.0
    player.damage_reduction_timer = 0.0
    player.damage_reduction = 0.0
    player.shield_remaining = 0.0
    player.shield_timer = 0.0
    player.slow_timer = 0.0
    player.slow_multiplier = 1.0
    player.root_timer = 0.0
    player.primary_charge = 0.0


def handle_player_death(player: PlayerState) -> None:
    """死亡立即清除強化、能量與撤離進度，並開始 5 秒重生倒數。"""

    if not player.alive:
        return
    player.status = PlayerStatus.DEAD
    player.health = 0.0
    player.upgrade_stacks = 0
    player.ultimate_energy = 0.0
    player.extraction_progress = 0.0
    player.death_timer = config.RESPAWN_DELAY
    player.tactical_cooldown = 0.0
    player.primary_cooldown = 0.0
    player.ability_input_blocked = True
    player.ammo = 0
    player.ammo_recovery_timer = 0.0
    player.max_health = player.base_max_health * player.health_passive_multiplier
    clear_player_effects(player)


def respawn_player(player: PlayerState, spawn_position: Vector2) -> None:
    """在指定的安全外圍位置重生，恢復基礎生命與完整彈匣。"""

    player.position = spawn_position.copy()
    player.spawn_position = spawn_position.copy()
    player.status = PlayerStatus.ALIVE
    player.death_timer = 0.0
    player.upgrade_stacks = 0
    player.ultimate_energy = 0.0
    player.max_health = player.base_max_health * player.health_passive_multiplier
    player.health = player.max_health
    player.ammo = player.ammo_capacity
    player.ammo_recovery_timer = 0.0
    player.primary_cooldown = 0.0
    player.tactical_cooldown = 0.0
    player.extraction_progress = 0.0
    # 重生後仍需等到上一個按鍵真正放開，避免死亡期間持續按住的
    # 普攻／大招／配件在重生同幀自動重播。
    player.ability_input_blocked = True
    clear_player_effects(player)


def update_player_timers(player: PlayerState, delta_time: float) -> None:
    """更新所有玩家短計時器；死亡倒數由 respawn_player 的呼叫端處理。"""

    dt = max(0.0, delta_time)
    player.primary_cooldown = max(0.0, player.primary_cooldown - dt)
    player.tactical_cooldown = max(0.0, player.tactical_cooldown - dt)
    player.invulnerability_timer = max(0.0, player.invulnerability_timer - dt)
    player.damage_reduction_timer = max(0.0, player.damage_reduction_timer - dt)
    player.shield_timer = max(0.0, player.shield_timer - dt)
    player.slow_timer = max(0.0, player.slow_timer - dt)
    player.root_timer = max(0.0, player.root_timer - dt)
    player.last_damage_time += dt
    if player.damage_reduction_timer <= 0:
        player.damage_reduction = 0.0
    if player.shield_timer <= 0:
        player.shield_remaining = 0.0
    if player.slow_timer <= 0:
        player.slow_multiplier = 1.0


def apply_slow(player: PlayerState | MonsterState, multiplier: float, duration: float) -> None:
    """保留較強的減速效果，避免短效果覆蓋長效果。"""

    player.slow_multiplier = min(player.slow_multiplier, max(0.0, min(1.0, multiplier)))
    player.slow_timer = max(player.slow_timer, max(0.0, duration))


def update_monster_timers(monster: MonsterState, delta_time: float) -> None:
    """更新怪物受到的減速與定身計時，讓控場效果真正影響怪物移動。"""

    dt = max(0.0, delta_time)
    monster.slow_timer = max(0.0, monster.slow_timer - dt)
    monster.root_timer = max(0.0, monster.root_timer - dt)
    if monster.slow_timer <= 0:
        monster.slow_multiplier = 1.0


def clear_monster_effects(monster: MonsterState) -> None:
    """重生時清除上一條生命留下的減速與定身狀態。"""

    monster.slow_timer = 0.0
    monster.slow_multiplier = 1.0
    monster.root_timer = 0.0


def update_extraction_progress(
    player: PlayerState,
    extraction_zone: CircleZone,
    delta_time: float,
    active: bool,
    required_time: float = config.EXTRACTION_REQUIRED_TIME,
) -> float:
    """每名玩家獨立累積撤離；離開時只將自己的進度歸零。"""

    if not active or not player.alive:
        player.extraction_progress = 0.0
    elif extraction_zone.contains(player.position):
        target_time = max(0.0, float(required_time))
        next_progress = min(
            target_time,
            player.extraction_progress + max(0.0, delta_time),
        )
        # 讓 239.99 + 0.01 這類合法邊界不因二進位浮點誤差停在
        # 9.999999...，確保時間到同幀的撤離勝負裁決可重現。
        player.extraction_progress = (
            target_time
            if next_progress >= target_time - 1e-9
            else next_progress
        )
    else:
        player.extraction_progress = 0.0
    return player.extraction_progress


def resolve_extraction_winner(
    players: list[PlayerState], required_time: float = config.EXTRACTION_REQUIRED_TIME
) -> int | None:
    """依固定玩家識別字裁決同一更新週期的多名完成者。"""

    candidates = [
        player.player_id
        for player in players
        if player.alive and player.extraction_progress >= required_time
    ]
    return min(candidates) if candidates else None


def resolve_match_timeout(match: MatchState) -> bool:
    """無勝者且時間到時切換為無人勝利；勝利狀態不會被覆蓋。"""

    if match.phase != MatchPhase.PLAYING or match.winner_id is not None:
        return False
    if match.elapsed_time < match.duration:
        return False
    match.phase = MatchPhase.NO_WINNER
    return True
