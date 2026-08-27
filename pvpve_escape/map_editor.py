"""以實際遊戲世界比例編輯牆體與草叢配置的獨立工具。"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

import pygame

from . import config


EDITOR_WIDTH = 1400
EDITOR_HEIGHT = 850
SIDEBAR_WIDTH = 320
MAP_MARGIN = 24
MAP_TOP = 78
MAP_BOTTOM = 818
GRID_SIZE = 20
SAVE_PATH = Path(__file__).resolve().parent.parent / "specs" / "004-obstacles-breach-bushes" / "map-layout-draft.json"

TOOL_LABELS = {
    "thin_wall": "薄牆",
    "thick_wall": "厚牆",
    "bush": "草叢",
    "select": "選取／移動",
}
TOOL_KEYS = {
    pygame.K_1: "thin_wall",
    pygame.K_2: "thick_wall",
    pygame.K_3: "bush",
    pygame.K_4: "select",
}
ITEM_COLORS = {
    "thin_wall": (212, 143, 62),
    "thick_wall": (115, 93, 105),
    "bush": (74, 156, 91),
}
ITEM_MIN_SIZE = {
    "thin_wall": (80, 40),
    "thick_wall": (100, 60),
    "bush": (100, 80),
}


@dataclass
class LayoutItem:
    """以世界座標保存一個可配置地形物件。"""

    kind: str
    left: int
    top: int
    width: int
    height: int

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.left, self.top, self.width, self.height)

    def to_dict(self) -> dict[str, int | str]:
        return {
            "kind": self.kind,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "LayoutItem":
        kind = str(value.get("kind", ""))
        if kind not in ITEM_COLORS:
            raise ValueError(f"未知地形類型：{kind}")
        return cls(
            kind,
            int(value["left"]),
            int(value["top"]),
            int(value["width"]),
            int(value["height"]),
        )


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont("microsoftjhenghei", size, bold=bold)


def _text(surface: pygame.Surface, font: pygame.font.Font, value: str, position: tuple[int, int], color: tuple[int, int, int]) -> None:
    surface.blit(font.render(value, True, color), position)


class MapEditor:
    """顯示完整遊戲世界，並以滑鼠拖曳編輯地形。"""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((EDITOR_WIDTH, EDITOR_HEIGHT))
        pygame.display.set_caption("PvPvE 地圖配置編輯器")
        self.clock = pygame.time.Clock()
        self.title_font = _font(28, True)
        self.section_font = _font(20, True)
        self.body_font = _font(17)
        self.small_font = _font(14)
        self.items: list[LayoutItem] = self._load_items()
        self.history: list[list[LayoutItem]] = []
        self.tool = "thin_wall"
        self.selected_index: int | None = None
        self.drag_start: tuple[float, float] | None = None
        self.drag_current: tuple[float, float] | None = None
        self.move_offset: tuple[float, float] | None = None
        self.drag_mode: str | None = None
        self.status_message = "目前尚未決定地形，畫面從空白配置開始。"
        self.status_until = 0
        self.running = True

        map_width = EDITOR_WIDTH - SIDEBAR_WIDTH - MAP_MARGIN * 2
        map_height = EDITOR_HEIGHT - MAP_TOP - (EDITOR_HEIGHT - MAP_BOTTOM) - 12
        self.scale = min(map_width / config.WORLD_WIDTH, map_height / config.WORLD_HEIGHT)
        self.map_width = round(config.WORLD_WIDTH * self.scale)
        self.map_height = round(config.WORLD_HEIGHT * self.scale)
        self.map_left = MAP_MARGIN
        self.map_top = MAP_TOP + (map_height - self.map_height) // 2
        self.map_rect = pygame.Rect(self.map_left, self.map_top, self.map_width, self.map_height)
        self.sidebar_left = EDITOR_WIDTH - SIDEBAR_WIDTH + 8

    def _load_items(self) -> list[LayoutItem]:
        if not SAVE_PATH.exists():
            return []
        try:
            data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
            return [LayoutItem.from_dict(item) for item in data.get("items", [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            self.status_message = f"讀取草稿失敗：{error}"
            return []

    def _snapshot(self) -> None:
        self.history.append(copy.deepcopy(self.items))
        if len(self.history) > 40:
            self.history.pop(0)

    def _undo(self) -> None:
        if not self.history:
            self._set_status("沒有可復原的操作。")
            return
        self.items = self.history.pop()
        self.selected_index = None
        self._set_status("已復原上一個配置動作。")

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_until = pygame.time.get_ticks() + 4000

    def save(self) -> None:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "world_width": config.WORLD_WIDTH,
            "world_height": config.WORLD_HEIGHT,
            "items": [item.to_dict() for item in self.items],
        }
        SAVE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._set_status(f"已儲存 {len(self.items)} 個物件到 map-layout-draft.json。")

    def _screen_to_world(self, position: tuple[int, int]) -> tuple[float, float] | None:
        if not self.map_rect.collidepoint(position):
            return None
        world_x = (position[0] - self.map_left) / self.scale
        world_y = (position[1] - self.map_top) / self.scale
        return (
            max(0.0, min(float(config.WORLD_WIDTH), world_x)),
            max(0.0, min(float(config.WORLD_HEIGHT), world_y)),
        )

    def _world_to_screen(self, position: tuple[float, float]) -> tuple[int, int]:
        return (
            round(self.map_left + position[0] * self.scale),
            round(self.map_top + position[1] * self.scale),
        )

    def _snap(self, value: float, maximum: int) -> int:
        return max(0, min(maximum, int(round(value / GRID_SIZE) * GRID_SIZE)))

    def _item_at(self, world_position: tuple[float, float]) -> int | None:
        point = (round(world_position[0]), round(world_position[1]))
        for index in range(len(self.items) - 1, -1, -1):
            if self.items[index].rect.collidepoint(point):
                return index
        return None

    def _reserved_rects(self) -> list[tuple[str, pygame.Rect]]:
        reserved: list[tuple[str, pygame.Rect]] = []
        for index, point in enumerate(config.SPAWN_POINTS):
            radius = 72
            reserved.append((f"出生點 {index + 1}", pygame.Rect(round(point.x - radius), round(point.y - radius), radius * 2, radius * 2)))
        for index, point in enumerate(config.MONSTER_CAMP_POINTS):
            radius = 94
            reserved.append((f"怪物區 {index + 1}", pygame.Rect(round(point.x - radius), round(point.y - radius), radius * 2, radius * 2)))
        center = config.EXTRACTION_CENTER
        radius = round(config.EXTRACTION_RADIUS + 20)
        reserved.append(("中央撤離區", pygame.Rect(round(center.x - radius), round(center.y - radius), radius * 2, radius * 2)))
        return reserved

    def _warnings_for(self, item: LayoutItem) -> list[str]:
        return [name for name, reserved in self._reserved_rects() if item.rect.colliderect(reserved)]

    def _make_item(self, start: tuple[float, float], end: tuple[float, float]) -> LayoutItem:
        left = self._snap(min(start[0], end[0]), config.WORLD_WIDTH)
        top = self._snap(min(start[1], end[1]), config.WORLD_HEIGHT)
        right = self._snap(max(start[0], end[0]), config.WORLD_WIDTH)
        bottom = self._snap(max(start[1], end[1]), config.WORLD_HEIGHT)
        minimum_width, minimum_height = ITEM_MIN_SIZE[self.tool]
        width = max(minimum_width, right - left)
        height = max(minimum_height, bottom - top)
        if right - left < minimum_width:
            center_x = self._snap((start[0] + end[0]) / 2, config.WORLD_WIDTH)
            left = max(0, min(config.WORLD_WIDTH - width, center_x - width // 2))
        if bottom - top < minimum_height:
            center_y = self._snap((start[1] + end[1]) / 2, config.WORLD_HEIGHT)
            top = max(0, min(config.WORLD_HEIGHT - height, center_y - height // 2))
        return LayoutItem(self.tool, left, top, width, height)

    def _move_item(self, index: int, world_position: tuple[float, float]) -> None:
        item = self.items[index]
        offset_x, offset_y = self.move_offset or (item.width / 2, item.height / 2)
        item.left = max(0, min(config.WORLD_WIDTH - item.width, self._snap(world_position[0] - offset_x, config.WORLD_WIDTH)))
        item.top = max(0, min(config.WORLD_HEIGHT - item.height, self._snap(world_position[1] - offset_y, config.WORLD_HEIGHT)))

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key in TOOL_KEYS:
                self.tool = TOOL_KEYS[event.key]
                self.selected_index = None
                self._set_status(f"目前工具：{TOOL_LABELS[self.tool]}。")
            elif event.key == pygame.K_s or (event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL):
                self.save()
            elif event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                self._undo()
            elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE) and self.selected_index is not None:
                self._snapshot()
                deleted = self.items.pop(self.selected_index)
                self.selected_index = None
                self._set_status(f"已移除{TOOL_LABELS[deleted.kind]}。")
            elif event.key == pygame.K_r:
                self.items = self._load_items()
                self.selected_index = None
                self._set_status("已重新載入上次儲存的配置。")
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            world_position = self._screen_to_world(event.pos)
            if world_position is None:
                return
            if event.button == 3:
                index = self._item_at(world_position)
                if index is not None:
                    self._snapshot()
                    removed = self.items.pop(index)
                    self.selected_index = None
                    self._set_status(f"已移除{TOOL_LABELS[removed.kind]}。")
                return
            if event.button != 1:
                return
            if self.tool == "select":
                self.selected_index = self._item_at(world_position)
                if self.selected_index is not None:
                    item = self.items[self.selected_index]
                    self._snapshot()
                    self.drag_mode = "move"
                    self.move_offset = (world_position[0] - item.left, world_position[1] - item.top)
            else:
                self.drag_mode = "create"
                self.drag_start = world_position
                self.drag_current = world_position
            return

        if event.type == pygame.MOUSEMOTION and self.drag_mode is not None:
            world_position = self._screen_to_world(event.pos)
            if world_position is None:
                return
            self.drag_current = world_position
            if self.drag_mode == "move" and self.selected_index is not None:
                self._move_item(self.selected_index, world_position)
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag_mode is not None:
            world_position = self._screen_to_world(event.pos) or self.drag_current
            if world_position is None:
                self.drag_mode = None
                return
            if self.drag_mode == "create" and self.drag_start is not None:
                item = self._make_item(self.drag_start, world_position)
                self.items.append(item)
                self.selected_index = len(self.items) - 1
                warnings = self._warnings_for(item)
                suffix = f"；注意可能重疊：{'、'.join(warnings)}" if warnings else "。"
                self._set_status(f"已放置{TOOL_LABELS[item.kind]} {item.width}×{item.height}{suffix}")
            elif self.drag_mode == "move" and self.selected_index is not None:
                item = self.items[self.selected_index]
                warnings = self._warnings_for(item)
                suffix = f"；注意可能重疊：{'、'.join(warnings)}" if warnings else "。"
                self._set_status(f"已移動{TOOL_LABELS[item.kind]}{suffix}")
            self.drag_mode = None
            self.drag_start = None
            self.drag_current = None
            self.move_offset = None

    def _draw_background(self) -> None:
        self.screen.fill(config.BACKGROUND_COLOR)
        pygame.draw.rect(self.screen, config.PANEL_COLOR, (0, 0, EDITOR_WIDTH, MAP_TOP - 12))
        pygame.draw.rect(self.screen, config.PANEL_COLOR, (EDITOR_WIDTH - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, EDITOR_HEIGHT))
        pygame.draw.rect(self.screen, config.GROUND_COLOR, self.map_rect)
        for x in range(0, config.WORLD_WIDTH + 1, 100):
            start = self._world_to_screen((x, 0))
            end = self._world_to_screen((x, config.WORLD_HEIGHT))
            color = (65, 82, 87) if x % 500 == 0 else config.GRID_COLOR
            pygame.draw.line(self.screen, color, start, end, 1)
        for y in range(0, config.WORLD_HEIGHT + 1, 100):
            start = self._world_to_screen((0, y))
            end = self._world_to_screen((config.WORLD_WIDTH, y))
            color = (65, 82, 87) if y % 500 == 0 else config.GRID_COLOR
            pygame.draw.line(self.screen, color, start, end, 1)
        pygame.draw.rect(self.screen, config.PANEL_BORDER_COLOR, self.map_rect, 2)

    def _draw_fixed_landmarks(self) -> None:
        for index, point in enumerate(config.SPAWN_POINTS):
            screen_point = self._world_to_screen((point.x, point.y))
            pygame.draw.circle(self.screen, config.ACCENT_COLOR, screen_point, max(5, round(24 * self.scale)), 2)
            _text(self.screen, self.small_font, f"出生{index + 1}", (screen_point[0] + 5, screen_point[1] - 22), config.ACCENT_COLOR)
        for index, point in enumerate(config.MONSTER_CAMP_POINTS):
            screen_point = self._world_to_screen((point.x, point.y))
            pygame.draw.circle(self.screen, (205, 106, 88), screen_point, max(10, round(64 * self.scale)), 2)
            _text(self.screen, self.small_font, f"怪物區{index + 1}", (screen_point[0] - 28, screen_point[1] + 66 * self.scale), (205, 150, 135))
        center = self._world_to_screen((config.EXTRACTION_CENTER.x, config.EXTRACTION_CENTER.y))
        pygame.draw.circle(self.screen, config.EXTRACTION_COLOR, center, max(20, round(config.EXTRACTION_RADIUS * self.scale)), 2)
        _text(self.screen, self.small_font, "中央撤離區", (center[0] - 32, center[1] - 8), config.EXTRACTION_COLOR)

    def _draw_item(self, index: int, item: LayoutItem) -> None:
        top_left = self._world_to_screen((item.left, item.top))
        bottom_right = self._world_to_screen((item.left + item.width, item.top + item.height))
        rect = pygame.Rect(top_left, (max(2, bottom_right[0] - top_left[0]), max(2, bottom_right[1] - top_left[1])))
        color = ITEM_COLORS[item.kind]
        if item.kind == "bush":
            bush_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            bush_surface.fill((*color, 130))
            self.screen.blit(bush_surface, rect.topleft)
            for x in range(rect.left + 8, rect.right, 14):
                pygame.draw.circle(self.screen, (144, 211, 116), (x, rect.centery), 2)
        else:
            pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, (235, 240, 242), rect, 2)
        if item.kind != "bush":
            pygame.draw.line(self.screen, (235, 240, 242), rect.topleft, rect.bottomright, 1)
        if self._warnings_for(item):
            pygame.draw.rect(self.screen, config.DANGER_COLOR, rect, 3)
        if index == self.selected_index:
            pygame.draw.rect(self.screen, config.WARNING_COLOR, rect.inflate(8, 8), 3)

    def _draw_preview(self) -> None:
        if self.drag_mode != "create" or self.drag_start is None or self.drag_current is None:
            return
        item = self._make_item(self.drag_start, self.drag_current)
        top_left = self._world_to_screen((item.left, item.top))
        bottom_right = self._world_to_screen((item.left + item.width, item.top + item.height))
        rect = pygame.Rect(top_left, (max(2, bottom_right[0] - top_left[0]), max(2, bottom_right[1] - top_left[1])))
        pygame.draw.rect(self.screen, ITEM_COLORS[item.kind], rect, 2)

    def _draw_sidebar(self) -> None:
        x = self.sidebar_left
        white = config.TEXT_COLOR
        muted = config.MUTED_TEXT_COLOR
        _text(self.screen, self.title_font, "地圖配置", (x, 24), white)
        _text(self.screen, self.body_font, "完整遊戲世界 2400 × 1400", (x, 62), muted)
        _text(self.screen, self.section_font, "工具", (x, 104), white)
        _text(self.screen, self.body_font, "1  薄牆", (x, 136), ITEM_COLORS["thin_wall"])
        _text(self.screen, self.body_font, "2  厚牆", (x, 162), ITEM_COLORS["thick_wall"])
        _text(self.screen, self.body_font, "3  草叢", (x, 188), ITEM_COLORS["bush"])
        _text(self.screen, self.body_font, "4  選取／移動", (x, 214), white)
        _text(self.screen, self.section_font, f"目前：{TOOL_LABELS[self.tool]}", (x, 256), config.WARNING_COLOR)
        _text(self.screen, self.body_font, "左鍵拖曳：新增或移動", (x, 292), white)
        _text(self.screen, self.body_font, "右鍵：移除物件", (x, 318), white)
        _text(self.screen, self.body_font, "Delete：移除選取物件", (x, 344), white)
        _text(self.screen, self.body_font, "Ctrl+Z：復原", (x, 370), white)
        _text(self.screen, self.body_font, "S：儲存草稿　R：重新載入", (x, 396), white)
        _text(self.screen, self.section_font, "目前配置", (x, 442), white)
        counts = {kind: sum(item.kind == kind for item in self.items) for kind in ITEM_COLORS}
        _text(self.screen, self.body_font, f"薄牆 {counts['thin_wall']}　厚牆 {counts['thick_wall']}", (x, 474), ITEM_COLORS["thin_wall"])
        _text(self.screen, self.body_font, f"草叢 {counts['bush']}　總數 {len(self.items)}", (x, 500), ITEM_COLORS["bush"])
        if self.selected_index is not None and self.selected_index < len(self.items):
            item = self.items[self.selected_index]
            _text(self.screen, self.section_font, "選取資訊", (x, 544), white)
            _text(self.screen, self.small_font, f"{TOOL_LABELS[item.kind]} 位置 ({item.left}, {item.top})", (x, 576), white)
            _text(self.screen, self.small_font, f"尺寸 {item.width} × {item.height}", (x, 598), white)
            warnings = self._warnings_for(item)
            if warnings:
                _text(self.screen, self.small_font, "⚠ 可能重疊：" + "、".join(warnings[:2]), (x, 624), config.DANGER_COLOR)
        else:
            _text(self.screen, self.small_font, "點選物件可查看座標與尺寸。", (x, 574), muted)
        _text(self.screen, self.small_font, "紅框表示可能堵住出生／營地／撤離區。", (x, 680), config.DANGER_COLOR)
        _text(self.screen, self.small_font, "黃色框表示目前選取物件。", (x, 704), config.WARNING_COLOR)
        status = self.status_message if pygame.time.get_ticks() < self.status_until else "拖曳配置完成後按 S 儲存。"
        _text(self.screen, self.small_font, status[:43], (x, 752), muted)
        _text(self.screen, self.small_font, "Esc：離開編輯器（不自動套用遊戲）", (x, 786), muted)

    def draw(self) -> None:
        self._draw_background()
        self._draw_fixed_landmarks()
        for index, item in enumerate(self.items):
            self._draw_item(index, item)
        self._draw_preview()
        _text(self.screen, self.title_font, "PvPvE 地圖配置預覽", (MAP_MARGIN, 24), config.TEXT_COLOR)
        _text(self.screen, self.small_font, "背景標記為既有出生點、怪物區與中央撤離區；地形尚未套用到正式遊戲。", (MAP_MARGIN + 300, 34), config.MUTED_TEXT_COLOR)
        self._draw_sidebar()
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)
            self.draw()
            self.clock.tick(60)
        pygame.quit()


def main() -> None:
    MapEditor().run()


if __name__ == "__main__":
    main()
