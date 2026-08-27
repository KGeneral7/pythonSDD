"""只負責 Pygame 繪製，不在繪製函式中修改遊戲狀態。"""

from __future__ import annotations

import math

import pygame

from . import config
from .aiming import build_aim_guide
from .characters import get_character_definition, get_tactical_definition
from .controllers import InputState
from .models import AimGuide, AbilityEffect, CharacterId, MatchPhase, MatchState, PlayerState, TacticalId, Vector2
from .world import world_to_screen


# Pygame 的預設字型通常不含繁體中文字形。依序尋找常見的系統中文字型，
# 並驗證候選字型確實能繪製本遊戲使用的中文字，再交給繪製函式共用。
_TEXT_FONT_CANDIDATES = (
    "Microsoft JhengHei",
    "Microsoft JhengHei UI",
    "Microsoft YaHei",
    "Microsoft YaHei UI",
    "PMingLiU",
    "MingLiU",
    "SimSun",
    "Arial Unicode MS",
)
_TEXT_FONT_PATH: str | None = None
_TEXT_FONT_PATH_DISCOVERED = False
_TEXT_FONT_CACHE: dict[int, pygame.font.Font] = {}
_PRIMARY_EFFECT_LABELS = {
    "breach_cone": "扇形散射",
    "breach_pellet": "散射彈",
    "sniper_line": "狙擊子彈",
    "guardian_arc": "盾擊",
    "boomerang": "回旋飛刃",
    "mine": "重力地雷",
    "beam": "吸能光束",
}


def _supports_traditional_chinese(font_path: str) -> bool:
    """確認字型有本遊戲介面需要的中文字形。"""

    try:
        font = pygame.font.Font(font_path, 24)
        metrics = font.metrics("撤離區")
    except pygame.error:
        return False
    return bool(metrics) and all(metric is not None and metric[4] > 0 for metric in metrics)


def _find_text_font_path() -> str | None:
    """尋找可繪製繁體中文的系統字型；找不到時交由 Pygame 預設字型兜底。"""

    global _TEXT_FONT_PATH, _TEXT_FONT_PATH_DISCOVERED
    if _TEXT_FONT_PATH_DISCOVERED:
        return _TEXT_FONT_PATH

    if not pygame.font.get_init():
        pygame.font.init()
    for font_name in _TEXT_FONT_CANDIDATES:
        font_path = pygame.font.match_font(font_name)
        if font_path and _supports_traditional_chinese(font_path):
            _TEXT_FONT_PATH = font_path
            break
    _TEXT_FONT_PATH_DISCOVERED = True
    return _TEXT_FONT_PATH


def get_text_font_path() -> str | None:
    """回傳目前選用的中文字型路徑，供啟動檢查與回歸測試使用。"""

    return _find_text_font_path()


def _get_text_font(size: int) -> pygame.font.Font:
    if size not in _TEXT_FONT_CACHE:
        font_path = _find_text_font_path()
        _TEXT_FONT_CACHE[size] = pygame.font.Font(font_path, size) if font_path else pygame.font.Font(None, size)
    return _TEXT_FONT_CACHE[size]


def create_screen() -> pygame.Surface:
    """建立固定尺寸的桌面視窗。"""

    return pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))


def draw_text(
    surface: pygame.Surface,
    text: str,
    position: tuple[int, int],
    size: int = 24,
    color: tuple[int, int, int] = config.TEXT_COLOR,
    center: bool = False,
) -> None:
    font = _get_text_font(size)
    image = font.render(text, True, color)
    rect = image.get_rect()
    if center:
        rect.center = position
    else:
        rect.topleft = position
    surface.blit(image, rect)


def _speed_label(player_or_definition: PlayerState | object) -> str:
    definition = (
        get_character_definition(player_or_definition.character_id)
        if isinstance(player_or_definition, PlayerState)
        else player_or_definition
    )
    if definition.projectile_speed <= 0:
        return "近戰" if definition.character_id == CharacterId.GUARDIAN else "引導"
    return f"{definition.projectile_speed:.0f}"


