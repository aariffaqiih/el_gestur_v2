# ============================================================
# EL PRESENTASI v2.0 — CLIPBOARD VOICE COMMANDS
# Parsing perintah suara Bahasa Indonesia untuk Clipboard Ring
# ============================================================

from __future__ import annotations

import re
from typing import Any

from clipboard_ring import (
    ClipboardItemNotFoundError,
    ClipboardRing,
    ClipboardRingError,
)

# --- Pola perintah paste item berdasarkan posisi ---
# "tempel yang sebelumnya" / "paste sebelumnya" / "paste yang sebelumnya"
_PASTE_PREVIOUS_PATTERNS = (
    re.compile(
        r"^(?:tolong\s+)?(?:tempel|paste|pakai)\s+(?:yang\s+)?sebelumnya$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:tolong\s+)?(?:tempel|paste|pakai)\s+(?:yang\s+)?(?:lalu|tadi|kemarin)$",
        re.IGNORECASE,
    ),
)

# "tempel nomor 2" / "tempel kedua" / "paste nomor 3" / "tempel ke 4"
_PASTE_POSITION_PATTERNS = (
    re.compile(
        r"^(?:tolong\s+)?(?:tempel|paste|pakai)\s+"
        r"(?:(?:yang|nomor|ke|nomer)\s+)?"
        r"(?P<position>\d+|satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh"
        r"|pertama|kedua|ketiga|keempat|kelima|keenam|ketujuh|kedelapan|kesembilan|kesepuluh)$",
        re.IGNORECASE,
    ),
)

# "lihat clipboard" / "riwayat clipboard"
_LIST_PATTERNS = (
    re.compile(
        r"^(?:tolong\s+)?(?:lihat|tampilkan|buka|tunjukkan)\s+"
        r"(?:riwayat\s+)?clipboard$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:tolong\s+)?riwayat\s+clipboard$",
        re.IGNORECASE,
    ),
)

# "hapus riwayat clipboard" / "bersihkan clipboard"
_CLEAR_PATTERNS = (
    re.compile(
        r"^(?:tolong\s+)?(?:hapus|bersihkan|kosongkan)\s+"
        r"(?:riwayat\s+)?clipboard$",
        re.IGNORECASE,
    ),
)

_POSITION_WORDS = {
    "satu": 1, "pertama": 1,
    "dua": 2, "kedua": 2,
    "tiga": 3, "ketiga": 3,
    "empat": 4, "keempat": 4,
    "lima": 5, "kelima": 5,
    "enam": 6, "keenam": 6,
    "tujuh": 7, "ketujuh": 7,
    "delapan": 8, "kedelapan": 8,
    "sembilan": 9, "kesembilan": 9,
    "sepuluh": 10, "kesepuluh": 10,
}


class ClipboardCommandService:
    """Coordinates clipboard ring operations and Indonesian voice commands."""

    def __init__(self, ring: ClipboardRing) -> None:
        self.ring = ring
        self._message = "Riwayat clipboard siap digunakan."
        self._revision = 0

    # ========================================================
    # HTTP / Direct API
    # ========================================================

    def list_items(self) -> dict[str, Any]:
        items = self.ring.get_ring()
        count = len(items)
        message = (
            f"{count} item di riwayat clipboard."
            if count
            else "Riwayat clipboard kosong."
        )
        return self._success_payload(
            message=message,
            items=items,
        )

    def paste_at(self, position: int) -> dict[str, Any]:
        try:
            item = self.ring.paste_item(position)
            return self._success_payload(
                command="clipboard_paste",
                message=f"Ditempel: item #{position}",
                item=item,
            )
        except ClipboardItemNotFoundError as error:
            return self._error_payload(str(error), command="clipboard_paste")
        except ClipboardRingError as error:
            return self._error_payload(str(error), command="clipboard_paste")

    def clear_ring(self) -> dict[str, Any]:
        self.ring.clear()
        return self._success_payload(
            command="clipboard_clear",
            message="Riwayat clipboard dikosongkan.",
            items=[],
        )

    # ========================================================
    # VOICE COMMAND HANDLER
    # ========================================================

    def handle_text(self, text: str) -> dict[str, Any] | None:
        """
        Parse an Indonesian voice command related to clipboard.
        Return a response dict if handled, or None to pass through.
        """
        normalized = _normalize_command_text(text)

        # --- "tempel yang sebelumnya" ---
        for pattern in _PASTE_PREVIOUS_PATTERNS:
            if pattern.fullmatch(normalized):
                return self.paste_at(2)

        # --- "tempel nomor N" / "tempel kedua" ---
        for pattern in _PASTE_POSITION_PATTERNS:
            match = pattern.fullmatch(normalized)
            if match:
                try:
                    position = _parse_position(match.group("position"))
                except ValueError as error:
                    return self._error_payload(
                        str(error), command="clipboard_paste"
                    )
                return self.paste_at(position)

        # --- "lihat clipboard" / "riwayat clipboard" ---
        for pattern in _LIST_PATTERNS:
            if pattern.fullmatch(normalized):
                return self.list_items()

        # --- "hapus riwayat clipboard" ---
        for pattern in _CLEAR_PATTERNS:
            if pattern.fullmatch(normalized):
                return self.clear_ring()

        return None

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "success",
            "message": self._message,
            "revision": self._revision,
            **self.ring.get_status(),
        }

    # ========================================================
    # INTERNAL PAYLOADS
    # ========================================================

    def _success_payload(
        self,
        *,
        message: str,
        command: str | None = None,
        item: dict[str, Any] | None = None,
        items: list[dict[str, Any]] | None = None,
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
        if item is not None:
            payload["item"] = item
        if items is not None:
            payload["items"] = items
        return payload

    def _error_payload(
        self, message: str, *, command: str | None = None
    ) -> dict[str, Any]:
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


# ========================================================
# UTILITY
# ========================================================

def _normalize_command_text(text: str) -> str:
    lowered = str(text).casefold()
    without_punctuation = re.sub(r"[.,!?;:]+", " ", lowered)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _parse_position(raw: str) -> int:
    normalized = raw.casefold().strip()
    if normalized.isdigit():
        return int(normalized)
    try:
        return _POSITION_WORDS[normalized]
    except KeyError as error:
        raise ValueError(
            f"Posisi clipboard \"{raw}\" tidak dikenali."
        ) from error
