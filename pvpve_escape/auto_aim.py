"""可配置的輕度自動瞄準。

自動瞄準只在施放當下解析一次方向。為了保留閃避空間，目標點不是
當前位置，而是 ``AUTO_AIM_LOOKBACK_SECONDS`` 秒前的位置；投射物離手後
不會追蹤目標。
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from . import config
from .characters import get_character_definition, get_tactical_definition
from .models import (
    CharacterId,
    MatchState,
    ObstacleState,
    PlayerState,
    TacticalId,
    Vector2,
)
from .terrain import first_obstacle_on_segment


@dataclass
class AutoAimResult:
    """一次自動瞄準解析的結果；不會把目標鎖成追蹤彈。"""

    direction: Vector2
    manual_direction: Vector2
    target_kind: str | None = None
    target_id: int | None = None
    target_position: Vector2 | None = None
    target_distance: float | None = None
    lookback_seconds: float = 0.0

    @property
    def has_target(self) -> bool:
        return self.target_kind is not None and self.target_id is not None


def _safe_direction(direction: Vector2) -> Vector2:
    normalized = direction.normalized()
    return normalized if normalized.length() else Vector2(1.0, 0.0)


def _entity_position(match: MatchState, target_kind: str, target_id: int) -> Vector2 | None:
    if target_kind == "player":
        target = next((player for player in match.players if player.player_id == target_id), None)
    else:
        target = next((monster for monster in match.monsters if monster.monster_id == target_id), None)
    position = getattr(target, "position", None)
    return position.copy() if isinstance(position, Vector2) else None


def record_position_history(match: MatchState, timestamp: float | None = None) -> None:
    """保存目前所有目標的位置，並限制歷史長度避免每局無限增長。"""

    sample_time = match.elapsed_time if timestamp is None else max(0.0, float(timestamp))
    keep_seconds = max(1.0, float(config.AUTO_AIM_LOOKBACK_SECONDS) + 0.5)
    cutoff = sample_time - keep_seconds
    entities = [
        ("player", player.player_id, player.position)
        for player in match.players
    ] + [
        ("monster", monster.monster_id, monster.position)
        for monster in match.monsters
    ]
    for target_kind, target_id, position in entities:
        key = (target_kind, target_id)
        samples = match.position_history.setdefault(key, [])
        if samples and abs(samples[-1][0] - sample_time) <= 1e-9:
            samples[-1] = (sample_time, position.copy())
        else:
            samples.append((sample_time, position.copy()))
        match.position_history[key] = [sample for sample in samples if sample[0] >= cutoff]


def historical_position(
    match: MatchState,
    target_kind: str,
    target_id: int,
    target_time: float,
) -> Vector2 | None:
    """以線性插值取得某個時間點的位置，缺資料時退回目前位置。"""

    samples = match.position_history.get((target_kind, target_id), [])
    if not samples:
        return _entity_position(match, target_kind, target_id)
    if target_time <= samples[0][0]:
        return samples[0][1].copy()
    if target_time >= samples[-1][0]:
        return samples[-1][1].copy()
    for (previous_time, previous_position), (next_time, next_position) in zip(samples, samples[1:]):
        if previous_time <= target_time <= next_time:
            interval = next_time - previous_time
            if interval <= 1e-9:
                return next_position.copy()
            ratio = (target_time - previous_time) / interval
            return previous_position + (next_position - previous_position) * ratio
    return samples[-1][1].copy()


def _is_target_bearing(player: PlayerState, ability_slot: str) -> bool:
    slot = ability_slot.lower()
    if slot == "primary":
        return True
    if slot == "ultimate":
        return player.character_id in {
            CharacterId.SNIPER,
            CharacterId.HUNTER,
            CharacterId.CONTROLLER,
        }
    if slot == "tactical":
        return player.tactical_id == TacticalId.CONTROL
    return False


def _target_range(player: PlayerState, ability_slot: str) -> float:
    slot = ability_slot.lower()
    definition = get_character_definition(player.character_id)
    if slot == "primary":
        return float(definition.primary_range)
    if slot == "ultimate":
        if player.character_id == CharacterId.SNIPER:
            return float(definition.parameters.get("ultimate_range", 1100.0))
        if player.character_id == CharacterId.HUNTER:
            return float(definition.parameters.get("ultimate_distance", 360.0))
        if player.character_id == CharacterId.CONTROLLER:
            return 220.0
    if slot == "tactical":
        tactical = get_tactical_definition(player.tactical_id)
        return float(tactical.parameters.get("radius", 100.0))
    return 0.0


def resolve_auto_aim(
    match: MatchState,
    player: PlayerState,
    ability_slot: str,
    manual_direction: Vector2,
    *,
    enabled: bool | None = None,
    obstacles: Iterable[ObstacleState] | None = None,
) -> AutoAimResult:
    """解析最近且在扇形內、未被目前牆體阻擋的目標。"""

    manual = _safe_direction(manual_direction if manual_direction.length() else player.aim_direction)
    auto_aim_enabled = player.auto_aim_enabled if enabled is None else bool(enabled)
    lookback = max(0.0, float(config.AUTO_AIM_LOOKBACK_SECONDS))
    result = AutoAimResult(
        direction=manual,
        manual_direction=manual,
        lookback_seconds=lookback,
    )
    if not auto_aim_enabled or not _is_target_bearing(player, ability_slot):
        return result

    max_range = _target_range(player, ability_slot)
    if max_range <= 0.0:
        return result
    obstacle_list = tuple(obstacles) if obstacles is not None else None
    target_time = match.elapsed_time - lookback
    half_angle = math.radians(max(0.0, float(config.AUTO_AIM_HALF_ANGLE_DEGREES)))
    candidates: list[tuple[int, int, str, Vector2]] = []

    for target in match.players:
        if target.player_id == player.player_id or not target.alive:
            continue
        target_position = (
            target.position.copy()
            if lookback <= config.GEOMETRY_EPSILON
            else historical_position(match, "player", target.player_id, target_time)
        )
        if target_position is None:
            continue
        candidates.append((0, target.player_id, "player", target_position))
    for target in match.monsters:
        if not target.alive:
            continue
        target_position = (
            target.position.copy()
            if lookback <= config.GEOMETRY_EPSILON
            else historical_position(match, "monster", target.monster_id, target_time)
        )
        if target_position is None:
            continue
        candidates.append((1, target.monster_id, "monster", target_position))

    valid_candidates: list[tuple[float, int, int, str, Vector2]] = []
    for kind_order, target_id, target_kind, target_position in candidates:
        offset = target_position - player.position
        distance = offset.length()
        if distance <= 1e-9 or distance > max_range + config.GEOMETRY_EPSILON:
            continue
        angle = math.acos(
            max(-1.0, min(1.0, manual.dot(offset / distance)))
        )
        if angle <= half_angle + config.GEOMETRY_EPSILON:
            if obstacle_list is not None:
                terrain_hit = first_obstacle_on_segment(
                    player.position,
                    target_position,
                    obstacle_list,
                )
                # 目標正好站在牆前接觸面時，牆命中點就是目標端點，
                # 仍可被視為可達；只有牆在目標之前才排除自動瞄準。
                if terrain_hit.blocked and terrain_hit.distance < distance - config.GEOMETRY_EPSILON:
                    continue
            valid_candidates.append((distance, kind_order, target_id, target_kind, target_position))

    if not valid_candidates:
        return result
    distance, _kind_order, target_id, target_kind, target_position = min(valid_candidates)
    result.target_kind = target_kind
    result.target_id = target_id
    result.target_position = target_position.copy()
    result.target_distance = distance
    result.direction = _safe_direction(target_position - player.position)
    return result