def draw_selection(
    surface: pygame.Surface,
    selected_character_index: int,
    selected_tactical_index: int,
) -> None:
    """繪製角色／配件選擇畫面與鍵盤提示。"""

    surface.fill(config.BACKGROUND_COLOR)
    from .characters import get_all_character_definitions, get_all_tactical_definitions

    draw_text(surface, "PvPvE 中央撤離競技", (config.WINDOW_WIDTH // 2, 48), 42, config.ACCENT_COLOR, True)
    draw_text(surface, "按 1～6 選擇角色，Q/W/E 選擇配件，Enter 開始", (config.WINDOW_WIDTH // 2, 88), 24, config.MUTED_TEXT_COLOR, True)
    definitions = get_all_character_definitions()
    card_width, card_height = 280, 126
    for index, definition in enumerate(definitions):
        column = index % 3
        row = index // 3
        rect = pygame.Rect(70 + column * 390, 135 + row * 155, card_width, card_height)
        selected = index == selected_character_index
        pygame.draw.rect(surface, config.PANEL_COLOR, rect, border_radius=10)
        pygame.draw.rect(surface, config.ACCENT_COLOR if selected else config.PANEL_BORDER_COLOR, rect, 3, border_radius=10)
        _draw_role_shape(
            surface,
            (rect.right - 34, rect.y + 34),
            17,
            config.ACCENT_COLOR if selected else config.PANEL_BORDER_COLOR,
            definition.character_id,
            Vector2(1, 0),
        )
        draw_text(surface, f"{index + 1}. {definition.display_name}", (rect.x + 14, rect.y + 12), 28, config.ACCENT_COLOR if selected else config.TEXT_COLOR)
        draw_text(surface, definition.primary_kind, (rect.x + 14, rect.y + 46), 21, config.MUTED_TEXT_COLOR)
        pellet_text = ""
        if definition.character_id == CharacterId.BREACHER:
            pellet_text = "×5"
        elif definition.character_id == CharacterId.SIPHONER:
            pellet_text = "/0.15s"
        draw_text(surface, f"生命 {definition.base_health:.0f}｜火力 {definition.primary_damage:.0f}{pellet_text}", (rect.x + 14, rect.y + 76), 17, config.TEXT_COLOR)
        draw_text(surface, f"射程 {definition.primary_range:.0f}｜速度 {_speed_label(definition)}", (rect.x + 14, rect.y + 99), 17, config.TEXT_COLOR)
    tactics = get_all_tactical_definitions()
    draw_text(surface, "戰術配件", (70, 470), 28, config.WARNING_COLOR)
    for index, definition in enumerate(tactics):
        rect = pygame.Rect(70 + index * 390, 510, 280, 88)
        selected = index == selected_tactical_index
        pygame.draw.rect(surface, config.PANEL_COLOR, rect, border_radius=8)
        pygame.draw.rect(surface, config.WARNING_COLOR if selected else config.PANEL_BORDER_COLOR, rect, 3, border_radius=8)
        draw_text(surface, f"{('Q', 'W', 'E')[index]}  {definition.display_name}", (rect.x + 14, rect.y + 12), 24, config.WARNING_COLOR if selected else config.TEXT_COLOR)
        draw_text(surface, f"冷卻 {definition.cooldown:.0f}s", (rect.x + 14, rect.y + 46), 18, config.MUTED_TEXT_COLOR)
    draw_text(surface, "假玩家固定不移動、不攻擊；可在比賽中使用 F1 開發者測試。", (70, 655), 20, config.MUTED_TEXT_COLOR)


def _screen_point(match: MatchState, position: Vector2) -> tuple[int, int]:
    point = world_to_screen(position, match.camera.position)
    return round(point.x), round(point.y)


def _polar_point(center: tuple[int, int], angle: float, distance: float) -> tuple[int, int]:
    return (
        round(center[0] + math.cos(angle) * distance),
        round(center[1] + math.sin(angle) * distance),
    )


def _effect_direction(direction: Vector2) -> Vector2:
    normalized = direction.normalized()
    return normalized if normalized.length() else Vector2(1.0, 0.0)


def _oriented_point(
    center: tuple[int, int],
    direction: Vector2,
    forward: float,
    lateral: float,
) -> tuple[int, int]:
    perpendicular = Vector2(-direction.y, direction.x)
    return (
        round(center[0] + direction.x * forward + perpendicular.x * lateral),
        round(center[1] + direction.y * forward + perpendicular.y * lateral),
    )


def _role_vertices(
    center: tuple[int, int],
    radius: int,
    character_id: CharacterId,
    direction: Vector2,
) -> list[tuple[int, int]]:
    direction = _effect_direction(direction)
    if character_id == CharacterId.BREACHER:
        return [
            _oriented_point(center, direction, radius * 1.25, 0),
            _oriented_point(center, direction, -radius * 0.75, radius * 0.85),
            _oriented_point(center, direction, -radius * 0.75, -radius * 0.85),
        ]
    if character_id == CharacterId.SNIPER:
        return [
            _oriented_point(center, direction, radius * 1.2, 0),
            _oriented_point(center, direction, 0, radius * 0.8),
            _oriented_point(center, direction, -radius * 1.2, 0),
            _oriented_point(center, direction, 0, -radius * 0.8),
        ]
    if character_id == CharacterId.GUARDIAN:
        return [
            _oriented_point(center, direction, -radius * 0.9, -radius * 0.8),
            _oriented_point(center, direction, radius * 0.45, -radius * 0.8),
            _oriented_point(center, direction, radius, 0),
            _oriented_point(center, direction, radius * 0.45, radius * 0.8),
            _oriented_point(center, direction, -radius * 0.9, radius * 0.8),
            _oriented_point(center, direction, -radius * 0.5, 0),
        ]
    if character_id == CharacterId.HUNTER:
        return [
            _oriented_point(center, direction, radius * 1.35, 0),
            _oriented_point(center, direction, -radius * 0.25, radius * 0.85),
            _oriented_point(center, direction, -radius * 0.9, radius * 0.45),
            _oriented_point(center, direction, -radius * 0.5, 0),
            _oriented_point(center, direction, -radius * 0.9, -radius * 0.45),
            _oriented_point(center, direction, -radius * 0.25, -radius * 0.85),
        ]
    if character_id == CharacterId.CONTROLLER:
        return [
            _polar_point(center, math.radians(30 + index * 60), radius)
            for index in range(6)
        ]
    return []


def _draw_role_shape(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    character_id: CharacterId,
    direction: Vector2,
) -> None:
    radius = max(4, round(radius))
    if character_id == CharacterId.SIPHONER:
        pygame.draw.circle(surface, color, center, radius)
        pygame.draw.circle(surface, config.TEXT_COLOR, center, radius, 2)
        pygame.draw.circle(surface, config.EXTRACTION_COLOR, center, max(2, radius // 2), 2)
        return
    vertices = _role_vertices(center, radius, character_id, direction)
    pygame.draw.polygon(surface, color, vertices)
    pygame.draw.polygon(surface, config.TEXT_COLOR, vertices, 2)


def _draw_health_bar(
    surface: pygame.Surface,
    center: tuple[int, int],
    health: float,
    max_health: float,
    y_offset: int,
    width: int = 56,
) -> None:
    ratio = max(0.0, min(1.0, health / max(max_health, 1.0)))
    bar = pygame.Rect(center[0] - width // 2, center[1] + y_offset, width, 6)
    pygame.draw.rect(surface, config.PANEL_COLOR, bar)
    if ratio > 0:
        health_color = config.DANGER_COLOR if ratio <= 0.3 else config.WARNING_COLOR if ratio <= 0.6 else config.ACCENT_COLOR
        pygame.draw.rect(surface, health_color, (bar.x + 1, bar.y + 1, max(1, round((bar.width - 2) * ratio)), bar.height - 2))


def _draw_player_overlay(surface: pygame.Surface, player: PlayerState, point: tuple[int, int]) -> None:
    character = get_character_definition(player.character_id)
    label_color = config.PLAYER_COLORS[player.player_id % len(config.PLAYER_COLORS)] if player.alive else config.DANGER_COLOR
    _draw_health_bar(surface, point, player.health, player.max_health, -34, 62)
    draw_text(surface, f"{player.health:.0f}/{player.max_health:.0f}", (point[0], point[1] - 47), 13, config.TEXT_COLOR, True)
    draw_text(surface, f"{player.player_id} {character.display_name}", (point[0], point[1] - 64), 14, label_color, True)


def _draw_player_roster(surface: pygame.Surface, match: MatchState) -> None:
    panel = pygame.Rect(880, 500, 384, 174)
    pygame.draw.rect(surface, config.PANEL_COLOR, panel, border_radius=8)
    pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, panel, 2, border_radius=8)
    draw_text(surface, "玩家／角色", (898, 510), 19, config.TEXT_COLOR)
    for index, player in enumerate(match.players):
        column = index % 2
        row = index // 2
        center = (896 + column * 188, 544 + row * 37)
        color = config.PLAYER_COLORS[player.player_id % len(config.PLAYER_COLORS)]
        _draw_role_shape(surface, center, 8, color, player.character_id, player.aim_direction)
        character = get_character_definition(player.character_id)
        status = "存活" if player.alive else "重生中"
        draw_text(surface, f"{player.player_id} {character.display_name}", (center[0] + 14, center[1] - 10), 15, color)
        draw_text(surface, status, (center[0] + 14, center[1] + 7), 12, config.MUTED_TEXT_COLOR)


def _draw_directional_wedge(
    surface: pygame.Surface,
    center: tuple[int, int],
    direction: Vector2,
    radius: float,
    angle_degrees: float,
    color: tuple[int, int, int],
) -> None:
    radius = max(24, round(radius))
    heading = math.atan2(direction.y, direction.x)
    half_angle = math.radians(angle_degrees) / 2
    left = _polar_point(center, heading - half_angle, radius)
    right = _polar_point(center, heading + half_angle, radius)
    pygame.draw.line(surface, color, center, left, 3)
    pygame.draw.line(surface, color, center, right, 3)
    # 不使用 pygame.draw.arc 的角度座標系，直接依攻擊方向取樣，避免弧線偏到反方向。
    arc_points = [
        _polar_point(center, heading - half_angle + 2 * half_angle * index / 12, radius)
        for index in range(13)
    ]
    pygame.draw.lines(surface, color, False, arc_points, 3)


def _aim_guide_color(guide: AimGuide) -> tuple[int, int, int]:
    if not guide.valid:
        return config.AIM_GUIDE_INVALID_COLOR
    return config.AIM_GUIDE_SECONDARY_COLOR if guide.ability_slot != "primary" else config.AIM_GUIDE_COLOR


def _draw_aim_guide(surface: pygame.Surface, match: MatchState, guide: AimGuide) -> None:
    """繪製按住技能時的世界座標預覽；預覽只讀取 AimGuide，不改變比賽狀態。"""

    color = _aim_guide_color(guide)
    origin = _screen_point(match, guide.origin)
    end = _screen_point(match, guide.end)
    if guide.shape == "wedge":
        if guide.path_points:
            points = [_screen_point(match, point) for point in guide.path_points]
            for point in points:
                pygame.draw.line(surface, color, origin, point, 3)
            pygame.draw.lines(surface, color, False, points, 2)
        else:
            _draw_directional_wedge(
                surface,
                origin,
                guide.direction,
                guide.range,
                guide.angle_degrees,
                color,
            )
    elif guide.shape in {"line", "beam"}:
        width = 7 if guide.shape == "beam" else 4
        pygame.draw.line(surface, color, origin, end, width)
        pygame.draw.line(surface, config.AIM_GUIDE_OUTLINE_COLOR, origin, end, 1)
        pygame.draw.circle(surface, color, end, 9 if guide.shape == "beam" else 7, 2)
    elif guide.shape == "path":
        points = [_screen_point(match, point) for point in (guide.path_points or (guide.origin, guide.end))]
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, 4)
            pygame.draw.circle(surface, color, points[-1], 10, 2)
    elif guide.shape == "circle":
        if origin != end:
            pygame.draw.line(surface, color, origin, end, 2)
        pygame.draw.circle(surface, color, end, max(8, round(guide.radius)), 3)
        pygame.draw.circle(surface, config.AIM_GUIDE_OUTLINE_COLOR, end, 4, 1)


def _preview_slot(input_state: InputState | None) -> str | None:
    """依契約回傳目前預覽欄位：大招優先於配件，再優先於普攻。"""

    if input_state is None:
        return None
    if input_state.ultimate_held:
        return "ultimate"
    if input_state.tactical_held:
        return "tactical"
    if input_state.primary_held:
        return "primary"
    return None


def _preview_is_valid(player: PlayerState, slot: str) -> bool:
    if slot == "ultimate":
        return player.alive and player.ultimate_energy >= 100.0
    if slot == "tactical":
        return player.alive and player.tactical_cooldown <= 0.0
    return player.alive and player.ammo > 0 and player.primary_cooldown <= 0.0


def _draw_ability_effect(surface: pygame.Surface, match: MatchState, effect: AbilityEffect) -> None:
    """以明確的幾何圖形繪製所有普攻、配件與大招效果。"""

    point = _screen_point(match, effect.position)
    direction = _effect_direction(effect.direction)
    kind = effect.kind
    label = _PRIMARY_EFFECT_LABELS.get(kind)

    if kind == "breach_cone":
        _draw_directional_wedge(
            surface,
            point,
            direction,
            effect.max_distance,
            float(effect.metadata.get("angle", 60)),
            config.WARNING_COLOR,
        )
        heading = math.atan2(direction.y, direction.x)
        half_angle = math.radians(float(effect.metadata.get("angle", 60))) / 2
        for fraction in (0.35, 0.65, 1.0):
            pygame.draw.line(
                surface,
                config.WARNING_COLOR,
                point,
                _polar_point(point, heading - half_angle + 2 * half_angle * fraction, effect.max_distance),
                2,
            )
    elif kind == "breach_pellet":
        tail = effect.metadata.get("visible_start")
        if not isinstance(tail, Vector2):
            tail = effect.position - direction * 26
        screen_tail = _screen_point(match, tail)
        pygame.draw.line(surface, config.WARNING_COLOR, screen_tail, point, 4)
        pygame.draw.circle(surface, config.WARNING_COLOR, point, 6)
        pygame.draw.circle(surface, config.TEXT_COLOR, point, 6, 1)
    elif kind == "sniper_line":
        impact_blocked = bool(effect.metadata.get("impact_blocked", 0))
        impact_color = config.DANGER_COLOR if impact_blocked else config.EXTRACTION_COLOR
        if effect.metadata.get("impacted"):
            impact = effect.impact_position or effect.position
            impact_point = _screen_point(match, impact)
            pygame.draw.circle(surface, impact_color, impact_point, 28, 4)
            pygame.draw.line(surface, impact_color, (impact_point[0] - 22, impact_point[1] - 22), (impact_point[0] + 22, impact_point[1] + 22), 3)
            pygame.draw.line(surface, impact_color, (impact_point[0] + 22, impact_point[1] - 22), (impact_point[0] - 22, impact_point[1] + 22), 3)
        else:
            tail = effect.metadata.get("visible_start")
            if not isinstance(tail, Vector2):
                tail = effect.position - direction * 42
            screen_tail = _screen_point(match, tail)
            pygame.draw.line(surface, config.EXTRACTION_COLOR, screen_tail, point, 6)
            pygame.draw.circle(surface, config.EXTRACTION_COLOR, point, 9)
            pygame.draw.circle(surface, config.TEXT_COLOR, point, 9, 2)
    elif kind == "sniper_ultimate_line":
        end = effect.position + direction * effect.max_distance
        line_color = config.EXTRACTION_COLOR
        pygame.draw.line(surface, line_color, point, _screen_point(match, end), 8)
        pygame.draw.line(surface, config.TEXT_COLOR, point, _screen_point(match, end), 2)
        pygame.draw.circle(surface, line_color, point, 9, 2)
    elif kind == "guardian_arc":
        _draw_directional_wedge(
            surface,
            point,
            direction,
            effect.max_distance,
            float(effect.metadata.get("angle", 100)),
            config.TEXT_COLOR,
        )
    elif kind == "boomerang":
        tail = effect.metadata.get("visible_start")
        if not isinstance(tail, Vector2):
            tail = effect.position - direction * 48
        pygame.draw.line(surface, config.ACCENT_COLOR, _screen_point(match, tail), point, 6)
        blade = [
            _oriented_point(point, direction, 23, 0),
            _oriented_point(point, direction, 0, 11),
            _oriented_point(point, direction, -23, 0),
            _oriented_point(point, direction, 0, -11),
        ]
        pygame.draw.polygon(surface, config.ACCENT_COLOR, blade)
        pygame.draw.polygon(surface, config.TEXT_COLOR, blade, 2)
        pygame.draw.circle(surface, config.TEXT_COLOR, point, 6, 2)
    elif kind == "mine":
        owner = next((player for player in match.players if player.player_id == effect.owner_id), None)
        if not effect.armed:
            tail = effect.metadata.get("visible_start")
            if not isinstance(tail, Vector2) and owner is not None:
                tail = owner.position
            if isinstance(tail, Vector2):
                pygame.draw.line(surface, config.WARNING_COLOR, _screen_point(match, tail), point, 3)
            pygame.draw.circle(surface, config.WARNING_COLOR, point, 9, 2)
            pygame.draw.circle(surface, config.TEXT_COLOR, point, 4)
        else:
            radius = max(24, round(float(effect.metadata.get("area_radius", effect.radius))))
            pygame.draw.circle(surface, config.WARNING_COLOR, point, radius, 3)
            pygame.draw.circle(surface, config.WARNING_COLOR, point, max(7, radius // 5), 2)
            pygame.draw.line(surface, config.WARNING_COLOR, (point[0] - 10, point[1] - 10), (point[0] + 10, point[1] + 10), 2)
            pygame.draw.line(surface, config.WARNING_COLOR, (point[0] + 10, point[1] - 10), (point[0] - 10, point[1] + 10), 2)
    elif kind == "beam":
        end = effect.position + direction * effect.max_distance
        screen_end = _screen_point(match, end)
        pygame.draw.line(surface, config.ACCENT_COLOR, point, screen_end, 10)
        pygame.draw.line(surface, config.TEXT_COLOR, point, screen_end, 3)
        pygame.draw.circle(surface, config.ACCENT_COLOR, point, 12, 2)
    elif kind in {"breach_burst", "siphon_burst"}:
        radius = max(30, round(effect.radius))
        color = config.WARNING_COLOR if kind == "breach_burst" else config.EXTRACTION_COLOR
        pygame.draw.circle(surface, color, point, radius, 5)
        pygame.draw.circle(surface, color, point, max(18, radius // 2), 2)
        for index in range(8):
            pygame.draw.line(
                surface,
                color,
                _polar_point(point, index * math.pi / 4, max(14, radius - 18)),
                _polar_point(point, index * math.pi / 4, radius + 14),
                3,
            )
    elif kind == "guardian_guard":
        pygame.draw.circle(surface, config.TEXT_COLOR, point, 38, 4)
        pygame.draw.circle(surface, config.ACCENT_COLOR, point, 29, 2)
    elif kind == "hunter_dash":
        end = effect.position + direction * effect.max_distance
        screen_end = _screen_point(match, end)
        pygame.draw.line(surface, config.ACCENT_COLOR, point, screen_end, 10)
        pygame.draw.line(surface, config.TEXT_COLOR, point, screen_end, 3)
        pygame.draw.circle(surface, config.ACCENT_COLOR, point, 20, 3)
        pygame.draw.circle(surface, config.ACCENT_COLOR, screen_end, 20, 3)
    elif kind == "gravity_cage":
        radius = max(30, round(effect.radius))
        pygame.draw.circle(surface, config.WARNING_COLOR, point, radius, 5)
        pygame.draw.circle(surface, config.EXTRACTION_COLOR, point, max(18, radius - 24), 2)
        for index in range(4):
            angle = index * math.pi / 2 + math.pi / 4
            pygame.draw.line(
                surface,
                config.WARNING_COLOR,
                _polar_point(point, angle, radius - 14),
                _polar_point(point, angle + math.pi, radius - 14),
                2,
            )
    elif kind == "dash":
        end = effect.position + direction * effect.max_distance
        screen_end = _screen_point(match, end)
        pygame.draw.line(surface, config.ACCENT_COLOR, point, screen_end, 8)
        pygame.draw.circle(surface, config.ACCENT_COLOR, point, 24, 3)
        pygame.draw.circle(surface, config.TEXT_COLOR, screen_end, 12, 2)
    elif kind == "shield":
        pygame.draw.circle(surface, config.EXTRACTION_COLOR, point, 36, 5)
        pygame.draw.circle(surface, config.TEXT_COLOR, point, 28, 2)
    elif kind == "control_zone":
        radius = max(24, round(effect.radius))
        pygame.draw.circle(surface, config.WARNING_COLOR, point, radius, 4)
        pygame.draw.circle(surface, config.WARNING_COLOR, point, max(10, radius // 3), 2)
        pygame.draw.line(surface, config.WARNING_COLOR, (point[0] - radius, point[1]), (point[0] + radius, point[1]), 2)
        pygame.draw.line(surface, config.WARNING_COLOR, (point[0], point[1] - radius), (point[0], point[1] + radius), 2)
    label_color = config.TEXT_COLOR
    if kind == "sniper_line" and effect.metadata.get("impacted"):
        status = effect.impact_status or str(effect.metadata.get("impact_status", "命中"))
        effective_damage = float(effect.metadata.get("impact_effective_damage", 0.0))
        if effect.metadata.get("impact_blocked"):
            label = f"狙擊被擋｜{status}"
            label_color = config.DANGER_COLOR
        else:
            label = f"狙擊命中｜-{effective_damage:.0f}"
            label_color = config.EXTRACTION_COLOR
    if label:
        label_point = point
        if kind in {"sniper_line", "boomerang"} and not (
            kind == "sniper_line" and effect.metadata.get("impacted")
        ):
            owner = next((player for player in match.players if player.player_id == effect.owner_id), None)
            if owner is not None:
                label_point = _screen_point(match, owner.position)
        draw_text(surface, label, (label_point[0], label_point[1] - 29), 14, label_color, True)


def _draw_control_status(
    surface: pygame.Surface,
    point: tuple[int, int],
    radius: int,
    slow_timer: float,
    slow_multiplier: float,
    root_timer: float,
) -> None:
    """在目標身上標出實際生效中的減速／定身，避免控場只有範圍圖形。"""

    if root_timer > 0.0:
        color = config.EXTRACTION_COLOR
        label = "定身"
    elif slow_timer > 0.0:
        color = config.WARNING_COLOR
        label = f"減速 {slow_multiplier:.1f}x"
    else:
        return
    pygame.draw.circle(surface, color, point, radius + 9, 3)
    draw_text(surface, label, (point[0], point[1] + radius + 14), 12, color, True)


def _draw_defense_status(surface: pygame.Surface, player: PlayerState, point: tuple[int, int]) -> None:
    """標出玩家身上目前生效的免傷、減傷或護盾狀態。"""

    if player.invulnerability_timer > 0.0:
        color, label = config.ACCENT_COLOR, "免傷"
    elif player.damage_reduction_timer > 0.0:
        color, label = config.TEXT_COLOR, "減傷"
    elif player.shield_timer > 0.0 and player.shield_remaining > 0.0:
        color, label = config.EXTRACTION_COLOR, f"護盾 {player.shield_remaining:.0f}"
    else:
        return
    pygame.draw.circle(surface, color, point, config.PLAYER_DRAW_RADIUS + 10, 3)
    draw_text(surface, label, (point[0], point[1] + config.PLAYER_DRAW_RADIUS + 16), 12, color, True)


def draw_world(surface: pygame.Surface, match: MatchState, input_state: InputState | None = None) -> None:
    """繪製地圖幾何圖形、玩家、怪物與撤離區。"""

    surface.fill(config.GROUND_COLOR)
    camera = match.camera.position
    for x in range(0, config.WORLD_WIDTH + 1, config.GRID_SIZE):
        start = world_to_screen(Vector2(x, 0), camera)
        end = world_to_screen(Vector2(x, config.WORLD_HEIGHT), camera)
        pygame.draw.line(surface, config.GRID_COLOR, start.tuple(), end.tuple(), 1)
    for y in range(0, config.WORLD_HEIGHT + 1, config.GRID_SIZE):
        start = world_to_screen(Vector2(0, y), camera)
        end = world_to_screen(Vector2(config.WORLD_WIDTH, y), camera)
        pygame.draw.line(surface, config.GRID_COLOR, start.tuple(), end.tuple(), 1)

    for camp in config.MONSTER_CAMP_POINTS:
        point = _screen_point(match, camp)
        pygame.draw.circle(surface, (66, 80, 70), point, 64, 2)
        draw_text(surface, "怪物區", (point[0] - 26, point[1] - 8), 16, config.MUTED_TEXT_COLOR)

    if match.elapsed_time >= match.extraction_start_time:
        center = _screen_point(match, match.extraction_zone.center)
        pygame.draw.circle(surface, config.EXTRACTION_COLOR, center, round(match.extraction_zone.radius), 4)
        pygame.draw.circle(surface, (60, 100, 140), center, round(match.extraction_zone.radius), 1)
        draw_text(surface, "撤離區", (center[0] - 25, center[1] - 9), 18, config.EXTRACTION_COLOR)

    for monster in match.monsters:
        if not monster.alive:
            continue
        point = _screen_point(match, monster.position)
        pygame.draw.circle(surface, config.MONSTER_COLOR, point, config.MONSTER_DRAW_RADIUS)
        _draw_health_bar(surface, point, monster.health, monster.max_health, -29, 58)
        draw_text(surface, f"{monster.health:.0f}/{monster.max_health:.0f}", (point[0], point[1] - 43), 12, config.TEXT_COLOR, True)

    # 技能效果畫在怪物上方、玩家下方，確保範圍與投射物不會被地圖物件遮住。
    for effect in match.effects:
        _draw_ability_effect(surface, match, effect)

    # 狀態標記在技能圖形之後繪製，確保實際被控場的目標一定看得到回饋。
    for monster in match.monsters:
        if monster.alive:
            _draw_control_status(
                surface,
                _screen_point(match, monster.position),
                config.MONSTER_DRAW_RADIUS,
                monster.slow_timer,
                monster.slow_multiplier,
                monster.root_timer,
            )

    for player in match.players:
        point = _screen_point(match, player.position)
        color = config.PLAYER_COLORS[player.player_id % len(config.PLAYER_COLORS)]
        if not player.alive:
            pygame.draw.circle(surface, config.DANGER_COLOR, point, config.PLAYER_DRAW_RADIUS, 2)
            pygame.draw.line(surface, config.DANGER_COLOR, (point[0] - 9, point[1] - 9), (point[0] + 9, point[1] + 9), 2)
            pygame.draw.line(surface, config.DANGER_COLOR, (point[0] + 9, point[1] - 9), (point[0] - 9, point[1] + 9), 2)
            _draw_player_overlay(surface, player, point)
            continue
        _draw_role_shape(surface, point, config.PLAYER_DRAW_RADIUS, color, player.character_id, player.aim_direction)
        if player.player_id == 0:
            # 額外外框讓人類玩家在地圖、怪物與技能效果中保持容易辨識。
            pygame.draw.circle(surface, config.ACCENT_COLOR, point, config.PLAYER_DRAW_RADIUS + 5, 2)
        aim_end = player.position + player.aim_direction.normalized() * 26
        pygame.draw.line(surface, config.TEXT_COLOR, point, _screen_point(match, aim_end), 2)
        draw_text(surface, str(player.player_id), (point[0] - 4, point[1] - 8), 16, config.PANEL_COLOR)
        _draw_player_overlay(surface, player, point)
        _draw_control_status(
            surface,
            point,
            config.PLAYER_DRAW_RADIUS,
            player.slow_timer,
            player.slow_multiplier,
            player.root_timer,
        )
        _draw_defense_status(surface, player, point)
    if match.players and input_state is not None:
        player = match.players[0]
        slot = _preview_slot(input_state)
        if slot is not None and player.alive:
            guide = build_aim_guide(
                player,
                slot,
                player.aim_direction,
                valid=_preview_is_valid(player, slot),
            )
            _draw_aim_guide(surface, match, guide)


def draw_hud(surface: pygame.Surface, match: MatchState, input_state: InputState | None = None) -> None:
    if not match.players:
        return
    player = match.players[0]
    panel = pygame.Rect(16, 16, 470, 276)
    pygame.draw.rect(surface, config.PANEL_COLOR, panel, border_radius=8)
    pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, panel, 2, border_radius=8)
    from .characters import get_character_definition, get_tactical_definition

    character = get_character_definition(player.character_id)
    tactical = get_tactical_definition(player.tactical_id)
    draw_text(surface, f"玩家 0｜{character.display_name}", (30, 27), 24, config.TEXT_COLOR)
    draw_text(surface, f"生命 {player.health:.0f}/{player.max_health:.0f}", (30, 58), 20, config.TEXT_COLOR)
    pellet_text = "×5" if player.character_id == CharacterId.BREACHER else "/0.15s" if player.character_id == CharacterId.SIPHONER else ""
    draw_text(surface, f"普攻火力 {character.primary_damage:.0f}{pellet_text}｜射程 {character.primary_range:.0f}", (30, 84), 18, config.ACCENT_COLOR)
    draw_text(surface, f"飛行速度 {_speed_label(player)}", (30, 108), 18, config.ACCENT_COLOR)
    draw_text(surface, f"彈藥 {player.ammo}/{player.ammo_capacity}｜補彈計時 {player.ammo_recovery_timer:.1f}s", (30, 132), 18, config.ACCENT_COLOR)
    draw_text(surface, f"大招能量 {player.ultimate_energy:.0f}%", (30, 156), 18, config.ACCENT_COLOR)
    primary_status = "可射擊" if player.primary_cooldown <= 0 else f"普攻冷卻 {player.primary_cooldown:.1f}s"
    tactical_status = "可使用" if player.tactical_cooldown <= 0 else f"配件冷卻 {player.tactical_cooldown:.1f}s"
    draw_text(surface, f"強化 {player.upgrade_stacks}/10｜{primary_status}", (30, 180), 18, config.WARNING_COLOR)
    draw_text(surface, f"{tactical.display_name}｜{tactical_status}", (30, 204), 18, config.WARNING_COLOR)
    if not player.alive:
        draw_text(surface, f"死亡｜{player.death_timer:.1f}s 後重生", (30, 228), 17, config.DANGER_COLOR)
    elif player.character_id == CharacterId.SNIPER:
        draw_text(surface, f"普攻提示：按住左鍵蓄力 {player.primary_charge:.1f}/0.6s，放開射擊", (30, 228), 16, config.MUTED_TEXT_COLOR)
    elif player.character_id == CharacterId.SIPHONER:
        draw_text(surface, "普攻提示：按住左鍵維持吸能光束，放開停止", (30, 228), 16, config.MUTED_TEXT_COLOR)
    else:
        draw_text(surface, "普攻提示：按住瞄準、放開施放｜大招：右鍵", (30, 228), 16, config.MUTED_TEXT_COLOR)
    preview_slot = _preview_slot(input_state)
    if preview_slot is not None:
        preview_name = {"primary": "普攻", "ultimate": "大招", "tactical": "配件"}[preview_slot]
        preview_state = "可施放" if _preview_is_valid(player, preview_slot) else "資源／冷卻不足"
        preview_color = config.ACCENT_COLOR if preview_state == "可施放" else config.AIM_GUIDE_INVALID_COLOR
        draw_text(surface, f"目前瞄準：{preview_name}｜{preview_state}", (30, 249), 16, preview_color)
    active_status = None
    active_status_color = config.TEXT_COLOR
    if player.invulnerability_timer > 0.0:
        active_status = f"目前狀態：免傷 {player.invulnerability_timer:.1f}s"
        active_status_color = config.ACCENT_COLOR
    elif player.damage_reduction_timer > 0.0:
        active_status = f"目前狀態：大招減傷 {player.damage_reduction_timer:.1f}s"
        active_status_color = config.TEXT_COLOR
    elif player.shield_timer > 0.0 and player.shield_remaining > 0.0:
        active_status = f"目前狀態：護盾 {player.shield_remaining:.0f}｜{player.shield_timer:.1f}s"
        active_status_color = config.EXTRACTION_COLOR
    elif player.root_timer > 0.0:
        active_status = f"目前狀態：定身 {player.root_timer:.1f}s"
        active_status_color = config.EXTRACTION_COLOR
    elif player.slow_timer > 0.0:
        active_status = f"目前狀態：減速 {player.slow_multiplier:.1f}x｜{player.slow_timer:.1f}s"
        active_status_color = config.WARNING_COLOR
    if active_status:
        draw_text(surface, active_status, (30, 267), 15, active_status_color)
    remaining = max(0.0, match.duration - match.elapsed_time)
    draw_text(surface, f"剩餘 {remaining:05.1f}s", (config.WINDOW_WIDTH - 180, 20), 28, config.WARNING_COLOR)
    if match.elapsed_time >= match.extraction_start_time:
        draw_text(surface, f"撤離進度 {player.extraction_progress:04.1f}/10.0s", (config.WINDOW_WIDTH - 270, 54), 20, config.EXTRACTION_COLOR)
    draw_text(surface, "WASD 移動｜左鍵普攻｜右鍵大招｜Space 配件｜F1 測試", (16, config.WINDOW_HEIGHT - 30), 18, config.MUTED_TEXT_COLOR)
    _draw_player_roster(surface, match)
    if match.developer_mode.enabled:
        draw_text(surface, f"開發者模式｜假玩家 {match.developer_mode.selected_dummy_id}｜1～5選取 M放入 N返回", (16, 300), 19, config.WARNING_COLOR)


def draw_match(surface: pygame.Surface, match: MatchState, input_state: InputState | None = None) -> None:
    draw_world(surface, match, input_state)
    draw_hud(surface, match, input_state)


def draw_result(surface: pygame.Surface, match: MatchState) -> None:
    surface.fill(config.BACKGROUND_COLOR)
    if match.phase == MatchPhase.VICTORY:
        title = f"玩家 {match.winner_id} 獲勝！"
        color = config.ACCENT_COLOR
    else:
        title = "無人勝利"
        color = config.WARNING_COLOR
    draw_text(surface, title, (config.WINDOW_WIDTH // 2, 260), 58, color, True)
    draw_text(surface, "按 R 重新開始｜按 Esc 離開", (config.WINDOW_WIDTH // 2, 350), 28, config.TEXT_COLOR, True)
