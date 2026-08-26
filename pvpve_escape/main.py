"""遊戲入口與輸入、更新、繪製的主迴圈。"""

from __future__ import annotations

import pygame

from . import config, rendering
from .controllers import DeveloperController, HumanController
from .models import CharacterId, MatchPhase, TacticalId, Vector2
from .world import create_match, place_dummy_in_extraction, return_dummy_to_spawn, update_match


class GameApplication:
    """保存視窗層狀態，並將每幀工作分成事件、更新與繪製。"""

    def __init__(self) -> None:
        pygame.init()
        self.screen = rendering.create_screen()
        pygame.display.set_caption("PvPvE 中央撤離競技")
        self.clock = pygame.time.Clock()
        self.human_controller = HumanController()
        self.developer_controller = DeveloperController()
        self.selected_character_index = 0
        self.selected_tactical_index = 0
        self.match = None
        self.running = True

    def start_match(self) -> None:
        self.match = create_match(
            list(CharacterId)[self.selected_character_index],
            list(TacticalId)[self.selected_tactical_index],
        )

    def restart(self) -> None:
        self.match = None
        self.selected_character_index = 0
        self.selected_tactical_index = 0

    def run(self) -> None:
        while self.running:
            events = pygame.event.get()
            phase = self.match.phase if self.match is not None else MatchPhase.CHARACTER_SELECT
            camera_position = self.match.camera.position if self.match is not None else Vector2()
            player_position = self.match.players[0].position if self.match and self.match.players else None
            human_input = self.human_controller.collect(events, camera_position, player_position, phase)
            if human_input.quit_requested:
                self.running = False
            if human_input.restart_requested:
                # 重新開始在任何階段都先回到選角頁；不能等到結算分支，
                # 否則進行中的比賽會繼續更新而忽略 R 按鍵。
                self.restart()
                rendering.draw_selection(self.screen, self.selected_character_index, self.selected_tactical_index)
                pygame.display.flip()
                continue
            delta_time = min(config.MAX_DELTA_TIME, self.clock.tick(config.FPS) / 1000.0)
            if phase == MatchPhase.CHARACTER_SELECT:
                self._update_selection(human_input)
                if self.match is None:
                    rendering.draw_selection(self.screen, self.selected_character_index, self.selected_tactical_index)
            elif self.match is not None and self.match.phase == MatchPhase.PLAYING:
                self._update_playing(human_input)
                update_match(self.match, human_input, delta_time)
                if self.match.phase == MatchPhase.PLAYING:
                    rendering.draw_match(self.screen, self.match)
                else:
                    rendering.draw_result(self.screen, self.match)
            elif self.match is not None:
                if self.match.phase == MatchPhase.PLAYING:
                    rendering.draw_match(self.screen, self.match)
                else:
                    rendering.draw_result(self.screen, self.match)
            pygame.display.flip()
        pygame.quit()

    def _update_selection(self, input_state: object) -> None:
        if input_state.selected_character_index is not None:
            self.selected_character_index = input_state.selected_character_index
        if input_state.selected_tactical_index is not None:
            self.selected_tactical_index = input_state.selected_tactical_index
        if input_state.start_requested:
            self.start_match()

    def _update_playing(self, input_state: object) -> None:
        if self.match is None:
            return
        if input_state.developer_toggle:
            self.match.developer_mode.enabled = not self.match.developer_mode.enabled
            self.match.developer_mode.show_overlay = self.match.developer_mode.enabled
        if not self.match.developer_mode.enabled:
            return
        if input_state.developer_dummy_id is not None:
            self.match.developer_mode.selected_dummy_id = input_state.developer_dummy_id
        if input_state.developer_place:
            place_dummy_in_extraction(self.match)
        if input_state.developer_return:
            return_dummy_to_spawn(self.match)
        self.developer_controller.collect(input_state)


def run() -> None:
    GameApplication().run()
