from __future__ import annotations


DEFAULT_REDO_SHORTCUT = ("ctrl", "y")
REDO_SHORTCUTS_BY_SOFTWARE = {
    "figma": ("ctrl", "shift", "z"),
    "notion": ("ctrl", "shift", "z"),
}


def get_redo_shortcut(software: str) -> tuple[str, ...]:
    """Return the redo shortcut used by the selected desktop software profile."""
    return REDO_SHORTCUTS_BY_SOFTWARE.get(software, DEFAULT_REDO_SHORTCUT)
