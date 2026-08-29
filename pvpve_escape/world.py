"""世界座標、地圖初始化、玩家移動與鏡頭邊界。"""

from __future__ import annotations

import math

from . import config
from .aiming import clamp_aim_endpoint
from .auto_aim import record_position_history, resolve_auto_aim
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
    MonsterBehavior,
    MonsterProjectileState,
    MonsterState,
    MonsterType,
    ObstacleKind,
    ObstacleState,
    TerrainHitResult,
    TerrainInteraction,
    PlayerState,
    TacticalId,
    Vector2,
    WorldRect,
)
from .monsters import MONSTER_SPAWN_ORDER, create_monster_state, get_monster_definition
from .navigation import find_grid_path, is_navigation_point_safe, world_to_grid
from .terrain import (
    build_terrain,
    destroy_bushes_on_segment,
    destroy_terrain_in_radius,
    first_obstacle_on_segment,
    move_circle_with_obstacles,
    resolve_dash_path,
    snapshot_obstacles,
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
    action_counts_as_attack,
    mark_player_attack,
    regenerate_player_health,
    is_visual_only_effect,
    primary_attack_active,
)
from .sprites import start_or_refresh_attack_animation, update_player_animation


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
    """建立四個生成區，每區各一隻三種怪物。"""

    offsets = (Vector2(-36, 0), Vector2(36, 0), Vector2(0, 36))
    monsters: list[MonsterState] = []
    monster_id = 0
    for zone_id, center in enumerate(get_monster_camp_points()):
        for offset, monster_type in zip(offsets, MONSTER_SPAWN_ORDER):
            spawn = center + offset
            monsters.append(create_monster_state(monster_id, zone_id, spawn, monster_type))
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
        max_health = definition.base_health * health_passive
        players.append(
            PlayerState(
                player_id=player_id,
                controller_type=ControllerType.HUMAN if player_id == 0 else ControllerType.DUMMY,
                character_id=role,
                tactical_id=tactical,
                position=spawn.copy(),
                spawn_position=spawn.copy(),
                radius=config.PLAYER_RADIUS,
                base_max_health=definition.base_health,
                health_passive_multiplier=health_passive,
                max_health=max_health,
                health=max_health,
                move_speed=config.PLAYER_BASE_SPEED * (1.15 if role == CharacterId.HUNTER else 1.0),
                ammo=definition.ammo_capacity,
                ammo_capacity=definition.ammo_capacity,
                auto_aim_enabled=config.AUTO_AIM_DEFAULT_ENABLED,
            )
        )
    obstacles, bushes = build_terrain()
    match = MatchState(
        phase=MatchPhase.PLAYING,
        duration=config.MATCH_DURATION,
        extraction_start_time=config.EXTRACTION_START_TIME,
        extraction_required_time=config.EXTRACTION_REQUIRED_TIME,
        players=players,
        monsters=create_monsters(),
        obstacles=obstacles,
        bushes=bushes,
    )
    record_position_history(match)
    match.camera.follow(players[0].position)
    return match


def update_player_movement(
    player: PlayerState,
    move_direction: Vector2,
    delta_time: float,
    obstacles: list[ObstacleState] | None = None,
) -> None:
    """更新存活玩家位置並以碰撞半徑夾制在世界邊界內。"""

    # 動畫狀態和位置使用同一個輸入與時間步長更新，但不會改寫位置以外
    # 的遊戲規則欄位；root 或死亡狀態會由動畫函式標記為非移動。
    update_player_animation(player, move_direction, delta_time)
    if not player.alive or player.root_timer > 0:
        return
    direction = move_direction.normalized()
    movement = direction * (player.move_speed * max(0.0, delta_time) * player.slow_multiplier)
    if obstacles is not None:
        player.position = move_circle_with_obstacles(player.position, movement, player.radius, obstacles)
    player.position = clamp_position(player.position, player.radius)


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


def _bounded_endpoint(
    origin: Vector2,
    direction: Vector2,
    distance: float,
    margin: float = 0.0,
) -> Vector2:
    """回傳與瞄準預覽相同的世界內有效端點。"""

    return clamp_aim_endpoint(origin, direction, max(0.0, distance), margin=margin)


def _resolve_action_path(
    match: MatchState,
    action: CombatAction,
    distance: float,
    radius: float = 0.0,
) -> tuple[TerrainHitResult, tuple[tuple[int, ObstacleKind, WorldRect], ...]]:
    """以動作政策解析路徑，並在必要時記錄施放瞬間的牆體快照。"""

    requested_distance = max(0.0, float(distance))
    bounded_end = _bounded_endpoint(action.origin, action.direction, requested_distance, radius)
    blocker_snapshot: tuple[tuple[int, ObstacleKind, WorldRect], ...] = ()
    source = match.obstacles
    if action.terrain_interaction == TerrainInteraction.BREAK_THIN_ON_PATH:
        blocker_snapshot = snapshot_obstacles(match.obstacles)
        source = blocker_snapshot
    result = first_obstacle_on_segment(action.origin, bounded_end, source, radius)
    if (
        result.obstacle is not None
        and action.terrain_interaction == TerrainInteraction.BREAK_THIN_ON_PATH
        and result.obstacle.destructible
    ):
        actual_obstacle = next(
            (
                obstacle
                for obstacle in match.obstacles
                if obstacle.obstacle_id == result.obstacle.obstacle_id
            ),
            None,
        )
        if actual_obstacle is not None:
            actual_obstacle.destroyed = True
            result.obstacle = actual_obstacle
        result.destroyed = True
    if action.terrain_interaction == TerrainInteraction.BREAK_THIN_ON_PATH:
        destroy_bushes_on_segment(action.origin, result.position, match.bushes, radius)
    return result, blocker_snapshot


def _path_end_for_action(
    match: MatchState,
    action: CombatAction,
    distance: float,
    radius: float = 0.0,
) -> tuple[Vector2, float, TerrainHitResult, tuple[tuple[int, ObstacleKind, WorldRect], ...]]:
    """回傳受世界邊界與牆體截斷的端點、距離及解析結果。"""

    result, blocker_snapshot = _resolve_action_path(match, action, distance, radius)
    return result.position.copy(), result.distance, result, blocker_snapshot


def _resolve_dash_path(
    match: MatchState,
    start: Vector2,
    direction: Vector2,
    max_distance: float,
    radius: float,
    allow_first_thin_break: bool = False,
) -> tuple[Vector2, float, TerrainHitResult | None, tuple[tuple[int, ObstacleKind, WorldRect], ...]]:
    """解析衝刺；DASH 只移除每段路徑首先遇到的薄牆並續走。"""
    current, travelled, removed_ids, last_hit = resolve_dash_path(
        start,
        direction,
        max_distance,
        radius,
        match.obstacles,
        allow_first_thin_break=allow_first_thin_break,
    )
    for obstacle in match.obstacles:
        if obstacle.obstacle_id in removed_ids and obstacle.destructible:
            obstacle.destroyed = True
    destroy_bushes_on_segment(start, current, match.bushes, radius)
    return current, travelled, last_hit, ()


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
    passive_range = float(definition.parameters.get("passive_range", 180.0))
    if definition.passive_condition == "close" and distance <= passive_range:
        damage *= definition.passive_multiplier
    elif definition.passive_condition == "far" and distance >= passive_range:
        damage *= definition.passive_multiplier
    return damage


