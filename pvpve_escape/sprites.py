"""破陣者像素素材的方向量化、載入快取與動畫狀態更新。"""

from __future__ import annotations

import math
from pathlib import Path
import warnings

import pygame

from . import config
from .models import PlayerState, Vector2


BREACHER_DIRECTION_NAMES = (
    "right",
    "down_right",
    "down",
    "down_left",
    "left",
    "up_left",
    "up",
    "up_right",
)
_VISUAL_STATES = frozenset(("idle", "move", "attack"))
# 生成器偶爾會在輪廓外留下低 alpha 的微弱抗鋸齒邊；尺寸標準化時
# 忽略這層不可見光暈，避免它把角色外框誤判得比實際像素主體更大。
_VISIBLE_ALPHA_THRESHOLD = 64
_SPRITE_ROOT = Path(__file__).resolve().parent / config.BREACHER_SPRITE_ASSET_ROOT
_SPRITE_SOURCE_CACHE: dict[tuple[str, int, int], pygame.Surface | None] = {}
_SPRITE_CROP_CACHE: dict[tuple[str, int, int], pygame.Surface | None] = {}
_SPRITE_CACHE: dict[tuple[str, int, int, tuple[int, int] | None], pygame.Surface | None] = {}
_SPRITE_ERRORS: dict[tuple[str, int, int], str] = {}


def clear_breacher_sprite_cache() -> None:
    """清除圖片與錯誤快取，供測試替身和重新載入使用。"""

    _SPRITE_SOURCE_CACHE.clear()
    _SPRITE_CROP_CACHE.clear()
    _SPRITE_CACHE.clear()
    _SPRITE_ERRORS.clear()


def breacher_sprite_error(
    visual_state: str, direction_index: int, frame_index: int
) -> str | None:
    """回傳指定圖片最近一次失敗的診斷訊息。"""

    return _SPRITE_ERRORS.get((visual_state, direction_index, frame_index))


def _record_error(
    key: tuple[str, int, int], message: str
) -> None:
    # 錯誤只保留第一筆，並在同一個快取生命週期內只警告一次，避免遊戲
    # 迴圈每幀重複製造相同診斷；清除快取後再次載入時仍能重新提醒。
    if key in _SPRITE_ERRORS:
        return
    _SPRITE_ERRORS[key] = message
    warnings.warn(
        f"破陣者圖片載入失敗，將使用幾何 fallback：{message}",
        RuntimeWarning,
        stacklevel=2,
    )


def quantize_sprite_direction(direction: Vector2) -> int:
    """將畫面座標系向量量化成右、右下、下、左下、左、左上、上、右上的索引。"""

    if direction.length() == 0.0:
        return 0
    angle = math.atan2(direction.y, direction.x)
    sector = (angle + math.pi / config.BREACHER_DIRECTION_COUNT) / (
        2.0 * math.pi / config.BREACHER_DIRECTION_COUNT
    )
    return math.floor(sector) % config.BREACHER_DIRECTION_COUNT


def _path_for_request(
    visual_state: str, direction_index: int, frame_index: int
) -> Path:
    direction_name = BREACHER_DIRECTION_NAMES[direction_index]
    if visual_state == "idle":
        return _SPRITE_ROOT / "idle" / f"{direction_name}.png"
    return _SPRITE_ROOT / visual_state / direction_name / f"frame_{frame_index + 1:02d}.png"


def _valid_request(
    visual_state: str, direction_index: int, frame_index: int
) -> bool:
    return (
        visual_state in _VISUAL_STATES
        and 0 <= direction_index < config.BREACHER_DIRECTION_COUNT
        and 0 <= frame_index < config.BREACHER_ANIMATION_FRAME_COUNT
        and (visual_state != "idle" or frame_index == 0)
    )


