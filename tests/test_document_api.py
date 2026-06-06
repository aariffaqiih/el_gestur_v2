import tempfile
import unittest
from pathlib import Path

from flask import Flask

from document_api import create_document_blueprint
from document_commands import DocumentCommandService
from document_finder import DocumentFinder


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.document = self.root / "Laporan Bulanan.xlsx"
        self.document.write_text("test", encoding="utf-8")
        self.opened_paths = []

        finder = DocumentFinder(
            roots=[self.root],
            extensions=[".xlsx"],
            opener=self.opened_paths.append,
        )
        commands = DocumentCommandService(finder)
        app = Flask(__name__)
        app.register_blueprint(create_document_blueprint(commands))
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_and_open_document(self):
        search_response = self.client.post(
            "/documents/search",
            json={"query": "laporan bulanan"},
        )
        result_id = search_response.get_json()["results"][0]["id"]

        open_response = self.client.post(
            "/documents/open",
            json={"result_id": result_id},
        )

        self.assertEqual(200, search_response.status_code)
        self.assertEqual(200, open_response.status_code)
        self.assertEqual(self.document.resolve(), self.opened_paths[0])

    def test_search_requires_a_query(self):
        response = self.client.post("/documents/search", json={"query": ""})

        self.assertEqual(400, response.status_code)
        self.assertEqual("error", response.get_json()["status"])

    def test_open_rejects_unknown_result_id(self):
        response = self.client.post(
            "/documents/open",
            json={"result_id": "not-indexed"},
        )

        self.assertEqual(404, response.status_code)
        self.assertEqual("error", response.get_json()["status"])

    def test_search_rejects_non_local_client(self):
        response = self.client.post(
            "/documents/search",
            json={"query": "laporan"},
            environ_base={"REMOTE_ADDR": "192.168.1.20"},
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual("error", response.get_json()["status"])

    def test_search_rejects_untrusted_browser_origin(self):
        response = self.client.post(
            "/documents/search",
            json={"query": "laporan"},
            headers={"Origin": "https://example.com"},
        )

        self.assertEqual(403, response.status_code)
        self.assertEqual("error", response.get_json()["status"])


if __name__ == "__main__":
    unittest.main()
