"""世界座標、地圖初始化、玩家移動與鏡頭邊界。"""

from __future__ import annotations

import math

from . import config
from .characters import (
    calculate_attack_damage,
    calculate_control_duration,
    create_primary_action,
    create_tactical_action,
    create_ultimate_action,
    get_character_definition,
)
from .controllers import InputState
from .models import (
    AbilityEffect,
    CharacterId,
    CombatAction,
    ControllerType,
    DamageEvent,
    MatchPhase,
    MatchState,
    MonsterState,
    PlayerState,
    TacticalId,
    Vector2,
)
from .rules import (
    add_ultimate_energy,
    apply_damage_to_monster,
    apply_damage_to_player,
    apply_slow,
    clear_monster_effects,
    handle_player_death,
    make_damage_event,
    recover_ammo,
    respawn_player,
    resolve_extraction_winner,
    resolve_match_timeout,
    update_monster_timers,
    update_extraction_progress,
    update_player_timers,
)


def clamp_position(position: Vector2, radius: float = config.PLAYER_RADIUS) -> Vector2:
    """將物件中心限制在世界矩形內，保留半徑避免穿出邊界。"""

    return Vector2(
        max(radius, min(position.x, config.WORLD_WIDTH - radius)),
        max(radius, min(position.y, config.WORLD_HEIGHT - radius)),
    )


def world_to_screen(position: Vector2, camera_position: Vector2) -> Vector2:
    """將世界座標減去鏡頭左上角，轉為畫面座標。"""

    return position - camera_position


def screen_to_world(position: Vector2, camera_position: Vector2) -> Vector2:
    """將畫面座標加上鏡頭左上角，轉回世界座標。"""

    return position + camera_position


def get_spawn_points() -> tuple[Vector2, ...]:
    return tuple(point.copy() for point in config.SPAWN_POINTS)


def get_monster_camp_points() -> tuple[Vector2, ...]:
    return tuple(point.copy() for point in config.MONSTER_CAMP_POINTS)


def create_monsters() -> list[MonsterState]:
    """建立四個生成區、每區三隻基礎近戰怪物。"""

    offsets = (Vector2(-36, 0), Vector2(36, 0), Vector2(0, 36))
    monsters: list[MonsterState] = []
    monster_id = 0
    for zone_id, center in enumerate(get_monster_camp_points()):
        for offset in offsets:
            spawn = center + offset
            monsters.append(
                MonsterState(
                    monster_id=monster_id,
                    spawn_zone_id=zone_id,
                    position=spawn.copy(),
                    spawn_position=spawn.copy(),
                    radius=config.MONSTER_RADIUS,
                    max_health=config.MONSTER_HEALTH,
                    health=config.MONSTER_HEALTH,
                    move_speed=config.MONSTER_SPEED,
                )
            )
            monster_id += 1
    return monsters


def create_match(
    selected_character: CharacterId = CharacterId.BREACHER,
    selected_tactical: TacticalId = TacticalId.DASH,
) -> MatchState:
    """建立一場 1 名人類加 5 名固定假玩家的可玩比賽。"""

    # 延遲匯入避免角色設定與世界初始化互相匯入。
    from .characters import get_character_definition

    roles = list(CharacterId)
    remaining_roles = [role for role in roles if role != selected_character]
    tactical_order = list(TacticalId)
    spawn_points = get_spawn_points()
    players: list[PlayerState] = []
    for player_id in range(config.PLAYER_COUNT):
        role = selected_character if player_id == 0 else remaining_roles[player_id - 1]
        tactical = selected_tactical if player_id == 0 else tactical_order[(player_id - 1) % len(tactical_order)]
        definition = get_character_definition(role)
        health_passive = 1.2 if role == CharacterId.GUARDIAN else 1.0
        spawn = spawn_points[player_id]
        max_health = config.PLAYER_BASE_HEALTH * health_passive
        players.append(
            PlayerState(
                player_id=player_id,
                controller_type=ControllerType.HUMAN if player_id == 0 else ControllerType.DUMMY,
                character_id=role,
                tactical_id=tactical,
                position=spawn.copy(),
                spawn_position=spawn.copy(),
                radius=config.PLAYER_RADIUS,
                base_max_health=config.PLAYER_BASE_HEALTH,
                health_passive_multiplier=health_passive,
                max_health=max_health,
                health=max_health,
                move_speed=config.PLAYER_BASE_SPEED * (1.15 if role == CharacterId.HUNTER else 1.0),
                ammo=definition.ammo_capacity,
                ammo_capacity=definition.ammo_capacity,
            )
        )
    match = MatchState(
        phase=MatchPhase.PLAYING,
        duration=config.MATCH_DURATION,
        extraction_start_time=config.EXTRACTION_START_TIME,
        extraction_required_time=config.EXTRACTION_REQUIRED_TIME,
        players=players,
        monsters=create_monsters(),
    )
    match.camera.follow(players[0].position)
    return match


