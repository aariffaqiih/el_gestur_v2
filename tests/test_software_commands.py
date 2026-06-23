import sys
import unittest
from unittest.mock import patch, MagicMock

# List of modules to mock during server import
mocked_modules = [
    'cv2', 'core.object_lock', 'core.gestur_engine', 'core.voice_typer',
    'core.app_launcher', 'core.document_api', 'core.document_commands',
    'core.document_finder', 'core.command_router', 'pyautogui'
]

# Save original modules
original_modules = {name: sys.modules.get(name) for name in mocked_modules}

# Install mocks in sys.modules
for name in mocked_modules:
    sys.modules[name] = MagicMock()

# Import server while modules are mocked
import server

# Restore original modules to prevent test pollution
for name in mocked_modules:
    orig = original_modules[name]
    if orig is not None:
        sys.modules[name] = orig
    else:
        del sys.modules[name]

# Mock pyautogui locally for our tests
class TestSoftwareCommands(unittest.TestCase):
    def setUp(self):
        # We need to mock pyautogui methods during test execution
        self.pyautogui_patcher = patch('server.pyautogui')
        self.mock_pyautogui = self.pyautogui_patcher.start()

    def tearDown(self):
        self.pyautogui_patcher.stop()

    @patch('server.current_software', 'ppt')
    def test_ppt_commands(self):
        # pena
        res = server.handle_software_commands("pena")
        self.assertEqual(res["command"], "aktifkan pena")
        self.mock_pyautogui.hotkey.assert_called_with("command" if sys.platform == "darwin" else "ctrl", "p")

        # hapus coretan
        res = server.handle_software_commands("hapus coretan")
        self.assertEqual(res["command"], "hapus coretan")
        self.mock_pyautogui.press.assert_called_with("e")

        # layar hitam
        res = server.handle_software_commands("layar hitam")
        self.assertEqual(res["command"], "layar hitam")
        self.mock_pyautogui.press.assert_called_with("b")

        # layar putih
        res = server.handle_software_commands("layar putih")
        self.assertEqual(res["command"], "layar putih")
        self.mock_pyautogui.press.assert_called_with("w")

        # kembali normal
        res = server.handle_software_commands("kembali normal")
        self.assertEqual(res["command"], "kembali normal")
        self.mock_pyautogui.press.assert_called_with("space")

    @patch('server.current_software', 'canva')
    def test_canva_commands(self):
        # hening
        res = server.handle_software_commands("hening")
        self.assertEqual(res["command"], "hening")
        self.mock_pyautogui.press.assert_called_with("q")

        # drumroll
        res = server.handle_software_commands("suara drum")
        self.assertEqual(res["command"], "drumroll")
        self.mock_pyautogui.press.assert_called_with("d")

        # timer 5 menit
        res = server.handle_software_commands("timer lima menit")
        self.assertEqual(res["command"], "timer 5 menit")
        self.mock_pyautogui.press.assert_called_with("5")

        # timer 3 menit (numeric digit)
        res = server.handle_software_commands("timer 3 menit")
        self.assertEqual(res["command"], "timer 3 menit")
        self.mock_pyautogui.press.assert_called_with("3")

    @patch('server.current_software', 'figma')
    def test_figma_commands(self):
        # zoom fit
        res = server.handle_software_commands("zoom fit")
        self.assertEqual(res["command"], "zoom fit")
        self.mock_pyautogui.hotkey.assert_called_with("shift", "1")

        # toggle grid
        res = server.handle_software_commands("grid")
        self.assertEqual(res["command"], "toggle grid")
        self.mock_pyautogui.hotkey.assert_called_with("ctrl", "shift", "4")

    @patch('server.current_software', 'notion')
    def test_notion_commands(self):
        # buat kutipan
        res = server.handle_software_commands("buat kutipan")
        self.assertEqual(res["command"], "buat kutipan")
        self.mock_pyautogui.typewrite.assert_called_with("/quote", interval=0.01)
        self.mock_pyautogui.press.assert_called_with("enter")

        # buat tabel
        self.mock_pyautogui.press.reset_mock()
        res = server.handle_software_commands("buat tabel")
        self.assertEqual(res["command"], "buat tabel")
        self.mock_pyautogui.typewrite.assert_called_with("/table", interval=0.01)
        self.mock_pyautogui.press.assert_called_with("enter")

if __name__ == "__main__":
    unittest.main()
