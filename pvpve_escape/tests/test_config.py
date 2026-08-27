"""集中設定與 GUI alpha 轉換測試。"""

from __future__ import annotations

import unittest

from pvpve_escape import config


class ConfigValueTests(unittest.TestCase):
    def test_gui_opacity_defaults_and_alpha_are_stable(self) -> None:
        self.assertEqual(config.GUI_OPACITY_PERCENT, 78)
        self.assertEqual(config.clamp_gui_opacity_percent(), 78)
        self.assertEqual(config.gui_panel_alpha(), round(255 * 0.78))

    def test_gui_opacity_accepts_inclusive_endpoints(self) -> None:
        self.assertEqual(config.clamp_gui_opacity_percent(50), 50)
        self.assertEqual(config.clamp_gui_opacity_percent(90), 90)
        self.assertEqual(config.gui_panel_alpha(50), 128)
        self.assertEqual(config.gui_panel_alpha(90), 230)

    def test_gui_opacity_clamps_out_of_range_and_invalid_values(self) -> None:
        self.assertEqual(config.clamp_gui_opacity_percent(49), 50)
        self.assertEqual(config.clamp_gui_opacity_percent(91), 90)
        self.assertEqual(config.clamp_gui_opacity_percent("not-a-number"), 78)
        self.assertGreater(config.gui_panel_alpha(49), 0)
        self.assertLess(config.gui_panel_alpha(91), 255)


if __name__ == "__main__":
    unittest.main()