def update_player_movement(player: PlayerState, move_direction: Vector2, delta_time: float) -> None:
    """更新存活玩家位置並以碰撞半徑夾制在世界邊界內。"""

    if not player.alive or player.root_timer > 0:
        return
    direction = move_direction.normalized()
    player.position = clamp_position(
        player.position + direction * (player.move_speed * max(0.0, delta_time) * player.slow_multiplier),
        player.radius,
    )


def update_camera(match: MatchState) -> None:
    """鏡頭只跟隨人類玩家，並由 Camera.clamp 保護世界邊界。"""

    if match.players:
        match.camera.follow(match.players[0].position)


def distance_to_segment(point: Vector2, start: Vector2, end: Vector2) -> float:
    """計算點到線段的距離，用於直線射擊與突進命中判定。"""

    segment = end - start
    length_squared = segment.dot(segment)
    if length_squared == 0:
        return point.distance_to(start)
    projection = max(0.0, min(1.0, (point - start).dot(segment) / length_squared))
    closest = start + segment * projection
    return point.distance_to(closest)


def _target_entries(match: MatchState, owner_id: int):
    """依序提供所有可被技能命中的存活玩家與怪物。"""

    for player in match.players:
        if player.player_id != owner_id and player.alive:
            yield "player", player.player_id, player.position, player.radius
    for monster in match.monsters:
        if monster.alive:
            yield "monster", monster.monster_id, monster.position, monster.radius


def _get_target(match: MatchState, target_kind: str, target_id: int):
    if target_kind == "player":
        return next((player for player in match.players if player.player_id == target_id), None)
    return next((monster for monster in match.monsters if monster.monster_id == target_id), None)


def apply_damage(
    match: MatchState,
    source_player_id: int | None,
    target_kind: str,
    target_id: int,
    raw_damage: float,
) -> DamageEvent | None:
    """套用傷害、能量與怪物最後一擊規則，回傳可追蹤事件。"""

    target = _get_target(match, target_kind, target_id)
    if target is None:
        return None
    if target_kind == "player":
        effective_damage = apply_damage_to_player(target, raw_damage)
    else:
        effective_damage = apply_damage_to_monster(target, raw_damage)
    event = make_damage_event(
        match.next_event_sequence,
        source_player_id,
        target_id,
        raw_damage,
        effective_damage,
        match.elapsed_time,
        target_kind,
    )
    match.next_event_sequence += 1
    if source_player_id is not None and effective_damage > 0:
        source = _get_target(match, "player", source_player_id)
        if source is not None:
            energy_multiplier = 1.0
            if source.character_id == CharacterId.SIPHONER and target_kind == "monster":
                energy_multiplier = 1.25
            add_ultimate_energy(source, effective_damage, energy_multiplier)
    if target_kind == "monster" and effective_damage > 0:
        target.last_damage_player_id = source_player_id
        if not target.alive and source_player_id is not None:
            source = _get_target(match, "player", source_player_id)
            if source is not None:
                from .rules import apply_monster_kill_upgrade

                apply_monster_kill_upgrade(source)
    return event


def _scaled_action_damage(match: MatchState, action: CombatAction, target_kind: str, target_id: int) -> float:
    owner = _get_target(match, "player", action.owner_id)
    if owner is None:
        return action.damage
    target = _get_target(match, target_kind, target_id)
    distance = owner.position.distance_to(target.position) if target is not None else action.range
    if action.metadata.get("primary_scaling"):
        return calculate_attack_damage(owner, distance, target_kind)
    from .rules import calculate_upgrade_multiplier

    damage = action.damage * calculate_upgrade_multiplier(owner.upgrade_stacks)
    definition = get_character_definition(owner.character_id)
    if definition.passive_condition == "close" and distance <= 180.0:
        damage *= definition.passive_multiplier
    elif definition.passive_condition == "far" and distance >= 450.0:
        damage *= definition.passive_multiplier
    return damage


