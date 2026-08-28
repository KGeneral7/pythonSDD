"""小怪使用的純 Python 網格導航入口。"""

from __future__ import annotations

from collections.abc import Iterable
import heapq
import math

from . import config
from .models import ObstacleKind, ObstacleState, Vector2, WorldRect
from .terrain import first_obstacle_on_segment, inflate_rect


GridCoordinate = tuple[int, int]
NavigationObstacle = ObstacleState | tuple[int, ObstacleKind | str, WorldRect]


def grid_size() -> tuple[int, int]:
    """回傳固定世界對應的欄數與列數。"""

    return (
        math.ceil(config.WORLD_WIDTH / config.MONSTER_NAVIGATION_CELL_SIZE),
        math.ceil(config.WORLD_HEIGHT / config.MONSTER_NAVIGATION_CELL_SIZE),
    )


def world_to_grid(position: Vector2) -> GridCoordinate:
    """將世界座標轉成包含該座標的整數網格欄列。"""

    cell_size = config.MONSTER_NAVIGATION_CELL_SIZE
    return math.floor(position.x / cell_size), math.floor(position.y / cell_size)


def grid_to_world(coordinate: GridCoordinate) -> Vector2:
    """將網格欄列轉成格子中心的世界座標。"""

    column, row = coordinate
    cell_size = config.MONSTER_NAVIGATION_CELL_SIZE
    return Vector2((column + 0.5) * cell_size, (row + 0.5) * cell_size)


def _solid_obstacles(obstacles: Iterable[NavigationObstacle]) -> tuple[ObstacleState, ...]:
    """建立本次搜尋使用的固體牆快照，不修改呼叫端的牆體狀態。"""

    solid: list[ObstacleState] = []
    for index, value in enumerate(obstacles):
        if isinstance(value, ObstacleState):
            if value.solid:
                solid.append(value)
            continue
        obstacle_id, kind, bounds = value
        solid.append(
            ObstacleState(
                obstacle_id=int(obstacle_id if obstacle_id is not None else index),
                kind=ObstacleKind(kind),
                bounds=bounds,
            )
        )
    return tuple(solid)


def _in_grid(coordinate: GridCoordinate) -> bool:
    width, height = grid_size()
    column, row = coordinate
    return 0 <= column < width and 0 <= row < height


def _point_is_safe(
    point: Vector2,
    radius: float,
    obstacles: tuple[ObstacleState, ...],
) -> bool:
    """確認物件中心保留半徑、導航 clearance 與世界邊界。"""

    safe_radius = max(0.0, float(radius))
    margin = safe_radius + config.MONSTER_NAVIGATION_CLEARANCE
    epsilon = config.TERRAIN_GEOMETRY_EPSILON
    # 網格中心和實際圓形中心都必須保留 clearance，避免只因中心點未入牆
    # 就讓怪物半徑擦過牆面；世界邊界也採用同一個內縮距離。
    if (
        point.x < margin - epsilon
        or point.x > config.WORLD_WIDTH - margin + epsilon
        or point.y < margin - epsilon
        or point.y > config.WORLD_HEIGHT - margin + epsilon
    ):
        return False
    # 實際移動的 _move_axis 使用膨脹矩形判定軸向碰撞；導航也採同一個
    # 保守安全區，避免圓形角距離判定認為安全、但移動系統在牆角攔住怪物。
    expanded_radius = safe_radius + config.MONSTER_NAVIGATION_CLEARANCE
    for obstacle in obstacles:
        expanded = inflate_rect(obstacle.bounds, expanded_radius)
        if (
            expanded.left - epsilon <= point.x <= expanded.right + epsilon
            and expanded.top - epsilon <= point.y <= expanded.bottom + epsilon
        ):
            return False
    return True


def is_navigation_point_safe(
    point: Vector2,
    radius: float,
    obstacles: Iterable[NavigationObstacle],
) -> bool:
    """提供給遊蕩候選點與測試使用的安全中心點判定。"""

    return _point_is_safe(point, radius, _solid_obstacles(obstacles))


def _cell_is_safe(
    coordinate: GridCoordinate,
    radius: float,
    obstacles: tuple[ObstacleState, ...],
    cache: dict[GridCoordinate, bool] | None = None,
) -> bool:
    if cache is not None and coordinate in cache:
        return cache[coordinate]
    result = _in_grid(coordinate) and _point_is_safe(grid_to_world(coordinate), radius, obstacles)
    if cache is not None:
        cache[coordinate] = result
    return result


