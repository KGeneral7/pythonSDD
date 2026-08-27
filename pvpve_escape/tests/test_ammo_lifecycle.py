"""普攻狀態與彈藥恢復的世界更新順序測試。"""

from __future__ import annotations

import unittest

from pvpve_escape.characters import get_character_definition
from pvpve_escape.controllers import InputState
from pvpve_escape.models import CharacterId, TacticalId, Vector2
from pvpve_escape.world import create_match, update_world


def _quiet_match(role: CharacterId, tactical: TacticalId = TacticalId.DASH):
    match = create_match(role, tactical)
    match.monsters = []
    for other in match.players[1:]:
        other.alive = False
    return match


class AmmoLifecycleTests(unittest.TestCase):
    def test_same_frame_primary_cast_cannot_recover_before_consuming_ammo(self) -> None:
        for role in CharacterId:
            definition = get_character_definition(role)
            for _ in range(20):
                match = _quiet_match(role)
                player = match.players[0]
                player.ammo = player.ammo_capacity - 1
                if role == CharacterId.SIPHONER:
                    attack_input = InputState(
                        aim_direction=Vector2(1, 0),
                        primary_pressed=True,
                        primary_held=True,
                    )
                else:
                    attack_input = InputState(
                        aim_direction=Vector2(1, 0),
                        primary_pressed=True,
                        primary_released=True,
                    )

                update_world(match, {0: attack_input}, 0.05)

                self.assertEqual(player.ammo, player.ammo_capacity - 2, role)
                self.assertEqual(player.ammo_recovery_timer, 0.0, role)

                # 即使經過很長時間，只要按住普攻（或持續引導），恢復
                # 計時仍必須保持清零。
                hold = InputState(aim_direction=Vector2(1, 0), primary_held=True)
                for _ in range(20):
                    update_world(match, {0: hold}, 0.05)
                self.assertEqual(player.ammo, player.ammo_capacity - 2, role)
                self.assertEqual(player.ammo_recovery_timer, 0.0, role)

                player.primary_cooldown = 0.0
                player.primary_charge = 0.0
                remaining = max(0.0, definition.ammo_recovery_interval - 0.01)
                while remaining > 0.0:
                    step = min(0.05, remaining)
                    update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, step)
                    remaining -= step
                self.assertEqual(player.ammo, player.ammo_capacity - 2, role)
                update_world(match, {0: InputState(aim_direction=Vector2(1, 0))}, 0.01)
                self.assertEqual(player.ammo, player.ammo_capacity - 1, role)

    def test_ultimate_and_tactical_alone_do_not_block_ammo_recovery(self) -> None:
        for role in CharacterId:
            for _ in range(20):
                ultimate_match = _quiet_match(role)
                ultimate_player = ultimate_match.players[0]
                ultimate_player.ammo = ultimate_player.ammo_capacity - 1
                ultimate_player.ultimate_energy = 100.0
                update_world(
                    ultimate_match,
                    {0: InputState(aim_direction=Vector2(1, 0), ultimate_pressed=True)},
                    0.10,
                )
                self.assertGreater(ultimate_player.ammo_recovery_timer, 0.0, role)

                tactical_match = _quiet_match(role, TacticalId.CONTROL)
                tactical_player = tactical_match.players[0]
                tactical_player.ammo = tactical_player.ammo_capacity - 1
                update_world(
                    tactical_match,
                    {0: InputState(aim_direction=Vector2(1, 0), tactical_pressed=True)},
                    0.10,
                )
                self.assertGreater(tactical_player.ammo_recovery_timer, 0.0, role)


if __name__ == "__main__":
    unittest.main()