def _knockback(match: MatchState, target_kind: str, target_id: int, origin: Vector2, distance: float) -> None:
    target = _get_target(match, target_kind, target_id)
    if target is None:
        return
    direction = (target.position - origin).normalized()
    target.position = clamp_position(target.position + direction * distance, target.radius)


def _targets_in_radius(match: MatchState, owner_id: int, center: Vector2, radius: float):
    for target_kind, target_id, position, target_radius in _target_entries(match, owner_id):
        if center.distance_to(position) <= radius + target_radius:
            yield target_kind, target_id, position, target_radius


def _targets_in_line(
    match: MatchState,
    owner_id: int,
    origin: Vector2,
    direction: Vector2,
    range_distance: float,
    width: float = 14.0,
):
    normalized_direction = direction.normalized() if direction.length() else Vector2(1, 0)
    end = origin + normalized_direction * range_distance
    candidates = []
    for target_kind, target_id, position, target_radius in _target_entries(match, owner_id):
        projection = (position - origin).dot(normalized_direction)
        # 端點也要包含目標半徑，否則子彈已與目標重疊但目標中心尚未進入
        # 本幀線段時，會出現圖顯命中卻沒有傷害的錯誤。
        if -target_radius <= projection <= range_distance + target_radius and distance_to_segment(position, origin, end) <= width + target_radius:
            candidates.append((projection, target_kind, target_id))
    return sorted(candidates)


def _next_effect(match: MatchState, kind: str, action: CombatAction, **kwargs) -> AbilityEffect:
    effect_values = {
        "remaining": action.duration,
        "max_distance": action.max_distance or action.range,
        "speed": float(action.metadata.get("speed", 0.0)),
    }
    effect_values.update(kwargs)
    effect = AbilityEffect(
        effect_id=match.next_effect_id,
        kind=kind,
        owner_id=action.owner_id,
        position=action.origin.copy(),
        direction=action.direction.normalized() if action.direction.length() else Vector2(1, 0),
        damage=action.damage,
        radius=float(effect_values.get("radius", action.radius)),
        remaining=float(effect_values["remaining"]),
        max_distance=float(effect_values["max_distance"]),
        speed=float(effect_values["speed"]),
        metadata=dict(action.metadata),
    )
    match.next_effect_id += 1
    match.effects.append(effect)
    return effect


