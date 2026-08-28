"""固定地形的純 Python 資料、碰撞、路徑與破壞輔助函式。"""

from __future__ import annotations

from collections.abc import Iterable
import math

from . import config
from .models import (
    BushState,
    ObstacleKind,
    ObstacleState,
    PlayerState,
    TerrainHitResult,
    Vector2,
    WorldRect,
)


TerrainObstacle = ObstacleState | tuple[int, ObstacleKind | str, WorldRect]
TerrainLayoutEntry = tuple[str | ObstacleKind, float, float, float, float]
NormalizedTerrainCell = tuple[str, int, int]

_TERRAIN_PRIORITY = {
    "bush": 1,
    ObstacleKind.THIN_WALL.value: 2,
    ObstacleKind.THICK_WALL.value: 3,
}


def _layout_kind_value(kind: str | ObstacleKind) -> str:
    return kind.value if isinstance(kind, ObstacleKind) else str(kind)


def _cell_coordinates(start: float, end: float, limit: int) -> range:
    """將一段布局邊界轉成世界內的完整地形格座標。"""

    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        return range(0, 0)
    cell_size = config.TERRAIN_CELL_SIZE
    first = math.floor(start / cell_size) * cell_size
    last = math.ceil(end / cell_size) * cell_size
    first = max(0, min(limit, first))
    last = max(0, min(limit, last))
    if last <= first:
        return range(0, 0)
    return range(first, last, cell_size)


def normalize_layout(layout: Iterable[TerrainLayoutEntry]) -> list[NormalizedTerrainCell]:
    """正規化布局、展開單格並按厚牆／薄牆／草叢優先級去除重疊。"""

    occupied: dict[tuple[int, int], tuple[int, str]] = {}
    for kind, left, top, width, height in layout:
        kind_value = _layout_kind_value(kind)
        if kind_value not in _TERRAIN_PRIORITY:
            raise ValueError(f"未知地形類型：{kind_value}")
        try:
            raw_left = float(left)
            raw_top = float(top)
            raw_right = raw_left + float(width)
            raw_bottom = raw_top + float(height)
        except (TypeError, ValueError):
            continue
        for cell_top in _cell_coordinates(raw_top, raw_bottom, config.WORLD_HEIGHT):
            for cell_left in _cell_coordinates(raw_left, raw_right, config.WORLD_WIDTH):
                key = (cell_left, cell_top)
                priority = _TERRAIN_PRIORITY[kind_value]
                current = occupied.get(key)
                if current is None or priority > current[0]:
                    occupied[key] = (priority, kind_value)

    return [
        (kind, left, top)
        for (left, top), (_, kind) in occupied.items()
    ]


def _normalized_layout() -> list[NormalizedTerrainCell]:
    """合併牆與草叢原始矩形，提供所有正式建立入口共用的結果。"""

    layout: list[TerrainLayoutEntry] = [
        (kind, left, top, width, height)
        for kind, left, top, width, height in config.OBSTACLE_LAYOUT
    ]
    layout.extend(
        ("bush", left, top, width, height)
        for left, top, width, height in config.BUSH_LAYOUT
    )
    return normalize_layout(layout)


def _build_terrain_states() -> tuple[list[ObstacleState], list[BushState]]:
    normalized = _normalized_layout()
    obstacles: list[ObstacleState] = []
    bushes: list[BushState] = []
    for kind, left, top in normalized:
        bounds = WorldRect(left, top, config.TERRAIN_CELL_SIZE, config.TERRAIN_CELL_SIZE)
        if kind == "bush":
            bushes.append(BushState(bush_id=len(bushes), bounds=bounds))
        else:
            obstacles.append(
                ObstacleState(
                    obstacle_id=len(obstacles),
                    kind=ObstacleKind(kind),
                    bounds=bounds,
                )
            )
    return obstacles, bushes


def create_obstacles() -> list[ObstacleState]:
    """依固定配置建立一場比賽專用的牆體狀態。"""

    obstacles, _ = _build_terrain_states()
    return obstacles


def create_bushes() -> list[BushState]:
    """依固定配置建立一場比賽專用的草叢狀態。"""

    _, bushes = _build_terrain_states()
    return bushes


def build_terrain() -> tuple[list[ObstacleState], list[BushState]]:
    """建立全新的牆體與草叢清單，確保每場比賽狀態互不污染。"""

    return _build_terrain_states()


def create_terrain() -> tuple[list[ObstacleState], list[BushState]]:
    """build_terrain 的語意別名，方便建立端使用較直觀的名稱。"""

    return build_terrain()


