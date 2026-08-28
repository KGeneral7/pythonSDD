"""遊戲主迴圈狀態轉換回歸測試。"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape.controllers import InputState
from pvpve_escape.main import GameApplication
from pvpve_escape.models import CharacterId, Vector2
from pvpve_escape.rules import handle_player_death, respawn_player
from pvpve_escape.world import create_match, update_match


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

    def test_restart_resets_controller_state_and_new_match_attack_state(self) -> None:
        application = GameApplication()
        application.start_match()
        application.human_controller._held["primary"] = True
        application.human_controller._blocked_until_release["primary"] = True
        application.match.players[0].primary_charge = 0.6

        application.restart()
        self.assertIsNone(application.match)
        self.assertFalse(application.human_controller._held["primary"])
        self.assertFalse(application.human_controller._blocked_until_release["primary"])

        application.start_match()
        player = application.match.players[0]
        self.assertEqual(player.primary_charge, 0.0)
        self.assertFalse(player.ability_input_blocked)

    def test_new_match_rebuilds_all_terrain_cell_states(self) -> None:
        application = GameApplication()
        application.start_match()
        previous_match = application.match
        previous_match.obstacles[0].destroyed = True
        previous_match.bushes[0].active = False

        application.restart()
        application.start_match()
        new_match = application.match

        self.assertTrue(all(not obstacle.destroyed for obstacle in new_match.obstacles))
        self.assertTrue(all(bush.active for bush in new_match.bushes))
        self.assertEqual(len(new_match.obstacles), 58)
        self.assertEqual(len(new_match.bushes), 92)

    def test_focus_loss_and_death_clear_channel_before_respawn(self) -> None:
        match = create_match(CharacterId.SIPHONER)
        match.monsters = []
        player = match.players[0]
        for other in match.players[1:]:
            other.alive = False

        update_match(
            match,
            InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True),
            0.05,
        )
        self.assertTrue(any(effect.kind == "beam" for effect in match.effects))
        update_match(
            match,
            InputState(aim_direction=Vector2(1, 0), primary_held=True, focus_lost=True),
            0.05,
        )
        self.assertFalse(any(effect.kind == "beam" for effect in match.effects))
        self.assertEqual(player.primary_charge, 0.0)

        player.primary_charge = 0.6
        handle_player_death(player)
        self.assertEqual(player.primary_charge, 0.0)
        self.assertEqual(player.primary_cooldown, 0.0)
        self.assertTrue(player.ability_input_blocked)

        for _ in range(110):
            update_match(match, InputState(aim_direction=Vector2(1, 0), primary_held=True), 0.05)
        self.assertTrue(player.alive)
        self.assertTrue(player.ability_input_blocked)
        self.assertFalse(any(effect.owner_id == player.player_id and effect.kind == "beam" for effect in match.effects))

        # 放開後先解除封鎖，再由下一個新按下事件取得施放資格。
        update_match(match, InputState(aim_direction=Vector2(1, 0)), 0.05)
        self.assertFalse(player.ability_input_blocked)

    def test_focus_death_respawn_and_restart_state_reset_repeat_twenty_times(self) -> None:
        application = GameApplication()
        for _ in range(20):
            application.start_match()
            player = application.match.players[0]
            player.primary_charge = 0.6
            player.ability_input_blocked = True
            application.human_controller._held["primary"] = True
            application.restart()
            self.assertIsNone(application.match)
            self.assertFalse(application.human_controller._held["primary"])

            match = create_match(CharacterId.SIPHONER)
            match.monsters = []
            player = match.players[0]
            for other in match.players[1:]:
                other.alive = False
            update_match(
                match,
                InputState(aim_direction=Vector2(1, 0), primary_pressed=True, primary_held=True),
                0.05,
            )
            update_match(
                match,
                InputState(aim_direction=Vector2(1, 0), primary_held=True, focus_lost=True),
                0.05,
            )
            self.assertFalse(any(effect.kind == "beam" for effect in match.effects))
            player.primary_charge = 0.6
            handle_player_death(player)
            self.assertEqual(player.primary_charge, 0.0)
            respawn_player(player, player.spawn_position)
            self.assertTrue(player.ability_input_blocked)


if __name__ == "__main__":
    unittest.main()