def _apply_action(match: MatchState, action: CombatAction) -> None:
    """將角色動作轉為立即命中或短生命週期效果。"""

    if action.kind == "breach_cone":
        half_angle = math.radians(float(action.metadata.get("angle", 60)) / 2)
        for target_kind, target_id, position, _ in _target_entries(match, action.owner_id):
            offset = position - action.origin
            if offset.length() <= action.range and offset.length() > 0:
                angle = math.acos(max(-1.0, min(1.0, action.direction.dot(offset.normalized()))))
                if angle <= half_angle:
                    for _ in range(int(action.metadata.get("pellets", 5))):
                        apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
        _next_effect(match, "breach_cone", action, remaining=0.45, max_distance=action.range)
        return
    if action.kind == "sniper_line":
        projectile_speed = config.SNIPER_PROJECTILE_SPEED
        _next_effect(
            match,
            "sniper_line",
            action,
            remaining=action.range / projectile_speed + 0.2,
            max_distance=action.range,
            speed=projectile_speed,
            radius=config.SNIPER_PROJECTILE_RADIUS,
        )
        return
    if action.kind == "sniper_ultimate_line":
        hits = _targets_in_line(match, action.owner_id, action.origin, action.direction, action.range, 10.0)
        for _, target_kind, target_id in hits:
            apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
        _next_effect(match, "sniper_ultimate_line", action, remaining=0.30, max_distance=action.range)
        return
    if action.kind == "guardian_arc":
        half_angle = math.radians(float(action.metadata.get("angle", 100)) / 2)
        for target_kind, target_id, position, _ in _target_entries(match, action.owner_id):
            offset = position - action.origin
            if 0 < offset.length() <= action.range:
                angle = math.acos(max(-1.0, min(1.0, action.direction.dot(offset.normalized()))))
                if angle <= half_angle:
                    apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
                    _knockback(match, target_kind, target_id, action.origin, float(action.metadata.get("knockback", 120)))
        _next_effect(match, "guardian_arc", action, remaining=0.45, max_distance=action.range)
        return
    if action.kind == "boomerang":
        _next_effect(match, "boomerang", action, remaining=4.0, max_distance=action.max_distance, speed=520.0)
        return
    if action.kind == "mine":
        active_mines = [effect for effect in match.effects if effect.owner_id == action.owner_id and effect.kind == "mine"]
        if len(active_mines) >= 2:
            match.effects.remove(active_mines[0])
        _next_effect(match, "mine", action, remaining=action.duration)
        return
    if action.kind == "beam":
        _next_effect(match, "beam", action, remaining=action.duration, max_distance=action.range, tick_timer=0.0)
        return
    if action.kind in {"breach_burst", "siphon_burst"}:
        total_effective = 0.0
        for target_kind, target_id, _, _ in list(_targets_in_radius(match, action.owner_id, action.origin, action.radius)):
            event = apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
            if event is not None:
                total_effective += event.effective_damage
            if action.kind == "breach_burst":
                _knockback(match, target_kind, target_id, action.origin, float(action.metadata.get("knockback", 120)))
        if action.kind == "siphon_burst":
            owner = _get_target(match, "player", action.owner_id)
            if owner is not None:
                owner.health = min(owner.max_health, owner.health + total_effective * float(action.metadata.get("heal_ratio", 0.5)))
        _next_effect(match, action.kind, action, remaining=0.65)
        return
    if action.kind == "guardian_guard":
        owner = _get_target(match, "player", action.owner_id)
        if owner is not None:
            owner.damage_reduction = float(action.metadata.get("reduction", 0.7))
            owner.damage_reduction_timer = action.duration
        _next_effect(match, "guardian_guard", action, remaining=action.duration)
        return
    if action.kind == "hunter_dash":
        owner = _get_target(match, "player", action.owner_id)
        if owner is None:
            return
        start = owner.position.copy()
        owner.invulnerability_timer = action.duration
        owner.position = clamp_position(start + action.direction * action.max_distance, owner.radius)
        for _, target_kind, target_id in _targets_in_line(match, action.owner_id, start, action.direction, action.max_distance, 28.0):
            apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
        _next_effect(match, "hunter_dash", action, remaining=0.65)
        return
    if action.kind == "gravity_cage":
        _next_effect(match, "gravity_cage", action, remaining=action.duration)
        return
    if action.kind == "tactical_dash":
        owner = _get_target(match, "player", action.owner_id)
        if owner is not None:
            owner.invulnerability_timer = action.duration
            owner.position = clamp_position(owner.position + action.direction * action.max_distance, owner.radius)
        _next_effect(match, "dash", action, remaining=0.45)
        return
    if action.kind == "tactical_shield":
        owner = _get_target(match, "player", action.owner_id)
        if owner is not None:
            owner.shield_remaining = float(action.metadata.get("absorb", 60))
            owner.shield_timer = action.duration
        _next_effect(match, "shield", action, remaining=action.duration)
        return
    if action.kind == "tactical_control":
        _next_effect(match, "control_zone", action, remaining=action.duration)