def _as_obstacle(value: TerrainObstacle, fallback_id: int = 0) -> ObstacleState:
    if isinstance(value, ObstacleState):
        return value
    obstacle_id, kind, bounds = value
    return ObstacleState(
        obstacle_id=int(obstacle_id if obstacle_id is not None else fallback_id),
        kind=ObstacleKind(kind),
        bounds=bounds,
    )


def _solid_obstacles(obstacles: Iterable[TerrainObstacle]) -> Iterable[ObstacleState]:
    for index, value in enumerate(obstacles):
        obstacle = _as_obstacle(value, index)
        if obstacle.solid:
            yield obstacle


def inflate_rect(rect: WorldRect, radius: float) -> WorldRect:
    """向外膨脹矩形，將圓形物件轉成中心點碰撞。"""

    safe_radius = max(0.0, float(radius))
    return WorldRect(
        rect.left - safe_radius,
        rect.top - safe_radius,
        rect.width + safe_radius * 2,
        rect.height + safe_radius * 2,
    )


def _circle_rect_distance_squared(center: Vector2, rect: WorldRect) -> float:
    """回傳圓心到軸對齊矩形最近點的距離平方。"""

    closest_x = max(rect.left, min(center.x, rect.right))
    closest_y = max(rect.top, min(center.y, rect.bottom))
    dx = center.x - closest_x
    dy = center.y - closest_y
    return dx * dx + dy * dy


def circle_intersects_rect(center: Vector2, radius: float, rect: WorldRect) -> bool:
    """以最近點距離檢查圓形和軸對齊矩形是否接觸或重疊。"""

    safe_radius = max(0.0, float(radius))
    return _circle_rect_distance_squared(center, rect) <= safe_radius * safe_radius + config.TERRAIN_GEOMETRY_EPSILON


def _segment_entry_fraction(start: Vector2, end: Vector2, rect: WorldRect) -> float | None:
    """回傳線段第一次進入矩形的比例；沒有相交時回傳 None。"""

    delta = end - start
    enter = 0.0
    exit = 1.0
    epsilon = config.TERRAIN_GEOMETRY_EPSILON

    for origin, movement, lower, upper in (
        (start.x, delta.x, rect.left, rect.right),
        (start.y, delta.y, rect.top, rect.bottom),
    ):
        if abs(movement) <= epsilon:
            if origin < lower - epsilon or origin > upper + epsilon:
                return None
            continue
        first = (lower - origin) / movement
        last = (upper - origin) / movement
        if first > last:
            first, last = last, first
        enter = max(enter, first)
        exit = min(exit, last)
        if enter > exit + epsilon:
            return None

    if exit < -epsilon or enter > 1.0 + epsilon:
        return None
    return max(0.0, min(1.0, enter))


def _entry_is_real(start: Vector2, end: Vector2, rect: WorldRect, fraction: float) -> bool:
    """排除從牆面邊界沿外側離開時的假命中。"""

    if fraction > config.TERRAIN_GEOMETRY_EPSILON:
        return True
    strict_epsilon = max(config.TERRAIN_GEOMETRY_EPSILON * 10, 1e-5)
    if (
        rect.left + strict_epsilon < start.x < rect.right - strict_epsilon
        and rect.top + strict_epsilon < start.y < rect.bottom - strict_epsilon
    ):
        return True
    delta = end - start
    delta_length = delta.length()
    if delta_length <= config.TERRAIN_GEOMETRY_EPSILON:
        return False
    sample = start + delta * min(1.0, strict_epsilon * 2 / delta_length)
    # 起點恰好落在膨脹矩形邊界時，只有下一個微小樣本仍進入矩形，
    # 才算是朝牆內的命中；沿外側離開不可把邊界接觸誤判成阻擋。
    return (
        rect.left + strict_epsilon < sample.x < rect.right - strict_epsilon
        and rect.top + strict_epsilon < sample.y < rect.bottom - strict_epsilon
    )


