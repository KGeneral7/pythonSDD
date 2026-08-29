"""共享的無頭測試與幾何斷言工具。"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from typing import Iterator

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape.models import CharacterId, TacticalId, Vector2
from pvpve_escape.world import create_match, update_world


@contextmanager
def headless_pygame() -> Iterator[None]:
    """初始化一個可重複使用的無頭 Pygame 測試生命週期。"""

    already_initialized = pygame.get_init()
    if not already_initialized:
        pygame.init()
    try:
        yield
    finally:
        if not already_initialized:
            pygame.quit()


def reset_rendering_test_state() -> None:
    """清除地圖與角色素材快取，避免測試互相共享圖片狀態。"""

    from pvpve_escape import rendering

    clear_cache = getattr(rendering, "clear_map_asset_cache", None)
    if clear_cache is not None:
        clear_cache()
    from pvpve_escape import sprites

    clear_sprite_cache = getattr(sprites, "clear_breacher_sprite_cache", None)
    if clear_sprite_cache is not None:
        clear_sprite_cache()


def fixed_steps(
    match,
    input_state,
    count: int,
    delta_time: float = 1.0 / 60.0,
) -> None:
    """以固定時間步驟更新比賽，避免測試結果依賴真實時鐘。"""

    for _ in range(max(0, count)):
        update_world(match, {0: input_state}, delta_time)


def make_match(
    role: CharacterId = CharacterId.BREACHER,
    tactical: TacticalId = TacticalId.DASH,
):
    """建立指定人類角色／配件的最小可玩比賽。"""

    return create_match(role, tactical)


def set_only_targets_alive(match, *target_ids: int) -> None:
    """只保留指定玩家存活，方便建立確定性的命中場景。"""

    allowed = set(target_ids)
    for player in match.players[1:]:
        player.alive = player.player_id in allowed


def assert_vector_close(
    testcase: unittest.TestCase,
    actual: Vector2,
    expected: Vector2,
    delta: float = 1e-5,
) -> None:
    """對自有 Vector2 提供可讀的座標誤差斷言。"""

    testcase.assertAlmostEqual(actual.x, expected.x, delta=delta)
    testcase.assertAlmostEqual(actual.y, expected.y, delta=delta)

