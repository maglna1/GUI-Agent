"""Local HTTP server for human-in-the-loop icon review.

Pure stdlib. Binds 127.0.0.1 only. Three API endpoints + static file serving
for the Vite-built UI. Reuses components_sync.sanitize_label and
merge_components_json from this package.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from components_sync import (
    IconRecord,
    sanitize_label,
    merge_components_json,
    build_component_entry,
)


_REVIEW_UI_DIST: Path = Path(__file__).parent / "review-ui" / "dist"
_TIMEOUT_SECONDS_DEFAULT = 30 * 60  # 30 minutes


class ReviewSessionResult(dict):
    """Convenience subclass so callers can use dict-style access."""


def _icon_url(filename: str) -> str:
    return f"/icons/{filename}"


def _build_queue_payload(records, label_map, dest: Path):
    icons = []
    for r in records:
        icons.append({
            "filename": r.filename,
            "icon_url": _icon_url(r.filename),
            "llm_label": label_map.get(r.filename, ""),
            "is_timestamp_fallback": label_map.get(r.filename, "").startswith("record_memory_icon_"),
            "action": r.action,
            "coords": list(r.coords),
            "current_software": r.current_software,
            "base": r.base,
        })
    # existing_labels from dest/components.json
    existing = []
    comp_path = dest / "components.json"
    if comp_path.exists():
        try:
            data = json.loads(comp_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = list(data.keys())
        except json.JSONDecodeError:
            existing = []
    return {
        "icons": icons,
        "existing_labels": existing,
        "dest": str(dest),
        "manual_mode_default": False,
    }


def _apply_decisions(
    records, label_map, dest: Path, screenshots_dir: Path,
    decisions: dict, manual_mode: bool, now_str: str,
) -> dict:
    """Filter decisions, run sanitize, then call _apply_components_updates-style logic.

    Returns dict with keys: accepted, edited, skipped, sanitize_fallback,
    keys_added, keys_updated, manual_mode.
    """
    # Load existing components.json
    comp_path = dest / "components.json"
    existing = {}
    if comp_path.exists():
        try:
            data = json.loads(comp_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
        except json.JSONDecodeError:
            existing = {}

    components_dir = dest / "components"
    components_dir.mkdir(parents=True, exist_ok=True)

    additions = {}
    counts = {"accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0}

    for r in records:
        d = decisions.get(r.filename)
        # In manual_mode, missing decisions are no-op (not auto-accepted).
        # In normal mode, missing decisions default to "accept" so the queue
        # auto-finalizes when the user clicks "Submit All Accept" without
        # reviewing each row.
        if d is None:
            if manual_mode:
                continue
            d = {"action": "accept"}

        if manual_mode and d["action"] == "accept":
            # treat as skip
            counts["skipped"] += 1
            continue

        if d["action"] == "skip":
            counts["skipped"] += 1
            continue

        if d["action"] == "edit":
            try:
                label = sanitize_label(d["label"])
                counts["edited"] += 1
            except ValueError:
                # sanitize failed -> fall back to LLM candidate
                label = label_map.get(r.filename, "")
                if not label:
                    # LLM also empty -> skip without inflating sanitize_fallback
                    counts["skipped"] += 1
                    continue
                counts["sanitize_fallback"] += 1
        else:  # accept
            raw = label_map.get(r.filename, "")
            timestamp_key = f"record_memory_icon_{r.base.replace('.', '_')}_crop"
            if not raw:
                # Empty LLM label -> skip without inflating accepted
                counts["skipped"] += 1
                continue
            if raw == timestamp_key:
                # Already a valid timestamp key - preserve verbatim (bypass
                # sanitize; matches _sync_components_to_dest's timestamp_keys
                # short-circuit, since sanitize would truncate the _crop suffix).
                label = raw
                counts["accepted"] += 1
            else:
                try:
                    label = sanitize_label(raw)
                    counts["accepted"] += 1
                except ValueError:
                    # Unsanitizable LLM label -> fall back to timestamp key
                    # (matches _sync_components_to_dest's ValueError branch).
                    label = timestamp_key
                    counts["sanitize_fallback"] += 1

        # Copy PNG to dest/components/<label>.png (skip if same source)
        src = screenshots_dir / "icons" / r.filename
        dst = components_dir / f"{label}.png"
        try:
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
        except OSError as e:
            raise RuntimeError(f"Could not copy {src} -> {dst}: {e}") from e

        # Build entry using merge semantics
        prior = existing.get(label)
        if prior is None:
            entry = build_component_entry(
                label=label,
                icon_file=f"components/{label}.png",
                learned_at=now_str,
                last_seen=now_str,
                seen_count=1,
            )
            existing[label] = entry
            additions.setdefault("added", []).append(label)
        else:
            existing[label] = dict(prior)
            existing[label]["last_seen"] = now_str
            existing[label]["seen_count"] = int(prior.get("seen_count", 0)) + 1
            existing[label]["consecutive_misses"] = 0
            existing[label]["base_memory"] = True
            additions.setdefault("updated", []).append(label)

    # Write components.json
    try:
        comp_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        raise RuntimeError(f"Could not write {comp_path}: {e}") from e

    return {
        **counts,
        "keys_added": additions.get("added", []),
        "keys_updated": additions.get("updated", []),
        "manual_mode": manual_mode,
    }


def _make_handler(
    records, label_map, screenshots_dir: Path, dist_dir: Path, dest: Path,
    state: dict, browser_opened: threading.Event,
):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Quiet — keep test output clean
            pass

        def _send_json(self, status, body):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_file(self, path: Path, content_type: str):
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

        def do_GET(self):
            state["last_activity"] = time.time()
            url = urlparse(self.path)
            path = url.path

            if path == "/api/queue":
                self._send_json(200, _build_queue_payload(records, label_map, dest))
                return

            if path.startswith("/icons/"):
                filename = path[len("/icons/"):]
                # Sanitize: no path traversal
                if ".." in filename or "/" in filename or "\\" in filename:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return
                icon_path = screenshots_dir / "icons" / filename
                if not icon_path.exists():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_file(icon_path, "image/png")
                return

            # Static: serve from dist
            if path == "/" or path == "":
                index = dist_dir / "index.html"
                if index.exists():
                    self._send_file(index, "text/html; charset=utf-8")
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            # Map /assets/foo.js to dist/assets/foo.js
            rel = path.lstrip("/")
            target = (dist_dir / rel).resolve()
            # Prevent traversal
            if not str(target).startswith(str(dist_dir.resolve())):
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            if target.is_file():
                ct = "application/javascript" if target.suffix == ".js" else \
                     "text/css" if target.suffix == ".css" else \
                     "application/octet-stream"
                self._send_file(target, ct)
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            state["last_activity"] = time.time()
            url = urlparse(self.path)
            path = url.path

            if path == "/api/decisions":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b""
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    decisions = payload.get("decisions", {})
                    manual_mode = bool(payload.get("manual_mode", False))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._send_json(400, {"error": "invalid JSON"})
                    return
                if not isinstance(decisions, dict):
                    self._send_json(400, {"error": "decisions must be an object"})
                    return
                state["decisions"] = decisions
                state["manual_mode"] = manual_mode
                self._send_json(200, {"ok": True, "count": len(decisions)})
                return

            if path == "/api/finish":
                decisions = state.get("decisions", {})
                manual_mode = state.get("manual_mode", False)
                # Validate that at least one decision was posted
                if not decisions:
                    self._send_json(400, {"missing": [r.filename for r in records]})
                    return
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result = _apply_decisions(
                    records, label_map, dest, screenshots_dir,
                    decisions, manual_mode, now_str,
                )
                # Store result for run_review_session to pick up, then shutdown
                state["final_result"] = result
                self._send_json(200, {
                    "applied": {
                        "accepted": result["accepted"],
                        "edited": result["edited"],
                        "skipped": result["skipped"],
                        "sanitize_fallback": result["sanitize_fallback"],
                    },
                    "keys_added": result["keys_added"],
                    "keys_updated": result["keys_updated"],
                })
                # Schedule shutdown from another thread
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return

            self.send_error(HTTPStatus.NOT_FOUND)

    return Handler


def _launch_ui(
    *,
    url: str,
    launcher: str,
    window_title: str,
    window_width: int,
    window_height: int,
) -> None:
    """Open the review UI in a native window (pywebview / puppeteer) or browser.

    launcher values:
      - "browser" (default): opens in the system browser via webbrowser.open()
      - "webview": native window via pywebview (Edge WebView2 on Windows)
      - "puppeteer": native window via Chromium --app mode (most reliable)
      - "auto": prefer puppeteer → webview → browser

    Native windows give a real desktop-app feel (proper title/icon, no browser
    chrome). For puppeteer, the launcher.cjs script blocks until the user closes
    the window; we spawn it and return immediately — the launcher's lifetime
    is decoupled from the review server's /api/finish wait.
    """
    if launcher in ("auto", "puppeteer"):
        if _try_launch_puppeteer(url, window_title, window_width, window_height):
            return
        if launcher == "puppeteer":
            raise RuntimeError(
                "puppeteer launcher failed; check that node + puppeteer are installed "
                "and the Chromium download in ~/.cache/puppeteer succeeded."
            )

    if launcher in ("auto", "webview"):
        try:
            if _try_launch_webview(url, window_title, window_width, window_height):
                return
        except ImportError:
            if launcher == "webview":
                raise ImportError(
                    "pywebview is required for launcher='webview' but is not installed. "
                    "Install with: pip install pywebview"
                )
        except Exception:
            pass  # already logged inside _try_launch_webview
        if launcher == "webview":
            raise RuntimeError("pywebview launcher failed")

    # Browser fallback.
    try:
        webbrowser.open(url)
    except webbrowser.Error:
        print(f"[review] Open {url} manually")


def _try_launch_puppeteer(
    url: str, window_title: str, width: int, height: int,
) -> bool:
    """Spawn the Node.js launcher.cjs which opens a Chromium --app window.

    Returns True on successful spawn, False on failure. The child process
    blocks until the user closes the window; we do not wait for it.
    """
    # Find launcher.cjs relative to this file:
    # review_server.py lives in record/Aloha_Learn/, launcher.cjs in
    # record/Aloha_Learn/review-ui/scripts/. Use the same _REVIEW_UI_DIST
    # parent (review-ui/) to find scripts/launcher.cjs.
    scripts_dir = _REVIEW_UI_DIST.parent / "scripts"
    launcher_script = scripts_dir / "launcher.cjs"
    if not launcher_script.exists():
        print(f"[review] puppeteer launcher not found at {launcher_script}")
        return False

    # Look for node on PATH. If not found, fail gracefully.
    node_exe = shutil.which("node")
    if node_exe is None:
        print("[review] 'node' not found on PATH; install Node.js to use puppeteer launcher")
        return False

    # Check that node_modules has puppeteer (otherwise launcher.cjs will fail at require).
    puppeteer_pkg = _REVIEW_UI_DIST.parent / "node_modules" / "puppeteer" / "package.json"
    if not puppeteer_pkg.exists():
        print(f"[review] puppeteer not installed at {puppeteer_pkg.parent}; "
              f"run `npm --prefix record/Aloha_Learn/review-ui install`")
        return False

    try:
        # Parse port from URL.
        from urllib.parse import urlparse
        port = urlparse(url).port
        if not port:
            print(f"[review] could not parse port from {url}")
            return False

        # Detach so the launcher survives if the parent process exits unexpectedly.
        # On Windows, use DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP. On POSIX,
        # start_new_session does the same job.
        kwargs: dict = {
            "args": [node_exe, str(launcher_script),
                    "--port", str(port),
                    "--title", window_title,
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
        subprocess.Popen(**kwargs)
        print(f"[review] puppeteer launcher spawned for {url}")
        return True
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[review] puppeteer spawn failed: {e}")
        return False


def _try_launch_webview(
    url: str, window_title: str, width: int, height: int,
) -> bool:
    """Try pywebview. Returns True on success.

    Raises ImportError if pywebview is not installed (callers can distinguish
    "module missing" from "runtime error"). Other exceptions during
    webview.start() are caught and converted to a False return so the caller
    can fall back to webbrowser.
    """
    try:
        import webview  # type: ignore
    except ImportError:
        # Re-raise — callers can distinguish "missing" from "runtime fail".
        raise

    try:
        webview.create_window(
            title=window_title,
            url=url,
            width=width,
            height=height,
            resizable=True,
        )
        webview.start()
        return True
    except Exception as e:
        print(f"[review] pywebview failed ({e}); falling back")
        return False


def run_review_session(
    records, label_map, screenshots_dir: Path, dest: Path,
    *, open_browser: bool = True, timeout_seconds: int = _TIMEOUT_SECONDS_DEFAULT,
    now_str: Optional[str] = None,
    launcher: str = "auto",
    window_title: str = "Record Icon Review",
    window_width: int = 1280,
    window_height: int = 800,
) -> dict:
    """Run the review session, blocking until /api/finish or timeout.

    launcher: "auto" (default; prefer puppeteer → webview → browser),
    "puppeteer" (force Chromium --app window; raise if unavailable),
    "webview" (force pywebview native window; raise if unavailable),
    "browser" (always use webbrowser.open).

    open_browser: if False, skip the launch step entirely (headless / CI).

    Returns dict with keys: accepted, edited, skipped, sanitize_fallback,
    keys_added, keys_updated, manual_mode, timed_out, port.
    """
    dist_dir = _REVIEW_UI_DIST
    if not dist_dir.exists():
        raise RuntimeError(
            f"review-ui/dist missing at {dist_dir}; "
            f"run `npm --prefix record/Aloha_Learn/review-ui run build`"
        )

    state = {
        "decisions": {},
        "manual_mode": False,
        "last_activity": time.time(),
    }

    handler_cls = _make_handler(
        records, label_map, screenshots_dir, dist_dir, dest, state, threading.Event(),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    state["port"] = port

    # Auto-open browser
    if open_browser:
        _launch_ui(
            url=f"http://127.0.0.1:{port}/",
            launcher=launcher,
            window_title=window_title,
            window_width=window_width,
            window_height=window_height,
        )

    # Run server in a thread so we can monitor timeout
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Poll for completion or timeout
    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            if "final_result" in state:
                break
            time.sleep(0.1)
    finally:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        server_thread.join(timeout=2)

    if "final_result" in state:
        result = state["final_result"]
        return {
            **result,
            "timed_out": False,
            "port": port,
        }

    # Timeout: treat all as accept
    now_str = now_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    decisions = {r.filename: {"action": "accept"} for r in records}
    result = _apply_decisions(
        records, label_map, dest, screenshots_dir,
        decisions, False, now_str,
    )
    return {
        **result,
        "timed_out": True,
        "port": port,
    }