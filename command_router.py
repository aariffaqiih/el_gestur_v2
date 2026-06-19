from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Union


CommandHandler = Callable[[str], Union[dict[str, Any], None]]


class CommandRouter:
    """Try voice command handlers in order and return the first handled result."""

    def __init__(self, handlers: Iterable[CommandHandler]) -> None:
        self._handlers = tuple(handlers)

    def handle_text(self, text: str) -> dict[str, Any] | None:
        for handler in self._handlers:
            result = handler(text)
            if result is not None:
                return result
        return None
