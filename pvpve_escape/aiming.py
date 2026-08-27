"""建立不依賴 Pygame 的瞄準預覽幾何。"""

from __future__ import annotations

import math

from . import config
from .characters import get_character_definition, get_tactical_definition
from .models import AimGuide, CharacterId, PlayerState, TacticalId, Vector2


def _safe_direction(direction: Vector2) -> Vector2:
    normalized = direction.normalized()
    return normalized if normalized.length() else Vector2(1.0, 0.0)


def clamp_world_point(point: Vector2, margin: float = 0.0) -> Vector2:
    """將預覽點限制在世界矩形內，避免顯示可操作的世界外區域。"""

    safe_margin = min(
        max(0.0, float(margin)),
        min(config.WORLD_WIDTH, config.WORLD_HEIGHT) / 2,
    )
    return Vector2(
        max(safe_margin, min(point.x, config.WORLD_WIDTH - safe_margin)),
        max(safe_margin, min(point.y, config.WORLD_HEIGHT - safe_margin)),
    )


def clamp_aim_endpoint(
    origin: Vector2,
    direction: Vector2,
    distance: float,
    world_width: float = config.WORLD_WIDTH,
    world_height: float = config.WORLD_HEIGHT,
    margin: float = 0.0,
) -> Vector2:
    """沿射線取最遠端點，並在抵達世界邊界時提前截斷。

    ``margin`` 讓投射物或角色本體保留碰撞半徑；更新與繪製可因此
    使用同一個世界內縮矩形，避免斜向接近邊界時被軸向夾制改變路徑。
    """

    safe_margin = min(
        max(0.0, float(margin)),
        min(float(world_width), float(world_height)) / 2,
    )
    min_x, max_x = safe_margin, max(safe_margin, world_width - safe_margin)
    min_y, max_y = safe_margin, max(safe_margin, world_height - safe_margin)
    start = Vector2(
        max(min_x, min(origin.x, max_x)),
        max(min_y, min(origin.y, max_y)),
    )
    heading = _safe_direction(direction)
    max_distance = max(0.0, distance)
    boundary_distance = max_distance
    if heading.x > 0:
        boundary_distance = min(boundary_distance, (max_x - start.x) / heading.x)
    elif heading.x < 0:
        boundary_distance = min(boundary_distance, (min_x - start.x) / heading.x)
    if heading.y > 0:
        boundary_distance = min(boundary_distance, (max_y - start.y) / heading.y)
    elif heading.y < 0:
        boundary_distance = min(boundary_distance, (min_y - start.y) / heading.y)
    return Vector2(
        max(min_x, min(max_x, start.x + heading.x * max(0.0, boundary_distance))),
        max(min_y, min(max_y, start.y + heading.y * max(0.0, boundary_distance))),
    )