def _update_effects(match: MatchState, inputs: dict[int, InputState], delta_time: float) -> None:
    """更新狙擊投射物、回旋飛刃、地雷、光束與持續控場效果。"""

    retained: list[AbilityEffect] = []
    for effect in match.effects:
        owner = _get_target(match, "player", effect.owner_id)
        if owner is None or not owner.alive:
            continue
        if effect.kind in {"breach_cone", "guardian_arc"}:
            # 短暫命中特效以施放者目前位置為錨點，避免鏡頭跟隨移動時看起來漂移。
            effect.position = owner.position.copy()
        if effect.kind in {"guardian_guard", "shield"}:
            effect.position = owner.position.copy()
        if effect.kind == "sniper_line":
            effect.remaining -= delta_time
            if effect.metadata.get("impacted"):
                # 命中閃光固定在傷害事件發生的位置，不跟著目標移動，避免
                # 目標離開後畫面仍顯示「正在命中」但生命不再變化。
                if effect.remaining > 0:
                    retained.append(effect)
                continue

            previous_position = effect.position.copy()
            step_distance = min(
                effect.speed * max(0.0, delta_time),
                max(0.0, effect.max_distance - effect.distance_travelled),
            )
            effect.position += effect.direction * step_distance
            effect.distance_travelled += step_distance
            # 讓繪製的子彈線段與本次碰撞掃掠使用完全相同的起點與終點。
            effect.metadata["visible_start"] = previous_position.copy()

            candidates = _targets_in_line(
                match,
                effect.owner_id,
                previous_position,
                effect.direction,
                step_distance,
                effect.radius,
            )
            if candidates:
                _, target_kind, target_id = candidates[0]
                impact_target = _get_target(match, target_kind, target_id)
                damage_action = CombatAction(
                    "sniper_line",
                    effect.owner_id,
                    previous_position,
                    effect.direction,
                    effect.damage,
                    range=effect.max_distance,
                    metadata={"primary_scaling": 1},
                )
                target_was_invulnerable = bool(
                    getattr(impact_target, "invulnerability_timer", 0.0) > 0
                )
                target_shield_before = float(
                    getattr(impact_target, "shield_remaining", 0.0)
                )
                event = apply_damage(
                    match,
                    effect.owner_id,
                    target_kind,
                    target_id,
                    _scaled_action_damage(match, damage_action, target_kind, target_id),
                )
                if impact_target is not None:
                    effect.position = impact_target.position.copy()
                effect.metadata["impacted"] = 1
                effect.metadata["impact_target_kind"] = target_kind
                effect.metadata["impact_target_id"] = target_id
                effective_damage = event.effective_damage if event is not None else 0.0
                effect.metadata["impact_effective_damage"] = effective_damage
                effect.metadata["impact_blocked"] = int(effective_damage <= 0.0)
                if effective_damage > 0.0:
                    effect.metadata["impact_status"] = "命中"
                elif target_was_invulnerable:
                    effect.metadata["impact_status"] = "免傷"
                elif target_shield_before > 0.0:
                    effect.metadata["impact_status"] = "護盾"
                else:
                    effect.metadata["impact_status"] = "無效"
                effect.remaining = 0.14
                retained.append(effect)
            elif effect.distance_travelled < effect.max_distance and effect.remaining > 0:
                retained.append(effect)
            continue
        if effect.kind == "beam":
            owner_input = inputs.get(effect.owner_id)
            if owner_input is None:
                continue
            if not owner_input.primary_held and not effect.metadata.get("one_shot"):
                continue
            effect.position = owner.position.copy()
            effect.direction = owner.aim_direction.normalized() if owner.aim_direction.length() else effect.direction
            effect.remaining -= delta_time
            effect.tick_timer -= delta_time
            while effect.tick_timer <= 0 and effect.remaining > -0.01:
                for _, target_kind, target_id in _targets_in_line(match, effect.owner_id, effect.position, effect.direction, effect.max_distance, 16.0):
                    apply_damage(match, effect.owner_id, target_kind, target_id, _scaled_action_damage(match, CombatAction("beam", effect.owner_id, effect.position, effect.direction, effect.damage, range=effect.max_distance, metadata={"primary_scaling": 1}), target_kind, target_id))
                effect.tick_timer += float(effect.metadata.get("tick", 0.15))
            if effect.remaining > 0:
                retained.append(effect)
            continue
        effect.remaining -= delta_time
        if effect.kind == "boomerang":
            if not effect.returning:
                step = effect.direction * (effect.speed * delta_time)
                effect.position += step
                effect.distance_travelled += step.length()
                if effect.distance_travelled >= effect.max_distance:
                    effect.returning = True
                    effect.direction = (owner.position - effect.position).normalized()
                    effect.hit_target_ids.clear()
            else:
                effect.direction = (owner.position - effect.position).normalized()
                effect.position += effect.direction * (effect.speed * delta_time)
                if effect.position.distance_to(owner.position) <= owner.radius + 10:
                    continue
            for target_kind, target_id, position, target_radius in _target_entries(match, effect.owner_id):
                key = (target_kind, target_id)
                if key not in effect.hit_target_ids and effect.position.distance_to(position) <= 22 + target_radius:
                    action = CombatAction("boomerang", effect.owner_id, effect.position, effect.direction, effect.damage, metadata={"primary_scaling": 1})
                    apply_damage(match, effect.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
                    effect.hit_target_ids.add(key)
        elif effect.kind == "mine":
            triggered = False
            for target_kind, target_id, position, target_radius in _target_entries(match, effect.owner_id):
                if effect.position.distance_to(position) <= effect.radius + target_radius:
                    action = CombatAction("mine", effect.owner_id, effect.position, effect.direction, effect.damage, metadata={"primary_scaling": 1})
                    apply_damage(match, effect.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
                    target = _get_target(match, target_kind, target_id)
                    if target is not None:
                        control_duration = float(effect.metadata.get("slow_duration", 1.5))
                        if owner.character_id == CharacterId.CONTROLLER:
                            control_duration = calculate_control_duration(owner, control_duration)
                        apply_slow(target, float(effect.metadata.get("slow", 0.5)), control_duration)
                    triggered = True
                    break
            if triggered:
                continue
        elif effect.kind in {"control_zone", "gravity_cage"}:
            for target_kind, target_id, position, target_radius in _target_entries(match, effect.owner_id):
                if effect.position.distance_to(position) <= effect.radius + target_radius:
                    target = _get_target(match, target_kind, target_id)
                    if target is None:
                        continue
                    apply_slow(target, float(effect.metadata.get("slow", 0.6)), effect.remaining)
                    if effect.kind == "gravity_cage":
                        target.root_timer = max(target.root_timer, float(effect.metadata.get("root", 0.75)))
        if effect.remaining > 0:
            retained.append(effect)
    match.effects = retained


def update_monsters(match: MatchState, delta_time: float) -> None:
    """更新近戰怪物追擊、接觸傷害與固定延遲重生。"""

    dt = max(0.0, delta_time)
    for monster in match.monsters:
        update_monster_timers(monster, dt)
        if not monster.alive:
            monster.respawn_timer -= dt
            if monster.respawn_timer <= 0:
                monster.alive = True
                monster.health = monster.max_health
                monster.position = monster.spawn_position.copy()
                monster.target_player_id = None
                monster.attack_timer = 0.0
                monster.last_damage_player_id = None
                clear_monster_effects(monster)
            continue
        living_players = [player for player in match.players if player.alive]
        if not living_players:
            continue
        target = min(living_players, key=lambda player: monster.position.distance_to(player.position))
        monster.target_player_id = target.player_id
        offset = target.position - monster.position
        distance = offset.length()
        if distance > monster.radius + target.radius and monster.root_timer <= 0:
            monster.position = clamp_position(
                monster.position + offset.normalized() * monster.move_speed * dt * monster.slow_multiplier,
                monster.radius,
            )
        monster.attack_timer -= dt
        if monster.position.distance_to(target.position) <= monster.radius + target.radius and monster.attack_timer <= 0:
            apply_damage(match, None, "player", target.player_id, config.MONSTER_CONTACT_DAMAGE)
            monster.attack_timer = config.MONSTER_ATTACK_INTERVAL


def place_dummy_in_extraction(match: MatchState) -> None:
    """開發者模式把選定假玩家放入中央撤離區，不改寫撤離規則。"""

    dummy_id = match.developer_mode.selected_dummy_id
    player = _get_target(match, "player", dummy_id)
    if player is not None and player.alive and player.controller_type == ControllerType.DUMMY:
        player.position = match.extraction_zone.center.copy()
        player.developer_placed = True
        player.extraction_progress = 0.0


def return_dummy_to_spawn(match: MatchState) -> None:
    """將開發者模式選定假玩家送回自己的外圍出生點。"""

    dummy_id = match.developer_mode.selected_dummy_id
    player = _get_target(match, "player", dummy_id)
    if player is not None and player.alive and player.controller_type == ControllerType.DUMMY:
        player.position = player.spawn_position.copy()
        player.developer_placed = False
        player.extraction_progress = 0.0


def _update_player_lifecycle(match: MatchState, delta_time: float) -> None:
    for player in match.players:
        update_player_timers(player, delta_time)
        if not player.alive:
            player.death_timer = max(0.0, player.death_timer - delta_time)
            if player.death_timer <= 0:
                respawn_player(player, player.spawn_position)
                continue
        definition = get_character_definition(player.character_id)
        recover_ammo(player, delta_time, definition.ammo_recovery_interval)


def _handle_human_actions(match: MatchState, human_input: InputState, delta_time: float) -> None:
    if not match.players:
        return
    player = match.players[0]
    if not player.alive:
        return
    player.aim_direction = human_input.aim_direction.normalized() if human_input.aim_direction.length() else player.aim_direction
    update_player_movement(player, human_input.move_direction, delta_time)
    definition = get_character_definition(player.character_id)
    if player.character_id == CharacterId.SNIPER:
        if human_input.primary_held:
            player.primary_charge += delta_time
            if player.primary_charge >= float(definition.parameters.get("charge", 0.6)):
                action = create_primary_action(player, player.aim_direction, player.primary_charge)
                if action is not None:
                    action.metadata["primary_scaling"] = 1
                    _apply_action(match, action)
                player.primary_charge = 0.0
        elif human_input.primary_pressed:
            action = create_primary_action(player, player.aim_direction, 0.0)
            if action is not None:
                action.metadata["primary_scaling"] = 1
                _apply_action(match, action)
        else:
            player.primary_charge = 0.0
    elif player.character_id == CharacterId.SIPHONER:
        has_beam = any(effect.owner_id == player.player_id and effect.kind == "beam" for effect in match.effects)
        if not human_input.primary_held:
            match.effects = [
                effect
                for effect in match.effects
                if not (
                    effect.owner_id == player.player_id
                    and effect.kind == "beam"
                    and not effect.metadata.get("one_shot")
                )
            ]
            if human_input.primary_pressed:
                action = create_primary_action(player, player.aim_direction)
                if action is not None:
                    action.metadata["primary_scaling"] = 1
                    action.metadata["one_shot"] = 1
                    _apply_action(match, action)
        elif not has_beam:
            action = create_primary_action(player, player.aim_direction)
            if action is not None:
                action.metadata["primary_scaling"] = 1
                _apply_action(match, action)
    elif human_input.primary_held or human_input.primary_pressed:
        action = create_primary_action(player, player.aim_direction)
        if action is not None:
            action.metadata["primary_scaling"] = 1
            _apply_action(match, action)
    if human_input.ultimate_pressed:
        action = create_ultimate_action(player, player.aim_direction)
        if action is not None:
            _apply_action(match, action)
    if human_input.tactical_pressed:
        action = create_tactical_action(player, player.aim_direction, human_input.move_direction)
        if action is not None:
            _apply_action(match, action)


def update_world(match: MatchState, inputs: dict[int, InputState], delta_time: float) -> None:
    """依固定順序更新時間、生命週期、玩家動作、技能、怪物、撤離與勝負。"""

    if match.phase != MatchPhase.PLAYING:
        return
    dt = max(0.0, min(config.MAX_DELTA_TIME, delta_time))
    match.elapsed_time = min(match.duration, match.elapsed_time + dt)
    _update_player_lifecycle(match, dt)
    _handle_human_actions(match, inputs.get(0, InputState()), dt)
    _update_effects(match, inputs, dt)
    update_monsters(match, dt)
    extraction_active = match.elapsed_time >= match.extraction_start_time
    for player in match.players:
        update_extraction_progress(
            player,
            match.extraction_zone,
            dt,
            extraction_active,
            match.extraction_required_time,
        )
    winner_id = resolve_extraction_winner(match.players, match.extraction_required_time) if extraction_active else None
    if winner_id is not None:
        match.winner_id = winner_id
        match.phase = MatchPhase.VICTORY
    else:
        resolve_match_timeout(match)
    update_camera(match)


def update_match(match: MatchState, human_input: InputState, delta_time: float) -> None:
    """主迴圈使用的人類輸入包裝入口；假玩家由固定零輸入規則處理。"""

    update_world(match, {0: human_input}, delta_time)
