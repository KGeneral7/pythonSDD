"""將 Pygame 事件轉成與畫面無關的輸入資料。"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from .models import MatchPhase, Vector2


@dataclass
class InputState:
    move_direction: Vector2 = field(default_factory=Vector2)
    aim_direction: Vector2 = field(default_factory=lambda: Vector2(1.0, 0.0))
    primary_pressed: bool = False
    primary_held: bool = False
    ultimate_pressed: bool = False
    tactical_pressed: bool = False
    quit_requested: bool = False
    restart_requested: bool = False
    start_requested: bool = False
    selected_character_index: int | None = None
    selected_tactical_index: int | None = None
    developer_toggle: bool = False
    developer_dummy_id: int | None = None
    developer_place: bool = False
    developer_return: bool = False


class HumanController:
    """讀取人類玩家的鍵盤與滑鼠，並產生單幀輸入。"""

    def collect(
        self,
        events: list[pygame.event.Event],
        camera_position: Vector2,
        player_position: Vector2 | None,
        phase: MatchPhase,
    ) -> InputState:
        state = InputState()
        for event in events:
            if event.type == pygame.QUIT:
                state.quit_requested = True
            if event.type == pygame.MOUSEBUTTONDOWN and phase == MatchPhase.PLAYING:
                if event.button == 1:
                    state.primary_pressed = True
                elif event.button == 3:
                    state.ultimate_pressed = True
                continue
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                state.quit_requested = True
            elif event.key == pygame.K_r:
                state.restart_requested = True
            elif event.key == pygame.K_RETURN and phase == MatchPhase.CHARACTER_SELECT:
                state.start_requested = True
            elif event.key == pygame.K_F1 and phase == MatchPhase.PLAYING:
                state.developer_toggle = True
            elif event.key == pygame.K_SPACE and phase == MatchPhase.PLAYING:
                # 以事件旗標保留按鍵當幀的配件輸入，不只依賴 get_pressed() 的
                # 時序，避免快速點按 Space 時配件完全沒有觸發。
                state.tactical_pressed = True
            elif event.key == pygame.K_m and phase == MatchPhase.PLAYING:
                state.developer_place = True
            elif event.key == pygame.K_n and phase == MatchPhase.PLAYING:
                state.developer_return = True
            elif phase == MatchPhase.CHARACTER_SELECT:
                if pygame.K_1 <= event.key <= pygame.K_6:
                    state.selected_character_index = event.key - pygame.K_1
                elif event.key in (pygame.K_q, pygame.K_w, pygame.K_e):
                    state.selected_tactical_index = {
                        pygame.K_q: 0,
                        pygame.K_w: 1,
                        pygame.K_e: 2,
                    }[event.key]
            elif phase == MatchPhase.PLAYING and pygame.K_1 <= event.key <= pygame.K_5:
                state.developer_dummy_id = event.key - pygame.K_1 + 1

        if phase != MatchPhase.PLAYING:
            return state

        keys = pygame.key.get_pressed()
        state.move_direction = Vector2(
            float(keys[pygame.K_d]) - float(keys[pygame.K_a]),
            float(keys[pygame.K_s]) - float(keys[pygame.K_w]),
        ).normalized()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        mouse_world = Vector2(mouse_x + camera_position.x, mouse_y + camera_position.y)
        if player_position is not None:
            state.aim_direction = (mouse_world - player_position).normalized()
        buttons = pygame.mouse.get_pressed(3)
        state.primary_held = bool(buttons[0])
        state.tactical_pressed = state.tactical_pressed or bool(keys[pygame.K_SPACE])
        return state


class DummyController:
    """固定假玩家控制器；永遠不主動移動或攻擊，沒有 AI。"""

    def collect(self) -> InputState:
        return InputState()


class DeveloperController:
    """將開發者測試按鍵映射為可測試的命令資料。"""

    def collect(self, human_input: InputState) -> InputState:
        return human_input