def _knockback(match: MatchState, target_kind: str, target_id: int, origin: Vector2, distance: float) -> None:
    target = _get_target(match, target_kind, target_id)
    if target is None:
        return
    direction = (target.position - origin).normalized()
    if not direction.length():
        return
    movement = direction * max(0.0, float(distance))
    target.position = move_circle_with_obstacles(
        target.position,
        movement,
        target.radius,
        match.obstacles,
    )
    target.position = clamp_position(target.position, target.radius)


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
    obstacles: list[ObstacleState] | None = None,
    blocker_snapshot: tuple[tuple[int, ObstacleKind, WorldRect], ...] | None = None,
):
    normalized_direction = direction.normalized() if direction.length() else Vector2(1, 0)
    end = origin + normalized_direction * range_distance
    if obstacles is not None or blocker_snapshot is not None:
        source = blocker_snapshot if blocker_snapshot is not None else obstacles or []
        end = first_obstacle_on_segment(origin, end, source, width).position
    return _targets_in_segment(match, owner_id, origin, end, width)


def _targets_in_segment(
    match: MatchState,
    owner_id: int,
    start: Vector2,
    end: Vector2,
    projectile_radius: float = 0.0,
):
    """回傳線段掃掠到的目標，排序後讓飛行物先命中路徑前方者。"""

    segment = end - start
    segment_length = segment.length()
    normalized_direction = segment.normalized() if segment_length else Vector2(1, 0)
    candidates = []
    for target_kind, target_id, position, target_radius in _target_entries(match, owner_id):
        projection = (position - start).dot(normalized_direction)
        # 目標半徑與投射物半徑共同形成碰撞帶；前後端點也納入，
        # 讓高速投射物跨過目標時不會因單幀取樣漏判。
        if (
            -target_radius <= projection <= segment_length + target_radius
            and distance_to_segment(position, start, end) <= projectile_radius + target_radius
        ):
            candidates.append((projection, target_kind, target_id))
    return sorted(candidates)


def _next_effect(match: MatchState, kind: str, action: CombatAction, **kwargs) -> AbilityEffect:
    effect_values = {
        "remaining": action.duration,
        "max_distance": action.max_distance or action.range,
        "projectile_speed": action.projectile_speed,
    }
    effect_values.update(kwargs)
    position = action.origin.copy()
    metadata = dict(action.metadata)
    metadata_override = effect_values.get("metadata")
    if isinstance(metadata_override, dict):
        metadata.update(metadata_override)
    radius = float(effect_values.get("radius", action.radius))
    max_distance = float(effect_values["max_distance"])
    terrain_interaction = effect_values.get("terrain_interaction", action.terrain_interaction)
    if not isinstance(terrain_interaction, TerrainInteraction):
        terrain_interaction = TerrainInteraction(terrain_interaction)
    terrain_blocker_snapshot = effect_values.get("terrain_blocker_snapshot", ())
    if terrain_interaction == TerrainInteraction.BREAK_THIN_ON_PATH and not terrain_blocker_snapshot:
        terrain_blocker_snapshot = snapshot_obstacles(match.obstacles)
    if max_distance > 0:
        # 所有具有路徑的效果都沿同一條世界內有效射線截斷；半徑較大的
        # 投射物需要使用內縮邊界，避免中心雖在世界內但圖像／碰撞半徑穿出。
        bounded_end = _bounded_endpoint(action.origin, action.direction, max_distance, radius)
        max_distance = min(max_distance, action.origin.distance_to(bounded_end))
    effect = AbilityEffect(
        effect_id=match.next_effect_id,
        kind=kind,
        owner_id=action.owner_id,
        position=position,
        previous_position=position.copy(),
        direction=action.direction.normalized() if action.direction.length() else Vector2(1, 0),
        damage=action.damage,
        radius=radius,
        remaining=float(effect_values["remaining"]),
        max_distance=max_distance,
        projectile_speed=float(effect_values["projectile_speed"]),
        armed=bool(effect_values.get("armed", True)),
        metadata=metadata,
        origin=action.origin.copy(),
        terrain_interaction=terrain_interaction,
        terrain_blocker_snapshot=tuple(terrain_blocker_snapshot),
    )
    if "impact_position" in effect_values:
        effect.impact_position = effect_values["impact_position"]
    if "impact_status" in effect_values:
        effect.impact_status = str(effect_values["impact_status"])
    match.next_effect_id += 1
    match.effects.append(effect)
    return effect