def _validate_surface(surface: pygame.Surface, path: Path) -> None:
    expected_size = (
        config.BREACHER_SPRITE_SOURCE_SIZE,
        config.BREACHER_SPRITE_SOURCE_SIZE,
    )
    if surface.get_size() != expected_size:
        raise ValueError(f"尺寸為 {surface.get_size()}，預期 {expected_size}")

    corners = (
        surface.get_at((0, 0)).a,
        surface.get_at((surface.get_width() - 1, 0)).a,
        surface.get_at((0, surface.get_height() - 1)).a,
        surface.get_at((surface.get_width() - 1, surface.get_height() - 1)).a,
    )
    if corners != (0, 0, 0, 0):
        raise ValueError(f"四角必須透明，實際為 {corners}")

    visible_bounds = surface.get_bounding_rect(min_alpha=1)
    if visible_bounds.width == 0 or visible_bounds.height == 0:
        raise ValueError("圖片沒有可見像素")
    if (
        visible_bounds.left <= 0
        or visible_bounds.top <= 0
        or visible_bounds.right >= surface.get_width()
        or visible_bounds.bottom >= surface.get_height()
    ):
        raise ValueError(f"非透明像素貼住畫布邊界：{visible_bounds}")


def _display_size_tuple(
    display_size: int | tuple[int, int] | None,
) -> tuple[int, int] | None:
    if display_size is None:
        return None
    if isinstance(display_size, int):
        safe_size = max(1, display_size)
        return safe_size, safe_size
    if len(display_size) != 2:
        raise ValueError("display_size 必須是整數或寬高二元組")
    return max(1, int(display_size[0])), max(1, int(display_size[1]))


def _extract_visible_sprite(asset: pygame.Surface) -> pygame.Surface:
    """從單張來源圖取出實際角色、槍與盾的非透明像素區域。"""

    visible_bounds = asset.get_bounding_rect(min_alpha=_VISIBLE_ALPHA_THRESHOLD)
    if visible_bounds.width == 0 or visible_bounds.height == 0:
        raise ValueError("圖片沒有可用的角色像素")
    return asset.subsurface(visible_bounds).copy()


def _fit_visible_sprite(content: pygame.Surface, display_size: tuple[int, int]) -> pygame.Surface:
    """將每張已裁切的角色圖直接重採樣到固定顯示格，消除幀間外框差異。"""

    # 來源圖已先裁到實際角色區域；此處對每一張圖使用同一個輸出尺寸，
    # 讓轉向、移動與攻擊不會因生成時的透明留白或外框比例不同而變大變小。
    return pygame.transform.scale(content, display_size)


def load_breacher_sprite(
    visual_state: str,
    direction_index: int,
    frame_index: int,
    display_size: int | tuple[int, int] | None = None,
) -> pygame.Surface | None:
    """載入一格破陣者圖片；失敗時回傳 None 讓繪製層使用幾何 fallback。"""

    key = (visual_state, direction_index, frame_index)
    if not _valid_request(visual_state, direction_index, frame_index):
        _record_error(key, "視覺狀態、方向或幀索引超出範圍")
        return None
    try:
        size = _display_size_tuple(display_size)
    except ValueError as error:
        _record_error(key, str(error))
        return None
    cache_key = (visual_state, direction_index, frame_index, size)
    if cache_key in _SPRITE_CACHE:
        return _SPRITE_CACHE[cache_key]

    path = _path_for_request(visual_state, direction_index, frame_index)
    if key not in _SPRITE_SOURCE_CACHE:
        try:
            if not path.is_file():
                raise OSError("找不到圖片檔案")
            source = pygame.image.load(str(path))
            _validate_surface(source, path)
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                source = source.convert_alpha()
        except (OSError, ValueError, TypeError, pygame.error) as error:
            _record_error(key, f"{path}: {error}")
            _SPRITE_SOURCE_CACHE[key] = None
        else:
            _SPRITE_SOURCE_CACHE[key] = source

    source = _SPRITE_SOURCE_CACHE[key]
    if source is None:
        _SPRITE_CACHE[cache_key] = None
        return None

    try:
        if size is None:
            asset = source
        else:
            if key not in _SPRITE_CROP_CACHE:
                _SPRITE_CROP_CACHE[key] = _extract_visible_sprite(source)
            cropped = _SPRITE_CROP_CACHE[key]
            if cropped is None:
                _SPRITE_CACHE[cache_key] = None
                return None
            asset = _fit_visible_sprite(cropped, size)
    except (OSError, ValueError, TypeError, pygame.error) as error:
        _record_error(key, f"{path}: {error}")
        _SPRITE_CROP_CACHE[key] = None
        _SPRITE_CACHE[cache_key] = None
        return None

    _SPRITE_ERRORS.pop(key, None)
    _SPRITE_CACHE[cache_key] = asset
    return asset


