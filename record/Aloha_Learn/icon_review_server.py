"""Human-in-the-loop icon confirmation server.

Mirrors review_server.py but for a different question: given all click
operations in a generated trace, let the user mark which ones are
"icon clicks" (where the click landed on a desktop / taskbar icon) and
pick the corresponding label from the icon memory library. The decisions
are returned to the caller (trace_generator.py) which injects `images[]`
into the matching aiTap operation.

Pattern: identical to review_server.py — stdlib HTTP server, 127.0.0.1,
OS-assigned port, detached puppeteer launcher (or webbrowser fallback),
30-minute timeout fallback returns empty decisions.
"""
from __future__ import annotations

import json
import shutil
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

from icon_library import (
    find_icon_by_label,
    list_labels,
    load_icon_as_data_url,
)

# dist location (built by `npm run build` in icon_review-ui/).
_ICON_REVIEW_UI_DIST: Path = Path(__file__).resolve().parent / "icon_review-ui" / "dist"

_TIMEOUT_SECONDS_DEFAULT = 30 * 60


def _launch_icon_review_ui(
    *,
    url: str,
    window_title: str,
    window_width: int,
    window_height: int,
) -> None:
    """Open the icon-review window. Same launcher logic as review_server."""
    node_exe = shutil.which("node")
    if node_exe is not None:
        scripts_dir = _ICON_REVIEW_UI_DIST.parent / "scripts"
        launcher_script = scripts_dir / "launcher.cjs"
        if launcher_script.exists():
            kwargs: dict = {
                "args": [node_exe, str(launcher_script),
                        "--port", str(urlparse(url).port),
                        "--title", window_title,
                        "--width", str(window_width),
                        "--height", str(window_height)],
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
                print(f"[icon-review] puppeteer launcher spawned for {url}")
                return
            except (OSError, subprocess.SubprocessError) as e:
                print(f"[icon-review] puppeteer spawn failed: {e}")
        else:
            print(f"[icon-review] puppeteer launcher not found at {launcher_script}")
    try:
        webbrowser.open(url)
    except webbrowser.Error:
        print(f"[icon-review] Open {url} manually")


def _make_icon_review_handler(
    *,
    clicks: list[dict],
    library_roots: list[str],
    screenshot_dir: Path,
    state: dict,
):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # quiet

        def _send_json(self, status: int, body):
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
            url = urlparse(self.path)
            path = url.path

            if path == "/api/clicks":
                # Augment each click with a screenshot crop URL.
                payload = []
                for click in clicks:
                    item = dict(click)
                    ts_str = f"{float(click['timestamp'] - 0.1):.3f}s"
                    item["screenshot_url"] = f"/api/screenshot/{ts_str}"
                    payload.append(item)
                self._send_json(200, {"clicks": payload, "total": len(payload)})
                return

            if path == "/api/labels":
                labels = list_labels(library_roots)
                # Provide lightweight metadata for the UI; image data is
                # fetched on demand to keep this response small.
                self._send_json(200, {"labels": labels})
                return

            if path.startswith("/api/icon/"):
                # /api/icon/<label> → data URL JSON
                label = path[len("/api/icon/"):]
                icon_path = find_icon_by_label(label, library_roots)
                if icon_path is None:
                    self._send_json(404, {"error": "icon not found", "label": label})
                    return
                data_url = load_icon_as_data_url(icon_path)
                self._send_json(200, {"label": label, "url": data_url})
                return

            if path.startswith("/api/screenshot/"):
                basename = path[len("/api/screenshot/"):]
                img = screenshot_dir / f"{basename}.crop.jpg"
                if img.exists():
                    self._send_file(img, "image/jpeg")
                else:
                    img = screenshot_dir / f"{basename}.jpg"
                    if img.exists():
                        self._send_file(img, "image/jpeg")
                    else:
                        self.send_error(HTTPStatus.NOT_FOUND)
                return

            # Static (icon_review-ui/dist/).
            if path == "/" or path == "":
                idx = _ICON_REVIEW_UI_DIST / "index.html"
                if idx.exists():
                    self._send_file(idx, "text/html; charset=utf-8")
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            rel = path.lstrip("/")
            target = (_ICON_REVIEW_UI_DIST / rel).resolve()
            try:
                target.relative_to(_ICON_REVIEW_UI_DIST.resolve())
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            if target.is_file():
                ct = (
                    "application/javascript" if target.suffix == ".js"
                    else "text/css" if target.suffix == ".css"
                    else "application/octet-stream"
                )
                self._send_file(target, ct)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            url = urlparse(self.path)
            path = url.path

            if path == "/api/decisions":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b""
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    decisions = payload.get("decisions", {})
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._send_json(400, {"error": "invalid JSON"})
                    return
                if not isinstance(decisions, dict):
                    self._send_json(400, {"error": "decisions must be an object"})
                    return
                # Merge into state.
                for k, v in decisions.items():
                    state["decisions"][str(k)] = v
                self._send_json(200, {"ok": True, "count": len(state["decisions"])})
                return

            if path == "/api/finish":
                state["finished_at"] = datetime.now().isoformat(timespec="seconds")
                self._send_json(200, {
                    "ok": True,
                    "decided": sum(
                        1 for v in state["decisions"].values()
                        if isinstance(v, dict) and v.get("is_icon")
                    ),
                    "total": len(clicks),
                })
                # Schedule shutdown from another thread.
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return

            self.send_error(HTTPStatus.NOT_FOUND)

    return Handler


def run_icon_review_session(
    clicks: list[dict],
    library_roots: list[str],
    screenshot_dir: Path,
    *,
    open_window: bool = True,
    timeout_seconds: int = _TIMEOUT_SECONDS_DEFAULT,
    window_title: str = "Record Icon Review",
    window_width: int = 1280,
    window_height: int = 800,
) -> dict[str, dict]:
    """Block until the user closes the icon-review window (or timeout).

    Returns: { step_idx_str: {"is_icon": bool, "label": str | None} }
    Empty dict on timeout (caller treats as "no decisions; don't inject icons").
    """
    dist_dir = _ICON_REVIEW_UI_DIST
    if not dist_dir.exists():
        raise RuntimeError(
            f"icon_review-ui/dist missing at {dist_dir}; "
            f"run `npm --prefix record/Aloha_Learn/icon_review-ui run build`"
        )

    state = {"decisions": {}, "finished_at": None}

    handler_cls = _make_icon_review_handler(
        clicks=clicks,
        library_roots=library_roots,
        screenshot_dir=screenshot_dir,
        state=state,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"

    if open_window:
        _launch_icon_review_ui(
            url=url,
            window_title=window_title,
            window_width=window_width,
            window_height=window_height,
        )

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            if state["finished_at"] is not None:
                break
            time.sleep(0.1)
    finally:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        server_thread.join(timeout=2)

    return state["decisions"]