def _apply_action(match: MatchState, action: CombatAction) -> None:
    """將角色動作轉為立即命中或短生命週期效果。"""

    owner = _get_target(match, "player", action.owner_id)
    if owner is not None and action_counts_as_attack(action):
        mark_player_attack(owner)
    # 只有成功建立的像素角色動作才進入共同攻擊動畫；蓄力、冷卻與資源
    # 仍由角色規則先行判定，這裡只接收已通過規則邊界的 CombatAction。
    if owner is not None and owner.character_id in {
        CharacterId.BREACHER,
        CharacterId.SNIPER,
    }:
        start_or_refresh_attack_animation(owner)

    if action.kind == "breach_cone":
        path_end, path_distance, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.range,
            config.BREACH_PELLET_RADIUS,
        )
        action.range = path_distance
        pellet_count = int(action.metadata.get("pellets", config.BREACH_PELLET_COUNT))
        spread_angle = float(action.metadata.get("angle", config.BREACH_CONE_ANGLE_DEGREES))
        cone_effect = _next_effect(
            match,
            "breach_cone",
            action,
            remaining=action.range / max(action.projectile_speed, 0.001) + 0.20,
            max_distance=action.range,
            projectile_speed=action.projectile_speed,
            metadata={"visual_only": 1, "path_end": path_end},
            terrain_blocker_snapshot=blocker_snapshot,
        )
        center_angle = math.atan2(action.direction.y, action.direction.x)
        divisor = max(1, pellet_count - 1)
        for index in range(pellet_count):
            offset_angle = spread_angle * (index - (pellet_count - 1) / 2) / divisor
            angle = center_angle + math.radians(offset_angle)
            pellet_direction = Vector2(math.cos(angle), math.sin(angle))
            pellet_action = CombatAction(
                kind="breach_pellet",
                owner_id=action.owner_id,
                origin=action.origin.copy(),
                direction=pellet_direction,
                damage=action.damage,
                range=action.range,
                max_distance=action.range,
                projectile_speed=action.projectile_speed,
                radius=config.BREACH_PELLET_RADIUS,
                metadata={
                    "pellet_index": index,
                    "angle": spread_angle,
                    "primary_scaling": 1,
                    "visual_parent_effect_id": cone_effect.effect_id,
                },
                terrain_interaction=TerrainInteraction.BLOCK,
            )
            _next_effect(
                match,
                "breach_pellet",
                pellet_action,
                remaining=action.range / max(action.projectile_speed, 0.001) + 0.2,
                max_distance=action.range,
                radius=config.BREACH_PELLET_RADIUS,
                terrain_blocker_snapshot=blocker_snapshot,
            )
        return
    if action.kind == "sniper_line":
        projectile_speed = max(action.projectile_speed, 0.001)
        _, path_distance, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.range,
            config.SNIPER_PROJECTILE_RADIUS,
        )
        action.range = path_distance
        _next_effect(
            match,
            "sniper_line",
            action,
            remaining=action.range / projectile_speed + 0.2,
            max_distance=action.range,
            projectile_speed=projectile_speed,
            radius=config.SNIPER_PROJECTILE_RADIUS,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "sniper_ultimate_line":
        _, action.range, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.range,
            10.0,
        )
        hits = _targets_in_line(
            match,
            action.owner_id,
            action.origin,
            action.direction,
            action.range,
            10.0,
            obstacles=match.obstacles,
        )
        for _, target_kind, target_id in hits:
            apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
        _next_effect(
            match,
            "sniper_ultimate_line",
            action,
            remaining=0.30,
            max_distance=action.range,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "guardian_arc":
        action.range = action.origin.distance_to(
            _bounded_endpoint(action.origin, action.direction, action.range)
        )
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
        _, path_distance, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.max_distance or action.range,
            config.BOOMERANG_PROJECTILE_RADIUS,
        )
        action.max_distance = path_distance
        _next_effect(
            match,
            "boomerang",
            action,
            remaining=4.0,
            max_distance=action.max_distance or action.range,
            projectile_speed=action.projectile_speed,
            radius=config.BOOMERANG_PROJECTILE_RADIUS,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "mine":
        active_mines = [effect for effect in match.effects if effect.owner_id == action.owner_id and effect.kind == "mine"]
        if len(active_mines) >= 2:
            match.effects.remove(active_mines[0])
        landing, distance, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.max_distance or action.range,
            config.MINE_PROJECTILE_RADIUS,
        )
        action.max_distance = distance
        _next_effect(
            match,
            "mine",
            action,
            remaining=action.duration,
            max_distance=distance,
            projectile_speed=action.projectile_speed,
            radius=config.MINE_PROJECTILE_RADIUS,
            armed=False,
            metadata={"slow": action.metadata.get("slow", 0.5), "slow_duration": action.metadata.get("slow_duration", 1.5), "area_radius": action.radius},
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "beam":
        _, action.range, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.range,
            16.0,
        )
        _next_effect(
            match,
            "beam",
            action,
            remaining=action.duration,
            max_distance=action.range,
            tick_timer=0.0,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind in {"breach_burst", "siphon_burst"}:
        if action.kind == "breach_burst":
            destroy_terrain_in_radius(
                action.origin,
                action.radius,
                match.obstacles,
                match.bushes,
            )
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
        landing, _, _, blocker_snapshot = _path_end_for_action(
            match,
            action,
            action.max_distance,
            owner.radius,
        )
        action.origin = start.copy()
        action.max_distance = start.distance_to(landing)
        owner.invulnerability_timer = action.duration
        owner.position = landing
        for _, target_kind, target_id in _targets_in_line(
            match,
            action.owner_id,
            start,
            action.direction,
            action.max_distance,
            28.0,
            obstacles=match.obstacles,
        ):
            apply_damage(match, action.owner_id, target_kind, target_id, _scaled_action_damage(match, action, target_kind, target_id))
        _next_effect(
            match,
            "hunter_dash",
            action,
            remaining=0.65,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "gravity_cage":
        distance = action.max_distance or action.range
        if distance > 0:
            action.origin, _, _, blocker_snapshot = _path_end_for_action(match, action, distance)
            action.max_distance = 0.0
        else:
            action.origin = clamp_position(action.origin, 0.0)
            blocker_snapshot = ()
        _next_effect(
            match,
            "gravity_cage",
            action,
            remaining=action.duration,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "tactical_dash":
        owner = _get_target(match, "player", action.owner_id)
        if owner is not None:
            action.origin = owner.position.copy()
            landing, distance, _, blocker_snapshot = _resolve_dash_path(
                match,
                action.origin,
                action.direction,
                action.max_distance,
                owner.radius,
                allow_first_thin_break=True,
            )
            action.max_distance = distance
            owner.invulnerability_timer = action.duration
            owner.position = landing
        else:
            blocker_snapshot = ()
        _next_effect(
            match,
            "dash",
            action,
            remaining=0.45,
            terrain_blocker_snapshot=blocker_snapshot,
        )
        return
    if action.kind == "tactical_shield":
        owner = _get_target(match, "player", action.owner_id)
        if owner is not None:
            owner.shield_remaining = float(action.metadata.get("absorb", 60))
            owner.shield_timer = action.duration
        _next_effect(match, "shield", action, remaining=action.duration)
        return
    if action.kind == "tactical_control":
        distance = action.max_distance or action.range
        if distance > 0:
            action.origin, _, _, blocker_snapshot = _path_end_for_action(match, action, distance)
            action.max_distance = 0.0
        else:
            action.origin = clamp_position(action.origin, 0.0)
            blocker_snapshot = ()
        _next_effect(
            match,
            "control_zone",
            action,
            remaining=action.duration,
            terrain_blocker_snapshot=blocker_snapshot,
        )


def _projectile_impact(
    match: MatchState,
    effect: AbilityEffect,
    target_kind: str,
    target_id: int,
    impact_position: Vector2,
) -> DamageEvent | None:
    """以飛行物實際掃掠位置套用一次傷害，並保存可繪製的結果。"""

    target = _get_target(match, target_kind, target_id)
    target_was_invulnerable = bool(getattr(target, "invulnerability_timer", 0.0) > 0.0)
    target_shield_before = float(getattr(target, "shield_remaining", 0.0))
    action = CombatAction(
        kind=effect.kind,
        owner_id=effect.owner_id,
        origin=effect.previous_position.copy(),
        direction=effect.direction,
        damage=effect.damage,
        range=effect.max_distance,
        projectile_speed=effect.projectile_speed,
        metadata={"primary_scaling": 1},
    )
    event = apply_damage(
        match,
        effect.owner_id,
        target_kind,
        target_id,
        _scaled_action_damage(match, action, target_kind, target_id),
    )
    effective_damage = event.effective_damage if event is not None else 0.0
    effect.position = impact_position.copy()
    effect.impact_position = impact_position.copy()
    effect.impact_status = (
        "命中"
        if effective_damage > 0.0
        else "免傷"
        if target_was_invulnerable
        else "護盾"
        if target_shield_before > 0.0
        else "無效"
    )
    # 舊版畫面測試讀取 metadata；同步保存顯式欄位與 metadata，讓資料
    # 模型已遷移後仍能相容既有畫面回歸。
    effect.metadata["impacted"] = 1
    effect.metadata["impact_target_kind"] = target_kind
    effect.metadata["impact_target_id"] = target_id
    effect.metadata["impact_effective_damage"] = effective_damage
    effect.metadata["impact_blocked"] = int(effective_damage <= 0.0)
    effect.metadata["impact_status"] = effect.impact_status
    effect.metadata["impact_position"] = impact_position.copy()
    return event


def _advance_projectile(
    effect: AbilityEffect,
    delta_time: float,
    obstacles: list[ObstacleState] | None = None,
    blocker_snapshot: tuple[tuple[int, ObstacleKind, WorldRect], ...] | None = None,
) -> tuple[Vector2, Vector2]:
    """以唯一的 projectile_speed 欄位更新飛行物，回傳本幀前後位置。"""

    previous = effect.position.copy()
    effect.previous_position = previous.copy()
    remaining_distance = max(0.0, effect.max_distance - effect.distance_travelled)
    step_distance = min(
        max(0.0, effect.projectile_speed) * max(0.0, delta_time),
        remaining_distance,
    )
    next_position = clamp_position(
        previous + effect.direction * step_distance,
        max(0.0, effect.radius),
    )
    terrain_hit = None
    if obstacles is not None or blocker_snapshot is not None:
        source = blocker_snapshot if blocker_snapshot is not None else obstacles or []
        terrain_hit = first_obstacle_on_segment(previous, next_position, source, effect.radius)
        if terrain_hit.blocked:
            next_position = terrain_hit.position.copy()
    actual_distance = previous.distance_to(next_position)
    effect.position = next_position
    effect.distance_travelled += actual_distance
    effect.metadata["visible_start"] = previous.copy()
    if terrain_hit is not None and terrain_hit.blocked:
        effect.metadata["terrain_blocked"] = 1
        effect.metadata["terrain_obstacle_id"] = terrain_hit.obstacle.obstacle_id if terrain_hit.obstacle else -1
        effect.metadata["terrain_obstacle_kind"] = terrain_hit.obstacle.kind.value if terrain_hit.obstacle else ""
        effect.metadata["impacted"] = 1
        effect.metadata["impact_target_kind"] = "terrain"
        effect.metadata["impact_target_id"] = -1
        effect.metadata["impact_blocked"] = 1
        effect.metadata["impact_status"] = "牆"
        effect.metadata["impact_position"] = next_position.copy()
        effect.impact_position = next_position.copy()
        effect.impact_status = "牆"
    return previous, next_position.copy()


def _segment_impact_position(start: Vector2, end: Vector2, projection: float) -> Vector2:
    direction = (end - start).normalized()
    return start + direction * max(0.0, min((end - start).length(), projection))


def _update_effects(match: MatchState, inputs: dict[int, InputState], delta_time: float) -> None:
    """更新飛行物、光束、地雷、護盾與持續控場效果。"""

    retained: list[AbilityEffect] = []
    projectile_kinds = {"breach_pellet", "sniper_line", "boomerang", "mine"}
    for effect in match.effects:
        owner = _get_target(match, "player", effect.owner_id)
        if owner is None or not owner.alive:
            continue
        if effect.kind in {"guardian_guard", "shield"}:
            # 防禦效果跟隨施放者；攻擊效果則固定使用自己的施放座標。
            effect.position = owner.position.copy()
        if is_visual_only_effect(effect):
            # 視覺-only 效果只更新自己的位置與壽命，絕不進入目標
            # 碰撞、傷害、控制或大招能量流程。
            effect.remaining -= delta_time
            if effect.metadata.get("terrain_blocked"):
                if effect.remaining > 0:
                    retained.append(effect)
                continue
            if effect.projectile_speed > 0.0:
                _advance_projectile(
                    effect,
                    delta_time,
                    match.obstacles,
                    effect.terrain_blocker_snapshot or None,
                )
            if effect.remaining > 0 and (
                effect.max_distance <= 0.0
                or effect.distance_travelled < effect.max_distance
            ):
                retained.append(effect)
            continue

        if effect.kind in projectile_kinds:
            effect.remaining -= delta_time
            if effect.kind in {"sniper_line", "breach_pellet"} and effect.metadata.get("impacted"):
                # 命中閃光標記固定在實際碰撞位置，不跟著目標移動。
                if effect.remaining > 0:
                    retained.append(effect)
                continue
            if effect.kind == "mine" and effect.metadata.get("triggered"):
                if effect.remaining > 0:
                    retained.append(effect)
                continue

            if effect.kind == "boomerang":
                # 去程受 max_distance 限制，回程則以施放者為目標，不能把
                # 已走完的去程距離再次當成剩餘距離，否則飛刃會停在原地。
                previous = effect.position.copy()
                effect.previous_position = previous.copy()
                if effect.returning:
                    to_owner = owner.position - previous
                    owner_distance = to_owner.length()
                    if owner_distance:
                        effect.direction = to_owner.normalized()
                    step_distance = min(
                        max(0.0, effect.projectile_speed) * max(0.0, delta_time),
                        owner_distance,
                    )
                    if owner_distance and step_distance >= owner_distance:
                        current = owner.position.copy()
                    elif owner_distance:
                        current = clamp_position(
                            previous + to_owner.normalized() * step_distance,
                            max(0.0, effect.radius),
                        )
                    else:
                        current = owner.position.copy()
                    return_terrain = first_obstacle_on_segment(
                        previous,
                        current,
                        effect.terrain_blocker_snapshot or match.obstacles,
                        effect.radius,
                    )
                    if return_terrain.blocked:
                        current = return_terrain.position.copy()
                        effect.metadata["terrain_blocked"] = 1
                        effect.metadata["terrain_obstacle_id"] = (
                            return_terrain.obstacle.obstacle_id
                            if return_terrain.obstacle is not None
                            else -1
                        )
                        effect.metadata["terrain_obstacle_kind"] = (
                            return_terrain.obstacle.kind.value
                            if return_terrain.obstacle is not None
                            else ""
                        )
                        effect.impact_position = current.copy()
                        effect.impact_status = "牆"
                        effect.remaining = min(effect.remaining, 0.14)
                    else:
                        # 擁有者若繞到牆的同一側，回程可以恢復；上一幀的
                        # 牆阻擋狀態不應讓飛刃無條件停到生命週期結束。
                        effect.metadata.pop("terrain_blocked", None)
                    effect.position = current.copy()
                    effect.metadata["visible_start"] = previous.copy()
                else:
                    previous, current = _advance_projectile(
                        effect,
                        delta_time,
                        match.obstacles,
                        effect.terrain_blocker_snapshot or None,
                    )
                candidates = _targets_in_segment(
                    match,
                    effect.owner_id,
                    previous,
                    current,
                    effect.radius,
                )
                for projection, target_kind, target_id in candidates:
                    key = (target_kind, target_id)
                    if key in effect.hit_target_ids:
                        continue
                    impact = _segment_impact_position(previous, current, projection)
                    _projectile_impact(match, effect, target_kind, target_id, impact)
                    effect.hit_target_ids.add(key)
                # 命中標記不應改變飛刃下一幀的實際飛行位置。
                effect.position = current.copy()
                effect.previous_position = previous.copy()
                if not effect.returning and effect.metadata.get("terrain_blocked"):
                    effect.max_distance = effect.distance_travelled
                    effect.returning = True
                    effect.metadata.pop("terrain_blocked", None)
                    effect.direction = (owner.position - effect.position).normalized()
                    effect.hit_target_ids.clear()
                elif effect.returning and effect.metadata.get("terrain_blocked"):
                    if effect.remaining > 0:
                        retained.append(effect)
                    continue
                elif not effect.returning and effect.distance_travelled >= effect.max_distance - 0.001:
                    effect.returning = True
                    effect.direction = (owner.position - effect.position).normalized()
                    effect.hit_target_ids.clear()
                elif effect.returning and effect.position.distance_to(owner.position) <= owner.radius + 10:
                    continue
                if effect.remaining > 0:
                    retained.append(effect)
                continue

            if effect.metadata.get("terrain_blocked"):
                if effect.kind == "mine" and not effect.armed:
                    effect.max_distance = effect.distance_travelled
                    previous = effect.position.copy()
                    current = effect.position.copy()
                elif effect.remaining > 0:
                    retained.append(effect)
                    continue
                else:
                    continue
            else:
                previous, current = _advance_projectile(
                    effect,
                    delta_time,
                    match.obstacles,
                    effect.terrain_blocker_snapshot or None,
                )
            candidates = _targets_in_segment(
                match,
                effect.owner_id,
                previous,
                current,
                effect.radius,
            )
            if effect.kind == "mine" and not effect.armed:
                # 地雷飛行中只更新位置；抵達落點後才進入 armed 狀態，
                # 因此路徑上的目標不會提前受到傷害或控制。
                if effect.distance_travelled >= effect.max_distance - 0.001:
                    effect.armed = True
                    effect.projectile_speed = 0.0
                    effect.metadata["armed"] = 1
                    effect.metadata.pop("terrain_blocked", None)
                else:
                    if effect.remaining > 0:
                        retained.append(effect)
                    continue

            if candidates and effect.kind != "mine":
                projection, target_kind, target_id = candidates[0]
                impact = _segment_impact_position(previous, current, projection)
                _projectile_impact(match, effect, target_kind, target_id, impact)
                effect.remaining = 0.12 if effect.kind == "breach_pellet" else 0.14
                retained.append(effect)
                continue

            if effect.kind == "mine" and effect.armed:
                triggered = False
                area_radius = float(effect.metadata.get("area_radius", effect.radius))
                for target_kind, target_id, position, target_radius in _target_entries(match, effect.owner_id):
                    if effect.position.distance_to(position) <= area_radius + target_radius:
                        _projectile_impact(match, effect, target_kind, target_id, effect.position.copy())
                        target = _get_target(match, target_kind, target_id)
                        if target is not None:
                            control_duration = float(effect.metadata.get("slow_duration", 1.5))
                            if owner.character_id == CharacterId.CONTROLLER:
                                control_duration = calculate_control_duration(owner, control_duration)
                            apply_slow(target, float(effect.metadata.get("slow", 0.5)), control_duration)
                        effect.metadata["triggered"] = 1
                        effect.remaining = 0.25
                        triggered = True
                        break
                if triggered:
                    retained.append(effect)
                    continue

                # 地雷落地後是持續存在的控制區，直到持續時間結束或觸發，
                # 不能沿用飛行物的 distance_travelled 結束條件立即消失。
                if effect.remaining > 0:
                    retained.append(effect)
                continue

            if effect.distance_travelled < effect.max_distance and effect.remaining > 0:
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
            mark_player_attack(owner)
            effect.remaining -= delta_time
            effect.tick_timer -= delta_time
            while effect.tick_timer <= 0 and effect.remaining > 0:
                beam_action = CombatAction(
                    kind="beam",
                    owner_id=effect.owner_id,
                    origin=effect.position.copy(),
                    direction=effect.direction,
                    damage=effect.damage,
                    range=effect.max_distance,
                    metadata={"primary_scaling": 1},
                )
                for _, target_kind, target_id in _targets_in_line(
                    match,
                    effect.owner_id,
                    effect.position,
                    effect.direction,
                    effect.max_distance,
                    16.0,
                    obstacles=match.obstacles,
                ):
                    apply_damage(match, effect.owner_id, target_kind, target_id, _scaled_action_damage(match, beam_action, target_kind, target_id))
                effect.tick_timer += float(effect.metadata.get("tick", 0.15))
            if effect.remaining > 0:
                retained.append(effect)
            continue

        effect.remaining -= delta_time
        if effect.kind in {"control_zone", "gravity_cage"}:
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


def _spawn_monster_projectile(
    match: MatchState,
    monster: MonsterState,
    target: PlayerState,
) -> None:
    definition = get_monster_definition(monster.monster_type)
    direction = (target.position - monster.position).normalized()
    if not direction.length() or definition.projectile_speed <= 0.0:
        return
    start = monster.position + direction * (monster.radius + 2.0)
    match.monster_projectiles.append(
        MonsterProjectileState(
            projectile_id=match.next_monster_projectile_id,
            source_monster_id=monster.monster_id,
            position=start.copy(),
            previous_position=start.copy(),
            direction=direction,
            damage=definition.attack_damage,
            projectile_speed=definition.projectile_speed,
            radius=definition.projectile_radius,
            max_distance=definition.projectile_range,
            remaining=definition.projectile_range / max(definition.projectile_speed, 0.001) + 0.25,
        )
    )
    match.next_monster_projectile_id += 1


def _monster_projectile_impact(
    match: MatchState,
    projectile: MonsterProjectileState,
    target: PlayerState,
    impact_position: Vector2,
) -> None:
    target_was_invulnerable = target.invulnerability_timer > 0.0
    target_shield_before = target.shield_remaining
    event = apply_damage(match, None, "player", target.player_id, projectile.damage)
    effective_damage = event.effective_damage if event is not None else 0.0
    projectile.position = impact_position.copy()
    projectile.impact_position = impact_position.copy()
    projectile.impact_target_id = target.player_id
    projectile.impact_status = (
        "命中"
        if effective_damage > 0.0
        else "免傷"
        if target_was_invulnerable
        else "護盾"
        if target_shield_before > 0.0
        else "無效"
    )
    projectile.remaining = 0.14


def _update_monster_projectiles(match: MatchState, delta_time: float) -> None:
    """更新射手怪物的慢速子彈，讓飛行路徑可被玩家讀取與閃避。"""

    retained: list[MonsterProjectileState] = []
    dt = max(0.0, delta_time)
    living_monster_ids = {monster.monster_id for monster in match.monsters if monster.alive}
    for projectile in match.monster_projectiles:
        if projectile.source_monster_id not in living_monster_ids:
            continue
        if projectile.impact_position is not None:
            projectile.remaining -= dt
            if projectile.remaining > 0.0:
                retained.append(projectile)
            continue

        projectile.remaining -= dt
        previous = projectile.position.copy()
        projectile.previous_position = previous.copy()
        remaining_distance = max(0.0, projectile.max_distance - projectile.distance_travelled)
        step_distance = min(projectile.projectile_speed * dt, remaining_distance)
        current = clamp_position(
            previous + projectile.direction * step_distance,
            max(0.0, projectile.radius),
        )
        terrain_hit = first_obstacle_on_segment(
            previous,
            current,
            match.obstacles,
            projectile.radius,
        )
        wall_distance = actual_distance = previous.distance_to(current)
        if terrain_hit.blocked:
            current = terrain_hit.position.copy()
            wall_distance = previous.distance_to(current)
        actual_distance = previous.distance_to(current)
        projectile.position = current.copy()
        projectile.distance_travelled += actual_distance

        candidates: list[tuple[float, PlayerState]] = []
        direction = (current - previous).normalized()
        for target in match.players:
            if not target.alive:
                continue
            projection = (target.position - previous).dot(direction) if direction.length() else 0.0
            if (
                -target.radius <= projection <= actual_distance + target.radius
                and projection <= wall_distance + target.radius
                and distance_to_segment(target.position, previous, current)
                <= projectile.radius + target.radius
            ):
                candidates.append((projection, target))
        if candidates:
            projection, target = min(candidates, key=lambda item: (item[0], item[1].player_id))
            impact = _segment_impact_position(previous, current, projection)
            _monster_projectile_impact(match, projectile, target, impact)
            retained.append(projectile)
            continue
        if terrain_hit.blocked:
            projectile.impact_position = current.copy()
            projectile.impact_status = "牆"
            projectile.remaining = 0.14
            retained.append(projectile)
            continue
        if projectile.distance_travelled < projectile.max_distance - 0.001 and projectile.remaining > 0.0:
            retained.append(projectile)
    match.monster_projectiles = retained


def _monster_destination(
    monster: MonsterState,
    target: PlayerState,
    obstacles: list[ObstacleState] | None = None,
) -> Vector2 | None:
    """依怪物類型取得追擊目的地；砲台蟲維持既有偏好距離策略。"""

    offset = target.position - monster.position
    distance = offset.length()
    definition = get_monster_definition(monster.monster_type)
    if distance <= config.TERRAIN_GEOMETRY_EPSILON:
        return None
    if monster.monster_type != MonsterType.SHOOTER:
        if distance <= monster.radius + target.radius:
            return None
        return target.position.copy()
    if definition.preferred_range <= 0.0:
        return target.position.copy()
    if abs(distance - definition.preferred_range) <= 36.0:
        return None
    away_from_target = (monster.position - target.position).normalized()
    if not away_from_target.length():
        away_from_target = Vector2(1.0, 0.0)
    preferred_position = target.position + away_from_target * definition.preferred_range
    if obstacles is not None and not is_navigation_point_safe(
        preferred_position,
        monster.radius,
        obstacles,
    ):
        # 偏好距離點若落在牆內，直接把牆後目標當作暫時導航終點，
        # 讓 A* 先繞過牆角；每次重算仍會重新評估偏好距離，避免卡在最近安全格。
        return target.position.copy()
    return preferred_position


def _monster_camp_center(monster: MonsterState) -> Vector2:
    """依出生區索引取得營地中心，不在怪物狀態中複製可能過期的座標。"""

    camp_index = max(0, min(monster.spawn_zone_id, len(config.MONSTER_CAMP_POINTS) - 1))
    return config.MONSTER_CAMP_POINTS[camp_index].copy()


def _clear_monster_navigation(monster: MonsterState) -> None:
    """清除路徑快取；呼叫端會在需要時立即把重算計時器歸零。"""

    monster.navigation_path.clear()
    monster.navigation_goal = None
    monster.navigation_repath_timer = 0.0


def _clear_monster_wander(monster: MonsterState) -> None:
    """清除只屬於遊蕩狀態的點與停留計時。"""

    monster.wander_target = None
    monster.wander_pause_timer = 0.0


def _set_monster_behavior(monster: MonsterState, behavior: MonsterBehavior) -> None:
    """切換狀態時清理上一種目的地，避免沿用失效的路徑或遊蕩點。"""

    if monster.behavior == behavior:
        return
    monster.behavior = behavior
    _clear_monster_navigation(monster)
    if behavior != MonsterBehavior.WANDER:
        _clear_monster_wander(monster)


def _player_by_id(match: MatchState, player_id: int | None) -> PlayerState | None:
    if player_id is None:
        return None
    return next(
        (player for player in match.players if player.player_id == player_id and player.alive),
        None,
    )


def _find_new_monster_target(
    monster: MonsterState,
    players: list[PlayerState],
    obstacles: list[ObstacleState],
) -> PlayerState | None:
    """只從存活、距離內且中心線沒有固體牆的玩家中選最近者。"""

    candidates: list[tuple[float, int, PlayerState]] = []
    for player in players:
        if not player.alive:
            continue
        distance = monster.position.distance_to(player.position)
        if distance > config.MONSTER_AGGRO_RADIUS + config.TERRAIN_GEOMETRY_EPSILON:
            continue
        if first_obstacle_on_segment(monster.position, player.position, obstacles).blocked:
            continue
        candidates.append((distance, player.player_id, player))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], item[1]))[2]


