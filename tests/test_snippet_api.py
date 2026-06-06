import tempfile
import unittest
from pathlib import Path

from flask import Flask

from snippet_api import create_snippet_blueprint
from snippet_commands import SnippetCommandService
from snippet_store import SnippetStore


class SnippetApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.inserted_texts = []
        store = SnippetStore(
            Path(self.temp_dir.name) / "snippets.json",
            seed_defaults=(),
        )
        commands = SnippetCommandService(store, inserter=self.inserted_texts.append)
        app = Flask(__name__)
        app.register_blueprint(create_snippet_blueprint(commands))
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_list_and_insert_snippet(self):
        create_response = self.client.post(
            "/snippets",
            json={
                "title": "Follow Up",
                "aliases": "follow up, tindak lanjut",
                "body": "Mohon update terbaru.",
            },
        )
        created = create_response.get_json()["snippet"]

        list_response = self.client.get("/snippets?query=tindak%20lanjut")
        insert_response = self.client.post(
            "/snippets/insert",
            json={"snippet_id": created["id"]},
        )

        self.assertEqual(201, create_response.status_code)
        self.assertEqual(200, list_response.status_code)
        self.assertEqual("Follow Up", list_response.get_json()["snippets"][0]["title"])
        self.assertEqual(200, insert_response.status_code)
        self.assertEqual(["Mohon update terbaru."], self.inserted_texts)

    def test_rejects_non_local_client(self):
        response = self.client.get(
            "/snippets",
            environ_base={"REMOTE_ADDR": "192.168.1.20"},
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual("error", response.get_json()["status"])


if __name__ == "__main__":
    unittest.main()
