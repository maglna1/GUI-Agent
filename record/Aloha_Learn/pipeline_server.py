"""HTTP server hosting the 4-step unified pipeline UI.

Endpoints:
    GET  /                              static pipeline-ui/dist/index.html (when built)
    GET  /api/pipeline/state           JSON snapshot of current orchestrator state
    GET  /api/pipeline/events          SSE stream of orchestrator events
    POST /api/pipeline/start            start (or restart) the pipeline
    POST /api/pipeline/labels          submit edited Step 1 labels  (forward to orchestrator)
    POST /api/pipeline/decisions        submit Step 3 click decisions
    POST /api/pipeline/run-actual-task  opt-in to real desktop task run
    POST /api/pipeline/cancel           cancel in-flight pipeline

Mirrors the pattern in icon_review_server.py: stdlib HTTP, OS-assigned port,
30-minute idle timeout fallback.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from pipeline_orchestrator import (
    Orchestrator,
    create_orchestrator,
    EventBus,
    _build_clicks_from_project,
)

# Static hosting for the unified UI. Reuse icon_review-ui/ build output for
# now (it has the styling tokens we like); front-end work below extends it.
_PIPELINE_UI_DIST: Path = (
    Path(__file__).resolve().parent / "icon_review-ui" / "dist"
)

_TIMEOUT_SECONDS_DEFAULT = 60 * 60  # 1 hour overall budget


@dataclass
class _Runtime:
    orchestrator: Orchestrator


def _launch_pipeline_ui(url: str, width: int = 1280, height: int = 800) -> None:
    node_exe = shutil.which("node")
    if node_exe is not None:
        scripts_dir = _PIPELINE_UI_DIST.parent / "scripts"
        launcher_script = scripts_dir / "launcher.cjs"
        if launcher_script.exists():
            kwargs: dict = {
                "args": [node_exe, str(launcher_script),
                        "--port", str(urlparse(url).port),
                        "--title", "Record Pipeline",
                        "--width", str(width),
                        "--height", str(height)],
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                kwargs["start_new_session"] = True
            try:
                subprocess.Popen(**kwargs)
                print(f"[pipeline] puppeteer launcher spawned for {url}")
                return
            except (OSError, subprocess.SubprocessError) as e:
                print(f"[pipeline] puppeteer spawn failed: {e}")
    try:
        webbrowser.open(url)
    except webbrowser.Error:
        print(f"[pipeline] Open {url} manually")


def _make_pipeline_handler(runtime: _Runtime):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # quiet
            pass

        def _send_json(self, status: int, body):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def _send_event_stream_start(self):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

        def _send_sse(self, event: dict[str, object]) -> None:
            data = json.dumps(event, ensure_ascii=False)
            chunk = f"event: {event.get('type', 'message')}\ndata: {data}\n\n"
            try:
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                raise

        def do_GET(self):
            url = urlparse(self.path)
            path = url.path

            if path == "/api/pipeline/state":
                self._send_json(200, runtime.orchestrator.state.as_dict())
                return

            if path == "/api/pipeline/projects":
                # List local record projects (dirs under Aloha_Learn/projects
                # that have an inputs/ subdir = valid recording project).
                learn_dir = Path(__file__).resolve().parent
                projects_root = learn_dir / "projects"
                names = []
                if projects_root.is_dir():
                    for p in sorted(projects_root.iterdir()):
                        if p.is_dir() and (p / "inputs").is_dir():
                            names.append(p.name)
                self._send_json(200, {"projects": names})
                return

            if path == "/api/pipeline/scenes":
                # List existing scenes under <data_root>/projects/ so the UI
                # can suggest them in the scene combobox.
                orch_state = runtime.orchestrator.state
                dr = orch_state.data_root or _detect_data_root(
                    Path(__file__).resolve().parents[2] / "execution"
                )
                scenes: list[str] = []
                if dr:
                    scenes_root = Path(dr) / "projects"
                    if scenes_root.is_dir():
                        scenes = sorted(
                            p.name for p in scenes_root.iterdir() if p.is_dir()
                        )
                self._send_json(200, {"scenes": scenes})
                return

            if path == "/api/pipeline/clicks":
                # Re-derive LClick metadata from the project's SC JSON so the
                # Step 3 view can render click rows without exposing the
                # snapshot directly through orchestrator state.
                clicks, _err = _build_clicks_from_project(runtime.orchestrator.state.project)
                if _err:
                    self._send_json(404, {"error": _err})
                    return
                self._send_json(200, {"clicks": clicks, "total": len(clicks)})
                return

            # -- Endpoints reused by Step 3's ClickRow (mirror icon_review_server) --
            # Labels + icon PNGs are scoped to the CURRENT project's components
            # dir only (not all projects), so the dropdown isn't flooded.
            if path == "/api/labels":
                project_dir = Path(runtime.orchestrator.state.project)
                components = (
                    project_dir
                    / "components_review_ui_mutimodal_memory_manual"
                    / "components"
                )
                labels = (
                    sorted(p.stem for p in components.glob("*.png") if p.is_file())
                    if components.is_dir() else []
                )
                self._send_json(200, {"labels": labels})
                return

            if path.startswith("/api/icon/"):
                # Library icon by label, served from the current project's
                # components dir.
                label = path[len("/api/icon/"):]
                if "/" in label or "\\" in label or ".." in label:
                    self._send_json(400, {"error": "invalid label"})
                    return
                # The label may or may not include .png; normalize.
                if not label.endswith(".png"):
                    label = label + ".png"
                project_dir = Path(runtime.orchestrator.state.project)
                icon_path = (
                    project_dir
                    / "components_review_ui_mutimodal_memory_manual"
                    / "components"
                    / label
                )
                if not icon_path.is_file():
                    self._send_json(404, {"error": "label not in library"})
                    return
                self._send_file(icon_path, "image/png")
                return

            if path.startswith("/api/screenshot/"):
                # Serve a screenshot jpg from the project's screenshots/ dir.
                basename = path[len("/api/screenshot/"):]
                if "/" in basename or ".." in basename:
                    self._send_json(400, {"error": "invalid screenshot name"})
                    return
                project_dir = Path(runtime.orchestrator.state.project)
                shot_path = project_dir / "screenshots" / basename
                if not shot_path.is_file():
                    self._send_json(404, {"error": "screenshot not found"})
                    return
                ct = "image/jpeg" if shot_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                self._send_file(shot_path, ct)
                return

            if path.startswith("/api/pipeline/icon/"):
                # Stream a project's screenshot/icon/*.png as image/png so the
                # Step 1 grid can render thumbnails directly. The basename
                # is constrained to a single segment to prevent path traversal.
                basename = path[len("/api/pipeline/icon/"):]
                if "/" in basename or ".." in basename:
                    self._send_json(400, {"error": "invalid icon name"})
                    return
                project_dir = Path(runtime.orchestrator.state.project)
                icon_path = project_dir / "screenshots" / "icons" / basename
                if not icon_path.is_file():
                    self._send_json(404, {"error": "icon not found"})
                    return
                self._send_file(icon_path, "image/png")
                return

            if path == "/api/pipeline/events":
                self._send_event_stream_start()
                sub = runtime.orchestrator.bus.subscribe()
                try:
                    # initial snapshot
                    self._send_sse({
                        "type": "state",
                        "snapshot": runtime.orchestrator.state.as_dict(),
                    })
                    last_keepalive = time.time()
                    while True:
                        try:
                            ev = sub.get(timeout=15)
                            if ev is None:
                                self._send_sse({"type": "keepalive"})
                                last_keepalive = time.time()
                                continue
                            self._send_sse(ev)
                        except queue.Empty:
                            self._send_sse({"type": "keepalive"})
                finally:
                    runtime.orchestrator.bus.unsubscribe(sub)
                return

            # Static UI (icon_review-ui/dist shared for now).
            if path == "/" or path == "":
                idx = _PIPELINE_UI_DIST / "index.html"
                if idx.exists():
                    self._send_file(idx, "text/html; charset=utf-8")
                    return
                self._send_json(404, {"error": "pipeline-ui/dist missing"})
                return

            rel = path.lstrip("/")
            target = (_PIPELINE_UI_DIST / rel).resolve()
            try:
                target.relative_to(_PIPELINE_UI_DIST.resolve())
            except ValueError:
                self._send_json(400, {"error": "invalid path"})
                return
            if target.is_file():
                ct = (
                    "application/javascript" if target.suffix == ".js"
                    else "text/css" if target.suffix == ".css"
                    else "image/png" if target.suffix == ".png"
                    else "application/octet-stream"
                )
                self._send_file(target, ct)
                return
            self._send_json(404, {"error": "not found"})

        def _send_file(self, path: Path, content_type: str) -> None:
            try:
                data = path.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return {}

        def do_POST(self):
            url = urlparse(self.path)
            path = url.path

            if path == "/api/pipeline/configure":
                # Set project/scene/task/goal before starting. Called from
                # the start screen's "开始 pipeline" button.
                body = self._read_body()
                project = str(body.get("project") or "").strip()
                scene = str(body.get("scene") or "").strip()
                task = str(body.get("task") or "").strip()
                goal = str(body.get("goal") or "").strip()
                if not project or not scene or not task:
                    self._send_json(400, {"error": "project/scene/task 不能为空"})
                    return
                # Resolve project to an absolute path (bare name -> projects/<name>).
                learn_dir = Path(__file__).resolve().parent
                p = Path(project)
                if not p.is_absolute():
                    cand = learn_dir / "projects" / project
                    p = cand if cand.is_dir() else (Path.cwd() / project)
                if not p.is_dir():
                    self._send_json(400, {"error": f"project 目录不存在: {project}"})
                    return
                with runtime.orchestrator._lock:
                    runtime.orchestrator.state.project = str(p.resolve())
                    runtime.orchestrator.state.scene = scene
                    runtime.orchestrator.state.task = task
                    runtime.orchestrator.state.goal = goal or f"运行 {task} 任务"
                self._send_json(200, {"ok": True, "snapshot": runtime.orchestrator.state.as_dict()})
                return

            if path == "/api/pipeline/start":
                body = self._read_body()
                # Allow override of goal / data_root via body for restart.
                if "goal" in body and body["goal"]:
                    runtime.orchestrator.state.goal = str(body["goal"])
                if "data_root" in body and body["data_root"]:
                    runtime.orchestrator.state.data_root = str(body["data_root"])
                # Require project/scene/task to be configured first.
                s = runtime.orchestrator.state
                if not s.project or not s.scene or not s.task:
                    self._send_json(400, {"error": "请先选择 project 并填写 scene/task"})
                    return
                runtime.orchestrator.start()
                self._send_json(200, {"ok": True, "snapshot": runtime.orchestrator.state.as_dict()})
                return

            if path == "/api/pipeline/cancel":
                runtime.orchestrator.cancel()
                self._send_json(200, {"ok": True})
                return

            if path == "/api/pipeline/labels":
                body = self._read_body()
                labels = body.get("labels") or {}
                if not isinstance(labels, dict):
                    self._send_json(400, {"error": "labels must be object"})
                    return
                cleaned = {str(k): str(v).strip() for k, v in labels.items() if str(v).strip()}
                runtime.orchestrator.submit_labels(cleaned)
                self._send_json(200, {"ok": True, "count": len(cleaned)})
                return

            if path == "/api/pipeline/decisions":
                body = self._read_body()
                decisions = body.get("decisions") or {}
                if not isinstance(decisions, dict):
                    self._send_json(400, {"error": "decisions must be object"})
                    return
                cleaned: dict[str, dict] = {}
                for k, v in decisions.items():
                    if not isinstance(v, dict):
                        continue
                    if v.get("is_icon") is True:
                        cleaned[str(k)] = {"is_icon": True, "label": str(v.get("label") or "").strip()}
                    else:
                        cleaned[str(k)] = {"is_icon": False, "label": ""}
                runtime.orchestrator.submit_decisions(cleaned)
                self._send_json(200, {"ok": True, "count": len(cleaned)})
                return

            if path == "/api/pipeline/run-actual-task":
                runtime.orchestrator.run_actual_task()
                self._send_json(200, {"ok": True, "started": True})
                return

            self.send_error(HTTPStatus.NOT_FOUND)

    return Handler


def run_pipeline_session(
    *,
    project: str,
    scene: str,
    task: str,
    goal: str,
    library_roots: list[str],
    data_root: Optional[str] = None,
    open_window: bool = True,
    timeout_seconds: int = _TIMEOUT_SECONDS_DEFAULT,
) -> dict:
    """Start the orchestrator + HTTP server, block until timeout or done."""
    dist_dir = _PIPELINE_UI_DIST
    if not dist_dir.exists():
        raise RuntimeError(
            f"pipeline-ui/dist missing at {dist_dir}; "
            "cd icon_review-ui && npm run build"
        )

    orch = create_orchestrator(
        project=project, scene=scene, task=task, goal=goal,
        library_roots=library_roots, data_root=data_root,
    )
    runtime = _Runtime(orchestrator=orch)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_pipeline_handler(runtime))
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"

    if open_window:
        _launch_pipeline_ui(url)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    deadline = time.time() + timeout_seconds
    try:
        # Keep the server alive even after the pipeline finishes so the user
        # can click "Run actual task" (opt-in desktop takeover). We only stop
        # on: overall timeout, an unrecoverable error (current_step < 0), or
        # an idle period after the actual task finishes.
        last_activity = time.time()
        started_once = False  # becomes True once the user clicks "start"
        while time.time() < deadline:
            # Track whether the pipeline has ever started (current_step > 0).
            if orch.state.current_step > 0:
                started_once = True
            finished = bool(orch.state.finished_at)
            errored = orch.state.current_step < 0
            # "activity" = pipeline still running, or actual task in flight.
            actual_running = orch._actual_task_running() if hasattr(orch, "_actual_task_running") else False
            pipeline_running = started_once and not finished and not errored
            if pipeline_running or actual_running:
                last_activity = time.time()
            # Only consider idle shutdown AFTER the pipeline has started.
            # Before start (current_step==0), keep serving indefinitely so the
            # user has time to click "开始 pipeline" without the server dying.
            if started_once:
                # Idle shutdown: 5 min after finished AND no actual task.
                if finished and not actual_running and time.time() - last_activity > 300:
                    break
                if errored and not actual_running and time.time() - last_activity > 60:
                    break
            time.sleep(0.3)
    finally:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        server_thread.join(timeout=2)

    return orch.state.as_dict()


def main(argv: list[str]) -> int:
    # All three params are now optional - the user picks them in the UI
    # (project dropdown + scene/task inputs) after the window opens.
    # Args, if provided, pre-fill the UI.
    project = argv[1] if len(argv) > 1 else ""
    scene = argv[2] if len(argv) > 2 else ""
    task = argv[3] if len(argv) > 3 else ""
    goal = os.environ.get("PIPELINE_GOAL", "")
    library_roots = [str(Path(__file__).resolve().parent / "projects")]
    data_root = os.environ.get("PIPELINE_DATA_ROOT") or None
    final = run_pipeline_session(
        project=project, scene=scene, task=task, goal=goal,
        library_roots=library_roots, data_root=data_root,
    )
    print(json.dumps({
        "finished_at": final.get("finished_at"),
        "current_step": final.get("current_step"),
        "step_status": {i: s["status"] for i, s in final.get("steps", {}).items()},
    }, ensure_ascii=False, indent=2))
    # On failure, dump the failing step's error + last log lines so the
    # cause is visible in the terminal (not just in the SSE stream).
    if not final.get("finished_at"):
        for i, s in final.get("steps", {}).items():
            if s.get("error") or s.get("log_lines"):
                print(f"--- step {i} (status={s['status']}) ---", file=sys.stderr)
                if s.get("error"):
                    print(f"  ERROR: {s['error']}", file=sys.stderr)
                for ln in s.get("log_lines", [])[-15:]:
                    print(f"  | {ln}", file=sys.stderr)
    return 0 if final.get("finished_at") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