def _update_monster_target_state(
    match: MatchState,
    monster: MonsterState,
    living_players: list[PlayerState],
) -> PlayerState | None:
    """執行一次目標保留／取得／解除，維持三狀態的單向更新語意。"""

    if monster.behavior == MonsterBehavior.CHASE:
        target = _player_by_id(match, monster.target_player_id)
        if (
            target is not None
            and monster.position.distance_to(target.position)
            <= config.MONSTER_AGGRO_RADIUS + config.TERRAIN_GEOMETRY_EPSILON
        ):
            return target
        monster.target_player_id = None
        _set_monster_behavior(monster, MonsterBehavior.RETURN)
        return None

    monster.target_player_id = None
    target = _find_new_monster_target(monster, living_players, match.obstacles)
    if target is not None:
        # 只有取得目標這一刻檢查視線；進入 CHASE 後由 A* 處理牆後追擊。
        monster.target_player_id = target.player_id
        _set_monster_behavior(monster, MonsterBehavior.CHASE)
        return target

    if monster.behavior == MonsterBehavior.RETURN:
        return None

    camp = _monster_camp_center(monster)
    if monster.position.distance_to(camp) > config.MONSTER_WANDER_RADIUS + config.TERRAIN_GEOMETRY_EPSILON:
        _set_monster_behavior(monster, MonsterBehavior.RETURN)
    return None


