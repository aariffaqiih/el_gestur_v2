import unittest

from desktop_shortcuts import get_redo_shortcut


class DesktopShortcutTests(unittest.TestCase):
    def test_powerpoint_and_canva_use_ctrl_y_for_redo(self):
        self.assertEqual(("ctrl", "y"), get_redo_shortcut("ppt"))
        self.assertEqual(("ctrl", "y"), get_redo_shortcut("canva"))

    def test_figma_and_notion_use_ctrl_shift_z_for_redo(self):
        self.assertEqual(("ctrl", "shift", "z"), get_redo_shortcut("figma"))
        self.assertEqual(("ctrl", "shift", "z"), get_redo_shortcut("notion"))


if __name__ == "__main__":
    unittest.main()
