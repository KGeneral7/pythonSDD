"""角色像素素材的方向量化、載入快取與動畫狀態更新。"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import warnings

import pygame

from . import config
from .models import CharacterId, PlayerState, Vector2


SPRITE_DIRECTION_NAMES = (
    "right",
    "down_right",
    "down",
    "down_left",
    "left",
    "up_left",
    "up",
    "up_right",
)
# 保留破陣者既有名稱；兩個像素角色共用相同的方向順序。
BREACHER_DIRECTION_NAMES = SPRITE_DIRECTION_NAMES
SNIPER_DIRECTION_NAMES = SPRITE_DIRECTION_NAMES
_VISUAL_STATES = frozenset(("idle", "move", "attack"))
_VISIBLE_ALPHA_THRESHOLD = 64


@dataclass(frozen=True)
class CharacterSpriteSpec:
    """一個可使用像素角色的資產與動畫規格。"""

    character_id: CharacterId
    asset_root: Path
    source_size: int
    display_size: int
    selection_size: int
    roster_size: int
    preload_display_sizes: tuple[int, ...]
    direction_names: tuple[str, ...]
    frame_count: int
    move_frame_time: float
    attack_frame_time: float
    attack_duration: float
    fit_mode: str = "visible_extent"


_SPRITE_ROOT = Path(__file__).resolve().parent / config.BREACHER_SPRITE_ASSET_ROOT
_SNIPER_SPRITE_ROOT = Path(__file__).resolve().parent / config.SNIPER_SPRITE_ASSET_ROOT
CHARACTER_SPRITE_SPECS: dict[CharacterId, CharacterSpriteSpec] = {
    CharacterId.BREACHER: CharacterSpriteSpec(
        character_id=CharacterId.BREACHER,
        asset_root=_SPRITE_ROOT,
        source_size=config.BREACHER_SPRITE_SOURCE_SIZE,
        display_size=config.BREACHER_SPRITE_DISPLAY_SIZE,
        selection_size=config.BREACHER_SELECTION_SPRITE_SIZE,
        roster_size=config.BREACHER_ROSTER_SPRITE_SIZE,
        preload_display_sizes=(
            config.BREACHER_SPRITE_DISPLAY_SIZE,
            config.BREACHER_SELECTION_SPRITE_SIZE,
            config.BREACHER_ROSTER_SPRITE_SIZE,
        ),
        direction_names=BREACHER_DIRECTION_NAMES,
        frame_count=config.BREACHER_ANIMATION_FRAME_COUNT,
        move_frame_time=config.BREACHER_MOVE_FRAME_TIME,
        attack_frame_time=config.BREACHER_ATTACK_FRAME_TIME,
        attack_duration=config.BREACHER_ATTACK_DURATION,
    ),
    CharacterId.SNIPER: CharacterSpriteSpec(
        character_id=CharacterId.SNIPER,
        asset_root=_SNIPER_SPRITE_ROOT,
        source_size=config.SNIPER_SPRITE_SOURCE_SIZE,
        display_size=config.SNIPER_SPRITE_DISPLAY_SIZE,
        selection_size=config.SNIPER_SELECTION_SPRITE_SIZE,
        roster_size=config.SNIPER_ROSTER_SPRITE_SIZE,
        preload_display_sizes=(
            config.SNIPER_SPRITE_DISPLAY_SIZE,
            config.SNIPER_SELECTION_SPRITE_SIZE,
            config.SNIPER_ROSTER_SPRITE_SIZE,
        ),
        direction_names=SNIPER_DIRECTION_NAMES,
        frame_count=config.SNIPER_ANIMATION_FRAME_COUNT,
        move_frame_time=config.SNIPER_MOVE_FRAME_TIME,
        attack_frame_time=config.SNIPER_ATTACK_FRAME_TIME,
        attack_duration=config.SNIPER_ATTACK_DURATION,
        fit_mode=config.SNIPER_SPRITE_FIT_MODE,
    ),
}
# 讓工具與測試可用較直觀的別名查閱同一份規格，不建立第二份可漂移的資料。
CHARACTER_SPRITE_CONFIGS = CHARACTER_SPRITE_SPECS

_CharacterAssetKey = tuple[CharacterId, str, int, int]
_CharacterDisplayCacheKey = tuple[
    CharacterId, str, int, int, tuple[int, int] | None
]

# 角色中立快取鍵明確包含角色 ID，避免兩套素材使用相同方向／幀索引時互相覆蓋。
_CHARACTER_SOURCE_CACHE: dict[_CharacterAssetKey, pygame.Surface | None] = {}
_CHARACTER_CROP_CACHE: dict[_CharacterAssetKey, pygame.Surface | None] = {}
_CHARACTER_SPRITE_CACHE: dict[
    _CharacterDisplayCacheKey, pygame.Surface | None
] = {}
_CHARACTER_ERRORS: dict[_CharacterAssetKey, str] = {}

# 破陣者舊快取名稱保留給既有測試與外部工具；load_breacher_sprite() 會同步寫入
# 這些 legacy view，但實際規格與來源快取仍由上面的角色中立流程管理。
_SPRITE_SOURCE_CACHE: dict[tuple[str, int, int], pygame.Surface | None] = {}
_SPRITE_CROP_CACHE: dict[tuple[str, int, int], pygame.Surface | None] = {}
_SPRITE_CACHE: dict[
    tuple[str, int, int, tuple[int, int] | None], pygame.Surface | None
] = {}
_SPRITE_ERRORS: dict[tuple[str, int, int], str] = {}


def _hashable_request_component(value: object) -> object:
    """讓格式錯誤的查詢值也能被安全記錄到錯誤快取。"""

    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


def _request_key(
    character_id: CharacterId,
    visual_state: object,
    direction_index: object,
    frame_index: object,
) -> _CharacterAssetKey:
    return (
        character_id,
        _hashable_request_component(visual_state),
        _hashable_request_component(direction_index),
        _hashable_request_component(frame_index),
    )  # type: ignore[return-value]


def _coerce_character_id(character_id: CharacterId | str) -> CharacterId | None:
    if isinstance(character_id, CharacterId):
        return character_id
    try:
        return CharacterId(character_id)
    except (TypeError, ValueError):
        return None


def _spec_for_character(
    character_id: CharacterId | str,
) -> CharacterSpriteSpec | None:
    resolved = _coerce_character_id(character_id)
    if resolved is None:
        return None
    return CHARACTER_SPRITE_SPECS.get(resolved)


def _legacy_breacher_key(
    visual_state: str, direction_index: int, frame_index: int
) -> tuple[str, int, int]:
    return visual_state, direction_index, frame_index


def _sync_breacher_source_cache(
    key: _CharacterAssetKey, source: pygame.Surface | None
) -> None:
    _, visual_state, direction_index, frame_index = key
    _SPRITE_SOURCE_CACHE[
        _legacy_breacher_key(visual_state, direction_index, frame_index)
    ] = source


def _sync_breacher_crop_cache(
    key: _CharacterAssetKey, crop: pygame.Surface | None
) -> None:
    _, visual_state, direction_index, frame_index = key
    _SPRITE_CROP_CACHE[
        _legacy_breacher_key(visual_state, direction_index, frame_index)
    ] = crop


def _sync_breacher_display_cache(
    cache_key: _CharacterDisplayCacheKey, surface: pygame.Surface | None
) -> None:
    _, visual_state, direction_index, frame_index, size = cache_key
    _SPRITE_CACHE[
        (visual_state, direction_index, frame_index, size)
    ] = surface


def clear_character_sprite_cache(
    character_id: CharacterId | str | None = None,
) -> None:
    """清除指定角色或全部角色的圖片、裁切、顯示與錯誤快取。"""

    resolved = (
        None if character_id is None else _coerce_character_id(character_id)
    )
    if character_id is not None and resolved is None:
        return

    if resolved is None:
        _CHARACTER_SOURCE_CACHE.clear()
        _CHARACTER_CROP_CACHE.clear()
        _CHARACTER_SPRITE_CACHE.clear()
        _CHARACTER_ERRORS.clear()
        _SPRITE_SOURCE_CACHE.clear()
        _SPRITE_CROP_CACHE.clear()
        _SPRITE_CACHE.clear()
        _SPRITE_ERRORS.clear()
        return

    for cache in (
        _CHARACTER_SOURCE_CACHE,
        _CHARACTER_CROP_CACHE,
        _CHARACTER_SPRITE_CACHE,
        _CHARACTER_ERRORS,
    ):
        for key in tuple(cache):
            if key[0] == resolved:
                del cache[key]
    if resolved == CharacterId.BREACHER:
        _SPRITE_SOURCE_CACHE.clear()
        _SPRITE_CROP_CACHE.clear()
        _SPRITE_CACHE.clear()
        _SPRITE_ERRORS.clear()


def clear_breacher_sprite_cache() -> None:
    """清除破陣者圖片與錯誤快取，保留既有相容介面。"""

    clear_character_sprite_cache(CharacterId.BREACHER)


def character_sprite_error(
    character_id: CharacterId | str,
    visual_state: str,
    direction_index: int,
    frame_index: int,
) -> str | None:
    """回傳指定角色圖片最近一次失敗的診斷訊息。"""

    resolved = _coerce_character_id(character_id)
    if resolved is None:
        return None
    return _CHARACTER_ERRORS.get(
        _request_key(resolved, visual_state, direction_index, frame_index)
    )


def breacher_sprite_error(
    visual_state: str, direction_index: int, frame_index: int
) -> str | None:
    """回傳指定破陣者圖片最近一次失敗的診斷訊息。"""

    return character_sprite_error(
        CharacterId.BREACHER, visual_state, direction_index, frame_index
    )


def sniper_sprite_error(
    visual_state: str, direction_index: int, frame_index: int
) -> str | None:
    """回傳指定狙擊者圖片最近一次失敗的診斷訊息。"""

    return character_sprite_error(
        CharacterId.SNIPER, visual_state, direction_index, frame_index
    )


def _record_error(
    character_id: CharacterId,
    key: _CharacterAssetKey,
    message: str,
) -> None:
    # 同一來源資產的不同顯示尺寸共用一筆錯誤，避免繪製迴圈每幀
    # 重複讀檔或發出相同警告；清除快取後才會重新提醒。
    if key in _CHARACTER_ERRORS:
        return
    _CHARACTER_ERRORS[key] = message
    if character_id == CharacterId.BREACHER:
        _SPRITE_ERRORS[_legacy_breacher_key(key[1], key[2], key[3])] = message
    role_label = {
        CharacterId.BREACHER: "破陣者",
        CharacterId.SNIPER: "狙擊者",
    }.get(character_id, "角色")
    warnings.warn(
        f"{role_label}圖片載入失敗，將使用幾何 fallback：{message}",
        RuntimeWarning,
        stacklevel=2,
    )


def quantize_sprite_direction(direction: Vector2) -> int:
    """將畫面座標系向量量化成八個固定方向；零向量不改變呼叫端狀態。"""

    if direction.length() == 0.0:
        return 0
    angle = math.atan2(direction.y, direction.x)
    sector = (angle + math.pi / len(SPRITE_DIRECTION_NAMES)) / (
        2.0 * math.pi / len(SPRITE_DIRECTION_NAMES)
    )
    # 22.5 度邊界透過 floor 歸入順時針側，和 Pygame y 向下座標一致。
    return math.floor(sector) % len(SPRITE_DIRECTION_NAMES)


def _path_for_request(
    visual_state: str, direction_index: int, frame_index: int
) -> Path:
    """保留破陣者既有路徑 helper，供舊測試與工具替換。"""

    direction_name = BREACHER_DIRECTION_NAMES[direction_index]
    if visual_state == "idle":
        return _SPRITE_ROOT / "idle" / f"{direction_name}.png"
    return _SPRITE_ROOT / visual_state / direction_name / f"frame_{frame_index + 1:02d}.png"


def _path_for_character_request(
    spec: CharacterSpriteSpec,
    visual_state: str,
    direction_index: int,
    frame_index: int,
) -> Path:
    if spec.character_id == CharacterId.BREACHER:
        return _path_for_request(visual_state, direction_index, frame_index)
    direction_name = spec.direction_names[direction_index]
    if visual_state == "idle":
        return spec.asset_root / "idle" / f"{direction_name}.png"
    return (
        spec.asset_root
        / visual_state
        / direction_name
        / f"frame_{frame_index + 1:02d}.png"
    )


def _valid_character_request(
    spec: CharacterSpriteSpec,
    visual_state: str,
    direction_index: int,
    frame_index: int,
) -> bool:
    return (
        isinstance(visual_state, str)
        and isinstance(direction_index, int)
        and isinstance(frame_index, int)
        and visual_state in _VISUAL_STATES
        and 0 <= direction_index < len(spec.direction_names)
        and 0 <= frame_index < spec.frame_count
        and (visual_state != "idle" or frame_index == 0)
    )


def _valid_request(
    visual_state: str, direction_index: int, frame_index: int
) -> bool:
    """保留破陣者舊查詢驗證 helper。"""

    spec = CHARACTER_SPRITE_SPECS[CharacterId.BREACHER]
    return _valid_character_request(
        spec, visual_state, direction_index, frame_index
    )


def _validate_surface(
    surface: pygame.Surface,
    path: Path,
    spec: CharacterSpriteSpec | None = None,
) -> None:
    """驗證來源畫布、透明角落、非透明內容與邊界。"""

    resolved_spec = spec or CHARACTER_SPRITE_SPECS[CharacterId.BREACHER]
    expected_size = (resolved_spec.source_size,) * 2
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

    # alpha > 0 用於來源圖品質閘門，避免低 alpha 邊緣貼住畫布或整張空白。
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
    """以 alpha >= 64 取出實際角色、槍與瞄具的非透明像素區域。"""

    visible_bounds = asset.get_bounding_rect(min_alpha=_VISIBLE_ALPHA_THRESHOLD)
    if visible_bounds.width == 0 or visible_bounds.height == 0:
        raise ValueError("圖片沒有可用的角色像素")
    return asset.subsurface(visible_bounds).copy()


def _fit_visible_sprite(
    content: pygame.Surface, display_size: tuple[int, int]
) -> pygame.Surface:
    """縮放到固定顯示格，並將可見角色外框安全置中。"""

    scaled = pygame.transform.scale(content, display_size)
    visible_bounds = scaled.get_bounding_rect(min_alpha=16)
    if visible_bounds.width == 0 or visible_bounds.height == 0:
        return scaled

    target_center = (display_size[0] / 2.0, display_size[1] / 2.0)
    offset_x = round(target_center[0] - visible_bounds.centerx)
    offset_y = round(target_center[1] - visible_bounds.centery)
    offset_x = max(-visible_bounds.left, min(offset_x, display_size[0] - visible_bounds.right))
    offset_y = max(-visible_bounds.top, min(offset_y, display_size[1] - visible_bounds.bottom))
    if offset_x == 0 and offset_y == 0:
        return scaled

    fitted = pygame.Surface(display_size, pygame.SRCALPHA)
    fitted.blit(scaled, (offset_x, offset_y))
    return fitted


def _fit_source_canvas(
    source: pygame.Surface, display_size: tuple[int, int]
) -> pygame.Surface:
    """依來源固定畫布縮放，讓身體錨點不受長槍外框影響。"""

    return pygame.transform.scale(source, display_size)


def load_character_sprite(
    character_id: CharacterId | str,
    visual_state: str,
    direction_index: int,
    frame_index: int,
    display_size: int | tuple[int, int] | None = None,
) -> pygame.Surface | None:
    """載入任一已登錄像素角色的一格圖片；失敗交由繪製層 fallback。"""

    resolved = _coerce_character_id(character_id)
    if resolved is None:
        return None
    spec = CHARACTER_SPRITE_SPECS.get(resolved)
    key = _request_key(resolved, visual_state, direction_index, frame_index)
    if spec is None:
        _record_error(resolved, key, "角色沒有登錄像素資產規格")
        return None
    if not _valid_character_request(
        spec, visual_state, direction_index, frame_index
    ):
        _record_error(key[0], key, "視覺狀態、方向或幀索引超出範圍")
        return None
    try:
        size = _display_size_tuple(display_size)
    except (TypeError, ValueError) as error:
        _record_error(key[0], key, str(error))
        return None

    cache_key: _CharacterDisplayCacheKey = (
        resolved,
        visual_state,
        direction_index,
        frame_index,
        size,
    )
    if resolved == CharacterId.BREACHER:
        legacy_cache_key = (
            visual_state,
            direction_index,
            frame_index,
            size,
        )
        if legacy_cache_key in _SPRITE_CACHE:
            return _SPRITE_CACHE[legacy_cache_key]
    if cache_key in _CHARACTER_SPRITE_CACHE:
        return _CHARACTER_SPRITE_CACHE[cache_key]

    path = _path_for_character_request(
        spec, visual_state, direction_index, frame_index
    )
    if key not in _CHARACTER_SOURCE_CACHE:
        try:
            if not path.is_file():
                raise OSError("找不到圖片檔案")
            source = pygame.image.load(str(path))
            _validate_surface(source, path, spec)
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                source = source.convert_alpha()
        except (OSError, ValueError, TypeError, pygame.error) as error:
            _record_error(key[0], key, f"{path}: {error}")
            _CHARACTER_SOURCE_CACHE[key] = None
        else:
            _CHARACTER_SOURCE_CACHE[key] = source
        if resolved == CharacterId.BREACHER:
            _sync_breacher_source_cache(
                key, _CHARACTER_SOURCE_CACHE[key]
            )

    source = _CHARACTER_SOURCE_CACHE[key]
    if source is None:
        _CHARACTER_SPRITE_CACHE[cache_key] = None
        if resolved == CharacterId.BREACHER:
            _sync_breacher_display_cache(cache_key, None)
        return None

    try:
        if size is None:
            asset = source
        elif spec.fit_mode == "source_canvas":
            # 狙擊者來源圖已在 1024 畫布內完成頭部比例、各方向動畫身體核心
            # 聯合外框固定比例與整體置中；保留畫布縮放，不能再次以武器外框裁切，
            # 否則走路幀或不同方向的頭部會跳大小。
            # 仍先執行 alpha >= 64 的可見像素品質閘門，避免空白或只有
            # 微弱 alpha 邊緣的失效素材繞過既有 fallback。
            if key not in _CHARACTER_CROP_CACHE:
                _CHARACTER_CROP_CACHE[key] = _extract_visible_sprite(source)
            if _CHARACTER_CROP_CACHE[key] is None:
                _CHARACTER_SPRITE_CACHE[cache_key] = None
                return None
            asset = _fit_source_canvas(source, size)
        else:
            if key not in _CHARACTER_CROP_CACHE:
                _CHARACTER_CROP_CACHE[key] = _extract_visible_sprite(source)
                if resolved == CharacterId.BREACHER:
                    _sync_breacher_crop_cache(
                        key, _CHARACTER_CROP_CACHE[key]
                    )
            cropped = _CHARACTER_CROP_CACHE[key]
            if cropped is None:
                _CHARACTER_SPRITE_CACHE[cache_key] = None
                if resolved == CharacterId.BREACHER:
                    _sync_breacher_display_cache(cache_key, None)
                return None
            asset = _fit_visible_sprite(cropped, size)
    except (OSError, ValueError, TypeError, pygame.error) as error:
        _record_error(key[0], key, f"{path}: {error}")
        _CHARACTER_CROP_CACHE[key] = None
        if resolved == CharacterId.BREACHER:
            _sync_breacher_crop_cache(key, None)
        _CHARACTER_SPRITE_CACHE[cache_key] = None
        if resolved == CharacterId.BREACHER:
            _sync_breacher_display_cache(cache_key, None)
        return None

    _CHARACTER_ERRORS.pop(key, None)
    if resolved == CharacterId.BREACHER:
        _SPRITE_ERRORS.pop(_legacy_breacher_key(*key[1:]), None)
    _CHARACTER_SPRITE_CACHE[cache_key] = asset
    if resolved == CharacterId.BREACHER:
        _sync_breacher_display_cache(cache_key, asset)
    return asset


def load_breacher_sprite(
    visual_state: str,
    direction_index: int,
    frame_index: int,
    display_size: int | tuple[int, int] | None = None,
) -> pygame.Surface | None:
    """載入一格破陣者圖片；保留原有呼叫介面。"""

    return load_character_sprite(
        CharacterId.BREACHER,
        visual_state,
        direction_index,
        frame_index,
        display_size,
    )


def load_sniper_sprite(
    visual_state: str,
    direction_index: int,
    frame_index: int,
    display_size: int | tuple[int, int] | None = None,
) -> pygame.Surface | None:
    """載入一格狙擊者圖片；失敗時回傳 None 供幾何 fallback。"""

    return load_character_sprite(
        CharacterId.SNIPER,
        visual_state,
        direction_index,
        frame_index,
        display_size,
    )


def _iter_sprite_requests(
    spec: CharacterSpriteSpec,
):
    for direction_index in range(len(spec.direction_names)):
        yield "idle", direction_index, 0
        for visual_state in ("move", "attack"):
            for frame_index in range(spec.frame_count):
                yield visual_state, direction_index, frame_index


def preload_character_sprites(
    character_id: CharacterId | str,
    display_sizes: tuple[int | tuple[int, int] | None, ...] | None = None,
) -> int:
    """預熱角色全部來源幀與顯示尺寸，回傳成功來源幀數。"""

    resolved = _coerce_character_id(character_id)
    spec = CHARACTER_SPRITE_SPECS.get(resolved) if resolved is not None else None
    if spec is None:
        return 0
    requested_display_sizes = (
        spec.preload_display_sizes
        if display_sizes is None
        else display_sizes
    )
    requests = tuple(_iter_sprite_requests(spec))
    loaded_count = 0
    for visual_state, direction_index, frame_index in requests:
        if (
            load_character_sprite(
                resolved, visual_state, direction_index, frame_index, None
            )
            is not None
        ):
            loaded_count += 1
    for display_size in requested_display_sizes:
        for visual_state, direction_index, frame_index in requests:
            load_character_sprite(
                resolved,
                visual_state,
                direction_index,
                frame_index,
                display_size,
            )
    return loaded_count


def preload_breacher_sprites(
    display_size: int | tuple[int, int] | None = config.BREACHER_SPRITE_DISPLAY_SIZE,
) -> int:
    """預熱所有破陣者幀；保留既有單一顯示尺寸 wrapper。"""

    return preload_character_sprites(
        CharacterId.BREACHER,
        display_sizes=(display_size,),
    )


def preload_sniper_sprites(
    display_sizes: tuple[int | tuple[int, int] | None, ...] | None = None,
) -> int:
    """預熱所有狙擊者來源幀與規格指定的顯示尺寸。"""

    return preload_character_sprites(
        CharacterId.SNIPER,
        display_sizes=display_sizes,
    )


def _animation_spec_for_character(
    character_id: CharacterId | str,
) -> CharacterSpriteSpec | None:
    return _spec_for_character(character_id)


def _move_frame(
    state,
    character_id: CharacterId | str = CharacterId.BREACHER,
) -> int:
    spec = _animation_spec_for_character(character_id)
    frame_time = spec.move_frame_time if spec else config.BREACHER_MOVE_FRAME_TIME
    frame_count = spec.frame_count if spec else config.BREACHER_ANIMATION_FRAME_COUNT
    return math.floor(state.move_elapsed / frame_time) % frame_count


def _attack_frame(
    state,
    character_id: CharacterId | str = CharacterId.BREACHER,
) -> int:
    spec = _animation_spec_for_character(character_id)
    frame_time = spec.attack_frame_time if spec else config.BREACHER_ATTACK_FRAME_TIME
    frame_count = spec.frame_count if spec else config.BREACHER_ANIMATION_FRAME_COUNT
    return min(frame_count - 1, math.floor(state.attack_elapsed / frame_time))


def current_sprite_request(player: PlayerState) -> tuple[str, int, int]:
    """依攻擊優先級、移動狀態與目前面向回傳資產查詢值。"""

    state = player.animation_state
    if state.attack_active:
        return "attack", state.facing_direction_index, _attack_frame(
            state, player.character_id
        )
    if state.moving:
        return "move", state.facing_direction_index, _move_frame(
            state, player.character_id
        )
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

    spec = _animation_spec_for_character(player.character_id)
    move_frame_time = spec.move_frame_time if spec else config.BREACHER_MOVE_FRAME_TIME
    attack_duration = spec.attack_duration if spec else config.BREACHER_ATTACK_DURATION
    state.moving = (
        player.alive
        and player.root_timer <= 0.0
        and move_direction.length() > 0.0
    )
    if state.moving:
        state.move_elapsed = (state.move_elapsed + max(0.0, delta_time)) % (
            move_frame_time * (spec.frame_count if spec else config.BREACHER_ANIMATION_FRAME_COUNT)
        )

    if state.attack_active:
        dt = max(0.0, delta_time)
        state.attack_elapsed = min(
            attack_duration,
            state.attack_elapsed + dt,
        )
        state.attack_hold = max(0.0, state.attack_hold - dt)
        if state.attack_hold <= 0.0:
            state.attack_elapsed = 0.0


def start_or_refresh_attack_animation(
    player: PlayerState,
    duration: float | None = None,
) -> None:
    """啟動攻擊動畫；連續動作只延長維持時間，不重設目前幀。"""

    spec = _animation_spec_for_character(player.character_id)
    safe_duration = max(
        0.0,
        duration
        if duration is not None
        else (spec.attack_duration if spec else config.BREACHER_ATTACK_DURATION),
    )
    state = player.animation_state
    if not state.attack_active:
        state.attack_elapsed = 0.0
    state.attack_hold = max(state.attack_hold, safe_duration)