def _rotate(direction: Vector2, angle_degrees: float) -> Vector2:
    angle = math.radians(angle_degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return Vector2(
        direction.x * cosine - direction.y * sine,
        direction.x * sine + direction.y * cosine,
    ).normalized()


def _guide(
    player: PlayerState,
    ability_slot: str,
    shape: str,
    direction: Vector2,
    end: Vector2,
    *,
    range_distance: float = 0.0,
    radius: float = 0.0,
    angle_degrees: float = 0.0,
    path_points: tuple[Vector2, ...] = (),
    valid: bool = True,
) -> AimGuide:
    return AimGuide(
        owner_id=player.player_id,
        ability_slot=ability_slot,
        shape=shape,
        origin=clamp_world_point(player.position),
        direction=direction,
        end=clamp_world_point(end),
        range=range_distance,
        radius=radius,
        angle_degrees=angle_degrees,
        path_points=tuple(clamp_world_point(point) for point in path_points),
        valid=valid,
    )


def build_aim_guide(
    player: PlayerState,
    ability_slot: str,
    aim_direction: Vector2,
    valid: bool = True,
    move_direction: Vector2 | None = None,
) -> AimGuide:
    """依角色與技能欄位建立一份不會修改玩家狀態的預覽資料。

    衝刺配件與實際施放共用移動方向優先規則；其他技能忽略
    ``move_direction``，仍只沿瞄準方向預覽。
    """

    slot = ability_slot.lower()
    if slot not in {"primary", "ultimate", "tactical"}:
        raise ValueError(f"unknown ability slot: {ability_slot}")
    direction = _safe_direction(aim_direction if aim_direction.length() else player.aim_direction)
    origin = clamp_world_point(player.position)
    character = get_character_definition(player.character_id)

    if slot == "primary":
        if player.character_id == CharacterId.BREACHER:
            distance = config.BREACH_CONE_RANGE
            half_angle = config.BREACH_CONE_ANGLE_DEGREES / 2.0
            pellet_count = config.BREACH_PELLET_COUNT
            divisor = max(1, pellet_count - 1)
            endpoints = tuple(
                clamp_world_point(
                    clamp_aim_endpoint(
                        origin,
                        _rotate(
                            direction,
                            -half_angle + config.BREACH_CONE_ANGLE_DEGREES * index / divisor,
                        ),
                        distance,
                        margin=config.BREACH_PELLET_RADIUS,
                    ),
                )
                for index in range(pellet_count)
            )
            return _guide(
                player,
                slot,
                "wedge",
                direction,
                endpoints[pellet_count // 2],
                range_distance=distance,
                angle_degrees=config.BREACH_CONE_ANGLE_DEGREES,
                path_points=endpoints,
                valid=valid,
            )
        if player.character_id == CharacterId.SNIPER:
            end = clamp_aim_endpoint(
                origin,
                direction,
                character.primary_range,
                margin=config.SNIPER_PROJECTILE_RADIUS,
            )
            return _guide(player, slot, "line", direction, end, range_distance=character.primary_range, valid=valid)
        if player.character_id == CharacterId.GUARDIAN:
            end = clamp_aim_endpoint(origin, direction, character.primary_range)
            return _guide(player, slot, "wedge", direction, end, range_distance=character.primary_range, angle_degrees=100.0, valid=valid)
        if player.character_id == CharacterId.HUNTER:
            end = clamp_aim_endpoint(
                origin,
                direction,
                character.primary_range,
                margin=config.BOOMERANG_PROJECTILE_RADIUS,
            )
            return _guide(player, slot, "path", direction, end, range_distance=character.primary_range, path_points=(origin, end, origin), valid=valid)
        if player.character_id == CharacterId.CONTROLLER:
            end = clamp_aim_endpoint(
                origin,
                direction,
                character.primary_range,
                margin=config.MINE_PROJECTILE_RADIUS,
            )
            return _guide(player, slot, "circle", direction, end, range_distance=character.primary_range, radius=100.0, valid=valid)
        end = clamp_aim_endpoint(origin, direction, character.primary_range)
        return _guide(player, slot, "beam", direction, end, range_distance=character.primary_range, valid=valid)

    if slot == "ultimate":
        if player.character_id == CharacterId.BREACHER:
            return _guide(player, slot, "circle", direction, origin, radius=190.0, valid=valid)
        if player.character_id == CharacterId.SNIPER:
            end = clamp_aim_endpoint(origin, direction, 1100.0)
            return _guide(player, slot, "line", direction, end, range_distance=1100.0, valid=valid)
        if player.character_id == CharacterId.GUARDIAN:
            return _guide(player, slot, "circle", direction, origin, radius=38.0, valid=valid)
        if player.character_id == CharacterId.HUNTER:
            end = clamp_aim_endpoint(
                origin,
                direction,
                360.0,
                margin=config.PLAYER_RADIUS,
            )
            return _guide(player, slot, "path", direction, end, range_distance=360.0, path_points=(origin, end), valid=valid)
        if player.character_id == CharacterId.CONTROLLER:
            end = clamp_aim_endpoint(origin, direction, 220.0)
            return _guide(player, slot, "circle", direction, end, radius=190.0, valid=valid)
        return _guide(player, slot, "circle", direction, origin, radius=220.0, valid=valid)

    tactical = get_tactical_definition(player.tactical_id)
    if player.tactical_id == TacticalId.DASH:
        if move_direction is not None and move_direction.length():
            direction = _safe_direction(move_direction)
        distance = float(tactical.parameters.get("distance", 220.0))
        end = clamp_aim_endpoint(
            origin,
            direction,
            distance,
            margin=config.PLAYER_RADIUS,
        )
        return _guide(player, slot, "path", direction, end, range_distance=distance, path_points=(origin, end), valid=valid)
    if player.tactical_id == TacticalId.SHIELD:
        return _guide(player, slot, "circle", direction, origin, radius=36.0, valid=valid)
    distance = float(tactical.parameters.get("radius", 100.0))
    end = clamp_aim_endpoint(origin, direction, distance)
    return _guide(player, slot, "circle", direction, end, range_distance=distance, radius=100.0, valid=valid)
