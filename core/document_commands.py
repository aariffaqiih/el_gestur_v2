from __future__ import annotations

import re
import threading
from typing import Any

from .document_finder import DocumentFinder, DocumentFinderError


_SEARCH_PATTERN = re.compile(
    r"^(?:tolong\s+)?(?:cari|carikan)\s+(?:(?:dokumen|file|berkas)\s+)?(?P<query>.+)$",
    re.IGNORECASE,
)
_OPEN_PATTERN = re.compile(
    r"^(?:tolong\s+)?buka\s+"
    r"(?:(?:hasil|dokumen|file|berkas)\s+)?"
    r"(?:(?:yang|nomor|ke)\s+)?"
    r"(?P<position>\d+|satu|dua|tiga|empat|lima|pertama|kedua|ketiga|keempat|kelima)$",
    re.IGNORECASE,
)
_POSITION_WORDS = {
    "satu": 1,
    "pertama": 1,
    "dua": 2,
    "kedua": 2,
    "tiga": 3,
    "ketiga": 3,
    "empat": 4,
    "keempat": 4,
    "lima": 5,
    "kelima": 5,
}


class DocumentCommandService:
    """Coordinates document search state for HTTP requests and Indonesian voice commands."""

    def __init__(self, finder: DocumentFinder) -> None:
        self.finder = finder
        self._lock = threading.RLock()
        self._latest_query = ""
        self._latest_results: list[dict[str, Any]] = []
        self._message = "Cari dokumen lokal melalui dashboard atau perintah suara."
        self._revision = 0

    def search(self, query: str, *, force_refresh: bool = False) -> dict:
        stripped_query = str(query).strip()
        if not stripped_query:
            raise ValueError("Masukkan kata kunci dokumen yang ingin dicari.")

        results = self.finder.search(stripped_query, force_refresh=force_refresh)
        message = (
            f"Ditemukan {len(results)} dokumen untuk \"{stripped_query}\"."
            if results
            else f"Tidak ada dokumen yang cocok dengan \"{stripped_query}\"."
        )
        with self._lock:
            self._latest_query = stripped_query
            self._latest_results = results
            self._message = message
            self._revision += 1
            return self._build_payload(command="document_search")

    def open_result(
        self,
        *,
        result_id: str | None = None,
        position: int | None = None,
    ) -> dict:
        selected_result_id = result_id
        if selected_result_id is None:
            selected_result_id = self._get_result_id_at_position(position)

        document = self.finder.open_document(selected_result_id)
        with self._lock:
            self._message = f"Membuka dokumen: {document['name']}"
            self._revision += 1
            payload = self._build_payload(command="document_open")
            payload["document"] = document
            return payload

    def handle_text(self, text: str) -> dict | None:
        """Return a document command response, or None when text is unrelated."""
        normalized_text = _normalize_command_text(text)
        search_match = _SEARCH_PATTERN.fullmatch(normalized_text)
        if search_match:
            try:
                return self.search(search_match.group("query"))
            except (ValueError, DocumentFinderError) as error:
                return self._error_payload("document_search", str(error))

        open_match = _OPEN_PATTERN.fullmatch(normalized_text)
        if open_match:
            try:
                position = _parse_position(open_match.group("position"))
                return self.open_result(position=position)
            except (ValueError, DocumentFinderError) as error:
                return self._error_payload("document_open", str(error))
        return None

    def get_status(self) -> dict:
        with self._lock:
            payload = self._build_payload()
        payload["index"] = self.finder.get_index_status()
        return payload

    def _get_result_id_at_position(self, position: int | None) -> str:
        if position is None:
            raise ValueError("Pilih dokumen berdasarkan ID atau nomor hasil pencarian.")
        with self._lock:
            if not self._latest_results:
                raise ValueError("Cari dokumen terlebih dahulu sebelum membuka hasil.")
            if position < 1 or position > len(self._latest_results):
                raise ValueError(
                    f"Nomor hasil harus berada di antara 1 dan {len(self._latest_results)}."
                )
            return str(self._latest_results[position - 1]["id"])

    def _error_payload(self, command: str, message: str) -> dict:
        with self._lock:
            self._message = message
            self._revision += 1
            payload = self._build_payload(command=command)
            payload["status"] = "error"
            return payload

    def _build_payload(self, *, command: str | None = None) -> dict:
        payload = {
            "status": "success",
            "query": self._latest_query,
            "results": list(self._latest_results),
            "message": self._message,
            "revision": self._revision,
        }
        if command:
            payload["command"] = command
        return payload


def _normalize_command_text(text: str) -> str:
    lowered = str(text).casefold()
    without_punctuation = re.sub(r"[.,!?;:]+", " ", lowered)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _parse_position(raw_position: str) -> int:
    normalized_position = raw_position.casefold()
    if normalized_position.isdigit():
        return int(normalized_position)
    try:
        return _POSITION_WORDS[normalized_position]
    except KeyError as error:
        raise ValueError("Nomor hasil dokumen tidak dikenali.") from error
