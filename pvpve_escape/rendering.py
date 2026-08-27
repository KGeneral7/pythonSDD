"""只負責 Pygame 繪製，不在繪製函式中修改遊戲狀態。"""

from __future__ import annotations

import math

import pygame

from . import config
from .aiming import build_aim_guide
from .auto_aim import AutoAimResult, resolve_auto_aim
from .characters import get_character_definition
from .controllers import InputState
from .models import AimGuide, AbilityEffect, CharacterId, MatchPhase, MatchState, MonsterType, PlayerState, TacticalId, Vector2
from .monsters import get_monster_definition
from .terrain import is_player_visible_to_viewer
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

# 頭頂 HUD 的所有元素都使用同一個螢幕錨點；寬度與邊界集中管理，
# 讓角色靠近視窗邊緣時只夾取當幀的資訊區塊，不會把資訊搬回固定角落。
_OVERHEAD_MAX_WIDTH = 240
_OVERHEAD_VIEWPORT_MARGIN = 8
_OVERHEAD_PRIVATE_ROW_WIDTH = _OVERHEAD_MAX_WIDTH
_OVERHEAD_IDENTITY_Y_OFFSET = -82
_OVERHEAD_HEALTH_BAR_Y_OFFSET = -62
_OVERHEAD_HEALTH_TEXT_Y_OFFSET = -50
_OVERHEAD_PRIVATE_ROW_Y_OFFSET = -36
_OVERHEAD_PRIVATE_ROW_HEIGHT = 24
_OVERHEAD_MAX_AMMO_SEGMENTS = 8
_DEATH_COUNTDOWN_FONT_SIZE = 56


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


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill_color: tuple[int, int, int] = config.PANEL_COLOR,
    border_color: tuple[int, int, int] = config.PANEL_BORDER_COLOR,
    border_width: int = 2,
    radius: int = 8,
    opacity_percent: int | float | None = None,
) -> None:
    """以局部 SRCALPHA surface 繪製半透明資訊面板。"""

    safe_rect = rect.copy()
    if safe_rect.width <= 0 or safe_rect.height <= 0:
        return
    alpha_value = config.gui_panel_alpha(
        config.GUI_OPACITY_PERCENT if opacity_percent is None else opacity_percent
    )
    panel = pygame.Surface(safe_rect.size, pygame.SRCALPHA)
    panel_rect = panel.get_rect()
    pygame.draw.rect(panel, (*fill_color, alpha_value), panel_rect, border_radius=max(0, radius))
    if border_width > 0:
        pygame.draw.rect(
            panel,
            (*border_color, alpha_value),
            panel_rect,
            max(1, int(border_width)),
            border_radius=max(0, radius),
        )
    surface.blit(panel, safe_rect.topleft)


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


def _truncate_text_to_width(text: str, size: int, max_width: int) -> str:
    """以目前遊戲字型將文字縮到指定寬度，超出時保留省略號。"""

    if max_width <= 0:
        return ""
    font = _get_text_font(size)
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "…"
    if font.size(ellipsis)[0] > max_width:
        return ""
    shortened = text
    while shortened and font.size(shortened + ellipsis)[0] > max_width:
        shortened = shortened[:-1]
    return shortened + ellipsis


def _overhead_width(surface: pygame.Surface, width: int = _OVERHEAD_MAX_WIDTH) -> int:
    """將頭頂資訊寬度限制在視窗可用範圍內。"""

    available_width = max(1, surface.get_width() - _OVERHEAD_VIEWPORT_MARGIN * 2)
    return min(max(1, int(width)), available_width)


def _overhead_left(surface: pygame.Surface, center_x: int, width: int = _OVERHEAD_MAX_WIDTH) -> int:
    """回傳符合視窗左右邊界的頭頂資訊區塊左緣。"""

    viewport_left = _OVERHEAD_VIEWPORT_MARGIN
    viewport_right = max(viewport_left, surface.get_width() - _OVERHEAD_VIEWPORT_MARGIN)
    safe_width = _overhead_width(surface, width)
    maximum_left = max(viewport_left, viewport_right - safe_width)
    desired_left = round(center_x - safe_width / 2)
    return max(viewport_left, min(maximum_left, desired_left))


def _overhead_vertical_shift(surface: pygame.Surface, center_y: int) -> int:
    """將頭頂資訊整組限制在視窗上下邊界內，仍保留玩家作為錨點。"""

    identity_half_height = _get_text_font(14).get_height() // 2
    block_top = center_y + _OVERHEAD_IDENTITY_Y_OFFSET - identity_half_height
    block_bottom = center_y + _OVERHEAD_PRIVATE_ROW_Y_OFFSET + _OVERHEAD_PRIVATE_ROW_HEIGHT
    viewport_top = _OVERHEAD_VIEWPORT_MARGIN
    viewport_bottom = surface.get_height() - _OVERHEAD_VIEWPORT_MARGIN
    if block_top < viewport_top:
        return viewport_top - block_top
    if block_bottom > viewport_bottom:
        return viewport_bottom - block_bottom
    return 0


def _speed_label(player_or_definition: PlayerState | object) -> str:
    definition = (
        get_character_definition(player_or_definition.character_id)
        if isinstance(player_or_definition, PlayerState)
        else player_or_definition
    )
    if definition.projectile_speed <= 0:
        return "近戰" if definition.character_id == CharacterId.GUARDIAN else "引導"
    return f"{definition.projectile_speed:.0f}"


