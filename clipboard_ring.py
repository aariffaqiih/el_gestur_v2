# ============================================================
# EL PRESENTASI v2.0 — CLIPBOARD RING (Smart Clipboard History)
# Menyimpan riwayat clipboard teks dan memungkinkan paste
# item lama tanpa harus copy ulang.
# ============================================================

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import pyautogui


class ClipboardRingError(Exception):
    """Base exception for clipboard ring operations."""


class ClipboardItemNotFoundError(ClipboardRingError):
    """Raised when a requested clipboard position does not exist."""


@dataclass(frozen=True)
class ClipboardItem:
    """A single clipboard entry with metadata."""
    text: str
    copied_at: str
    source_label: str = ""

    def to_public_dict(self, position: int) -> dict[str, Any]:
        preview = self.text[:120] + ("…" if len(self.text) > 120 else "")
        return {
            "position": position,
            "text": self.text,
            "preview": preview,
            "length": len(self.text),
            "copied_at": self.copied_at,
            "source_label": self.source_label,
        }


def _read_clipboard() -> str | None:
    """Read current clipboard text content, returning None on failure."""
    try:
        import pyperclip
        content = pyperclip.paste()
        return content if isinstance(content, str) else None
    except ImportError:
        pass
    except Exception:
        return None

    # Fallback: Windows PowerShell
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                return result.stdout.rstrip("\r\n")
        except Exception:
            pass
    return None


def _write_clipboard(text: str) -> None:
    """Write text to the system clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except ImportError:
        pass

    # Fallback: Windows clip.exe
    if sys.platform == "win32":
        try:
            process = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE, shell=True,
            )
            process.communicate(text.encode("utf-16-le"))
            return
        except Exception:
            pass
    raise ClipboardRingError("Tidak dapat menulis ke clipboard.")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class ClipboardRing:
    """
    Background clipboard monitor that maintains a ring buffer of recent
    text copies.  Items can be pasted back into the active application
    by position number.
    """

    def __init__(
        self,
        max_size: int = 10,
        poll_interval: float = 0.5,
        *,
        clock: Callable[[], str] | None = None,
        inserter: Callable[[str], None] | None = None,
    ) -> None:
        if max_size <= 0:
            raise ValueError("max_size harus lebih besar dari nol.")
        if poll_interval <= 0:
            raise ValueError("poll_interval harus lebih besar dari nol.")

        self.max_size = max_size
        self.poll_interval = poll_interval
        self._clock = clock or _utc_now_iso
        self._inserter = inserter or self._default_inserter
        self._lock = threading.RLock()
        self._ring: deque[ClipboardItem] = deque(maxlen=max_size)
        self._last_clipboard_text: str | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._is_running = False
        self._revision = 0

    # ========================================================
    # PUBLIC API
    # ========================================================

    def start(self) -> bool:
        """Start the background clipboard watcher thread."""
        if self._is_running:
            return False
        # Seed with current clipboard content so it's not duplicated
        # on the very first poll cycle.
        self._last_clipboard_text = _read_clipboard()
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("📋 ClipboardRing: Monitoring dimulai.")
        return True

    def stop(self) -> bool:
        """Stop the background watcher thread."""
        if not self._is_running:
            return False
        self._stop_event.set()
        self._is_running = False
        print("📋 ClipboardRing: Monitoring dihentikan.")
        return True

    def get_ring(self) -> list[dict[str, Any]]:
        """Return the full ring as a list of public dicts, newest first."""
        with self._lock:
            return [
                item.to_public_dict(position=index + 1)
                for index, item in enumerate(self._ring)
            ]

    def get_item(self, position: int) -> ClipboardItem:
        """Get a ring item by 1-based position (1 = newest)."""
        with self._lock:
            if position < 1 or position > len(self._ring):
                raise ClipboardItemNotFoundError(
                    f"Posisi {position} tidak ada di riwayat clipboard "
                    f"(tersedia 1–{len(self._ring)})."
                )
            return self._ring[position - 1]

    def paste_item(self, position: int) -> dict[str, Any]:
        """
        Paste a specific ring item into the currently active application.
        This replaces the system clipboard with the chosen item and
        sends Ctrl+V.
        """
        item = self.get_item(position)
        self._inserter(item.text)
        # Update last_clipboard_text so the watcher doesn't re-record
        # the item we just pasted.
        with self._lock:
            self._last_clipboard_text = item.text
        return item.to_public_dict(position=position)

    def clear(self) -> None:
        """Empty the ring buffer."""
        with self._lock:
            self._ring.clear()
            self._revision += 1
        print("📋 ClipboardRing: Riwayat dihapus.")

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "is_running": self._is_running,
                "count": len(self._ring),
                "max_size": self.max_size,
                "revision": self._revision,
            }

    # ========================================================
    # INTERNAL
    # ========================================================

    def _poll_loop(self) -> None:
        """Periodically check clipboard and push new items to the ring."""
        while not self._stop_event.is_set():
            try:
                current = _read_clipboard()
                if current and current != self._last_clipboard_text:
                    self._push(current)
                    self._last_clipboard_text = current
            except Exception as error:
                print(f"📋 ClipboardRing poll error: {error}")
            self._stop_event.wait(self.poll_interval)

    def _push(self, text: str) -> None:
        """Add a new item to the front of the ring."""
        with self._lock:
            # Deduplicate: jika teks yang sama sudah ada di posisi 1, abaikan
            if self._ring and self._ring[0].text == text:
                return
            # Jika teks sudah ada di posisi lain, hapus duplikat lama
            self._ring = deque(
                (item for item in self._ring if item.text != text),
                maxlen=self.max_size,
            )
            self._ring.appendleft(
                ClipboardItem(text=text, copied_at=self._clock())
            )
            self._revision += 1

    @staticmethod
    def _default_inserter(text: str) -> None:
        """Write to clipboard and press Ctrl+V."""
        _write_clipboard(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