def _refresh_monster_path(
    monster: MonsterState,
    destination: Vector2,
    obstacles: list[ObstacleState],
    force: bool = False,
    shared_cache: dict | None = None,
) -> bool:
    """在目的地格、快取不存在或重算計時器到期時建立安全節點序列。"""

    destination_cell = world_to_grid(destination)
    goal_cell = world_to_grid(monster.navigation_goal) if monster.navigation_goal is not None else None
    needs_repath = (
        force
        or monster.navigation_goal is None
        or goal_cell != destination_cell
        or monster.navigation_repath_timer <= 0.0
    )
    if not needs_repath:
        return bool(monster.navigation_path)

    result = find_grid_path(
        monster.position,
        destination,
        monster.radius,
        obstacles,
        allow_goal_fallback=monster.behavior == MonsterBehavior.CHASE,
        shared_cache=shared_cache,
    )
    monster.navigation_goal = destination.copy()
    monster.navigation_path = list(result or ())
    monster.navigation_repath_timer = (
        config.MONSTER_NAVIGATION_REPATH_INTERVAL
        if result is not None
        else config.MONSTER_NAVIGATION_RETRY_INTERVAL
    )
    return result is not None


def _refresh_monster_chase_path(
    monster: MonsterState,
    target: PlayerState,
    destination: Vector2,
    obstacles: list[ObstacleState],
    force: bool = False,
    shared_cache: dict | None = None,
) -> bool:
    """建立追擊路徑；砲台蟲偏好點不可達時改走可達的目標路線。"""

    path_ready = _refresh_monster_path(
        monster,
        destination,
        obstacles,
        force=force,
        shared_cache=shared_cache,
    )
    if path_ready:
        return True
    if (
        monster.monster_type != MonsterType.SHOOTER
        or destination.distance_to(target.position) <= config.TERRAIN_GEOMETRY_EPSILON
    ):
        return False

    # 偏好距離點可能本身安全，卻被牆封在與怪物不同的可達區域；
    # 目標位置是追擊狀態已有的合法終點，讓 A* 先繞出封閉區域。
    return _refresh_monster_path(
        monster,
        target.position,
        obstacles,
        force=True,
        shared_cache=shared_cache,
    )