def _fast_segment_entry_fraction(
    start: Vector2,
    end: Vector2,
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> float | None:
    """以不建立 WorldRect 的 slab 判定找出線段首次進入矩形比例。"""

    delta = end - start
    enter = 0.0
    exit = 1.0
    epsilon = config.TERRAIN_GEOMETRY_EPSILON
    for origin, movement, lower, upper in (
        (start.x, delta.x, left, right),
        (start.y, delta.y, top, bottom),
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


def _segment_is_safe(
    start: Vector2,
    end: Vector2,
    radius: float,
    obstacles: tuple[ObstacleState, ...],
    segment_cache: dict[tuple[tuple[float, float], tuple[float, float]], bool] | None = None,
    expanded_obstacles: tuple[tuple[float, float, float, float], ...] | None = None,
) -> bool:
    """用圓形半徑再次掃掠候選線段，避免格中心安全卻切過牆角。"""

    start_key = (start.x, start.y)
    end_key = (end.x, end.y)
    cache_key = (start_key, end_key) if start_key <= end_key else (end_key, start_key)
    if segment_cache is not None and cache_key in segment_cache:
        return segment_cache[cache_key]

    safe_radius = max(0.0, float(radius)) + config.MONSTER_NAVIGATION_CLEARANCE
    strict_epsilon = max(config.TERRAIN_GEOMETRY_EPSILON * 10, 1e-5)
    delta = end - start
    delta_length = delta.length()
    segment_left = min(start.x, end.x)
    segment_right = max(start.x, end.x)
    segment_top = min(start.y, end.y)
    segment_bottom = max(start.y, end.y)
    if expanded_obstacles is None:
        expanded_obstacles = tuple(
            (
                obstacle.bounds.left - safe_radius,
                obstacle.bounds.top - safe_radius,
                obstacle.bounds.right + safe_radius,
                obstacle.bounds.bottom + safe_radius,
            )
            for obstacle in obstacles
        )
    for obstacle, (left, top, right, bottom) in zip(obstacles, expanded_obstacles):
        if (
            right < segment_left - strict_epsilon
            or left > segment_right + strict_epsilon
            or bottom < segment_top - strict_epsilon
            or top > segment_bottom + strict_epsilon
        ):
            continue
        fraction = _fast_segment_entry_fraction(
            start,
            end,
            left,
            top,
            right,
            bottom,
        )
        if fraction is None:
            continue
        # 和 terrain.first_obstacle_on_segment 相同：從邊界沿外側離開不算
        # 阻擋，但真正進入膨脹矩形的線段仍會被拒絕。
        if fraction > config.TERRAIN_GEOMETRY_EPSILON:
            result = False
            break
        start_inside_expanded = (
            left + strict_epsilon < start.x < right - strict_epsilon
            and top + strict_epsilon < start.y < bottom - strict_epsilon
        )
        if start_inside_expanded:
            end_inside_expanded = (
                left + strict_epsilon < end.x < right - strict_epsilon
                and top + strict_epsilon < end.y < bottom - strict_epsilon
            )
            if end_inside_expanded:
                result = False
                break
            # 實際怪物碰撞只使用 radius；怪物可能因上一幀的實際碰撞
            # 合法地落在額外 clearance 內。此時允許它離開規劃安全區，
            # 但仍用既有精確半徑掃掠確認離開線段沒有真的穿過牆體。
            if first_obstacle_on_segment(
                start,
                end,
                (obstacle,),
                radius=max(0.0, float(radius)),
            ).blocked:
                result = False
                break
            continue
        if delta_length <= config.TERRAIN_GEOMETRY_EPSILON:
            continue
        sample = start + delta * min(1.0, strict_epsilon * 2 / delta_length)
        if (
            left + strict_epsilon < sample.x < right - strict_epsilon
            and top + strict_epsilon < sample.y < bottom - strict_epsilon
        ):
            result = False
            break
    else:
        result = True
    if segment_cache is not None:
        segment_cache[cache_key] = result
    return result


def _nearest_safe_cell(
    point: Vector2,
    radius: float,
    obstacles: tuple[ObstacleState, ...],
    cache: dict[GridCoordinate, bool] | None = None,
) -> GridCoordinate | None:
    width, height = grid_size()
    start_column, start_row = world_to_grid(point)
    max_distance = max(
        start_column,
        start_row,
        width - 1 - start_column,
        height - 1 - start_row,
    )
    # 怪物通常位於可通行格的附近；由起點向外擴張可避免每次尋路都掃完整張圖。
    # 若起點真的落在牆內，仍會逐圈搜尋到最遠的安全格，保留原本的容錯能力。
    for manhattan_distance in range(max_distance + 1):
        candidates: list[tuple[float, int, int, GridCoordinate]] = []
        for column_offset in range(-manhattan_distance, manhattan_distance + 1):
            row_offset_distance = manhattan_distance - abs(column_offset)
            row_offsets = (
                (row_offset_distance, -row_offset_distance)
                if row_offset_distance
                else (0,)
            )
            for row_offset in row_offsets:
                coordinate = (start_column + column_offset, start_row + row_offset)
                if not _cell_is_safe(coordinate, radius, obstacles, cache):
                    continue
                center = grid_to_world(coordinate)
                candidates.append(
                    (center.distance_to(point), coordinate[1], coordinate[0], coordinate)
                )
        if candidates:
            return min(candidates)[-1]
    return None


def _octile_distance(first: GridCoordinate, second: GridCoordinate) -> float:
    dx = abs(first[0] - second[0])
    dy = abs(first[1] - second[1])
    return max(dx, dy) + (math.sqrt(2.0) - 1.0) * min(dx, dy)


def _neighbors(
    coordinate: GridCoordinate,
    radius: float,
    obstacles: tuple[ObstacleState, ...],
    cache: dict[GridCoordinate, bool] | None = None,
) -> Iterable[tuple[GridCoordinate, float]]:
    column, row = coordinate
    for delta_column, delta_row, cost in (
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, math.sqrt(2.0)),
        (1, -1, math.sqrt(2.0)),
        (-1, 1, math.sqrt(2.0)),
        (1, 1, math.sqrt(2.0)),
    ):
        neighbor = (column + delta_column, row + delta_row)
        if not _cell_is_safe(neighbor, radius, obstacles, cache):
            continue
        if delta_column and delta_row:
            # 斜向移動不能只看終點，兩個正交格也要安全；這是網格尋路
            # 的 no-corner-cut 規則，避免怪物從矩形牆角的對角縫隙切過去。
            if not _cell_is_safe((column + delta_column, row), radius, obstacles, cache):
                continue
            if not _cell_is_safe((column, row + delta_row), radius, obstacles, cache):
                continue
        yield neighbor, cost


def _astar(
    start: GridCoordinate,
    goal: GridCoordinate,
    radius: float,
    obstacles: tuple[ObstacleState, ...],
    cache: dict[GridCoordinate, bool] | None = None,
) -> list[GridCoordinate] | None:
    open_nodes: list[tuple[float, float, int, int, GridCoordinate]] = []
    heapq.heappush(open_nodes, (_octile_distance(start, goal), 0.0, start[1], start[0], start))
    came_from: dict[GridCoordinate, GridCoordinate] = {}
    costs: dict[GridCoordinate, float] = {start: 0.0}
    closed: set[GridCoordinate] = set()

    while open_nodes:
        _, current_cost, _, _, current = heapq.heappop(open_nodes)
        if current in closed:
            continue
        closed.add(current)
        if current == goal:
            route: list[GridCoordinate] = [current]
            while route[-1] != start:
                route.append(came_from[route[-1]])
            route.reverse()
            return route

        for neighbor, step_cost in _neighbors(
            current,
            radius,
            obstacles,
            cache,
        ):
            if neighbor in closed:
                continue
            next_cost = current_cost + step_cost
            if next_cost >= costs.get(neighbor, math.inf):
                continue
            costs[neighbor] = next_cost
            came_from[neighbor] = current
            priority = next_cost + _octile_distance(neighbor, goal)
            heapq.heappush(
                open_nodes,
                (priority, next_cost, neighbor[1], neighbor[0], neighbor),
            )
    return None


def find_grid_path(
    start: Vector2,
    goal: Vector2,
    radius: float,
    obstacles: Iterable[NavigationObstacle],
    allow_goal_fallback: bool = False,
    shared_cache: dict | None = None,
) -> tuple[Vector2, ...] | None:
    """以固定八方向 A* 尋找避開固體牆體的安全路徑。

    預設要求目標本身可供物件站立；追擊用途可啟用目標備援，
    讓貼牆玩家改以最近的安全格作為接近位置。
    """

    solid_obstacles = _solid_obstacles(obstacles)
    safe_radius = max(0.0, float(radius))
    expanded_obstacles = tuple(
        (
            obstacle.bounds.left - safe_radius - config.MONSTER_NAVIGATION_CLEARANCE,
            obstacle.bounds.top - safe_radius - config.MONSTER_NAVIGATION_CLEARANCE,
            obstacle.bounds.right + safe_radius + config.MONSTER_NAVIGATION_CLEARANCE,
            obstacle.bounds.bottom + safe_radius + config.MONSTER_NAVIGATION_CLEARANCE,
        )
        for obstacle in solid_obstacles
    )
    if shared_cache is None:
        safe_cells: dict[GridCoordinate, bool] = {}
        segment_cache: dict[tuple[tuple[float, float], tuple[float, float]], bool] = {}
        route_cache: dict[tuple[GridCoordinate, GridCoordinate], tuple[GridCoordinate, ...] | None] = {}
    else:
        obstacle_key = tuple(
            (obstacle.obstacle_id, obstacle.kind, obstacle.bounds)
            for obstacle in solid_obstacles
        )
        cache_entry = shared_cache.setdefault((safe_radius, obstacle_key), ({}, {}, {}))
        safe_cells, segment_cache, route_cache = cache_entry
    exact_goal_is_safe = _point_is_safe(goal, safe_radius, solid_obstacles)
    goal_cell = world_to_grid(goal)
    if exact_goal_is_safe and _cell_is_safe(goal_cell, safe_radius, solid_obstacles, safe_cells):
        pass
    elif allow_goal_fallback:
        goal_cell = _nearest_safe_cell(goal, safe_radius, solid_obstacles, safe_cells)
        if goal_cell is None:
            return None
        exact_goal_is_safe = False
    else:
        return None
    start_cell = _nearest_safe_cell(start, safe_radius, solid_obstacles, safe_cells)
    if start_cell is None:
        return None

    route_key = (start_cell, goal_cell)
    if route_key not in route_cache:
        computed_route = _astar(
            start_cell,
            goal_cell,
            safe_radius,
            solid_obstacles,
            safe_cells,
        )
        route_cache[route_key] = tuple(computed_route) if computed_route is not None else None
    cached_route = route_cache[route_key]
    route = list(cached_route) if cached_route is not None else None
    if route is None:
        return None

    points = [grid_to_world(coordinate) for coordinate in route[1:]]
    if not points:
        if not exact_goal_is_safe or start.distance_to(goal) <= config.MONSTER_NAVIGATION_NODE_ARRIVAL_TOLERANCE:
            return ()
        if not _segment_is_safe(
            start,
            goal,
            safe_radius,
            solid_obstacles,
            segment_cache,
            expanded_obstacles,
        ):
            return None
        return (goal.copy(),)

    # 起點可能位在格子邊緣；只有直接連到第一個 A* 節點會跨過一格
    # 對角線時，才先走到起點格中心，避免產生過長的首段路徑。
    start_center = grid_to_world(start_cell)
    max_step = config.MONSTER_NAVIGATION_CELL_SIZE * math.sqrt(2.0)
    direct_segment_is_safe = _segment_is_safe(
        start,
        points[0],
        safe_radius,
        solid_obstacles,
        segment_cache,
        expanded_obstacles,
    )
    if (
        not direct_segment_is_safe
        or start.distance_to(points[0]) > max_step + config.TERRAIN_GEOMETRY_EPSILON
    ):
        if not _segment_is_safe(
            start,
            start_center,
            safe_radius,
            solid_obstacles,
            segment_cache,
            expanded_obstacles,
        ):
            return None
        points.insert(0, start_center)

    if exact_goal_is_safe and points[-1].distance_to(goal) > config.TERRAIN_GEOMETRY_EPSILON:
        if _segment_is_safe(
            points[-1],
            goal,
            safe_radius,
            solid_obstacles,
            segment_cache,
            expanded_obstacles,
        ):
            points[-1] = goal.copy()

    return tuple(points)
