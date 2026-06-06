from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable


class SnippetStoreError(Exception):
    """Base exception for quick template operations."""


class SnippetNotFoundError(SnippetStoreError):
    """Raised when a snippet cannot be found."""


class SnippetValidationError(SnippetStoreError):
    """Raised when snippet input is invalid."""


@dataclass(frozen=True)
class SnippetRecord:
    id: str
    title: str
    body: str
    aliases: tuple[str, ...]
    category: str
    created_at: str
    updated_at: str

    def to_public_dict(self, score: float | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "aliases": list(self.aliases),
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if score is not None:
            payload["score"] = round(score, 2)
        return payload


DEFAULT_SNIPPETS = (
    {
        "title": "Follow Up",
        "aliases": ["follow up", "tindak lanjut"],
        "category": "Email",
        "body": (
            "Halo, saya ingin menindaklanjuti pesan sebelumnya. "
            "Mohon kabari jika ada pembaruan atau hal yang perlu saya lengkapi. "
            "Terima kasih."
        ),
    },
    {
        "title": "Approval Singkat",
        "aliases": ["approval", "persetujuan"],
        "category": "Email",
        "body": (
            "Saya setuju dengan usulan tersebut. Silakan dilanjutkan sesuai rencana, "
            "dengan tetap memperhatikan catatan dan batas waktu yang sudah disepakati."
        ),
    },
    {
        "title": "Laporan Harian",
        "aliases": ["laporan harian", "daily report"],
        "category": "Laporan",
        "body": (
            "Laporan harian:\n"
            "1. Pekerjaan selesai:\n"
            "2. Kendala:\n"
            "3. Rencana berikutnya:\n"
            "4. Bantuan yang dibutuhkan:"
        ),
    },
)


class SnippetStore:
    """Persist and search reusable text snippets in a local JSON file."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        seed_defaults: Iterable[dict[str, Any]] | None = DEFAULT_SNIPPETS,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self._seed_defaults = tuple(seed_defaults or ())
        self._clock = clock or _utc_now_iso
        self._lock = threading.RLock()
        self._snippets: tuple[SnippetRecord, ...] | None = None

    def list(self, query: str | None = None) -> list[dict[str, Any]]:
        normalized_query = _normalize_text(query or "")
        snippets = self._ensure_loaded()
        if not normalized_query:
            return [snippet.to_public_dict() for snippet in snippets]

        scored = [
            (self._score(snippet, normalized_query), snippet)
            for snippet in snippets
        ]
        matches = [(score, snippet) for score, snippet in scored if score > 0]
        matches.sort(
            key=lambda item: (
                -item[0],
                item[1].title.casefold(),
            )
        )
        return [snippet.to_public_dict(score=score) for score, snippet in matches]

    def create(
        self,
        *,
        title: str,
        body: str,
        aliases: Iterable[str] | None = None,
        category: str = "",
    ) -> dict[str, Any]:
        now = self._clock()
        record = SnippetRecord(
            id=uuid.uuid4().hex[:12],
            title=_validate_title(title),
            body=_validate_body(body),
            aliases=_normalize_aliases(aliases or ()),
            category=_validate_category(category),
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            snippets = list(self._ensure_loaded())
            snippets.append(record)
            self._save(snippets)
        return record.to_public_dict()

    def update(self, snippet_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            snippets = list(self._ensure_loaded())
            for index, snippet in enumerate(snippets):
                if snippet.id == snippet_id:
                    updated = SnippetRecord(
                        id=snippet.id,
                        title=(
                            _validate_title(updates["title"])
                            if "title" in updates
                            else snippet.title
                        ),
                        body=(
                            _validate_body(updates["body"])
                            if "body" in updates
                            else snippet.body
                        ),
                        aliases=(
                            _normalize_aliases(updates["aliases"])
                            if "aliases" in updates
                            else snippet.aliases
                        ),
                        category=(
                            _validate_category(updates.get("category", ""))
                            if "category" in updates
                            else snippet.category
                        ),
                        created_at=snippet.created_at,
                        updated_at=self._clock(),
                    )
                    snippets[index] = updated
                    self._save(snippets)
                    return updated.to_public_dict()
        raise SnippetNotFoundError("Template tidak ditemukan.")

    def delete(self, snippet_id: str) -> dict[str, Any]:
        with self._lock:
            snippets = list(self._ensure_loaded())
            kept = [snippet for snippet in snippets if snippet.id != snippet_id]
            if len(kept) == len(snippets):
                raise SnippetNotFoundError("Template tidak ditemukan.")
            self._save(kept)
        return {"id": snippet_id}

    def get(self, snippet_id: str) -> dict[str, Any]:
        for snippet in self._ensure_loaded():
            if snippet.id == snippet_id:
                return snippet.to_public_dict()
        raise SnippetNotFoundError("Template tidak ditemukan.")

    def find_best(self, query: str) -> dict[str, Any]:
        matches = self.list(query=query)
        if not matches:
            raise SnippetNotFoundError(f'Template "{query}" tidak ditemukan.')
        return matches[0]

    def _ensure_loaded(self) -> tuple[SnippetRecord, ...]:
        with self._lock:
            if self._snippets is not None:
                return self._snippets
            if not self.path.exists():
                records = tuple(
                    self._record_from_seed(item) for item in self._seed_defaults
                )
                self._save(records)
                return records

            try:
                raw_items = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise SnippetStoreError(f"File template rusak: {error}") from error

            if not isinstance(raw_items, list):
                raise SnippetStoreError("File template harus berisi daftar JSON.")

            records = tuple(self._record_from_json(item) for item in raw_items)
            self._snippets = tuple(sorted(records, key=lambda item: item.title.casefold()))
            return self._snippets

    def _save(self, snippets: Iterable[SnippetRecord]) -> None:
        records = tuple(sorted(snippets, key=lambda item: item.title.casefold()))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(
                [record.to_public_dict() for record in records],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_path.replace(self.path)
        self._snippets = records

    def _record_from_seed(self, item: dict[str, Any]) -> SnippetRecord:
        now = self._clock()
        return SnippetRecord(
            id=uuid.uuid4().hex[:12],
            title=_validate_title(item.get("title", "")),
            body=_validate_body(item.get("body", "")),
            aliases=_normalize_aliases(item.get("aliases", ())),
            category=_validate_category(item.get("category", "")),
            created_at=now,
            updated_at=now,
        )

    def _record_from_json(self, item: Any) -> SnippetRecord:
        if not isinstance(item, dict):
            raise SnippetStoreError("Setiap template harus berupa object JSON.")
        return SnippetRecord(
            id=str(item.get("id", "")).strip() or uuid.uuid4().hex[:12],
            title=_validate_title(item.get("title", "")),
            body=_validate_body(item.get("body", "")),
            aliases=_normalize_aliases(item.get("aliases", ())),
            category=_validate_category(item.get("category", "")),
            created_at=str(item.get("created_at") or self._clock()),
            updated_at=str(item.get("updated_at") or self._clock()),
        )

    def _score(self, snippet: SnippetRecord, normalized_query: str) -> float:
        normalized_title = _normalize_text(snippet.title)
        normalized_aliases = [_normalize_text(alias) for alias in snippet.aliases]
        normalized_category = _normalize_text(snippet.category)
        searchable = [normalized_title, *normalized_aliases, normalized_category]

        if normalized_query == normalized_title:
            return 200
        if normalized_query in normalized_aliases:
            return 190

        phrase_score = 0
        for value in searchable:
            if normalized_query and normalized_query in value:
                phrase_score = max(phrase_score, 120 if value in normalized_aliases else 100)

        query_tokens = normalized_query.split()
        token_score = 0
        for token in query_tokens:
            if any(token == part for value in searchable for part in value.split()):
                token_score += 24
            elif any(token in value for value in searchable):
                token_score += 10

        similarity = max(
            SequenceMatcher(None, normalized_query, value).ratio()
            for value in searchable
            if value
        )
        if phrase_score == 0 and token_score == 0 and similarity < 0.70:
            return 0
        return phrase_score + token_score + similarity * 30


def resolve_snippet_store_path(configured_path: str | os.PathLike[str]) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(str(configured_path))))
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def _validate_title(title: Any) -> str:
    value = re.sub(r"\s+", " ", str(title).strip())
    if not value:
        raise SnippetValidationError("Judul template wajib diisi.")
    if len(value) > 80:
        raise SnippetValidationError("Judul template maksimal 80 karakter.")
    return value


def _validate_body(body: Any) -> str:
    value = str(body).strip()
    if not value:
        raise SnippetValidationError("Isi template wajib diisi.")
    if len(value) > 5000:
        raise SnippetValidationError("Isi template maksimal 5000 karakter.")
    return value


def _validate_category(category: Any) -> str:
    value = re.sub(r"\s+", " ", str(category or "").strip())
    if len(value) > 60:
        raise SnippetValidationError("Kategori template maksimal 60 karakter.")
    return value


def _normalize_aliases(aliases: Iterable[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        value = re.sub(r"\s+", " ", str(alias).strip())
        if not value:
            continue
        if len(value) > 80:
            raise SnippetValidationError("Alias template maksimal 80 karakter.")
        key = value.casefold()
        if key not in seen:
            normalized.append(value)
            seen.add(key)
    if len(normalized) > 10:
        raise SnippetValidationError("Alias template maksimal 10 item.")
    return tuple(normalized)


def _normalize_text(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(text))
    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
