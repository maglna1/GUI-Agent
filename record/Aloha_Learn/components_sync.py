"""Pure helpers for syncing record-flow icons into harness components/.

This module deliberately holds zero I/O and zero state — every function is a
pure mapping from inputs to outputs so it can be unit-tested in isolation.
The orchestrator lives in screenshot_processor.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


#: 30 chars matches gui_harness/planning/learn.py:224's LABEL_MAX_LEN.
_LABEL_MAX_LEN = 30


@dataclass(frozen=True)
class IconRecord:
    """Metadata for one icon file produced by the default-click branch."""

    filename: str
    action: str
    coords: tuple
    current_software: str
    base: str


# Pre-compiled character-class stripper: backslash, colon, question mark, asterisk.
_SPECIAL_CHARS_RE = re.compile(r"[\\:?*]")


def sanitize_label(raw: str) -> str:
    """Normalize a free-form label to snake_case, lowercased, alnum+underscore.

    Rules (verbatim from spec):
    - lowercase
    - whitespace -> "_"
    - "/" -> "-"
    - strip "\\", ":", "?", "*"
    - truncate to 30 chars

    Raises ValueError when the resulting label is empty (caller should fall back
    to a timestamp key).
    """
    if not raw:
        raise ValueError("label is empty")

    s = raw.strip().lower()
    s = s.replace("\\", "-").replace("/", "-")
    s = _SPECIAL_CHARS_RE.sub("", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"-+", "-", s).strip("-_")
    s = re.sub(r"_+", "_", s).strip("_")
    s = s[:_LABEL_MAX_LEN].rstrip("-_")

    if not s:
        raise ValueError(f"label '{raw}' has no safe characters after sanitization")
    return s