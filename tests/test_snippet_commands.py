import tempfile
import unittest
from pathlib import Path

from snippet_commands import SnippetCommandService
from snippet_store import SnippetStore


class SnippetCommandServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        store = SnippetStore(
            Path(self.temp_dir.name) / "snippets.json",
            seed_defaults=(),
        )
        store.create(
            title="Follow Up",
            aliases=["follow up", "tindak lanjut"],
            body="Mohon update terbaru.",
        )
        self.inserted_texts = []
        self.service = SnippetCommandService(
            store,
            inserter=self.inserted_texts.append,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_voice_command_inserts_matching_template(self):
        payload = self.service.handle_text("pakai template follow up")

        self.assertEqual("success", payload["status"])
        self.assertEqual("snippet_insert", payload["command"])
        self.assertEqual(["Mohon update terbaru."], self.inserted_texts)

    def test_unrelated_voice_text_is_not_claimed(self):
        self.assertIsNone(self.service.handle_text("selamat pagi semuanya"))
        self.assertEqual([], self.inserted_texts)

    def test_unknown_template_returns_error(self):
        payload = self.service.handle_text("tempel snippet tidak ada")

        self.assertEqual("error", payload["status"])
        self.assertEqual("snippet_insert", payload["command"])
        self.assertEqual([], self.inserted_texts)

    def test_insert_requires_explicit_template(self):
        payload = self.service.insert()

        self.assertEqual("error", payload["status"])
        self.assertEqual("snippet_insert", payload["command"])
        self.assertEqual([], self.inserted_texts)


if __name__ == "__main__":
    unittest.main()
