import unittest

from command_router import CommandRouter


class CommandRouterTests(unittest.TestCase):
    def test_returns_first_handled_command(self):
        calls = []

        def first_handler(text):
            calls.append(("first", text))
            return None

        def second_handler(text):
            calls.append(("second", text))
            return {"status": "success", "command": "handled"}

        router = CommandRouter([first_handler, second_handler])

        result = router.handle_text("pakai template follow up")

        self.assertEqual({"status": "success", "command": "handled"}, result)
        self.assertEqual(
            [("first", "pakai template follow up"), ("second", "pakai template follow up")],
            calls,
        )


if __name__ == "__main__":
    unittest.main()