def _move_monster_along_path(
    monster: MonsterState,
    delta_time: float,
    obstacles: list[ObstacleState],
    speed_ratio: float = 1.0,
) -> None:
    """沿下一個安全節點移動，實際位移仍交給既有碰撞函式。"""

    if monster.root_timer > 0.0:
        return
    tolerance = config.MONSTER_NAVIGATION_NODE_ARRIVAL_TOLERANCE
    while monster.navigation_path and monster.position.distance_to(monster.navigation_path[0]) <= tolerance:
        monster.navigation_path.pop(0)
    if not monster.navigation_path:
        return
    node = monster.navigation_path[0]
    direction = (node - monster.position).normalized()
    if not direction.length():
        monster.navigation_path.pop(0)
        return
    max_distance = max(0.0, delta_time) * monster.move_speed * max(0.0, speed_ratio) * monster.slow_multiplier
    movement = direction * min(max_distance, monster.position.distance_to(node))
    next_position = move_circle_with_obstacles(
        monster.position,
        movement,
        monster.radius,
        obstacles,
    )
    next_position = clamp_position(next_position, monster.radius)
    actual_movement = next_position - monster.position
    monster.position = next_position
    if actual_movement.length() > config.TERRAIN_GEOMETRY_EPSILON:
        monster.aim_direction = actual_movement.normalized()


def _choose_wander_target(monster: MonsterState, obstacles: list[ObstacleState]) -> Vector2 | None:
    """以怪物 ID 與序號產生可重現的營地安全候選點。"""

    camp = _monster_camp_center(monster)
    minimum_radius = 48.0
    maximum_radius = max(minimum_radius, float(config.MONSTER_WANDER_RADIUS))
    radius_span = maximum_radius - minimum_radius
    for _ in range(32):
        index = monster.wander_index
        monster.wander_index += 1
        angle_degrees = (monster.monster_id * 97 + index * 137) % 360
        radius_fraction = ((monster.monster_id * 29 + index * 71) % 997) / 996.0
        radius = minimum_radius + radius_span * radius_fraction
        angle = math.radians(angle_degrees)
        candidate = camp + Vector2(math.cos(angle) * radius, math.sin(angle) * radius)
        if (
            camp.distance_to(candidate) <= config.MONSTER_WANDER_RADIUS + config.TERRAIN_GEOMETRY_EPSILON
            and is_navigation_point_safe(candidate, monster.radius, obstacles)
        ):
            return candidate
    return None


