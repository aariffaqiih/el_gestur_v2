from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable, Sequence


class DocumentFinderError(Exception):
    """Base exception for local document operations."""


class DocumentNotFoundError(DocumentFinderError):
    """Raised when a document result no longer exists or is unknown."""


class DocumentOpenError(DocumentFinderError):
    """Raised when the operating system cannot open a document."""


@dataclass(frozen=True)
class DocumentRecord:
    result_id: str
    path: Path
    modified_timestamp: float
    size_bytes: int

    def to_public_dict(self, score: float | None = None) -> dict:
        result = {
            "id": self.result_id,
            "name": self.path.name,
            "path": str(self.path),
            "parent": str(self.path.parent),
            "extension": self.path.suffix.lower(),
            "size_bytes": self.size_bytes,
            "modified_at": _format_timestamp(self.modified_timestamp),
            "modified_timestamp": self.modified_timestamp,
        }
        if score is not None:
            result["score"] = round(score, 2)
        return result


def resolve_search_roots(
    configured_paths: Iterable[str | os.PathLike[str]],
    environment_override: str | None = None,
) -> tuple[Path, ...]:
    """Resolve configured roots, optionally replacing them with an OS-path-separated override."""
    raw_paths: Iterable[str | os.PathLike[str]] = configured_paths
    if environment_override:
        raw_paths = [part for part in environment_override.split(os.pathsep) if part.strip()]

    resolved_roots: list[Path] = []
    seen: set[str] = set()
    for raw_path in raw_paths:
        expanded = os.path.expandvars(os.path.expanduser(str(raw_path).strip()))
        if not expanded:
            continue
        root = Path(expanded).resolve()
        root_key = os.path.normcase(str(root))
        if root_key not in seen:
            resolved_roots.append(root)
            seen.add(root_key)
    return tuple(resolved_roots)