def first_obstacle_on_segment(
    start: Vector2,
    end: Vector2,
    obstacles: Iterable[TerrainObstacle],
    radius: float = 0.0,
) -> TerrainHitResult:
    """找出線段上第一面尚未破壞的牆，並回傳牆前端點。"""

    delta = end - start
    segment_length = delta.length()
    best: tuple[float, int, ObstacleState] | None = None
    for obstacle in _solid_obstacles(obstacles):
        expanded = inflate_rect(obstacle.bounds, radius)
        fraction = _segment_entry_fraction(start, end, expanded)
        if fraction is None or not _entry_is_real(start, end, expanded, fraction):
            continue
        candidate = (fraction, obstacle.obstacle_id, obstacle)
        if best is None or candidate[:2] < best[:2]:
            best = candidate

    if best is None:
        return TerrainHitResult(
            distance=segment_length,
            position=end.copy(),
            blocked=False,
        )

    fraction, _, obstacle = best
    position = start + delta * fraction
    return TerrainHitResult(
        obstacle=obstacle,
        distance=segment_length * fraction,
        position=position,
        blocked=True,
    )


def resolve_path_endpoint(
    origin: Vector2,
    direction: Vector2,
    max_distance: float,
    obstacles: Iterable[TerrainObstacle],
    radius: float = 0.0,
    blocker_snapshot: Iterable[TerrainObstacle] | None = None,
) -> TerrainHitResult:
    """沿方向解析最遠端點，遇牆時停在第一面牆前。"""

    heading = direction.normalized()
    safe_heading = heading if heading.length() else Vector2(1.0, 0.0)
    distance = max(0.0, float(max_distance))
    end = origin + safe_heading * distance
    source = blocker_snapshot if blocker_snapshot is not None else obstacles
    return first_obstacle_on_segment(origin, end, source, radius)


def _bounded_path_endpoint(origin: Vector2, direction: Vector2, distance: float, radius: float = 0.0) -> Vector2:
    """取世界內縮邊界內的路徑端點，供純地形 DASH 解析與瞄準共用。"""

    safe_margin = min(
        max(0.0, float(radius)),
        min(float(config.WORLD_WIDTH), float(config.WORLD_HEIGHT)) / 2,
    )
    min_x, max_x = safe_margin, max(safe_margin, config.WORLD_WIDTH - safe_margin)
    min_y, max_y = safe_margin, max(safe_margin, config.WORLD_HEIGHT - safe_margin)
    start = Vector2(
        max(min_x, min(origin.x, max_x)),
        max(min_y, min(origin.y, max_y)),
    )
    heading = direction.normalized() if direction.length() else Vector2(1.0, 0.0)
    boundary_distance = max(0.0, float(distance))
    if heading.x > 0:
        boundary_distance = min(boundary_distance, (max_x - start.x) / heading.x)
    elif heading.x < 0:
        boundary_distance = min(boundary_distance, (min_x - start.x) / heading.x)
    if heading.y > 0:
        boundary_distance = min(boundary_distance, (max_y - start.y) / heading.y)
    elif heading.y < 0:
        boundary_distance = min(boundary_distance, (min_y - start.y) / heading.y)
    safe_distance = max(0.0, boundary_distance)
    return Vector2(
        max(min_x, min(max_x, start.x + heading.x * safe_distance)),
        max(min_y, min(max_y, start.y + heading.y * safe_distance)),
    )


def resolve_dash_path(
    start: Vector2,
    direction: Vector2,
    max_distance: float,
    radius: float,
    obstacles: Iterable[TerrainObstacle],
    allow_first_thin_break: bool = True,
) -> tuple[Vector2, float, tuple[int, ...], TerrainHitResult | None]:
    """以不改寫狀態的方式模擬 DASH，回傳端點、距離與虛擬移除牆 ID。"""

    heading = direction.normalized() if direction.length() else Vector2(1.0, 0.0)
    requested_distance = max(0.0, float(max_distance))
    current = start.copy()
    remaining = requested_distance
    travelled = 0.0
    virtual_obstacles = list(obstacles)
    removed_ids: list[int] = []
    last_hit: TerrainHitResult | None = None
    epsilon = max(config.TERRAIN_GEOMETRY_EPSILON, 1e-5)

    while remaining > epsilon:
        end = _bounded_path_endpoint(current, heading, remaining, radius)
        segment_distance = current.distance_to(end)
        if segment_distance <= epsilon:
            break
        hit = first_obstacle_on_segment(current, end, virtual_obstacles, radius)
        if not hit.blocked:
            current = end
            travelled += segment_distance
            break

        last_hit = hit
        if (
            allow_first_thin_break
            and not removed_ids
            and hit.obstacle is not None
            and hit.obstacle.destructible
        ):
            removed_ids.append(hit.obstacle.obstacle_id)
            virtual_obstacles = [
                obstacle
                for obstacle in virtual_obstacles
                if _as_obstacle(obstacle).obstacle_id != hit.obstacle.obstacle_id
            ]
            current = hit.position.copy()
            travelled += hit.distance
            remaining = max(0.0, remaining - hit.distance)
            continue

        current = hit.position.copy()
        travelled += hit.distance
        break

    return current, travelled, tuple(removed_ids), last_hit