def _update_wandering_monster(
    monster: MonsterState,
    delta_time: float,
    obstacles: list[ObstacleState],
    shared_cache: dict | None = None,
) -> None:
    """更新營地遊蕩、抵達後停留與安全候選點重試。"""

    if monster.wander_pause_timer > 0.0:
        monster.wander_pause_timer = max(0.0, monster.wander_pause_timer - delta_time)
        _clear_monster_navigation(monster)
        return

    if monster.wander_target is None:
        if monster.navigation_repath_timer > 0.0:
            return
        target = _choose_wander_target(monster, obstacles)
        if target is None:
            monster.navigation_repath_timer = config.MONSTER_NAVIGATION_RETRY_INTERVAL
            return
        monster.wander_target = target
        _clear_monster_navigation(monster)

    target = monster.wander_target
    if target is None:
        return
    _refresh_monster_path(monster, target, obstacles, shared_cache=shared_cache)
    _move_monster_along_path(
        monster,
        delta_time,
        obstacles,
        config.MONSTER_WANDER_SPEED_RATIO,
    )
    if monster.position.distance_to(target) <= config.MONSTER_NAVIGATION_NODE_ARRIVAL_TOLERANCE:
        monster.wander_target = None
        monster.wander_pause_timer = config.MONSTER_WANDER_PAUSE
        _clear_monster_navigation(monster)


def _update_returning_monster(
    monster: MonsterState,
    delta_time: float,
    obstacles: list[ObstacleState],
    allow_arrival: bool = True,
    shared_cache: dict | None = None,
) -> None:
    """沿營地中心安全路徑返營，距中心 64px 內才回到遊蕩。"""

    camp = _monster_camp_center(monster)
    if (
        allow_arrival
        and monster.position.distance_to(camp)
        <= config.MONSTER_CAMP_ARRIVAL_RADIUS + config.TERRAIN_GEOMETRY_EPSILON
    ):
        _set_monster_behavior(monster, MonsterBehavior.WANDER)
        return
    _refresh_monster_path(monster, camp, obstacles, shared_cache=shared_cache)
    _move_monster_along_path(monster, delta_time, obstacles)
    if (
        allow_arrival
        and monster.position.distance_to(camp)
        <= config.MONSTER_CAMP_ARRIVAL_RADIUS + config.TERRAIN_GEOMETRY_EPSILON
    ):
        _set_monster_behavior(monster, MonsterBehavior.WANDER)


def _reset_monster_after_respawn(match: MatchState, monster: MonsterState) -> None:
    """重生時清除上一條生命的追擊、路徑、遊蕩與牆體快取。"""

    monster.alive = True
    monster.health = monster.max_health
    monster.respawn_timer = 0.0
    monster.position = monster.spawn_position.copy()
    monster.target_player_id = None
    monster.behavior = MonsterBehavior.WANDER
    monster.navigation_path.clear()
    monster.navigation_goal = None
    monster.navigation_obstacle_signature = ()
    monster.navigation_repath_timer = 0.0
    monster.wander_target = None
    monster.wander_index = 0
    monster.wander_pause_timer = 0.0
    monster.attack_timer = 0.0
    monster.last_damage_player_id = None
    monster.aim_direction = Vector2(1.0, 0.0)
    clear_monster_effects(monster)
    match.monster_projectiles = [
        projectile
        for projectile in match.monster_projectiles
        if projectile.source_monster_id != monster.monster_id
    ]


def update_monsters(match: MatchState, delta_time: float) -> None:
    """更新牆體快照、三狀態導航、戰鬥定位與固定延遲重生。"""

    dt = max(0.0, delta_time)
    obstacle_signature = snapshot_obstacles(match.obstacles)
    living_players = [player for player in match.players if player.alive]
    if match.navigation_cache_obstacle_signature != obstacle_signature:
        match.navigation_cache.clear()
        match.navigation_cache_obstacle_signature = obstacle_signature
    navigation_cache = match.navigation_cache
    for monster in match.monsters:
        update_monster_timers(monster, dt)
        if not monster.alive:
            monster.respawn_timer -= dt
            if monster.respawn_timer <= 0.0:
                _reset_monster_after_respawn(match, monster)
            continue

        monster.attack_timer = max(0.0, monster.attack_timer - dt)
        monster.navigation_repath_timer = max(0.0, monster.navigation_repath_timer - dt)
        terrain_changed = monster.navigation_obstacle_signature != obstacle_signature
        if terrain_changed:
            # 牆體狀態只在本次更新開頭取樣；差異優先於一般 0.25 秒重算。
            _clear_monster_navigation(monster)
            monster.navigation_obstacle_signature = obstacle_signature

        previous_behavior = monster.behavior
        target = _update_monster_target_state(match, monster, living_players)
        # 先處理狀態，再決定目的地；因此舊的遊蕩點或追擊路徑不會跨狀態殘留。
        if target is not None and monster.behavior == MonsterBehavior.CHASE:
            destination = _monster_destination(monster, target, match.obstacles)
            if destination is None:
                _clear_monster_navigation(monster)
            else:
                _refresh_monster_chase_path(
                    monster,
                    target,
                    destination,
                    match.obstacles,
                    force=terrain_changed,
                    shared_cache=navigation_cache,
                )
                _move_monster_along_path(monster, dt, match.obstacles)
        elif monster.behavior == MonsterBehavior.RETURN:
            _update_returning_monster(
                monster,
                dt,
                match.obstacles,
                allow_arrival=not (
                    previous_behavior == MonsterBehavior.CHASE
                    and monster.behavior == MonsterBehavior.RETURN
                ),
                shared_cache=navigation_cache,
            )
        elif monster.behavior == MonsterBehavior.WANDER:
            _update_wandering_monster(monster, dt, match.obstacles, navigation_cache)

        # 遊蕩與返營只移動，不執行任何攻擊；只有仍鎖定的 CHASE 可進入既有戰鬥規則。
        if target is None or monster.behavior != MonsterBehavior.CHASE or not target.alive:
            continue
        definition = get_monster_definition(monster.monster_type)
        distance_after_move = monster.position.distance_to(target.position)
        if monster.monster_type == MonsterType.SHOOTER:
            if distance_after_move <= definition.attack_range and monster.attack_timer <= 0.0:
                aim_direction = (target.position - monster.position).normalized()
                if aim_direction.length():
                    monster.aim_direction = aim_direction
                _spawn_monster_projectile(match, monster, target)
                monster.attack_timer = definition.attack_interval
        elif (
            distance_after_move <= monster.radius + target.radius
            and monster.attack_timer <= 0.0
        ):
            apply_damage(match, None, "player", target.player_id, definition.attack_damage)
            monster.attack_timer = definition.attack_interval


def _remove_dead_player_effects(match: MatchState) -> None:
    """同一更新週期內死亡的玩家不得留下尚未完成的技能效果。"""

    living_player_ids = {player.player_id for player in match.players if player.alive}
    match.effects = [effect for effect in match.effects if effect.owner_id in living_player_ids]


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
            if player.death_timer <= 0.0:
                # 外部測試／開發者可以用 alive=False 暫時停用目標；沒有倒數
                # 時不應在下一幀被誤當成已完成重生。
                continue
            player.death_timer = max(0.0, player.death_timer - delta_time)
            if player.death_timer <= 0:
                respawn_player(player, player.spawn_position)


