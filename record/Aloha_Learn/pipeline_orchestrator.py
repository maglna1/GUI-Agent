"""Pipeline orchestrator — driving the 4-step icon-review flow as a single
state machine:

    1. 图标命名 (LLM 预生成 + 用户可改并确认)
    2. Trace 生成 (parser.py step 3 子进程，吐 stdout lines)
    3. 点击事件图标确认 (复用 icon_review_server.run_icon_review_session)
    4. Sync + init + validate (subprocess chain), 提供 Run actual task 按钮

设计：单例 orchestrator 在主线程持有全局状态，每一步用一个 worker
thread 跑，对外通过 callback (jsonable 事件) 推到 HTTP 层 / SSE。

线程模型：
    main thread: HTTP server (read state, push events via SSE)
    step1 worker:  LLM 调 + 等 UI 提交
    step2 worker:  subprocess parser.py
    step3 worker:  run_icon_review_session (blocking on UI)
    step4 worker:  subprocess chain (sync / init / validate)
    user can run `task run` separately (single-shot subprocess)
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
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# Load record/.env at module import time so step 1/2's LLM calls find
# OPENAI_* / MIDSCENE_MODEL_* keys. Mirrors parser.py's load_dotenv.
try:
    from dotenv import load_dotenv
    _PROJECT_ENV = Path(__file__).resolve().parents[1] / ".env"
    if _PROJECT_ENV.is_file():
        load_dotenv(_PROJECT_ENV, override=False)
except Exception:
    pass


STEPS = [
    {"id": 1, "key": "label",    "label": "图标命名"},
    {"id": 2, "key": "trace",    "label": "Trace 生成"},
    {"id": 3, "key": "icons",    "label": "图标点击确认"},
    {"id": 4, "key": "exec",     "label": "Sync + 转换 + 验证"},
]

# -------------------------------------------------------------------- state --


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepState:
    status: StepStatus = StepStatus.PENDING
    progress_current: int = 0
    progress_total: int = 0
    log_lines: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PipelineState:
    run_id: str
    project: str
    scene: str
    task: str
    goal: str
    library_roots: list[str]
    data_root: Optional[str] = None
    steps: dict[int, StepState] = field(default_factory=dict)
    # Step 1 user-editable labels: filename -> label.
    step1_labels: dict[str, str] = field(default_factory=dict)
    step1_llm_labels: dict[str, str] = field(default_factory=dict)
    # Step 3 click decisions: step_idx str -> {is_icon, label}.
    step3_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Step 4 results.
    step4_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""
    current_step: int = 0  # 0 = idle, > 0 = step index 1-4, < 0 = errored

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project": self.project,
            "scene": self.scene,
            "task": self.task,
            "goal": self.goal,
            "library_roots": self.library_roots,
            "data_root": self.data_root,
            "current_step": self.current_step,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "steps": {i: _step_to_dict(s) for i, s in self.steps.items()},
            "step1_labels": self.step1_labels,
            "step1_llm_labels": self.step1_llm_labels,
            "step3_decisions": self.step3_decisions,
            "step4_results": self.step4_results,
            "step_defs": STEPS,
        }


def _step_to_dict(step: StepState) -> dict[str, Any]:
    return {
        "status": step.status.value,
        "progress_current": step.progress_current,
        "progress_total": step.progress_total,
        "log_lines": step.log_lines[-200:],  # cap retained lines
        "error": step.error,
    }


class EventBus:
    """Tiny pub-sub for orchestrator → SSE bridge.

    Each subscriber gets its own queue. Subscribers pop events. The HTTP
    layer maintains one queue per SSE client.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1024)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                # Drop oldest if the listener can't keep up; the live state
                # is always available via GET /api/pipeline/state.
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass


# ---------------------------------------------------------------- orchestrator --


