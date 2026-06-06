import tempfile
import unittest
from pathlib import Path

from snippet_store import SnippetStore, SnippetValidationError


class SnippetStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "snippets.json"
        self.store = SnippetStore(
            self.path,
            seed_defaults=(),
            clock=lambda: "2026-06-06T10:00:00+07:00",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_list_and_search_snippet_by_alias(self):
        self.store.create(
            title="Follow Up Client",
            aliases=["follow up", "tindak lanjut"],
            category="Email",
            body="Mohon update terbaru.",
        )

        results = self.store.list(query="tindak lanjut")

        self.assertEqual(1, len(results))
        self.assertEqual("Follow Up Client", results[0]["title"])
        self.assertEqual(["follow up", "tindak lanjut"], results[0]["aliases"])

    def test_update_and_delete_snippet(self):
        created = self.store.create(title="Approval", body="Setuju.")

        updated = self.store.update(created["id"], {"body": "Disetujui."})
        deleted = self.store.delete(created["id"])

        self.assertEqual("Disetujui.", updated["body"])
        self.assertEqual(created["id"], deleted["id"])
        self.assertEqual([], self.store.list())

    def test_rejects_empty_body(self):
        with self.assertRaises(SnippetValidationError):
            self.store.create(title="Kosong", body="")


if __name__ == "__main__":
    unittest.main()
