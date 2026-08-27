"""草叢觀看者視角與戰鬥規則不變性的測試。"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pvpve_escape import config, rendering
from pvpve_escape.models import Vector2
from pvpve_escape.world import create_match


class BushViewerRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def setUp(self) -> None:
        self.match = create_match()
        self.match.monsters = []
        self.match.camera.position = Vector2()
        self.hidden_player = self.match.players[1]
        self.hidden_player.position = Vector2(1050, 540)
        self.match.players[0].position = Vector2(500, 260)
        for player in self.match.players[2:]:
            player.alive = False

    def _overlay_players(self, mock_overlay) -> list[object]:
        return [call.args[1] for call in mock_overlay.call_args_list]

    def test_self_view_keeps_role_and_overlay_while_other_view_hides_them(self) -> None:
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))

        with (
            patch("pvpve_escape.rendering._draw_player_overlay") as overlay,
            patch("pvpve_escape.rendering.draw_text"),
        ):
            rendering.draw_match(surface, self.match, viewer_id=0)
            other_view_players = self._overlay_players(overlay)
            self.assertNotIn(self.hidden_player, other_view_players)
            # draw_match 之後右下玩家名單會覆蓋部分世界像素；取樣另一片
            # 不在 HUD 上的草叢，確認地形仍由正式入口繪出。
            self.assertEqual(surface.get_at((900, 260))[:3], config.BUSH_COLOR)

            overlay.reset_mock()
            rendering.draw_match(surface, self.match, viewer_id=self.hidden_player.player_id)
            self.assertIn(self.hidden_player, self._overlay_players(overlay))

    def test_inactive_bush_restores_other_view_and_roster_without_revealing_beforehand(self) -> None:
        surface = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        hidden_character_name = "狙擊者"

        with patch("pvpve_escape.rendering.draw_text") as draw_text:
            rendering._draw_player_roster(surface, self.match, viewer_id=0)
            hidden_text = [str(call.args[1]) for call in draw_text.call_args_list]
            self.assertFalse(any(hidden_character_name in value for value in hidden_text))

            for bush in self.match.bushes:
                bush.active = False
            draw_text.reset_mock()
            rendering._draw_player_roster(surface, self.match, viewer_id=0)
            revealed_text = [str(call.args[1]) for call in draw_text.call_args_list]
            self.assertTrue(any(hidden_character_name in value for value in revealed_text))

    def test_visibility_does_not_change_known_target_or_damage_state(self) -> None:
        from pvpve_escape.world import _target_entries, apply_damage

        entries = list(_target_entries(self.match, self.match.players[0].player_id))
        self.assertIn(("player", self.hidden_player.player_id, self.hidden_player.position, self.hidden_player.radius), entries)
        health_before = self.hidden_player.health
        event = apply_damage(
            self.match,
            self.match.players[0].player_id,
            "player",
            self.hidden_player.player_id,
            10.0,
        )
        self.assertIsNotNone(event)
        self.assertLess(self.hidden_player.health, health_before)


if __name__ == "__main__":
    unittest.main()