def _move_axis(
    position: Vector2,
    delta: Vector2,
    radius: float,
    obstacles: Iterable[TerrainObstacle],
    axis: str,
) -> Vector2:
    """只解析一個軸的中心點移動，讓另一軸能沿牆滑動。"""

    amount = delta.x if axis == "x" else delta.y
    if abs(amount) <= config.TERRAIN_GEOMETRY_EPSILON:
        return position.copy()

    coordinate = position.x if axis == "x" else position.y
    orthogonal = position.y if axis == "x" else position.x
    direction = 1.0 if amount > 0 else -1.0
    desired = coordinate + amount
    limit: float | None = None
    epsilon = max(config.TERRAIN_GEOMETRY_EPSILON, 1e-6)

    for obstacle in _solid_obstacles(obstacles):
        expanded = inflate_rect(obstacle.bounds, radius)
        orthogonal_min, orthogonal_max = (
            (expanded.top, expanded.bottom) if axis == "x" else (expanded.left, expanded.right)
        )
        # 正好貼在矩形的上/下（或左/右）邊界時，沿邊移動是合法的滑動，
        # 因此只把正交座標位於內部的情況視為這一軸的阻擋。
        if not orthogonal_min + epsilon < orthogonal < orthogonal_max - epsilon:
            continue
        lower, upper = (
            (expanded.left, expanded.right) if axis == "x" else (expanded.top, expanded.bottom)
        )

        if direction > 0:
            if coordinate >= upper - epsilon or desired <= lower + epsilon:
                continue
            contact = 0.0 if coordinate >= lower else (lower - coordinate) / amount
            contact = max(0.0, min(1.0, contact))
            allowed = max(0.0, contact * abs(amount) - epsilon)
        else:
            if coordinate <= lower + epsilon or desired >= upper - epsilon:
                continue
            contact = 0.0 if coordinate <= upper else (upper - coordinate) / amount
            contact = max(0.0, min(1.0, contact))
            allowed = max(0.0, contact * abs(amount) - epsilon)

        if limit is None or allowed < limit:
            limit = allowed

    if limit is not None:
        coordinate = coordinate + direction * limit
    else:
        coordinate = desired
    return Vector2(coordinate, position.y) if axis == "x" else Vector2(position.x, coordinate)


def _slide_after_diagonal_collision(
    hit: TerrainHitResult,
    movement: Vector2,
    radius: float,
    obstacles: Iterable[TerrainObstacle],
) -> Vector2:
    """斜向撞牆後保留剩餘切線位移，避免貼牆時每幀停在原地。"""

    if hit.obstacle is None:
        return hit.position.copy()

    movement_length = movement.length()
    if movement_length <= config.TERRAIN_GEOMETRY_EPSILON:
        return hit.position.copy()

    expanded = inflate_rect(hit.obstacle.bounds, radius)
    face_epsilon = max(config.TERRAIN_GEOMETRY_EPSILON * 10, 1e-5)
    on_vertical_face = (
        abs(hit.position.x - expanded.left) <= face_epsilon
        or abs(hit.position.x - expanded.right) <= face_epsilon
    )
    on_horizontal_face = (
        abs(hit.position.y - expanded.top) <= face_epsilon
        or abs(hit.position.y - expanded.bottom) <= face_epsilon
    )

    if on_vertical_face and not on_horizontal_face:
        blocked_axis = "x"
    elif on_horizontal_face and not on_vertical_face:
        blocked_axis = "y"
    else:
        # 牆角同時命中兩個面時，選擇位移較大的軸作為阻擋軸，
        # 保留另一軸滑動；相等時固定先阻擋 X，避免穿過牆角。
        blocked_axis = "x" if abs(movement.x) >= abs(movement.y) else "y"

    remaining_ratio = max(0.0, min(1.0, 1.0 - hit.distance / movement_length))
    if blocked_axis == "x":
        tangent = Vector2(0.0, movement.y * remaining_ratio)
        return _move_axis(hit.position, tangent, radius, obstacles, "y")

    tangent = Vector2(movement.x * remaining_ratio, 0.0)
    return _move_axis(hit.position, tangent, radius, obstacles, "x")


