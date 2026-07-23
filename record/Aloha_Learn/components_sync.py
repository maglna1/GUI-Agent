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


def dedup_labels(labels):
    """Append _2/_3/... suffixes to duplicates so each returned label is unique.

    Order-preserving: first occurrence wins without suffix; later collisions get
    suffixes that avoid clashing with already-seen labels.
    """
    seen = set()
    out = []
    for label in labels:
        candidate = label
        suffix = 2
        while candidate in seen:
            candidate = f"{label}_{suffix}"
            suffix += 1
        seen.add(candidate)
        out.append(candidate)
    return out


@dataclass(frozen=True)
class ComponentEntry:
    """One entry in the harness components.json — mirrors the schema of the
    existing 17 desktop/ entries (see gui_harness/memory/apps/desktop/components.json).
    """

    type: str
    source: str
    icon_file: str
    label: str
    learned_at: str
    last_seen: str
    seen_count: int
    consecutive_misses: int
    base_memory: bool


def build_component_entry(
    *,
    label: str,
    icon_file: str,
    learned_at: str,
    last_seen: str,
    seen_count: int,
    base_memory: bool = True,
) -> dict:
    """Construct a full component entry dict.

    base_memory defaults to True and is load-bearing: harness uses it to skip
    freshly-imported icons from automatic forgetting. Never set to False.
    """
    return ComponentEntry(
        type="icon",
        source="learn_batch",
        icon_file=icon_file,
        label=label,
        learned_at=learned_at,
        last_seen=last_seen,
        seen_count=seen_count,
        consecutive_misses=0,
        base_memory=base_memory,
    ).__dict__