def preload_breacher_sprites(
    display_size: int | tuple[int, int] | None = config.BREACHER_SPRITE_DISPLAY_SIZE,
) -> int:
    """在進入對局前預熱所有破陣者幀，避免首個遊戲畫面出現讀檔卡頓。"""

    loaded_count = 0
    for direction_index in range(config.BREACHER_DIRECTION_COUNT):
        if load_breacher_sprite("idle", direction_index, 0, display_size) is not None:
            loaded_count += 1
        for visual_state in ("move", "attack"):
            for frame_index in range(config.BREACHER_ANIMATION_FRAME_COUNT):
                if load_breacher_sprite(visual_state, direction_index, frame_index, display_size) is not None:
                    loaded_count += 1
    return loaded_count


def _move_frame(state) -> int:
    return math.floor(state.move_elapsed / config.BREACHER_MOVE_FRAME_TIME) % config.BREACHER_ANIMATION_FRAME_COUNT


def _attack_frame(state) -> int:
    return min(
        config.BREACHER_ANIMATION_FRAME_COUNT - 1,
        math.floor(state.attack_elapsed / config.BREACHER_ATTACK_FRAME_TIME),
    )


def current_sprite_request(player: PlayerState) -> tuple[str, int, int]:
    """依攻擊優先級、移動狀態與目前面向回傳資產查詢值。"""

    state = player.animation_state
    if state.attack_active:
        return "attack", state.facing_direction_index, _attack_frame(state)
    if state.moving:
        return "move", state.facing_direction_index, _move_frame(state)
    return "idle", state.facing_direction_index, 0


def update_player_animation(
    player: PlayerState, move_direction: Vector2, delta_time: float
) -> None:
    """更新面向、移動狀態與動畫時間，不觸碰位置或任何戰鬥欄位。"""

    state = player.animation_state
    if player.aim_direction.length() > 0.0:
        state.facing_direction_index = quantize_sprite_direction(player.aim_direction)
    elif move_direction.length() > 0.0:
        state.facing_direction_index = quantize_sprite_direction(move_direction)

    dt = max(0.0, delta_time)
    state.moving = player.alive and player.root_timer <= 0.0 and move_direction.length() > 0.0
    if state.moving:
        state.move_elapsed = (state.move_elapsed + dt) % (
            config.BREACHER_MOVE_FRAME_TIME * config.BREACHER_ANIMATION_FRAME_COUNT
        )

    if state.attack_active:
        state.attack_elapsed = min(
            config.BREACHER_ATTACK_DURATION,
            state.attack_elapsed + dt,
        )
        state.attack_hold = max(0.0, state.attack_hold - dt)
        if state.attack_hold <= 0.0:
            state.attack_elapsed = 0.0


def start_or_refresh_attack_animation(
    player: PlayerState,
    duration: float = config.BREACHER_ATTACK_DURATION,
) -> None:
    """啟動攻擊動畫；連續動作只延長維持時間，不重設目前幀。"""

    state = player.animation_state
    safe_duration = max(0.0, duration)
    if not state.attack_active:
        state.attack_elapsed = 0.0
    state.attack_hold = max(state.attack_hold, safe_duration)