class DocumentFinder:
    """Indexes, searches, and securely opens local documents from configured roots."""

    def __init__(
        self,
        roots: Sequence[str | os.PathLike[str]],
        extensions: Iterable[str],
        *,
        max_results: int = 5,
        index_ttl_seconds: float = 60,
        excluded_directory_names: Iterable[str] = (),
        max_index_files: int = 20_000,
        opener: Callable[[Path], None] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if max_results <= 0:
            raise ValueError("max_results harus lebih besar dari nol.")
        if index_ttl_seconds < 0:
            raise ValueError("index_ttl_seconds tidak boleh negatif.")
        if max_index_files <= 0:
            raise ValueError("max_index_files harus lebih besar dari nol.")

        self.roots = tuple(Path(root).expanduser().resolve() for root in roots)
        self.extensions = frozenset(_normalize_extension(extension) for extension in extensions)
        self.max_results = max_results
        self.index_ttl_seconds = index_ttl_seconds
        self.excluded_directory_names = frozenset(
            name.casefold() for name in excluded_directory_names
        )
        self.max_index_files = max_index_files
        self._opener = opener or _open_with_default_application
        self._clock = clock
        self._lock = threading.RLock()
        self._records: tuple[DocumentRecord, ...] = ()
        self._records_by_id: dict[str, DocumentRecord] = {}
        self._last_indexed_at: float | None = None
        self._limit_reached = False

    def refresh(self) -> dict:
        """Rebuild the local index while tolerating unreadable folders and files."""
        records_by_path: dict[str, DocumentRecord] = {}
        limit_reached = False

        for root in self.roots:
            if not root.is_dir():
                continue

            for current_dir, directory_names, file_names in os.walk(
                root,
                topdown=True,
                onerror=lambda _error: None,
            ):
                directory_names[:] = [
                    name
                    for name in directory_names
                    if not self._should_skip_directory(name)
                ]

                for file_name in file_names:
                    if Path(file_name).suffix.lower() not in self.extensions:
                        continue

                    path = Path(current_dir, file_name)
                    try:
                        resolved_path = path.resolve()
                        stat = resolved_path.stat()
                    except OSError:
                        continue

                    path_key = os.path.normcase(str(resolved_path))
                    records_by_path[path_key] = DocumentRecord(
                        result_id=_create_result_id(resolved_path),
                        path=resolved_path,
                        modified_timestamp=stat.st_mtime,
                        size_bytes=stat.st_size,
                    )
                    if len(records_by_path) >= self.max_index_files:
                        limit_reached = True
                        break

                if limit_reached:
                    break
            if limit_reached:
                break

        records = tuple(
            sorted(
                records_by_path.values(),
                key=lambda record: (-record.modified_timestamp, record.path.name.casefold()),
            )
        )
        with self._lock:
            self._records = records
            self._records_by_id = {record.result_id: record for record in records}
            self._last_indexed_at = self._clock()
            self._limit_reached = limit_reached
            return self.get_index_status()

    def search(
        self,
        query: str,
        *,
        max_results: int | None = None,
        force_refresh: bool = False,
    ) -> list[dict]:
        normalized_query = _normalize_text(query)
        if not normalized_query:
            raise ValueError("Kata kunci pencarian dokumen tidak boleh kosong.")

        self._ensure_index(force_refresh=force_refresh)
        result_limit = max_results or self.max_results
        if result_limit <= 0:
            raise ValueError("Batas hasil pencarian harus lebih besar dari nol.")

        with self._lock:
            scored_records = [
                (self._score(record, normalized_query), record)
                for record in self._records
            ]
        matching_records = [
            (score, record) for score, record in scored_records if score > 0
        ]
        matching_records.sort(
            key=lambda item: (
                -item[0],
                -item[1].modified_timestamp,
                item[1].path.name.casefold(),
            )
        )
        return [
            record.to_public_dict(score=score)
            for score, record in matching_records[:result_limit]
        ]

    def open_document(self, result_id: str) -> dict:
        """Open an indexed document using the operating system default application."""
        self._ensure_index(force_refresh=False)
        with self._lock:
            record = self._records_by_id.get(str(result_id))
        if record is None:
            raise DocumentNotFoundError("Dokumen tidak ditemukan pada indeks lokal.")
        if not record.path.is_file():
            raise DocumentNotFoundError("Dokumen sudah dipindahkan atau dihapus.")

        try:
            self._opener(record.path)
        except OSError as error:
            raise DocumentOpenError(f"Gagal membuka dokumen: {error}") from error
        return record.to_public_dict()

    def get_index_status(self) -> dict:
        with self._lock:
            available_roots = [str(root) for root in self.roots if root.is_dir()]
            missing_roots = [str(root) for root in self.roots if not root.is_dir()]
            return {
                "indexed_count": len(self._records),
                "indexed_at": (
                    _format_timestamp(self._last_indexed_at)
                    if self._last_indexed_at is not None
                    else None
                ),
                "available_roots": available_roots,
                "missing_roots": missing_roots,
                "limit_reached": self._limit_reached,
            }

    def _ensure_index(self, *, force_refresh: bool) -> None:
        with self._lock:
            is_stale = (
                self._last_indexed_at is None
                or self._clock() - self._last_indexed_at >= self.index_ttl_seconds
            )
        if force_refresh or is_stale:
            self.refresh()

    def _should_skip_directory(self, directory_name: str) -> bool:
        return (
            directory_name.startswith(".")
            or directory_name.casefold() in self.excluded_directory_names
        )

    def _score(self, record: DocumentRecord, normalized_query: str) -> float:
        normalized_name = _normalize_text(record.path.name)
        normalized_stem = _normalize_text(record.path.stem)
        query_tokens = normalized_query.split()
        name_tokens = set(normalized_stem.split())

        phrase_match = normalized_query in normalized_stem
        token_scores = []
        for token in query_tokens:
            if token in name_tokens:
                token_scores.append(24)
            elif token in normalized_name:
                token_scores.append(14)
            else:
                token_scores.append(0)

        similarity = SequenceMatcher(None, normalized_query, normalized_stem).ratio()
        if not phrase_match and not any(token_scores) and similarity < 0.55:
            return 0

        exact_phrase_score = 160 if normalized_query == normalized_stem else 0
        phrase_score = 100 if phrase_match else 0
        similarity_score = similarity * 30
        age_days = max(0, self._clock() - record.modified_timestamp) / 86_400
        recency_score = 12 / (1 + age_days / 30)
        return exact_phrase_score + phrase_score + sum(token_scores) + similarity_score + recency_score


def _normalize_extension(extension: str) -> str:
    normalized = extension.strip().lower()
    if not normalized:
        raise ValueError("Ekstensi dokumen tidak boleh kosong.")
    return normalized if normalized.startswith(".") else f".{normalized}"


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text))
    without_accents = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()


def _create_result_id(path: Path) -> str:
    normalized_path = os.path.normcase(str(path)).encode("utf-8")
    return hashlib.sha256(normalized_path).hexdigest()[:16]


def _format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


def _open_with_default_application(path: Path) -> None:
    if hasattr(os, "startfile"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