@dataclass
class Orchestrator:
    """Drives a single pipeline run end-to-end."""

    state: PipelineState
    bus: EventBus = field(default_factory=EventBus)
    # RLock because helpers like _set_progress/_set_step_status hold _lock
    # while calling _step(), which also acquires _lock. A plain Lock would
    # deadlock the same thread on re-entry.
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _step2_proc: Optional[subprocess.Popen] = None
    _step4_proc: Optional[subprocess.Popen] = None
    _actual_task_thread: Optional[threading.Thread] = None
    _labels_event: threading.Event = field(default_factory=threading.Event)
    _decisions_event: threading.Event = field(default_factory=threading.Event)

    def publish(self, event: dict[str, Any]) -> None:
        """Convenience: merge state + emit."""
        self.bus.publish(event)

    # ----- step management -----

    def _step(self, idx: int) -> StepState:
        with self._lock:
            if idx not in self.state.steps:
                self.state.steps[idx] = StepState()
            return self.state.steps[idx]

    def _set_step_status(self, idx: int, status: StepStatus) -> None:
        with self._lock:
            self._step(idx).status = status
        self.publish({
            "type": "state",
            "step": idx,
            "status": status.value,
            "snapshot": self.state.as_dict(),
        })

    def _append_log(self, idx: int, line: str) -> None:
        with self._lock:
            self._step(idx).log_lines.append(line)
        self.publish({
            "type": "log",
            "step": idx,
            "line": line,
        })

    def _set_progress(self, idx: int, current: int, total: int) -> None:
        with self._lock:
            s = self._step(idx)
            s.progress_current = current
            s.progress_total = total
        self.publish({
            "type": "progress",
            "step": idx,
            "current": current,
            "total": total,
        })

    # ----- top-level run control -----

    def start(self) -> None:
        """Start the pipeline (async). Idempotent."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.state.started_at = datetime.now().isoformat(timespec="seconds")
        self.state.finished_at = ""
        self.state.current_step = 1
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._stop_event.set()
        # Tear down running subprocesses.
        for proc in (self._step2_proc, self._step4_proc):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    # ----- submit user inputs -----

    def submit_labels(self, labels: dict[str, str]) -> None:
        with self._lock:
            self.state.step1_labels = dict(labels)
        self._labels_event.set()

    def submit_decisions(self, decisions: dict[str, dict[str, Any]]) -> None:
        # Defensive filter: keep only dict values; coerce label to "" when
        # is_icon is False. Mirrors the HTTP layer cleaning; safe even if
        # the caller already cleaned.
        cleaned: dict[str, dict[str, Any]] = {}
        for k, v in (decisions or {}).items():
            if not isinstance(v, dict):
                continue
            if v.get("is_icon") is True:
                cleaned[str(k)] = {"is_icon": True, "label": str(v.get("label") or "").strip()}
            else:
                cleaned[str(k)] = {"is_icon": False, "label": ""}
        with self._lock:
            self.state.step3_decisions = cleaned
        self._decisions_event.set()

    # ----- main loop -----

    def _run(self) -> None:
        for step_method in (
            self._run_step1,
            self._run_step2,
            self._run_step3,
            self._run_step4_sync_init_validate,
        ):
            if self._stop_event.is_set():
                return
            try:
                step_method()
            except Exception as e:
                # Don't let one step's failure silently kill the
                # orchestrator. Mark the current step failed and stop
                # the pipeline.
                failed_step = self.state.current_step
                self.state.current_step = -1
                self._append_log(
                    failed_step,
                    f"{type(e).__name__}: {e}",
                )
                self.publish({
                    "type": "error",
                    "error": f"{type(e).__name__}: {e}",
                    "failed_step": failed_step,
                    "snapshot": self.state.as_dict(),
                })
                return
        self.state.finished_at = datetime.now().isoformat(timespec="seconds")
        self.publish({
            "type": "state",
            "snapshot": self.state.as_dict(),
            "note": "pipeline finished",
        })

    def _halt_step(self, idx: int, message: str) -> None:
        """Mark a step failed and raise so the outer loop stops subsequent steps."""
        self._set_step_status(idx, StepStatus.FAILED)
        self._step(idx).error = message
        self._append_log(idx, message)
        raise RuntimeError(f"step {idx}: {message}")

    def _run_step1(self) -> None:
        self.state.current_step = 1
        self._set_step_status(1, StepStatus.RUNNING)
        from screenshot_processor import VideoScreenshotExtractor
        project_dir = Path(self.state.project)
        screenshots_dir = project_dir / "screenshots"
        icons_dir = screenshots_dir / "icons"
        if not icons_dir.is_dir():
            self._halt_step(1, f"找不到 {icons_dir}；先跑 parser.py step 1+2")

        icon_files = sorted(p for p in icons_dir.glob("*.png") if p.is_file())
        self._set_progress(1, 0, len(icon_files))

        sc_log = project_dir / f"{project_dir.name}_processed_log_sc.json"
        try:
            actions = json.loads(sc_log.read_text(encoding="utf-8")) if sc_log.exists() else []
        except Exception:
            actions = []

        icon_actions: list[dict[str, Any]] = []
        if isinstance(actions, list):
            for i, a in enumerate(actions):
                if isinstance(a, dict) and (a.get("action") or "").startswith("LClick at"):
                    coords = a.get("coords") or []
                    if isinstance(coords, list) and coords:
                        first = coords[0] if isinstance(coords[0], dict) else {}
                        x, y = first.get("x"), first.get("y")
                    else:
                        x, y = 0, 0
                    icon_actions.append({
                        "action": a.get("action", ""),
                        "coords": [x, y],
                        "current_software": a.get("current_software", ""),
                    })

        # _request_component_labels accesses fields as attributes
        # (.filename, .action, .coords, .current_software, .base), so use
        # SimpleNamespace, not dict.
        from types import SimpleNamespace
        records: list[Any] = []
        for idx, f in enumerate(icon_files):
            meta = icon_actions[idx] if idx < len(icon_actions) else {}
            records.append(SimpleNamespace(
                filename=f.name,
                action=meta.get("action", ""),
                # coords must be a 2-element list; _request_component_labels
                # accesses r.coords[0]/[1]. Default to [0, 0] when this icon
                # has no matching LClick action (e.g. more icons than clicks).
                coords=meta.get("coords") or [0, 0],
                current_software=meta.get("current_software", ""),
                base=f.stem,
            ))

        self._append_log(1, f"已构建 {len(records)} 个 icon records，调 LLM...")
        extractor = VideoScreenshotExtractor()
        try:
            labels = extractor._request_component_labels(records, screenshots_dir)
        except Exception as e:
            self._halt_step(1, f"LLM 调失败：{e}")

        with self._lock:
            self.state.step1_llm_labels = dict(labels)
            self.state.step1_labels = dict(labels)
        self._set_progress(1, len(icon_files), len(icon_files))
        self._append_log(1, f"LLM 返回 {len(labels)} 个 label")
        self.publish({
            "type": "step1_complete_llm",
            "labels": labels,
            "snapshot": self.state.as_dict(),
        })
        self._set_step_status(1, StepStatus.WAITING)
        self._labels_event.clear()
        self._labels_event.wait()
        if self._stop_event.is_set():
            return
        labels_file = project_dir / f"{project_dir.name}_icon_labels.json"
        labels_file.write_text(
            json.dumps(self.state.step1_labels, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Sync accepted icons into the project's component library so Step 3's
        # LabelPicker (which scans components/) can see the newly-named icons.
        # This replaces what run_review_session did in the legacy flow (which
        # we skip via SKIP_COMPONENTS_REVIEW=1 to avoid a second popup).
        components_dir = (
            project_dir
            / "components_review_ui_mutimodal_memory_manual"
            / "components"
        )
        components_dir.mkdir(parents=True, exist_ok=True)
        icons_dir = screenshots_dir / "icons"
        synced = 0
        for filename, label in self.state.step1_labels.items():
            label = (label or "").strip()
            if not label:
                continue
            src = icons_dir / filename
            if not src.is_file():
                self._append_log(1, f"跳过同步 {filename}：源文件不存在")
                continue
            dst = components_dir / f"{label}.png"
            try:
                import shutil as _shutil
                _shutil.copy2(src, dst)
                synced += 1
            except OSError as e:
                self._append_log(1, f"同步 {filename} -> {label}.png 失败: {e}")
        self._append_log(1, f"已同步 {synced} 个图标到 {components_dir.name}/components/")

        self._set_step_status(1, StepStatus.SUCCEEDED)
        self.publish({
            "type": "step1_complete",
            "labels": self.state.step1_labels,
            "saved_to": str(labels_file),
            "synced_icons": synced,
            "snapshot": self.state.as_dict(),
        })

    def _run_step2(self) -> None:
        self.state.current_step = 2
        self._set_step_status(2, StepStatus.RUNNING)
        project_dir = Path(self.state.project)
        sc_log = project_dir / f"{project_dir.name}_processed_log_sc.json"
        if not sc_log.exists():
            self._set_step_status(2, StepStatus.FAILED)
            self._step(2).error = f"缺少 {sc_log}；先跑 parser.py"
            return
        # Detect total steps for progress.
        try:
            actions = json.loads(sc_log.read_text(encoding="utf-8"))
            click_count = sum(
                1 for a in (actions or [])
                if (a.get("action") or "").startswith("LClick at")
            )
        except Exception:
            click_count = 0
        self._set_progress(2, 0, click_count)

        # We can't run parser.py interactively without re-running step 1/2
        # which would also re-spawn the legacy review-ui window. Instead, we
        # run trace_generator directly with library_roots + decisions path,
        # bypassing the icon-review auto-popup by pre-loading an empty
        # decisions cache so the popup is skipped.
        # python_path = Path(sys.executable)
        # Actually easier: invoke parser.py step 3 in a subprocess that
        # bypasses step 1+2 (they already ran). Simplest is to shell out
        # to parser.py full run but skip the legacy review UI via env.
        # RUN_ICON_REVIEW=0 tells parser.py to skip its internal icon-review
        # popup (we handle icon-click confirmation in the main UI at Step 3
        # instead, so a second popup would be redundant).
        env = os.environ.copy()
        env["RUN_ICON_REVIEW"] = "0"
        env["SKIP_COMPONENTS_REVIEW"] = "1"  # Step 1 already labeled icons; skip parser.py's review-ui popup
        env["PYTHONUNBUFFERED"] = "1"  # stream subprocess stdout in real time
        repo = Path(__file__).resolve().parents[2]
        cwd = str(repo)
        args = [
            sys.executable,
            str(repo / "record" / "Aloha_Learn" / "parser.py"),
            str(project_dir),
        ]
        self._append_log(2, f"启动 parser.py: {' '.join(args[-2:])}")
        try:
            self._step2_proc = subprocess.Popen(
                args,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            self._halt_step(2, f"无法启动 parser.py: {e}")

        step_re = re.compile(r"^parsing Step (\d+):")
        for raw in self._step2_proc.stdout or []:
            line = raw.rstrip()
            self._append_log(2, line)
            m = step_re.match(line)
            if m:
                self._set_progress(2, int(m.group(1)), click_count)

        rc = self._step2_proc.wait()
        self._step2_proc = None
        if rc == 0:
            self._set_step_status(2, StepStatus.SUCCEEDED)
        else:
            self._set_step_status(2, StepStatus.FAILED)
            self._step(2).error = f"parser.py 退出码 {rc}"

    def _run_step3(self) -> None:
        self.state.current_step = 3
        self._set_step_status(3, StepStatus.WAITING)
        project_dir = Path(self.state.project)
        trace_path = project_dir / f"{project_dir.name}_trace.json"
        if not trace_path.exists():
            self._halt_step(3, "需要先完成 Step 2（trace.json 不存在）")
        clicks, err = _build_clicks_from_project(str(project_dir))
        if err:
            self._halt_step(3, err)
        self._set_progress(3, 0, len(clicks))
        self._append_log(3, f"等待你在主界面确认 {len(clicks)} 个 click 是否图标点击...")
        self._append_log(3, f"图标库: {self.state.library_roots}")

        # No popup: the main UI (PipelineStep3Icons) renders the click grid
        # inline. The user submits decisions via POST /api/pipeline/decisions
        # -> submit_decisions() -> _decisions_event.set().
        self._decisions_event.clear()
        self._decisions_event.wait()
        if self._stop_event.is_set():
            return

        decisions = self.state.step3_decisions
        decided_count = sum(1 for d in decisions.values() if d.get("is_icon"))
        self._set_progress(3, decided_count, len(clicks))
        self._append_log(3, f"收到 {len(decisions)} 个 decision（{decided_count} 标为图标），注入 images 到 trace...")

        # Apply decisions to trace.json (inject images[] into click operations).
        from trace_generator import apply_icon_decisions
        try:
            traj = json.loads(trace_path.read_text(encoding="utf-8"))["trajectory"]
        except Exception as e:
            self._halt_step(3, f"读取 trace.json 失败: {e}")
            return
        new_traj = apply_icon_decisions(traj, decisions, self.state.library_roots)
        trace_path.write_text(
            json.dumps({"trajectory": new_traj}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Persist decisions for re-use (matches parser.py / run_icon_review.py).
        decisions_path = project_dir / f"{project_dir.name}_icon_review.json"
        decisions_path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "decisions": decisions,
                    "libraryRoots": self.state.library_roots,
                    "decidedAt": datetime.now().isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        injected = sum(
            1 for s in new_traj
            if (s.get("caption", {}).get("operation", {}) or {}).get("images")
        )
        self._append_log(3, f"已注入 images 到 {injected} 个 step；持久化 {decisions_path.name}")
        self._set_step_status(3, StepStatus.SUCCEEDED)
        self.publish({
            "type": "step3_complete",
            "decisions": decisions,
            "injected": injected,
            "snapshot": self.state.as_dict(),
        })

    def _run_icon_review_blocking(
        self,
        *,
        clicks: list[dict[str, Any]],
        library_roots: list[str],
        screenshots_dir: str,
        decisions_path: Path,
    ) -> dict[str, dict[str, Any]]:
        """Run icon_review_server synchronously and return decisions.

        The icon review window is launched via puppeteer. The orchestrator
        blocks here until the user submits or hits timeout.
        """
        from icon_review_server import run_icon_review_session
        decisions = run_icon_review_session(
            clicks=clicks,
            library_roots=library_roots,
            screenshot_dir=Path(screenshots_dir),
        )
        # Persist for traceability (matches parser.run_icon_review.py).
        decisions_path.write_text(
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
        return decisions

    def _run_step4_sync_init_validate(self) -> None:
        self.state.current_step = 4
        self._set_step_status(4, StepStatus.RUNNING)
        # Three subprocesses in series: sync, init-from-trace, validate.
        repo = Path(__file__).resolve().parents[2]
        execution_dir = repo / "execution"
        results: dict[str, dict[str, Any]] = {}

        sync_cmd = [
            sys.executable,
            str(repo / "record" / "Aloha_Learn" / "scripts" / "sync_to_execution.py"),
            self.state.project,
            self.state.scene,
            self.state.task,
            "--force",
        ]
        init_cmd = [
            "npm", "run", "cua", "--", "task", "init-from-trace",
            "--scene", self.state.scene,
            "--task", self.state.task,
            "--goal", self.state.goal,
        ]
        validate_cmd = [
            "npm", "run", "cua", "--", "task", "validate",
            "--scene", self.state.scene,
            "--task", self.state.task,
        ]

        if self.state.data_root:
            data_root = self.state.data_root
        else:
            data_root = _detect_data_root(execution_dir)
        if data_root:
            sync_cmd.extend(["--data-root", data_root])

        # init-from-trace refuses to overwrite existing task.yaml/task.json.
        # Since we just re-synced the source, remove stale task assets so the
        # conversion produces a fresh YAML from the latest trace.
        if data_root:
            task_root = Path(data_root) / "projects" / self.state.scene / self.state.task
            for stale in ("task.yaml", "task.json"):
                stale_path = task_root / stale
                if stale_path.exists():
                    self._append_log(4, f"删除旧 {stale} 以便重新转换")
                    try:
                        stale_path.unlink()
                    except OSError as e:
                        self._append_log(4, f"警告: 无法删除 {stale}: {e}")

        # Windows: CreateProcess doesn't search PATHEXT, so "npm" (npm.cmd)
        # won't be found by subprocess.Popen without shell=True. Resolve it
        # to the full path. On other platforms which() returns "npm" as-is.
        npm_exe = shutil.which("npm") or "npm"
        init_cmd[0] = npm_exe
        validate_cmd[0] = npm_exe

        sub_cmds = [
            ("sync", sync_cmd, Path(repo)),
            ("init_from_trace", init_cmd, execution_dir),
            ("validate", validate_cmd, execution_dir),
        ]
        total = len(sub_cmds)
        for i, (key, args, cwd) in enumerate(sub_cmds, start=1):
            if self._stop_event.is_set():
                return
            self._append_log(4, f"--- {key}: {' '.join(args[:4])} ... ---")
            rc, stdout_text = _run_with_log(
                args,
                cwd=str(cwd),
                on_line=lambda ln: self._append_log(4, ln),
            )
            results[key] = {
                "status": "succeeded" if rc == 0 else "failed",
                "exit_code": rc,
                "stdout_tail": stdout_text[-1000:],
            }
            self.publish({
                "type": "step4_substep",
                "step": 4,
                "substep": key,
                "status": "succeeded" if rc == 0 else "failed",
                "snapshot": self.state.as_dict(),
            })
            if rc != 0:
                self._set_step_status(4, StepStatus.FAILED)
                with self._lock:
                    self.state.step4_results = results
                return
        with self._lock:
            self.state.step4_results = results
        self._set_step_status(4, StepStatus.SUCCEEDED)

    # ----- actual task run (separate, opt-in) -----

    def run_actual_task(self) -> None:
        """Opt-in subprocess that takes over the desktop. Spawns in a daemon
        thread; events come via the bus."""
        if self._actual_task_thread is not None and self._actual_task_thread.is_alive():
            return  # already running

        def _runner() -> None:
            try:
                execution_dir = Path(__file__).resolve().parents[2] / "execution"
                cmd = [
                    shutil.which("npm") or "npm", "run", "cua", "--", "task", "run",
                    "--scene", self.state.scene,
                    "--task", self.state.task,
                ]
                self.publish({"type": "actual_task_started", "cmd": " ".join(cmd)})
                rc, stdout_text = _run_with_log(
                    cmd,
                    cwd=str(execution_dir),
                    on_line=lambda ln: self._append_log(4, f"[run] {ln}"),
                )
                self.publish({
                    "type": "actual_task_finished",
                    "exit_code": rc,
                    "status": "succeeded" if rc == 0 else "failed",
                })
            except Exception as e:  # pragma: no cover
                self.publish({"type": "actual_task_error", "error": str(e)})

        self._actual_task_thread = threading.Thread(target=_runner, daemon=True)
        self._actual_task_thread.start()

    def _actual_task_running(self) -> bool:
        """True if the opt-in `task run` subprocess thread is in flight."""
        return (
            self._actual_task_thread is not None
            and self._actual_task_thread.is_alive()
        )


# ---------------------------------------------------------------- helpers --


def _build_clicks_from_project(project: str) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Re-derive LClick metadata from a project's processed-log SC JSON.

    Used by both the orchestrator (to feed the icon_review session) and the
    HTTP server (to expose /api/pipeline/clicks for the Step 3 view).
    Returns (clicks, error_message); on success error_message is None.
    """
    project_dir = Path(project)
    sc_log = project_dir / f"{project_dir.name}_processed_log_sc.json"
    if not sc_log.exists():
        return [], f"缺少 {sc_log}；先跑 parser.py step 1+2"
    try:
        actions = json.loads(sc_log.read_text(encoding="utf-8"))
    except Exception as e:
        return [], f"无法解析 sc log: {e}"
    clicks: list[dict[str, Any]] = []
    if not isinstance(actions, list):
        return [], f"{sc_log} 格式异常"
    for idx, a in enumerate(actions):
        if not isinstance(a, dict):
            continue
        if not (a.get("action") or "").startswith("LClick at"):
            continue
        coords = a.get("coords") or []
        if isinstance(coords, list) and coords:
            first = coords[0] if isinstance(coords[0], dict) else {}
            x, y = first.get("x"), first.get("y")
        else:
            x, y = None, None
        # screenshot path: prefer crop, fall back to full. Strip any
        # "screenshots/" prefix the recorder may have written.
        shot = a.get("screenshot_crop") or a.get("screenshot_full") or a.get("screenshot") or ""
        if isinstance(shot, str) and shot.startswith("screenshots/"):
            shot = shot[len("screenshots/"):]
        clicks.append({
            "step_idx": idx,
            "timestamp": a.get("timestamp", 0),
            "coords": [x, y],
            "current_software": a.get("current_software", ""),
            "prompt": "",
            "screenshot_url": f"/api/screenshot/{shot}" if shot else "",
        })
    return clicks, None


