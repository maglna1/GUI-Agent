# parser.py
import json
import os
import glob
from pathlib import Path
from dotenv import load_dotenv

from log_processor import LogProcessor
from screenshot_processor import VideoScreenshotExtractor
from trace_generator import TraceGenerator


def _resolve_project_dir(project_name: str) -> Path:
    """
    Accept either a bare name ('Drag_0') or a full path.

    Lookup order:
      1. <project_name> as-is (covers absolute or cwd-relative paths)
      2. <cwd>/projects/<project_name>           (record/-style cwd)
      3. <script_dir>/projects/<project_name>     (running from repo root)
    """
    learn_dir = Path(__file__).resolve().parent
    candidates = [
        Path(project_name),
        Path.cwd() / "projects" / project_name,
        learn_dir / "projects" / project_name,
    ]
    for cand in candidates:
        if cand.is_dir():
            return cand.resolve()
    raise FileNotFoundError(
        "Project folder not found. Tried:\n  - "
        + "\n  - ".join(str(c) for c in candidates)
    )


def _find_single_log(inputs_dir: Path) -> Path:
    """
    Find exactly one log file in inputs_dir with extensions .txt, .log, .json.
    Match the behavior expected by the existing LogProcessor CLI.
    """
    hits = []
    for ext in ("*.txt", "*.log", "*.json"):
        hits.extend(inputs_dir.glob(ext))
    if not hits:
        raise FileNotFoundError(f"No log files in {inputs_dir} (accepted: .txt, .log, .json)")
    if len(hits) > 1:
        names = ", ".join(h.name for h in hits)
        raise RuntimeError(f"Multiple log files in {inputs_dir}: {names}. Keep only one.")
    return hits[0]


def run_pipeline(project_name: str) -> Path:
    """
    Orchestrate the 3-step pipeline:
      1) parse & merge events -> {project}_processed_log.json
      2) extract screenshots + crops -> {project}_processed_log_sc.json
      3) LLM trace generation -> {project}_trace.json

    Env flags (used by the unified pipeline window to split prep vs trace):
      PARSER_PREP_ONLY=1   -> run step 1+2 only (generate screenshots + icon
                              crops), skip step 3. Lets the pipeline name
                              icons before trace generation.
      PARSER_TRACE_ONLY=1  -> run step 3 only (assumes step 1+2 already ran).

    Only input: project_name (string). Returns final trace path (or processed
    log path when prep-only).
    """
    learn_dir = Path(__file__).resolve().parent
    load_dotenv(learn_dir.parent / ".env", override=True)
    project_dir = _resolve_project_dir(project_name)

    prep_only = os.environ.get("PARSER_PREP_ONLY", "0") == "1"
    trace_only = os.environ.get("PARSER_TRACE_ONLY", "0") == "1"

    processed_log_path = project_dir / f"{project_dir.name}_processed_log.json"
    screenshots_dir: str = str(project_dir / "screenshots")

    if not trace_only:
        # ---------- Step 1: process raw log -> processed log ----------
        inputs_dir = project_dir / "inputs"
        if not inputs_dir.exists():
            raise FileNotFoundError(f"Inputs directory not found: {inputs_dir}")
        raw_log = _find_single_log(inputs_dir)

        lp = LogProcessor()
        lp.process_log_file(str(raw_log), str(processed_log_path), time_threshold=5.0)

        # ---------- Step 2: screenshots + scaled coords -> *_processed_log_sc.json ----------
        vse = VideoScreenshotExtractor()
        _, screenshots_dir, meta = vse.process_project(str(project_dir))

    if prep_only:
        print("=== Prep Complete (PARSER_PREP_ONLY=1, step 3 skipped) ===")
        print(f"Project: {project_dir.name}")
        print(f"Processed log: {processed_log_path.name}")
        print(f"Screenshots dir: {Path(screenshots_dir).name}")
        return processed_log_path

    # ---------- Step 3: generate LLM trace -> {project}_trace.json ----------
    log_sc = project_dir / f"{project_dir.name}_processed_log_sc.json"
    if not log_sc.exists():
        raise FileNotFoundError(f"Expected processed-with-screenshots log not found: {log_sc}")

    out_trace = project_dir / f"{project_dir.name}_trace.json"

    tg = TraceGenerator(
        default_prompt_path=str(learn_dir / "default_prompt.json"),
        api_provider="openai",
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        claude_model="claude-sonnet-4-20250514",
        api_keys_path=str(learn_dir / "config" / "api_keys.json"),
    )

    library_roots = [str(learn_dir / "projects")]
    run_icon_review = os.environ.get("RUN_ICON_REVIEW", "1") != "0"
    force_icon_review = os.environ.get("FORCE_ICON_REVIEW", "0") == "1"
    decisions_path = project_dir / f"{project_dir.name}_icon_review.json"

    preloaded_decisions: dict | None = None
    if decisions_path.exists() and not force_icon_review:
        try:
            payload = json.loads(decisions_path.read_text(encoding="utf-8"))
            preloaded_decisions = payload.get("decisions") or {}
        except (OSError, ValueError):
            preloaded_decisions = None

    tg.generate_trace(
        recording_json_path=str(log_sc),
        screenshots_dir=str(screenshots_dir),
        output_trace_path=str(out_trace),
        overall_task="",
        library_roots=library_roots,
        run_icon_review=run_icon_review,
        icon_review_decisions_path=decisions_path,
        icon_review_decisions=preloaded_decisions,
    )

    print("=== Pipeline Complete ===")
    print(f"Project: {project_dir.name}")
    print(f"Processed log: {processed_log_path.name}")
    print(f"Screenshots dir: {Path(screenshots_dir).name}")
    print(f"Processed log (+screens): {log_sc.name}")
    print(f"Trace: {out_trace.name}")
    return out_trace


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run full Parser pipeline (1) log → (2) screenshots → (3) trace")
    parser.add_argument("project_name", help="Either a bare name (e.g., 'Drag_0') or a full path to the project folder.")
    args = parser.parse_args()
    run_pipeline(args.project_name)