def _selection_attack_hint(definition: object) -> str:
    """由既有角色定義推導選角頁的普攻操作提示。"""

    if definition.character_id == CharacterId.SNIPER:
        charge_time = definition.parameters.get("charge", 0.6)
        return f"普攻：按住左鍵蓄力 {charge_time:.1f}s，放開射擊"
    if definition.character_id == CharacterId.SIPHONER:
        return "普攻：按住左鍵持續引導吸能，放開停止"
    return "普攻：左鍵瞄準後施放"


def draw_selection(
    surface: pygame.Surface,
    selected_character_index: int,
    selected_tactical_index: int,
) -> None:
    """繪製角色／配件選擇畫面與鍵盤提示。"""

    surface.fill(config.BACKGROUND_COLOR)
    from .characters import get_all_character_definitions, get_all_tactical_definitions

    draw_text(surface, "PvPvE 中央撤離競技", (config.WINDOW_WIDTH // 2, 48), 42, config.ACCENT_COLOR, True)
    draw_text(surface, "按 1～6 選擇角色，Q/W/E 選擇配件，Enter 開始，I 查看玩法", (config.WINDOW_WIDTH // 2, 88), 24, config.MUTED_TEXT_COLOR, True)
    draw_text(surface, "操作：左鍵普攻｜右鍵大招｜Space 配件", (config.WINDOW_WIDTH // 2, 112), 20, config.WARNING_COLOR, True)
    definitions = get_all_character_definitions()
    card_width, card_height = 280, 142
    for index, definition in enumerate(definitions):
        column = index % 3
        row = index // 3
        rect = pygame.Rect(70 + column * 390, 135 + row * 155, card_width, card_height)
        selected = index == selected_character_index
        draw_panel(
            surface,
            rect,
            border_color=config.ACCENT_COLOR if selected else config.PANEL_BORDER_COLOR,
            border_width=3,
            radius=10,
        )
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
        draw_text(
            surface,
            _truncate_text_to_width(_selection_attack_hint(definition), 14, card_width - 28),
            (rect.x + 14, rect.y + 121),
            14,
            config.MUTED_TEXT_COLOR,
        )
    tactics = get_all_tactical_definitions()
    draw_text(surface, "戰術配件", (70, 470), 28, config.WARNING_COLOR)
    for index, definition in enumerate(tactics):
        rect = pygame.Rect(70 + index * 390, 510, 280, 88)
        selected = index == selected_tactical_index
        draw_panel(
            surface,
            rect,
            border_color=config.WARNING_COLOR if selected else config.PANEL_BORDER_COLOR,
            border_width=3,
            radius=8,
        )
        draw_text(surface, f"{('Q', 'W', 'E')[index]}  {definition.display_name}", (rect.x + 14, rect.y + 12), 24, config.WARNING_COLOR if selected else config.TEXT_COLOR)
        draw_text(surface, f"冷卻 {definition.cooldown:.0f}s", (rect.x + 14, rect.y + 46), 18, config.MUTED_TEXT_COLOR)
        draw_text(
            surface,
            _truncate_text_to_width(definition.description, 13, rect.width - 28),
            (rect.x + 14, rect.y + 68),
            13,
            config.TEXT_COLOR,
        )
    draw_text(surface, "假玩家固定不移動、不攻擊；可在比賽中使用 F1 開發者測試。", (70, 655), 20, config.MUTED_TEXT_COLOR)


def draw_intro(surface: pygame.Surface) -> None:
    """繪製開場玩法介紹，讓第一次進入遊戲即可知道目標與操作。"""

    surface.fill(config.BACKGROUND_COLOR)
    draw_text(surface, "PvPvE 中央撤離競技", (config.WINDOW_WIDTH // 2, 48), 44, config.ACCENT_COLOR, True)
    draw_text(surface, "玩法導覽｜活下來、收集強化，並在最後撤離", (config.WINDOW_WIDTH // 2, 91), 25, config.TEXT_COLOR, True)

    panels = (
        (pygame.Rect(54, 135, 370, 430), "一局怎麼玩", config.ACCENT_COLOR),
        (pygame.Rect(455, 135, 370, 430), "戰鬥與操作", config.WARNING_COLOR),
        (pygame.Rect(856, 135, 370, 430), "敵人與瞄準", config.EXTRACTION_COLOR),
    )
    for rect, title, color in panels:
        draw_panel(surface, rect, border_color=color, border_width=2, radius=12)
        draw_text(surface, title, (rect.x + 24, rect.y + 22), 29, color)

    left_lines = (
        "1. 在地圖外圍出生，和其他玩家競爭。",
        "2. 擊敗怪物取得強化層數與大招能量。",
        "3. 210 秒後中央撤離區開啟。",
        "4. 在撤離區累積 10 秒即可獲勝。",
        "",
        "死亡會在 5 秒後回到自己的出生點，",
        "但本次生命的強化與大招能量會重置。",
        "薄牆可以破壞，草叢可作為走位掩護。",
    )
    for index, line in enumerate(left_lines):
        draw_text(surface, line, (78, 206 + index * 39), 18, config.TEXT_COLOR if line else config.MUTED_TEXT_COLOR)

    middle_lines = (
        "WASD      移動",
        "滑鼠左鍵  普攻／蓄力",
        "滑鼠右鍵  大招",
        "Space     戰術配件",
        "Tab       切換自動瞄準",
        "R         回到選角頁",
        "",
        "自動瞄準預設開啟，只會取",
        f"{config.AUTO_AIM_LOOKBACK_SECONDS:.2f} 秒前的位置。",
        "子彈離手後不追蹤，請靠走位閃避。",
    )
    for index, line in enumerate(middle_lines):
        draw_text(surface, line, (479, 206 + index * 32), 18, config.TEXT_COLOR if line else config.MUTED_TEXT_COLOR)

    right_lines = (
        "追獵獸  追近玩家並接觸攻擊",
        "砲台蟲  保持距離發射慢速子彈",
        "重裝巨獸  血厚、速度慢、近戰痛",
        "",
        "自動瞄準只鎖定目前扇形內最近目標，",
        "標記顯示的是回看位置，不是必中點。",
        "你改變方向或離開瞄準角度，",
        "就能讓攻擊落空。",
    )
    for index, line in enumerate(right_lines):
        draw_text(surface, line, (880, 206 + index * 39), 18, config.TEXT_COLOR if line else config.MUTED_TEXT_COLOR)

    draw_text(surface, "Enter／Space 開始選擇角色    Esc 返回選角", (config.WINDOW_WIDTH // 2, 623), 24, config.ACCENT_COLOR, True)
    draw_text(surface, "第一次遊玩建議先看完導覽；選角頁可按 I 再次查看。", (config.WINDOW_WIDTH // 2, 663), 18, config.MUTED_TEXT_COLOR, True)


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
    draw_panel(surface, bar, border_width=0, radius=0)
    if ratio > 0:
        health_color = config.DANGER_COLOR if ratio <= 0.3 else config.WARNING_COLOR if ratio <= 0.6 else config.ACCENT_COLOR
        pygame.draw.rect(surface, health_color, (bar.x + 1, bar.y + 1, max(1, round((bar.width - 2) * ratio)), bar.height - 2))


def _draw_ammo_segments(
    surface: pygame.Surface,
    left: int,
    top: int,
    ammo: int,
    capacity: int,
) -> None:
    """繪製固定寬度、可辨識空格的彈藥分段。"""

    safe_capacity = max(0, min(_OVERHEAD_MAX_AMMO_SEGMENTS, int(capacity)))
    safe_ammo = max(0, min(safe_capacity, int(ammo)))
    if safe_capacity == 0:
        return
    segment_gap = 2
    segment_width = max(3, (56 - segment_gap * (safe_capacity - 1)) // safe_capacity)
    for index in range(safe_capacity):
        rect = pygame.Rect(left + index * (segment_width + segment_gap), top, segment_width, 10)
        if index < safe_ammo:
            pygame.draw.rect(surface, config.ACCENT_COLOR, rect)
        else:
            pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, 1)


def _safe_display_float(value: float, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = minimum
    if not math.isfinite(numeric):
        numeric = minimum
    return max(minimum, min(maximum, numeric))


def _draw_player_overlay(
    surface: pygame.Surface,
    player: PlayerState,
    point: tuple[int, int],
    show_private_info: bool = False,
) -> None:
    """繪製玩家頭頂公開資訊，並在觀看者為本人時追加私人戰鬥列。"""

    character = get_character_definition(player.character_id)
    label_color = config.PLAYER_COLORS[player.player_id % len(config.PLAYER_COLORS)] if player.alive else config.DANGER_COLOR
    raw_max_health = _safe_display_float(player.max_health, 1.0, 1_000_000.0)
    safe_health = _safe_display_float(player.health, 0.0, raw_max_health)
    overhead_width = _overhead_width(surface, _OVERHEAD_PRIVATE_ROW_WIDTH)
    overhead_left = _overhead_left(surface, point[0], overhead_width)
    overhead_center = (
        overhead_left + overhead_width // 2,
        point[1] + _overhead_vertical_shift(surface, point[1]),
    )
    _draw_health_bar(
        surface,
        overhead_center,
        safe_health,
        raw_max_health,
        _OVERHEAD_HEALTH_BAR_Y_OFFSET,
        62,
    )
    identity = _truncate_text_to_width(
        f"{player.player_id} {character.display_name}",
        14,
        overhead_width - 16,
    )
    draw_text(
        surface,
        identity,
        (overhead_center[0], overhead_center[1] + _OVERHEAD_IDENTITY_Y_OFFSET),
        14,
        label_color,
        True,
    )
    draw_text(
        surface,
        f"{safe_health:.0f}/{raw_max_health:.0f}",
        (overhead_center[0], overhead_center[1] + _OVERHEAD_HEALTH_TEXT_Y_OFFSET),
        13,
        config.TEXT_COLOR,
        True,
    )

    if not show_private_info:
        return

    private_row = pygame.Rect(
        overhead_left,
        overhead_center[1] + _OVERHEAD_PRIVATE_ROW_Y_OFFSET,
        overhead_width,
        _OVERHEAD_PRIVATE_ROW_HEIGHT,
    )
    draw_panel(
        surface,
        private_row,
        fill_color=config.PANEL_COLOR,
        border_color=config.PANEL_BORDER_COLOR,
        border_width=1,
        radius=6,
    )
    safe_capacity = max(0, min(_OVERHEAD_MAX_AMMO_SEGMENTS, int(player.ammo_capacity)))
    safe_ammo = max(0, min(safe_capacity, int(player.ammo)))
    _draw_ammo_segments(surface, overhead_left + 5, private_row.y + 7, safe_ammo, safe_capacity)
    draw_text(
        surface,
        f"彈藥 {safe_ammo}/{safe_capacity}",
        (overhead_left + 62, private_row.y + 5),
        12,
        config.TEXT_COLOR,
    )
    gadget_color = (
        config.EXTRACTION_COLOR
        if player.alive and player.tactical_cooldown <= 0.0
        else config.PANEL_BORDER_COLOR
    )
    gadget_center = (overhead_left + 124, private_row.y + 12)
    pygame.draw.circle(surface, gadget_color, gadget_center, 8)
    pygame.draw.circle(surface, config.PANEL_COLOR, gadget_center, 4)
    safe_energy = _safe_display_float(player.ultimate_energy, 0.0, config.MAX_ULTIMATE_ENERGY)
    draw_text(
        surface,
        f"大招 {safe_energy:.0f}%",
        (overhead_left + 134, private_row.y + 5),
        12,
        config.EXTRACTION_COLOR if safe_energy >= config.MAX_ULTIMATE_ENERGY else config.TEXT_COLOR,
    )
    safe_upgrade = max(0, min(config.MAX_UPGRADE_STACKS, int(player.upgrade_stacks)))
    draw_text(
        surface,
        f"強化 {safe_upgrade}/{config.MAX_UPGRADE_STACKS}",
        (overhead_left + 198, private_row.y + 5),
        12,
        config.WARNING_COLOR if safe_upgrade else config.TEXT_COLOR,
    )


def _draw_player_roster(surface: pygame.Surface, match: MatchState, viewer_id: int = 0) -> None:
    panel = pygame.Rect(880, 500, 384, 174)
    draw_panel(surface, panel, radius=8)
    draw_text(surface, "玩家／角色", (898, 510), 19, config.TEXT_COLOR)
    visible_players = [
        player
        for player in match.players
        if is_player_visible_to_viewer(player, viewer_id, match.bushes)
    ]
    for index, player in enumerate(visible_players):
        column = index % 2
        row = index // 2
        center = (896 + column * 188, 544 + row * 37)
        color = config.PLAYER_COLORS[player.player_id % len(config.PLAYER_COLORS)]
        _draw_role_shape(surface, center, 8, color, player.character_id, player.aim_direction)
        character = get_character_definition(player.character_id)
        status = "存活" if player.alive else "重生中"
        draw_text(surface, f"{player.player_id} {character.display_name}", (center[0] + 14, center[1] - 10), 15, color)
        draw_text(surface, status, (center[0] + 14, center[1] + 7), 12, config.MUTED_TEXT_COLOR)


def _draw_death_countdown(surface: pygame.Surface, player: PlayerState) -> None:
    """以 Pygame 字型在觀看者本人死亡時顯示中央重生倒數。"""

    if player.alive or player.death_timer <= 0.0:
        return
    remaining = _safe_display_float(player.death_timer, 0.0, config.RESPAWN_DELAY)
    draw_text(
        surface,
        f"死亡倒數 {remaining:.1f}s",
        surface.get_rect().center,
        _DEATH_COUNTDOWN_FONT_SIZE,
        config.DANGER_COLOR,
        True,
    )


def _draw_directional_wedge(
    surface: pygame.Surface,
    center: tuple[int, int],
    direction: Vector2,
    radius: float,
    angle_degrees: float,
    color: tuple[int, int, int],
) -> None:
    # 半徑必須遵守呼叫端提供的世界邊界端點；固定放大到 24 會讓
    # 玩家貼近邊界時的瞄準弧線再次畫出世界外。
    radius = max(1, round(radius))
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


def _draw_translucent_polygon(
    surface: pygame.Surface,
    points: list[tuple[int, int]],
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    """只在幾何圖形的包圍盒建立 alpha surface，避免污染世界前景。"""

    if len(points) < 3:
        return
    min_x = max(0, min(point[0] for point in points))
    min_y = max(0, min(point[1] for point in points))
    max_x = min(surface.get_width() - 1, max(point[0] for point in points))
    max_y = min(surface.get_height() - 1, max(point[1] for point in points))
    if min_x > max_x or min_y > max_y:
        return
    overlay = pygame.Surface((max_x - min_x + 1, max_y - min_y + 1), pygame.SRCALPHA)
    local_points = [(x - min_x, y - min_y) for x, y in points]
    pygame.draw.polygon(overlay, (*color, max(0, min(255, int(alpha)))), local_points)
    surface.blit(overlay, (min_x, min_y))


def _draw_filled_directional_wedge(
    surface: pygame.Surface,
    center: tuple[int, int],
    direction: Vector2,
    radius: float,
    angle_degrees: float,
    color: tuple[int, int, int],
    alpha: int = 76,
) -> list[tuple[int, int]]:
    """繪製方向一致的填色扇形，回傳外弧點供呼叫端補上邊框。"""

    safe_radius = max(1, round(radius))
    heading = math.atan2(direction.y, direction.x)
    half_angle = math.radians(angle_degrees) / 2
    arc_points = [
        _polar_point(
            center,
            heading - half_angle + 2 * half_angle * index / 16,
            safe_radius,
        )
        for index in range(17)
    ]
    _draw_translucent_polygon(surface, [center, *arc_points], color, alpha)
    pygame.draw.lines(surface, color, False, [center, *arc_points], 2)
    return arc_points


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
            _draw_translucent_polygon(surface, [origin, *points], color, 58)
            for point in points:
                pygame.draw.line(surface, color, origin, point, 3)
            pygame.draw.lines(surface, color, False, points, 2)
        else:
            _draw_filled_directional_wedge(
                surface,
                origin,
                guide.direction,
                min(guide.range, guide.origin.distance_to(guide.end)),
                guide.angle_degrees,
                color,
                58,
            )
            _draw_directional_wedge(
                surface,
                origin,
                guide.direction,
                min(guide.range, guide.origin.distance_to(guide.end)),
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
        cone_origin = _screen_point(match, effect.origin)
        front_distance = min(effect.max_distance, max(0.0, effect.distance_travelled))
        arc_points = _draw_filled_directional_wedge(
            surface,
            cone_origin,
            direction,
            front_distance,
            float(effect.metadata.get("angle", 60)),
            config.ABILITY_COLORS["breach"],
            82,
        )
        if arc_points:
            pygame.draw.lines(surface, config.ABILITY_COLORS["breach"], False, arc_points, 3)
        for result in effect.metadata.get("impact_results", {}).values():
            if not isinstance(result, dict):
                continue
            impact_position = result.get("position")
            if not isinstance(impact_position, Vector2):
                continue
            impact_point = _screen_point(match, impact_position)
            impact_color = config.EXTRACTION_COLOR if result.get("effective_damage", 0) > 0 else config.DANGER_COLOR
            pygame.draw.circle(surface, impact_color, impact_point, 20, 3)
            pygame.draw.line(surface, impact_color, (impact_point[0] - 12, impact_point[1]), (impact_point[0] + 12, impact_point[1]), 2)
            pygame.draw.line(surface, impact_color, (impact_point[0], impact_point[1] - 12), (impact_point[0], impact_point[1] + 12), 2)
    elif kind == "breach_pellet":
        tail = effect.metadata.get("visible_start")
        if not isinstance(tail, Vector2):
            tail = effect.position - direction * 26
        screen_tail = _screen_point(match, tail)
        pellet_radius = max(1, int(round(config.BREACH_PELLET_RADIUS)))
        pellet_width = max(1, pellet_radius * 2)
        pygame.draw.line(surface, config.ABILITY_COLORS["breach"], screen_tail, point, pellet_width)
        pygame.draw.circle(surface, config.ABILITY_COLORS["breach"], point, pellet_radius)
        pygame.draw.circle(surface, config.TEXT_COLOR, point, pellet_radius, 1)
    elif kind == "sniper_line":
        impact_blocked = bool(effect.metadata.get("impact_blocked", 0))
        impact_color = config.DANGER_COLOR if impact_blocked else config.ABILITY_COLORS["sniper"]
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
            pygame.draw.line(surface, config.ABILITY_COLORS["sniper"], screen_tail, point, 6)
            pygame.draw.circle(surface, config.ABILITY_COLORS["sniper"], point, 9)
            pygame.draw.circle(surface, config.TEXT_COLOR, point, 9, 2)
    elif kind == "sniper_ultimate_line":
        end = effect.position + direction * effect.max_distance
        line_color = config.ABILITY_COLORS["sniper"]
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
            config.ABILITY_COLORS["guardian"],
        )
    elif kind == "boomerang":
        tail = effect.metadata.get("visible_start")
        if not isinstance(tail, Vector2):
            tail = effect.position - direction * 48
        pygame.draw.line(surface, config.ABILITY_COLORS["hunter"], _screen_point(match, tail), point, 6)
        blade = [
            _oriented_point(point, direction, 23, 0),
            _oriented_point(point, direction, 0, 11),
            _oriented_point(point, direction, -23, 0),
            _oriented_point(point, direction, 0, -11),
        ]
        pygame.draw.polygon(surface, config.ABILITY_COLORS["hunter"], blade)
        pygame.draw.polygon(surface, config.TEXT_COLOR, blade, 2)
        pygame.draw.circle(surface, config.TEXT_COLOR, point, 6, 2)
    elif kind == "mine":
        owner = next((player for player in match.players if player.player_id == effect.owner_id), None)
        if not effect.armed:
            tail = effect.metadata.get("visible_start")
            if not isinstance(tail, Vector2) and owner is not None:
                tail = owner.position
            if isinstance(tail, Vector2):
                pygame.draw.line(surface, config.ABILITY_COLORS["controller"], _screen_point(match, tail), point, 3)
            pygame.draw.circle(surface, config.ABILITY_COLORS["controller"], point, 9, 2)
            pygame.draw.circle(surface, config.TEXT_COLOR, point, 4)
        else:
            radius = max(24, round(float(effect.metadata.get("area_radius", effect.radius))))
            pygame.draw.circle(surface, config.ABILITY_COLORS["controller"], point, radius, 3)
            pygame.draw.circle(surface, config.ABILITY_COLORS["controller"], point, max(7, radius // 5), 2)
            pygame.draw.line(surface, config.ABILITY_COLORS["controller"], (point[0] - 10, point[1] - 10), (point[0] + 10, point[1] + 10), 2)
            pygame.draw.line(surface, config.ABILITY_COLORS["controller"], (point[0] + 10, point[1] - 10), (point[0] - 10, point[1] + 10), 2)
    elif kind == "beam":
        end = effect.position + direction * effect.max_distance
        screen_end = _screen_point(match, end)
        pygame.draw.line(surface, config.ABILITY_COLORS["siphoner"], point, screen_end, 10)
        pygame.draw.line(surface, config.TEXT_COLOR, point, screen_end, 3)
        pygame.draw.circle(surface, config.ACCENT_COLOR, point, 12, 2)
    elif kind in {"breach_burst", "siphon_burst"}:
        radius = max(30, round(effect.radius))
        color = config.ABILITY_COLORS["breach"] if kind == "breach_burst" else config.ABILITY_COLORS["siphoner"]
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
        pygame.draw.circle(surface, config.ABILITY_COLORS["guardian"], point, 29, 2)
    elif kind == "hunter_dash":
        end = effect.position + direction * effect.max_distance
        screen_end = _screen_point(match, end)
        pygame.draw.line(surface, config.ABILITY_COLORS["hunter"], point, screen_end, 10)
        pygame.draw.line(surface, config.TEXT_COLOR, point, screen_end, 3)
        pygame.draw.circle(surface, config.ABILITY_COLORS["hunter"], point, 20, 3)
        pygame.draw.circle(surface, config.ABILITY_COLORS["hunter"], screen_end, 20, 3)
    elif kind == "gravity_cage":
        radius = max(30, round(effect.radius))
        pygame.draw.circle(surface, config.ABILITY_COLORS["controller"], point, radius, 5)
        pygame.draw.circle(surface, config.EXTRACTION_COLOR, point, max(18, radius - 24), 2)
        for index in range(4):
            angle = index * math.pi / 2 + math.pi / 4
            pygame.draw.line(
                surface,
                config.ABILITY_COLORS["controller"],
                _polar_point(point, angle, radius - 14),
                _polar_point(point, angle + math.pi, radius - 14),
                2,
            )
    elif kind == "dash":
        end = effect.position + direction * effect.max_distance
        screen_end = _screen_point(match, end)
        pygame.draw.line(surface, config.ABILITY_COLORS["tactical"], point, screen_end, 8)
        pygame.draw.circle(surface, config.ABILITY_COLORS["tactical"], point, 24, 3)
        pygame.draw.circle(surface, config.TEXT_COLOR, screen_end, 12, 2)
    elif kind == "shield":
        pygame.draw.circle(surface, config.ABILITY_COLORS["tactical"], point, 36, 5)
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


def _monster_color(monster_type: MonsterType) -> tuple[int, int, int]:
    return {
        MonsterType.CHASER: config.MONSTER_CHASER_COLOR,
        MonsterType.SHOOTER: config.MONSTER_SHOOTER_COLOR,
        MonsterType.BRUTE: config.MONSTER_BRUTE_COLOR,
    }.get(monster_type, config.MONSTER_COLOR)


def _draw_monster_shape(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    monster_type: MonsterType,
    direction: Vector2,
) -> None:
    """用形狀區分三種怪物，不依賴額外圖片素材。"""

    radius = max(7, int(radius))
    color = _monster_color(monster_type)
    heading = _effect_direction(direction)
    if monster_type == MonsterType.CHASER:
        pygame.draw.circle(surface, color, center, radius)
        pygame.draw.circle(surface, config.TEXT_COLOR, center, radius, 2)
        pygame.draw.circle(surface, config.DANGER_COLOR, center, max(3, radius // 3))
        return
    if monster_type == MonsterType.SHOOTER:
        points = [
            _oriented_point(center, heading, radius * 1.35, 0),
            _oriented_point(center, heading, 0, radius * 0.9),
            _oriented_point(center, heading, -radius * 1.35, 0),
            _oriented_point(center, heading, 0, -radius * 0.9),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, config.TEXT_COLOR, points, 2)
        pygame.draw.circle(surface, config.DANGER_COLOR, center, max(3, radius // 3))
        return
    points = [
        _polar_point(center, math.radians(30 + index * 60), radius)
        for index in range(6)
    ]
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, config.TEXT_COLOR, points, 2)
    pygame.draw.line(surface, config.DANGER_COLOR, (center[0] - radius // 2, center[1]), (center[0] + radius // 2, center[1]), 3)


def _draw_monster_projectile(
    surface: pygame.Surface,
    match: MatchState,
    projectile,
) -> None:
    point = _screen_point(match, projectile.position)
    if projectile.impact_position is not None:
        impact = _screen_point(match, projectile.impact_position)
        color = config.DANGER_COLOR if projectile.impact_status != "命中" else config.EXTRACTION_COLOR
        pygame.draw.circle(surface, color, impact, 17, 3)
        pygame.draw.line(surface, color, (impact[0] - 11, impact[1] - 11), (impact[0] + 11, impact[1] + 11), 2)
        pygame.draw.line(surface, color, (impact[0] + 11, impact[1] - 11), (impact[0] - 11, impact[1] + 11), 2)
        draw_text(surface, f"怪物子彈｜{projectile.impact_status}", (impact[0], impact[1] - 25), 13, color, True)
        return
    tail = _screen_point(match, projectile.previous_position)
    pygame.draw.line(surface, config.MONSTER_PROJECTILE_COLOR, tail, point, 4)
    pygame.draw.circle(surface, config.MONSTER_PROJECTILE_COLOR, point, max(4, round(projectile.radius)))
    pygame.draw.circle(surface, config.TEXT_COLOR, point, max(4, round(projectile.radius)), 1)


def _draw_auto_aim_marker(
    surface: pygame.Surface,
    match: MatchState,
    result: AutoAimResult,
) -> None:
    if result.target_position is None:
        return
    marker = _screen_point(match, result.target_position)
    color = config.ACCENT_COLOR
    radius = max(8, int(config.AUTO_AIM_TARGET_MARKER_RADIUS))
    pygame.draw.circle(surface, color, marker, radius, 2)
    pygame.draw.line(surface, color, (marker[0] - radius - 4, marker[1]), (marker[0] + radius + 4, marker[1]), 1)
    pygame.draw.line(surface, color, (marker[0], marker[1] - radius - 4), (marker[0], marker[1] + radius + 4), 1)
    draw_text(surface, f"自動瞄準｜{result.lookback_seconds:.2f}s 前", (marker[0], marker[1] - radius - 19), 13, color, True)


def _world_rect_to_screen(
    left: int,
    top: int,
    width: int,
    height: int,
    camera: Vector2,
) -> pygame.Rect:
    """將設定中的世界矩形平移成 Pygame 畫面矩形。"""

    top_left = world_to_screen(Vector2(left, top), camera)
    return pygame.Rect(round(top_left.x), round(top_left.y), width, height)


def _draw_bush(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """繪製草叢填色與少量葉片筆觸，讓草叢和地面有清楚差異。"""

    pygame.draw.rect(surface, config.BUSH_COLOR, rect)
    pygame.draw.rect(surface, config.BUSH_HIGHLIGHT_COLOR, rect, 1)

    # 葉片只放在下方區域，避免覆蓋草叢中心的代表色，也讓無頭測試能穩定取樣。
    leaf_step = max(24, rect.width // 4)
    leaf_base_y = rect.bottom - 10
    for x in range(rect.left + 12, rect.right - 8, leaf_step):
        leaf_top_y = max(rect.top + 4, leaf_base_y - 10)
        pygame.draw.line(
            surface,
            config.BUSH_HIGHLIGHT_COLOR,
            (x - 4, leaf_base_y),
            (x, leaf_top_y),
            2,
        )


def _draw_wall(surface: pygame.Surface, rect: pygame.Rect, kind: str) -> None:
    """繪製厚牆或薄牆，並以裂紋提示薄牆可破壞。"""

    wall_color = config.THICK_WALL_COLOR if kind == "thick_wall" else config.THIN_WALL_COLOR
    pygame.draw.rect(surface, wall_color, rect)
    pygame.draw.rect(surface, config.WALL_BORDER_COLOR, rect, config.WALL_BORDER_WIDTH)

    if kind != "thin_wall":
        return

    crack_count = max(0, config.THIN_WALL_CRACK_COUNT)
    for index in range(crack_count):
        # 將裂紋放在矩形的上、下分區，避免小型薄牆的中心被整條線蓋住。
        vertical_fraction = 0.25 if index % 2 == 0 else 0.75
        crack_x = rect.left + round(rect.width * (index + 1) / (crack_count + 1))
        crack_y = rect.top + round(rect.height * vertical_fraction)
        segment = max(4, min(16, min(rect.width, rect.height) // 4))
        end_x = max(rect.left + 2, crack_x - max(3, segment // 2))
        end_y = min(rect.bottom - 3, crack_y + max(3, segment // 2))
        pygame.draw.line(
            surface,
            config.WALL_BORDER_COLOR,
            (crack_x, crack_y),
            (end_x, end_y),
            config.THIN_WALL_CRACK_WIDTH,
        )


def draw_terrain(surface: pygame.Surface, match: MatchState) -> None:
    """繪製正式配置中的全部草叢與牆體，不以文字標記取代地圖物件。"""

    camera = match.camera.position
    viewport = surface.get_rect()

    # 草叢先畫，牆再畫；若日後配置邊界重疊，牆的阻擋輪廓仍會保持清楚。
    for bush in match.bushes:
        if not bush.active:
            continue
        bounds = bush.bounds
        rect = _world_rect_to_screen(bounds.left, bounds.top, bounds.width, bounds.height, camera)
        if rect.colliderect(viewport):
            # Pygame 會自動裁切，但先跳過完全在視窗外的物件可避免每幀
            # 對遠處地形做不必要的筆觸計算；裁切後的 Rect 仍保留相同顏色
            # 與邊界，因此相機移動到物件時會在正式畫面立即出現。
            _draw_bush(surface, rect.clip(viewport))

    for obstacle in match.obstacles:
        if not obstacle.solid:
            continue
        bounds = obstacle.bounds
        rect = _world_rect_to_screen(bounds.left, bounds.top, bounds.width, bounds.height, camera)
        if rect.colliderect(viewport):
            _draw_wall(surface, rect.clip(viewport), obstacle.kind.value)


def draw_world(
    surface: pygame.Surface,
    match: MatchState,
    input_state: InputState | None = None,
    viewer_id: int = 0,
) -> None:
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

    draw_terrain(surface, match)

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
        monster_radius = max(10, round(monster.radius * 0.85))
        _draw_monster_shape(surface, point, monster_radius, monster.monster_type, monster.aim_direction)
        _draw_health_bar(surface, point, monster.health, monster.max_health, -29, 58)
        draw_text(surface, f"{monster.health:.0f}/{monster.max_health:.0f}", (point[0], point[1] - 43), 12, config.TEXT_COLOR, True)
        definition = get_monster_definition(monster.monster_type)
        draw_text(surface, definition.display_name, (point[0], point[1] + monster_radius + 5), 12, _monster_color(monster.monster_type), True)

    for projectile in match.monster_projectiles:
        _draw_monster_projectile(surface, match, projectile)

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
        if not is_player_visible_to_viewer(player, viewer_id, match.bushes):
            continue
        point = _screen_point(match, player.position)
        color = config.PLAYER_COLORS[player.player_id % len(config.PLAYER_COLORS)]
        show_private_info = player.player_id == viewer_id
        if not player.alive:
            pygame.draw.circle(surface, config.DANGER_COLOR, point, config.PLAYER_DRAW_RADIUS, 2)
            pygame.draw.line(surface, config.DANGER_COLOR, (point[0] - 9, point[1] - 9), (point[0] + 9, point[1] + 9), 2)
            pygame.draw.line(surface, config.DANGER_COLOR, (point[0] + 9, point[1] - 9), (point[0] - 9, point[1] + 9), 2)
            _draw_player_overlay(surface, player, point, show_private_info=show_private_info)
            continue
        _draw_role_shape(surface, point, config.PLAYER_DRAW_RADIUS, color, player.character_id, player.aim_direction)
        if player.player_id == 0:
            # 額外外框讓人類玩家在地圖、怪物與技能效果中保持容易辨識。
            pygame.draw.circle(surface, config.ACCENT_COLOR, point, config.PLAYER_DRAW_RADIUS + 5, 2)
        aim_end = player.position + player.aim_direction.normalized() * 26
        pygame.draw.line(surface, config.TEXT_COLOR, point, _screen_point(match, aim_end), 2)
        draw_text(surface, str(player.player_id), (point[0] - 4, point[1] - 8), 16, config.PANEL_COLOR)
        _draw_player_overlay(surface, player, point, show_private_info=show_private_info)
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
        player = next(
            (candidate for candidate in match.players if candidate.player_id == viewer_id),
            match.players[0],
        )
        slot = _preview_slot(input_state)
        if (
            slot is not None
            and player.alive
            and is_player_visible_to_viewer(player, viewer_id, match.bushes)
        ):
            manual_direction = input_state.aim_direction if input_state.aim_direction.length() else player.aim_direction
            aim_result = resolve_auto_aim(
                match,
                player,
                slot,
                manual_direction,
                obstacles=match.obstacles,
            )
            guide = build_aim_guide(
                player,
                slot,
                aim_result.direction,
                valid=_preview_is_valid(player, slot),
                move_direction=input_state.move_direction,
                range_override=aim_result.target_distance,
                obstacles=match.obstacles,
            )
            _draw_aim_guide(surface, match, guide)
            target = next(
                (
                    candidate
                    for candidate in match.players
                    if candidate.player_id == aim_result.target_id
                ),
            None)
            if aim_result.has_target and (
                target is None
                or is_player_visible_to_viewer(target, viewer_id, match.bushes)
            ):
                _draw_auto_aim_marker(surface, match, aim_result)


def draw_hud(
    surface: pygame.Surface,
    match: MatchState,
    input_state: InputState | None = None,
    viewer_id: int = 0,
) -> None:
    if not match.players:
        return
    player = next(
        (candidate for candidate in match.players if candidate.player_id == viewer_id),
        match.players[0],
    )
    _draw_death_countdown(surface, player)
    remaining = max(0.0, match.duration - match.elapsed_time)
    draw_text(surface, f"剩餘 {remaining:05.1f}s", (config.WINDOW_WIDTH - 180, 20), 28, config.WARNING_COLOR)
    if match.elapsed_time >= match.extraction_start_time:
        draw_text(surface, f"撤離進度 {player.extraction_progress:04.1f}/10.0s", (config.WINDOW_WIDTH - 270, 54), 20, config.EXTRACTION_COLOR)
    draw_text(surface, "WASD 移動｜Tab 自瞄｜F1 測試", (16, config.WINDOW_HEIGHT - 30), 18, config.MUTED_TEXT_COLOR)
    _draw_player_roster(surface, match, viewer_id)
    if match.developer_mode.enabled:
        draw_text(surface, f"開發者模式｜假玩家 {match.developer_mode.selected_dummy_id}｜1～5選取 M放入 N返回", (16, 330), 19, config.WARNING_COLOR)


def draw_match(
    surface: pygame.Surface,
    match: MatchState,
    input_state: InputState | None = None,
    viewer_id: int = 0,
) -> None:
    draw_world(surface, match, input_state, viewer_id)
    draw_hud(surface, match, input_state, viewer_id)


def draw_result(surface: pygame.Surface, match: MatchState) -> None:
    surface.fill(config.BACKGROUND_COLOR)
    panel = pygame.Rect(config.WINDOW_WIDTH // 2 - 310, 190, 620, 220)
    draw_panel(surface, panel, radius=12)
    if match.phase == MatchPhase.VICTORY:
        title = f"玩家 {match.winner_id} 獲勝！"
        color = config.ACCENT_COLOR
    else:
        title = "無人勝利"
        color = config.WARNING_COLOR
    draw_text(surface, title, (config.WINDOW_WIDTH // 2, 260), 58, color, True)
    draw_text(surface, "按 R 重新開始｜按 Esc 離開", (config.WINDOW_WIDTH // 2, 350), 28, config.TEXT_COLOR, True)
