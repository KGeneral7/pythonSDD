"""遊戲主迴圈狀態轉換回歸測試。"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape.main import GameApplication


class GameApplicationFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def test_restart_key_during_playing_returns_to_character_selection(self) -> None:
        pygame.event.clear()
        application = GameApplication()
        application.start_match()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        pygame.event.post(pygame.event.Event(pygame.QUIT))

        # GameApplication.run() 會在正常桌面流程結束時關閉 Pygame；
        # 單元測試保留初始化好的 Pygame，避免污染其他畫面測試。
        with patch("pvpve_escape.main.pygame.quit"):
            application.run()

        self.assertIsNone(application.match)


if __name__ == "__main__":
    unittest.main()
