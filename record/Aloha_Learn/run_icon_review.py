"""One-shot wrapper: load record/.env, then run_icon_review_session.

Mirrors run_review_ui.py:24-79 but for the icon-review (Step 3 trace
generation helper). Pops a Chromium --app window listing every click
operation; the user marks which are "icon clicks" and picks the matching
label from the icon memory library. The script then prints the decisions
to stdout as JSON for piping (the Python caller — trace_generator.py —
consumes this; the user-facing CLI is a wrapper around that).

CLI use:
    python Aloha_Learn/run_icon_review.py <project_path>
Output: JSON with `decisions` array.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Re-use the run_review_ui.py env-loader (small + tested).
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _load_env_file(env_path: Path) -> int:
    if not env_path.exists():
        return 0
    loaded = 0
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
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

    project_dir = Path(argv[1]).resolve()
    if not (project_dir / f"{project_dir.name}_processed_log_sc.json").exists():
        print(f"ERROR: {project_dir.name}_processed_log_sc.json not found in {project_dir}. "
              f"Run parser.py first.", file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / ".env"
    loaded = _load_env_file(env_path)
    print(f"[run_icon_review] loaded {loaded} vars from {env_path}", file=sys.stderr)

    sys.path.insert(0, str(script_dir))
    from icon_review_server import run_icon_review_session

    # Load click metadata from _sc.json. Only LClick actions are candidates.
    sc_actions = json.loads((project_dir / f"{project_dir.name}_processed_log_sc.json").read_text(encoding="utf-8"))
    clicks: list[dict] = []
    for idx, a in enumerate(sc_actions):
        if (a.get("action") or "").startswith("LClick at"):
            coords = a.get("coords") or []
            x, y = (coords[0]["x"], coords[0]["y"]) if coords else (None, None)
            clicks.append({
                "step_idx": idx,
                "timestamp": a["timestamp"],
                "coords": [x, y],
                "current_software": a.get("current_software", ""),
            })

    if not clicks:
        print(json.dumps({"decisions": {}}))
        return 0

    screenshot_dir = project_dir / "screenshots"
    # Default library root: <record>/Aloha_Learn/projects. script_dir
    # lives at record/Aloha_Learn/run_icon_review.py; parent is record/.
    library_roots = [str(script_dir.parent / "Aloha_Learn" / "projects")]

    decisions = run_icon_review_session(
        clicks=clicks,
        library_roots=library_roots,
        screenshot_dir=screenshot_dir,
    )

    # Persist decisions so the next parser.py / run_icon_review.py run can
    # skip the window when the user already decided. Mirrors parser.py.
    out_path = project_dir / f"{project_dir.name}_icon_review.json"
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "decisions": decisions,
                "libraryRoots": library_roots,
                "decidedAt": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(json.dumps({
        "decisions": decisions,
        "click_count": len(clicks),
        "persisted_to": str(out_path),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))