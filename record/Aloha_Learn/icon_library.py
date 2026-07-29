"""Icon memory library scanner (Python side).

Mirrors execution/cua/icon-memory/find-icon.ts:18-50 but in plain Python so
record/Aloha_Learn does not need to spawn node for a 30-line scan.

Convention: each library root contains project directories with
    <project>/components_review_ui_mutimodal_memory_manual/components/<label>.png
This is the byproduct of review-UI sync (record/Aloha_Learn/components_sync.py).
"""
from __future__ import annotations

import base64
from pathlib import Path


def find_icon_by_label(label: str, library_roots: list[str]) -> str | None:
    """Return absolute path to the alphabetically-first PNG matching <label>.png.

    Raises ValueError on empty label / roots (caller bug). Returns None when
    no project under any root has the label.

    Multiple library roots are scanned; the first match (by sorted project
    directory, then root order) wins. This mirrors execution's behaviour.
    """
    if not label:
        raise ValueError("label 不能为空")
    if not library_roots:
        raise ValueError("library_roots 不能为空")

    icon_name = f"{label}.png"

    # Roots are scanned in caller-supplied order; within each root the
    # project sub-directories are sorted lexicographically for determinism.
    # The first match wins (root order > project order > not retried).
    for root in library_roots:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        for project_dir in sorted(p for p in root_path.iterdir() if p.is_dir()):
            candidate = (
                project_dir
                / "components_review_ui_mutimodal_memory_manual"
                / "components"
                / icon_name
            )
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def load_icon_as_data_url(icon_path: str) -> str:
    """Read PNG and return 'data:image/png;base64,...' URL.

    Mirrors execution/cua/icon-memory/load-icon.ts.
    """
    data = Path(icon_path).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def list_labels(library_roots: list[str]) -> list[str]:
    """Return all distinct labels available across library roots (sorted)."""
    labels: set[str] = set()
    for root in library_roots:
        root_path = Path(root)
        if not root_path.is_dir():
            continue
        for project_dir in (p for p in root_path.iterdir() if p.is_dir()):
            comp_dir = (
                project_dir
                / "components_review_ui_mutimodal_memory_manual"
                / "components"
            )
            if comp_dir.is_dir():
                for f in comp_dir.iterdir():
                    if f.suffix.lower() == ".png" and f.stem:
                        labels.add(f.stem)
    return sorted(labels)