def _detect_data_root(execution_dir: Path) -> Optional[str]:
    for fn in (".env.local", ".env"):
        p = execution_dir / fn
        if p.is_file():
            for raw in p.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == "CUA_DATA_ROOT":
                    val = v.strip().strip('"').strip("'")
                    if val:
                        return val
    return None


def _run_with_log(args: list[str], cwd: str, on_line: Callable[[str], None]) -> tuple[int, str]:
    """Run subprocess; stream stdout line by line; return (exit_code, stdout tail)."""
    try:
        # encoding=utf-8 + errors=replace: subprocess output (npm/tsx/parser.py)
        # contains UTF-8 Chinese text. The Windows default (GBK) would raise
        # UnicodeDecodeError on those bytes.
        proc = subprocess.Popen(
            args, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            encoding="utf-8", errors="replace",
        )
    except Exception as e:
        on_line(f"无法启动: {e}")
        return 1, ""

    captured: list[str] = []
    assert proc.stdout
    for raw in proc.stdout:
        line = raw.rstrip()
        captured.append(line)
        on_line(line)
    rc = proc.wait()
    return rc, "\n".join(captured[-200:])


# ---------------------------------------------------------------- factory --


def create_orchestrator(
    *,
    project: str,
    scene: str,
    task: str,
    goal: str,
    library_roots: list[str],
    data_root: Optional[str] = None,
) -> Orchestrator:
    return Orchestrator(
        state=PipelineState(
            run_id=str(uuid.uuid4())[:8],
            project=project,
            scene=scene,
            task=task,
            goal=goal,
            library_roots=library_roots,
            data_root=data_root,
        ),
    )