def _recover_player_ammo(
    match: MatchState,
    inputs: dict[int, InputState],
    delta_time: float,
) -> None:
    """在本幀攻擊、效果與怪物傷害都結算後，統一處理彈藥恢復。"""

    for player in match.players:
        definition = get_character_definition(player.character_id)
        input_state = inputs.get(player.player_id, InputState())
        recover_ammo(
            player,
            delta_time,
            definition.ammo_recovery_interval,
            blocked=primary_attack_active(player, input_state.primary_held),
        )


def _recover_player_health(match: MatchState, delta_time: float) -> None:
    """在本幀所有受擊結算後統一處理戰鬥外生命恢復。"""

    for player in match.players:
        regenerate_player_health(player, delta_time)


def _cast_requested(input_state: InputState, slot: str) -> bool:
    """只把放開邊緣視為長按技能的施放；單幀 pressed 仍代表快速點按。"""

    released = bool(getattr(input_state, f"{slot}_released", False))
    pressed = bool(getattr(input_state, f"{slot}_pressed", False))
    held = bool(getattr(input_state, f"{slot}_held", False))
    return released or (pressed and not held)


def _remove_siphoner_beam(match: MatchState, player_id: int) -> None:
    """移除吸能者當前引導，避免失焦或死亡後光束殘留。"""

    match.effects = [
        effect
        for effect in match.effects
        if not (
            effect.owner_id == player_id
            and effect.kind == "beam"
            and not effect.metadata.get("one_shot")
        )
    ]


def _resolve_human_aim(
    match: MatchState,
    player: PlayerState,
    ability_slot: str,
    manual_direction: Vector2,
):
    """在施放端使用與畫面預覽相同的歷史位置自動瞄準結果。"""

    result = resolve_auto_aim(
        match,
        player,
        ability_slot,
        manual_direction,
        obstacles=match.obstacles,
    )
    player.aim_direction = result.direction
    return result


def _handle_human_actions(match: MatchState, human_input: InputState, delta_time: float) -> None:
    if not match.players:
        return
    player = match.players[0]
    if human_input.auto_aim_toggle_pressed:
        player.auto_aim_enabled = not player.auto_aim_enabled
    if not player.alive:
        player.ability_input_blocked = True
        player.primary_charge = 0.0
        _remove_siphoner_beam(match, player.player_id)
        return
    manual_direction = (
        human_input.aim_direction.normalized()
        if human_input.aim_direction.length()
        else player.aim_direction
    )
    player.aim_direction = manual_direction
    update_player_movement(player, human_input.move_direction, delta_time, match.obstacles)
    if human_input.focus_lost:
        player.ability_input_blocked = True
        player.primary_charge = 0.0
        _remove_siphoner_beam(match, player.player_id)
        return
    if player.ability_input_blocked:
        if not (human_input.primary_held or human_input.ultimate_held or human_input.tactical_held):
            player.ability_input_blocked = False
            player.primary_charge = 0.0
            _remove_siphoner_beam(match, player.player_id)
            return
        else:
            return
    definition = get_character_definition(player.character_id)
    if player.character_id == CharacterId.SNIPER:
        if human_input.primary_held:
            _resolve_human_aim(match, player, "primary", manual_direction)
            charge_limit = float(definition.parameters.get("charge", 0.6))
            player.primary_charge = min(charge_limit, player.primary_charge + delta_time)
        elif _cast_requested(human_input, "primary"):
            aim = _resolve_human_aim(match, player, "primary", manual_direction)
            action = create_primary_action(player, aim.direction, player.primary_charge, aim.target_distance)
            if action is not None:
                action.metadata["primary_scaling"] = 1
                _apply_action(match, action)
            player.primary_charge = 0.0
        elif not human_input.primary_held:
            player.primary_charge = 0.0
    elif player.character_id == CharacterId.SIPHONER:
        has_beam = any(effect.owner_id == player.player_id and effect.kind == "beam" for effect in match.effects)
        if not human_input.primary_held:
            _remove_siphoner_beam(match, player.player_id)
        else:
            aim = _resolve_human_aim(match, player, "primary", manual_direction)
            if not has_beam:
                action = create_primary_action(player, aim.direction, target_distance=aim.target_distance)
            else:
                action = None
            if action is not None:
                action.metadata["primary_scaling"] = 1
                _apply_action(match, action)
    elif _cast_requested(human_input, "primary"):
        aim = _resolve_human_aim(match, player, "primary", manual_direction)
        action = create_primary_action(player, aim.direction, target_distance=aim.target_distance)
        if action is not None:
            action.metadata["primary_scaling"] = 1
            _apply_action(match, action)
    if _cast_requested(human_input, "ultimate"):
        aim = _resolve_human_aim(match, player, "ultimate", manual_direction)
        action = create_ultimate_action(player, aim.direction, aim.target_distance)
        if action is not None:
            _apply_action(match, action)
    if _cast_requested(human_input, "tactical"):
        aim = _resolve_human_aim(match, player, "tactical", manual_direction)
        action = create_tactical_action(player, aim.direction, human_input.move_direction, aim.target_distance)
        if action is not None:
            _apply_action(match, action)


def update_world(match: MatchState, inputs: dict[int, InputState], delta_time: float) -> None:
    """依固定順序更新時間、生命週期、玩家動作、技能、怪物、撤離與勝負。"""

    if match.phase != MatchPhase.PLAYING:
        return
    # 建局後第一幀才正式開始取樣；這也讓開發者／測試在開局前調整出生位置
    # 時，不會被 create_match 當下的舊快照覆蓋。
    if match.elapsed_time <= 0.0:
        record_position_history(match, 0.0)
    previous_elapsed = max(0.0, min(match.duration, match.elapsed_time))
    if previous_elapsed >= match.duration:
        # 時間已經結束的狀態不應再接受一幀輸入；只補做一次最終勝負裁決。
        winner_id = (
            resolve_extraction_winner(match.players, match.extraction_required_time)
            if previous_elapsed >= match.extraction_start_time
            else None
        )
        if winner_id is not None:
            match.winner_id = winner_id
            match.phase = MatchPhase.VICTORY
        else:
            resolve_match_timeout(match)
        update_camera(match)
        return

    dt = max(0.0, min(config.MAX_DELTA_TIME, delta_time))
    dt = min(dt, match.duration - previous_elapsed)
    match.elapsed_time = previous_elapsed + dt
    _update_player_lifecycle(match, dt)
    _handle_human_actions(match, inputs.get(0, InputState()), dt)
    _update_effects(match, inputs, dt)
    update_monsters(match, dt)
    _update_monster_projectiles(match, dt)
    _recover_player_health(match, dt)
    _recover_player_ammo(match, inputs, dt)
    _remove_dead_player_effects(match)
    extraction_active = match.elapsed_time >= match.extraction_start_time
    extraction_dt = (
        dt
        if previous_elapsed >= match.extraction_start_time
        else max(0.0, match.elapsed_time - match.extraction_start_time)
    )
    for player in match.players:
        update_extraction_progress(
            player,
            match.extraction_zone,
            extraction_dt,
            extraction_active,
            match.extraction_required_time,
        )
    winner_id = resolve_extraction_winner(match.players, match.extraction_required_time) if extraction_active else None
    if winner_id is not None:
        match.winner_id = winner_id
        match.phase = MatchPhase.VICTORY
    else:
        resolve_match_timeout(match)
    record_position_history(match)
    update_camera(match)


def update_match(match: MatchState, human_input: InputState, delta_time: float) -> None:
    """主迴圈使用的人類輸入包裝入口；假玩家由固定零輸入規則處理。"""

    update_world(match, {0: human_input}, delta_time)
