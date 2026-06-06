from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable
from typing import Any

import pyautogui

from snippet_store import (
    SnippetNotFoundError,
    SnippetStore,
    SnippetStoreError,
    SnippetValidationError,
)


_INSERT_PATTERNS = (
    re.compile(
        r"^(?:tolong\s+)?(?:pakai|gunakan)\s+(?:template|snippet)\s+(?P<query>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:tolong\s+)?(?:tempel|paste|tulis|masukkan|masukan)\s+"
        r"(?:template|snippet)\s+(?P<query>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:tolong\s+)?(?:template|snippet)\s+(?P<query>.+)$",
        re.IGNORECASE,
    ),
)


class SnippetCommandService:
    """Coordinates snippet CRUD, insertion, and Indonesian voice commands."""

    def __init__(
        self,
        store: SnippetStore,
        *,
        inserter: Callable[[str], None] | None = None,
    ) -> None:
        self.store = store
        self._inserter = inserter or paste_text_to_active_app
        self._message = "Pilih atau ucapkan nama template untuk menempelkannya."
        self._revision = 0

    def list(self, query: str | None = None) -> dict[str, Any]:
        try:
            snippets = self.store.list(query=query)
            message = (
                f"Ditemukan {len(snippets)} template."
                if query
                else "Daftar template siap digunakan."
            )
            return self._success_payload(message=message, snippets=snippets)
        except SnippetStoreError as error:
            return self._error_payload(str(error))

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            snippet = self.store.create(
                title=data.get("title", ""),
                body=data.get("body", ""),
                aliases=_coerce_aliases(data.get("aliases", ())),
                category=data.get("category", ""),
            )
            return self._success_payload(
                command="snippet_create",
                message=f"Template dibuat: {snippet['title']}",
                snippet=snippet,
                snippets=self.store.list(),
            )
        except (SnippetStoreError, SnippetValidationError) as error:
            return self._error_payload(str(error), command="snippet_create")

    def update(self, snippet_id: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            updates = dict(data)
            if "aliases" in updates:
                updates["aliases"] = _coerce_aliases(updates["aliases"])
            snippet = self.store.update(snippet_id, updates)
            return self._success_payload(
                command="snippet_update",
                message=f"Template diperbarui: {snippet['title']}",
                snippet=snippet,
                snippets=self.store.list(),
            )
        except (SnippetStoreError, SnippetValidationError) as error:
            return self._error_payload(str(error), command="snippet_update")

    def delete(self, snippet_id: str) -> dict[str, Any]:
        try:
            deleted = self.store.delete(snippet_id)
            return self._success_payload(
                command="snippet_delete",
                message="Template dihapus.",
                snippet=deleted,
                snippets=self.store.list(),
            )
        except SnippetStoreError as error:
            return self._error_payload(str(error), command="snippet_delete")

    def insert(
        self,
        *,
        snippet_id: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        try:
            normalized_query = str(query or "").strip()
            if not snippet_id and not normalized_query:
                return self._error_payload(
                    "Pilih template atau masukkan nama template yang ingin ditempel.",
                    command="snippet_insert",
                )
            snippet = (
                self.store.get(str(snippet_id))
                if snippet_id
                else self.store.find_best(normalized_query)
            )
            self._inserter(str(snippet["body"]))
            return self._success_payload(
                command="snippet_insert",
                message=f"Template ditempel: {snippet['title']}",
                snippet=snippet,
            )
        except SnippetNotFoundError as error:
            return self._error_payload(str(error), command="snippet_insert")
        except SnippetStoreError as error:
            return self._error_payload(str(error), command="snippet_insert")
        except Exception as error:
            return self._error_payload(
                f"Gagal menempel template: {error}",
                command="snippet_insert",
            )

    def handle_text(self, text: str) -> dict[str, Any] | None:
        normalized_text = _normalize_command_text(text)
        for pattern in _INSERT_PATTERNS:
            match = pattern.fullmatch(normalized_text)
            if match:
                query = match.group("query").strip()
                if not query:
                    return self._error_payload(
                        "Sebutkan nama template yang ingin dipakai.",
                        command="snippet_insert",
                    )
                return self.insert(query=query)
        return None

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "success",
            "message": self._message,
            "revision": self._revision,
        }

    def _success_payload(
        self,
        *,
        message: str,
        command: str | None = None,
        snippet: dict[str, Any] | None = None,
        snippets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._message = message
        self._revision += 1
        payload: dict[str, Any] = {
            "status": "success",
            "message": message,
            "revision": self._revision,
        }
        if command:
            payload["command"] = command
        if snippet is not None:
            payload["snippet"] = snippet
        if snippets is not None:
            payload["snippets"] = snippets
        return payload

    def _error_payload(self, message: str, *, command: str | None = None) -> dict[str, Any]:
        self._message = message
        self._revision += 1
        payload: dict[str, Any] = {
            "status": "error",
            "message": message,
            "revision": self._revision,
        }
        if command:
            payload["command"] = command
        return payload


def paste_text_to_active_app(text: str) -> None:
    """Paste exact snippet text into the active app using the clipboard."""
    try:
        import pyperclip

        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        return
    except ImportError:
        pass

    process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
    process.communicate(str(text).encode("utf-16-le"))
    time.sleep(0.05)
    pyautogui.hotkey("ctrl", "v")


def _coerce_aliases(raw_aliases: Any) -> list[str]:
    if raw_aliases is None:
        return []
    if isinstance(raw_aliases, str):
        return [part.strip() for part in raw_aliases.split(",") if part.strip()]
    return [str(alias).strip() for alias in raw_aliases if str(alias).strip()]


def _normalize_command_text(text: str) -> str:
    lowered = str(text).casefold()
    without_punctuation = re.sub(r"[.,!?;:]+", " ", lowered)
    return re.sub(r"\s+", " ", without_punctuation).strip()
