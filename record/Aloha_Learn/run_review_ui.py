"""One-shot wrapper: load record/.env, run process_project, print review-related meta.

Usage:
    cd record
    ../.venv/Scripts/python.exe Aloha_Learn/run_review_ui.py <project_path>

What it does:
1. Loads record/.env (KEY=VALUE lines, ignoring comments and blanks) into os.environ.
   Existing env vars take precedence (not overwritten).
2. Invokes VideoScreenshotExtractor().process_project(project_path), which always
   runs the human-in-the-loop review UI and writes to
   <project_dir>/components_review_ui_mutimodal_memory_manual/.
3. Prints the review-related meta fields (components_dest / components_synced /
   review_decisions / review_port / etc.).

This exists so a single command (no inline `python -c`) can drive the full flow
on a project that has already produced <project>_processed_log.json.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_env_file(env_path: Path) -> int:
    """Load KEY=VALUE pairs from env_path into os.environ.

    Skips blank lines and lines starting with '#'. Existing env vars take
    precedence (setdefault semantics). Returns the count of vars loaded.
    """
    if not env_path.exists():
        return 0
    loaded = 0
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        if k in os.environ:
            continue
        os.environ[k] = v
        loaded += 1
    return loaded


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        print("ERROR: project path argument required.", file=sys.stderr)
        return 2

    project_path = argv[1]

    # Load .env from the record/ directory (this script lives in record/Aloha_Learn/).
    script_dir = Path(__file__).resolve().parent
    record_dir = script_dir.parent
    env_path = record_dir / ".env"
    loaded = _load_env_file(env_path)
    print(f"[run_review_ui] loaded {loaded} vars from {env_path}")

    # Make sure the Aloha_Learn package is importable when invoked as a script.
    sys.path.insert(0, str(record_dir))

    from screenshot_processor import VideoScreenshotExtractor

    ext = VideoScreenshotExtractor()
    _actions, _shots, meta = ext.process_project(project_path)

    print("=== DONE ===")
    for k in sorted(meta):
        if k.startswith("review") or k.startswith("components"):
            print(f"  {k}: {meta[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))