def move_circle_with_obstacles(
    position: Vector2,
    movement: Vector2,
    radius: float,
    obstacles: Iterable[TerrainObstacle],
) -> Vector2:
    """先檢查斜向連續路徑，再分軸解析，避免穿牆角並保留沿牆滑動。"""

    obstacle_list = list(obstacles)
    # 分軸修正能讓角色沿牆滑動，但若兩軸同時切過矩形角落，單獨檢查
    # 會把「先沿上邊、再沿右邊」誤當成合法路徑。先做一次連續斜向掃掠，
    # 確保牆角不能被位移順序穿過；命中時停在第一面牆前仍符合滑動政策。
    if (
        abs(movement.x) > config.TERRAIN_GEOMETRY_EPSILON
        and abs(movement.y) > config.TERRAIN_GEOMETRY_EPSILON
    ):
        diagonal_hit = first_obstacle_on_segment(
            position,
            position + movement,
            obstacle_list,
            radius,
        )
        if diagonal_hit.blocked:
            return _slide_after_diagonal_collision(
                diagonal_hit,
                movement,
                radius,
                obstacle_list,
            )
    after_x = _move_axis(position, movement, radius, obstacle_list, "x")
    return _move_axis(after_x, Vector2(0.0, movement.y), radius, obstacle_list, "y")


def destroy_thin_wall_on_path(
    start: Vector2,
    end: Vector2,
    obstacles: Iterable[ObstacleState],
    radius: float = 0.0,
) -> ObstacleState | None:
    """只破壞路徑上第一面薄牆；厚牆會繼續阻擋且不被移除。"""

    hit = first_obstacle_on_segment(start, end, obstacles, radius)
    if hit.obstacle is None or not hit.obstacle.destructible:
        return None
    hit.obstacle.destroyed = True
    return hit.obstacle


def destroy_terrain_in_radius(
    center: Vector2,
    radius: float,
    obstacles: Iterable[ObstacleState],
    bushes: Iterable[BushState],
) -> tuple[list[ObstacleState], list[BushState]]:
    """移除範圍內的薄牆與草叢，厚牆維持存在。"""

    removed_obstacles: list[ObstacleState] = []
    removed_bushes: list[BushState] = []
    for obstacle in obstacles:
        if obstacle.solid and obstacle.destructible and circle_intersects_rect(center, radius, obstacle.bounds):
            obstacle.destroyed = True
            removed_obstacles.append(obstacle)
    for bush in bushes:
        if bush.active and circle_intersects_rect(center, radius, bush.bounds):
            bush.active = False
            removed_bushes.append(bush)
    return removed_obstacles, removed_bushes


def destroy_bushes_on_segment(
    start: Vector2,
    end: Vector2,
    bushes: Iterable[BushState],
    radius: float = 0.0,
) -> list[BushState]:
    """移除和破壞路徑相交的有效草叢；草叢不會阻擋路徑。"""

    removed: list[BushState] = []
    for bush in bushes:
        if not bush.active:
            continue
        expanded = inflate_rect(bush.bounds, radius)
        if _segment_entry_fraction(start, end, expanded) is not None:
            bush.active = False
            removed.append(bush)
    return removed


def snapshot_obstacles(obstacles: Iterable[ObstacleState]) -> tuple[tuple[int, ObstacleKind, WorldRect], ...]:
    """保存施放當下的牆體幾何，避免遠程破牆同次穿透。"""

    return tuple(
        (obstacle.obstacle_id, obstacle.kind, obstacle.bounds)
        for obstacle in obstacles
        if obstacle.solid
    )


def is_player_in_bush(player: PlayerState, bushes: Iterable[BushState]) -> bool:
    """以存活玩家中心點導出目前是否位於有效草叢。"""

    if not player.alive:
        return False
    return any(bush.active and bush.bounds.contains(player.position) for bush in bushes)


def is_player_visible_to_viewer(
    player: PlayerState,
    viewer_id: int,
    bushes: Iterable[BushState],
) -> bool:
    """玩家自己永遠可見；其他觀看者看不到有效草叢內的存活玩家。"""

    if viewer_id == player.player_id:
        return True
    return not is_player_in_bush(player, bushes)


def terrain_counts(obstacles: Iterable[ObstacleState], bushes: Iterable[BushState]) -> dict[str, int]:
    """回傳除錯/測試用的地形數量，不參與遊戲規則。"""

    return {
        "obstacles": len(list(obstacles)),
        "bushes": len(list(bushes)),
    }
