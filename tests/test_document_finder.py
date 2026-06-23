import os
import tempfile
import time
import unittest
from pathlib import Path

from core.document_commands import DocumentCommandService
from core.document_finder import (
    DocumentFinder,
    DocumentNotFoundError,
    resolve_search_roots,
)


class DocumentFinderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.opened_paths = []
        self.finder = DocumentFinder(
            roots=[self.root],
            extensions=[".docx", ".xlsx", ".pdf"],
            index_ttl_seconds=60,
            excluded_directory_names=["ignored"],
            opener=self.opened_paths.append,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_indexes_allowed_extensions_and_skips_excluded_directories(self):
        self._create_file("Laporan Keuangan April.xlsx")
        self._create_file("catatan.md")
        self._create_file("ignored/Laporan Rahasia.pdf")

        results = self.finder.search("laporan", force_refresh=True)

        self.assertEqual(["Laporan Keuangan April.xlsx"], [result["name"] for result in results])
        self.assertEqual(1, self.finder.get_index_status()["indexed_count"])

    def test_search_prioritizes_exact_phrase_and_recent_document(self):
        old_file = self._create_file("Laporan Keuangan April lama.xlsx")
        exact_file = self._create_file("Laporan Keuangan April.xlsx")
        now = time.time()
        os.utime(old_file, (now - 600, now - 600))
        os.utime(exact_file, (now, now))

        results = self.finder.search("laporan keuangan april", force_refresh=True)

        self.assertEqual("Laporan Keuangan April.xlsx", results[0]["name"])

    def test_open_document_only_accepts_an_indexed_result_id(self):
        document = self._create_file("Proposal Kegiatan.docx")
        result = self.finder.search("proposal", force_refresh=True)[0]

        opened_document = self.finder.open_document(result["id"])

        self.assertEqual(document.resolve(), self.opened_paths[0])
        self.assertEqual("Proposal Kegiatan.docx", opened_document["name"])
        with self.assertRaises(DocumentNotFoundError):
            self.finder.open_document("../Proposal Kegiatan.docx")

    def test_resolve_search_roots_uses_environment_override(self):
        override_root = self.root / "override"
        roots = resolve_search_roots(["~/Documents"], str(override_root))

        self.assertEqual((override_root.resolve(),), roots)

    def _create_file(self, relative_path):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test", encoding="utf-8")
        return path


class DocumentCommandServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.opened_paths = []
        finder = DocumentFinder(
            roots=[self.root],
            extensions=[".docx", ".xlsx", ".pdf"],
            opener=self.opened_paths.append,
        )
        self.service = DocumentCommandService(finder)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_voice_search_and_open_number_use_latest_results(self):
        document = self._create_file("Proposal Kegiatan.docx")

        search_payload = self.service.handle_text("cari dokumen proposal kegiatan")
        open_payload = self.service.handle_text("buka nomor satu")

        self.assertEqual("document_search", search_payload["command"])
        self.assertEqual("Proposal Kegiatan.docx", search_payload["results"][0]["name"])
        self.assertEqual("document_open", open_payload["command"])
        self.assertEqual(document.resolve(), self.opened_paths[0])

    def test_unrelated_voice_text_is_not_claimed(self):
        self.assertIsNone(self.service.handle_text("selamat pagi semuanya"))

    def test_open_voice_command_requires_previous_search(self):
        payload = self.service.handle_text("buka hasil pertama")

        self.assertEqual("error", payload["status"])
        self.assertEqual("document_open", payload["command"])

    def _create_file(self, relative_path):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test", encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
