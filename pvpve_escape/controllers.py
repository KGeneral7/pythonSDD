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
    primary_released: bool = False
    ultimate_pressed: bool = False
    ultimate_held: bool = False
    ultimate_released: bool = False
    tactical_pressed: bool = False
    tactical_held: bool = False
    tactical_released: bool = False
    focus_lost: bool = False
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

    def __init__(self) -> None:
        self._focused = True
        self._held = {"primary": False, "ultimate": False, "tactical": False}
        self._blocked_until_release = {"primary": False, "ultimate": False, "tactical": False}

    def collect(
        self,
        events: list[pygame.event.Event],
        camera_position: Vector2,
        player_position: Vector2 | None,
        phase: MatchPhase,
    ) -> InputState:
        state = InputState()
        button_down = {"primary": False, "ultimate": False, "tactical": False}
        button_up = {"primary": False, "ultimate": False, "tactical": False}
        for event in events:
            if event.type == pygame.QUIT:
                state.quit_requested = True
            if event.type == pygame.WINDOWFOCUSLOST:
                self._focused = False
                state.focus_lost = True
                for name in self._held:
                    self._held[name] = False
                    self._blocked_until_release[name] = True
                continue
            if event.type == pygame.WINDOWFOCUSGAINED:
                self._focused = True
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and phase == MatchPhase.PLAYING and self._focused:
                if event.button == 1:
                    button_down["primary"] = True
                elif event.button == 3:
                    button_down["ultimate"] = True
                continue
            if event.type == pygame.MOUSEBUTTONUP and phase == MatchPhase.PLAYING:
                if event.button == 1:
                    button_up["primary"] = True
                elif event.button == 3:
                    button_up["ultimate"] = True
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and phase == MatchPhase.PLAYING and self._focused:
                button_down["tactical"] = True
                continue
            if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                button_up["tactical"] = True
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
            for name in self._held:
                self._held[name] = False
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
        polled = {
            "primary": bool(buttons[0]),
            "ultimate": bool(buttons[2]),
            "tactical": bool(keys[pygame.K_SPACE]),
        }

        def resolve_button(name: str) -> tuple[bool, bool, bool]:
            previous = self._held[name]
            if not self._focused or state.focus_lost:
                current = False
                pressed = False
                released = False
            else:
                if self._blocked_until_release[name]:
                    # 失焦時按住的鍵必須先真正放開，回到視窗後才可再次觸發。
                    if button_up[name] or not polled[name]:
                        self._blocked_until_release[name] = False
                    current = False
                    # 這個放開只用來解除失焦封鎖，不得被世界更新解讀成
                    # 一次新的施放，避免回到視窗時補發技能。
                    pressed = False
                    released = False
                else:
                    current = polled[name]
                    # 測試環境或事件與輪詢不同步時，按下事件本身仍代表
                    # 本幀已進入按住；同幀的放開則優先回到未按住。
                    if button_down[name] and not button_up[name]:
                        current = True
                    if button_up[name]:
                        current = False
                    pressed = button_down[name] or (current and not previous)
                    released = button_up[name] or (previous and not current)
            self._held[name] = current
            return pressed, current, released

        state.primary_pressed, state.primary_held, state.primary_released = resolve_button("primary")
        state.ultimate_pressed, state.ultimate_held, state.ultimate_released = resolve_button("ultimate")
        state.tactical_pressed, state.tactical_held, state.tactical_released = resolve_button("tactical")
        return state


class DummyController:
    """固定假玩家控制器；永遠不主動移動或攻擊，沒有 AI。"""

    def collect(self) -> InputState:
        return InputState()


class DeveloperController:
    """將開發者測試按鍵映射為可測試的命令資料。"""

    def collect(self, human_input: InputState) -> InputState:
        return human_input
