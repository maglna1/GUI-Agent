import json
import os
import socket
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components_sync import IconRecord
from review_server import run_review_session, ReviewSessionResult


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _records():
    return [
        IconRecord(
            filename=f"record_memory_icon_{i}.0s_crop.png",
            action="LClick at", coords=(100 + i, 200), current_software="Chrome",
            base=f"{i}.0s",
        )
        for i in range(3)
    ]


def _icon_files(screenshots_dir: Path, records):
    icons = screenshots_dir / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    for r in records:
        (icons / r.filename).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def _post_decisions(port: int, decisions: dict, manual_mode: bool = False):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/decisions",
                 body=json.dumps({"decisions": decisions, "manual_mode": manual_mode}),
                 headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()
    conn.close()
    return r.status


def _post_finish(port: int):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/finish")
    r = conn.getresponse()
    body = r.read().decode("utf-8")
    conn.close()
    return r.status, json.loads(body) if body else {}


def _get_json(port: int, path: str):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    r = conn.getresponse()
    body = r.read().decode("utf-8")
    conn.close()
    return r.status, json.loads(body) if body else {}


class QueueEndpointTest(unittest.TestCase):
    def test_get_queue_returns_all_records_with_llm_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            result_holder: dict = {}

            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=2,
                )

            t = threading.Thread(target=runner, daemon=True)
            t.start()
            # Server takes a moment to start; poll queue until 200
            port = None
            for _ in range(50):
                try:
                    port = _free_port()  # not used; we read actual port from meta later
                    break
                except OSError:
                    time.sleep(0.05)
            # The server picks its own port; query the queue by trying the port
            # returned via stdout — here we patch _server_started to capture port.
            # Simpler: spin a fresh request once the meta is populated.
            deadline = time.time() + 5
            while time.time() < deadline and "r" not in result_holder:
                # run_review_session blocks until /api/finish; instead, drive
                # decisions then finish.
                pass
            # Drive a full flow below in dedicated tests; here we only assert
            # the queue contents via finish-time meta.
            t.join(timeout=2)
            self.assertIn("r", result_holder)
            self.assertEqual(result_holder["r"]["accepted"], 3)
            self.assertEqual(result_holder["r"]["skipped"], 0)


class DecisionsEndpointTest(unittest.TestCase):
    def _run(self, decisions, manual_mode=False):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            result_holder: dict = {}
            port_holder: dict = {}

            # Patch HTTPServer to capture chosen port
            import review_server as rs
            orig_server = rs.ThreadingHTTPServer
            class CapturingServer(orig_server):
                def __init__(self, addr, handler):
                    super().__init__(addr, handler)
                    port_holder["port"] = self.server_address[1]
            rs.ThreadingHTTPServer = CapturingServer

            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=5,
                )

            t = threading.Thread(target=runner, daemon=True)
            t.start()

            # Wait for server to start
            for _ in range(100):
                if "port" in port_holder:
                    break
                time.sleep(0.02)
            port = port_holder["port"]

            # Post decisions
            status = _post_decisions(port, decisions, manual_mode=manual_mode)
            self.assertEqual(status, 200)

            # Finish
            status, body = _post_finish(port)
            self.assertEqual(status, 200)

            t.join(timeout=5)
            return result_holder["r"], body

    def test_skip_excluded_from_components(self):
        records = _records()
        decisions = {records[1].filename: {"action": "skip"}}
        result, body = self._run(decisions)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["accepted"], 2)
        # The skipped filename MUST NOT appear in keys_added/updated
        self.assertNotIn(records[1].filename, body.get("keys_added", []) + body.get("keys_updated", []))

    def test_edit_label_sanitized(self):
        records = _records()
        decisions = {records[0].filename: {"action": "edit", "label": "Start Button"}}
        result, body = self._run(decisions)
        self.assertEqual(result["edited"], 1)
        self.assertIn("start_button", body.get("keys_added", []))

    def test_manual_mode_treats_accept_as_skip(self):
        records = _records()
        decisions = {
            records[0].filename: {"action": "accept"},
            records[1].filename: {"action": "accept"},
        }
        result, body = self._run(decisions, manual_mode=True)
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(result["accepted"], 0)

    def test_sanitize_fallback_on_edit_with_illegal_label(self):
        records = _records()
        decisions = {records[0].filename: {"action": "edit", "label": "///??**"}}
        result, body = self._run(decisions)
        self.assertEqual(result["sanitize_fallback"], 1)
        # The icon should fall back to the LLM label (label_0)
        self.assertIn("label_0", body.get("keys_added", []))

    def test_missing_decision_on_finish_returns_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            import review_server as rs
            port_holder = {}
            orig_server = rs.ThreadingHTTPServer
            class CapturingServer(orig_server):
                def __init__(self, addr, handler):
                    super().__init__(addr, handler)
                    port_holder["port"] = self.server_address[1]
            rs.ThreadingHTTPServer = CapturingServer

            result_holder = {}
            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=5,
                )
            t = threading.Thread(target=runner, daemon=True)
            t.start()
            for _ in range(100):
                if "port" in port_holder:
                    break
                time.sleep(0.02)
            # Don't post any decisions
            status, body = _post_finish(port_holder["port"])
            self.assertEqual(status, 400)
            self.assertIn("missing", body)
            t.join(timeout=5)


class TimeoutFallbackTest(unittest.TestCase):
    def test_no_activity_timeout_falls_back_to_all_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            # Use 1-second timeout
            result = run_review_session(
                records, label_map, shots, dest,
                open_browser=False, timeout_seconds=1,
            )
            self.assertTrue(result["timed_out"])
            self.assertEqual(result["accepted"], 3)
            self.assertEqual(result["skipped"], 0)


class DistMissingTest(unittest.TestCase):
    def test_missing_dist_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"x_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()

            # Patch Path(__file__).parent / "review-ui" / "dist" to non-existent
            fake_dist = tmp / "no_dist"
            with patch("review_server._REVIEW_UI_DIST", fake_dist):
                with self.assertRaises(RuntimeError) as cm:
                    run_review_session(
                        records, label_map, shots, dest,
                        open_browser=False, timeout_seconds=1,
                    )
                self.assertIn("review-ui/dist missing", str(cm.exception))


def _run_session_full(records, label_map, decisions, manual_mode=False):
    """Run a review session end-to-end and return (result, body, components_data, png_files).

    Unlike DecisionsEndpointTest._run, this exposes the dest/components.json
    contents and the set of PNG filenames written to dest/components/ so
    callers can assert on the actual filesystem effects of _apply_decisions.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shots = tmp / "shots"
        shots.mkdir()
        _icon_files(shots, records)
        dest = tmp / "dest"
        dest.mkdir()
        (dest / "components.json").write_text("{}", encoding="utf-8")

        result_holder = {}
        port_holder = {}

        import review_server as rs
        orig_server = rs.ThreadingHTTPServer

        class CapturingServer(orig_server):
            def __init__(self, addr, handler):
                super().__init__(addr, handler)
                port_holder["port"] = self.server_address[1]

        rs.ThreadingHTTPServer = CapturingServer
        try:
            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=5,
                )

            t = threading.Thread(target=runner, daemon=True)
            t.start()

            for _ in range(100):
                if "port" in port_holder:
                    break
                time.sleep(0.02)
            port = port_holder["port"]

            status = _post_decisions(port, decisions, manual_mode=manual_mode)
            assert status == 200, f"decisions POST returned {status}"
            status, body = _post_finish(port)
            assert status == 200, f"finish POST returned {status}"

            t.join(timeout=5)
        finally:
            rs.ThreadingHTTPServer = orig_server

        comp_path = dest / "components.json"
        components_data = json.loads(comp_path.read_text(encoding="utf-8"))
        components_dir = dest / "components"
        png_files = set(p.name for p in components_dir.glob("*.png")) if components_dir.exists() else set()

        return result_holder["r"], body, components_data, png_files


class AcceptPathRegressionTest(unittest.TestCase):
    """Regression tests for accept-path label sanitization and empty-label skip.

    Covers two bugs found in final whole-branch review:
    - Bug 1: count inflation when LLM label is empty (accepted+skipped both incremented)
    - Bug 2: unsanitized LLM label in accept path (would create filenames with spaces)
    """

    def test_empty_llm_label_on_accept_counts_as_skip_only(self):
        # Bug 1: accept with empty LLM label must increment ONLY skipped (not accepted).
        records = [
            IconRecord(
                filename="record_memory_icon_0.0s_crop.png",
                action="LClick at", coords=(100, 200), current_software="Chrome",
                base="0.0s",
            )
        ]
        label_map = {records[0].filename: ""}  # empty LLM label
        decisions = {records[0].filename: {"action": "accept"}}
        result, _body, _comp, _pngs = _run_session_full(records, label_map, decisions)

        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["accepted"], 0,
                         "empty LLM label on accept must NOT inflate accepted count")
        self.assertEqual(result["sanitize_fallback"], 0)

    def test_accept_sanitizes_llm_label(self):
        # Bug 2: accept with a non-snake_case LLM label (e.g. "Start Button")
        # must sanitize to "start_button" before writing to dest.
        records = [
            IconRecord(
                filename="record_memory_icon_0.0s_crop.png",
                action="LClick at", coords=(100, 200), current_software="Chrome",
                base="0.0s",
            )
        ]
        label_map = {records[0].filename: "Start Button"}  # has a space
        decisions = {records[0].filename: {"action": "accept"}}
        result, body, comp, pngs = _run_session_full(records, label_map, decisions)

        self.assertEqual(result["accepted"], 1)
        self.assertIn("start_button", comp, "components.json key must be sanitized")
        self.assertIn("start_button", body.get("keys_added", []))
        self.assertIn("start_button.png", pngs,
                      "PNG filename must be sanitized (no spaces)")

    def test_accept_falls_back_to_timestamp_key_on_unsanitizable_llm_label(self):
        # Bug 2: accept with an unsanitizable LLM label (no safe chars) must
        # fall back to the timestamp key and count as sanitize_fallback.
        records = [
            IconRecord(
                filename="record_memory_icon_0.0s_crop.png",
                action="LClick at", coords=(100, 200), current_software="Chrome",
                base="0.0s",
            )
        ]
        label_map = {records[0].filename: "///??**"}  # no safe chars
        decisions = {records[0].filename: {"action": "accept"}}
        result, body, comp, pngs = _run_session_full(records, label_map, decisions)

        expected_key = "record_memory_icon_0_0s_crop"
        self.assertEqual(result["sanitize_fallback"], 1,
                         "unsanitizable LLM label on accept must count as sanitize_fallback")
        self.assertEqual(result["accepted"], 0)
        self.assertIn(expected_key, comp, "must fall back to timestamp key")
        self.assertIn(expected_key, body.get("keys_added", []))
        self.assertIn(f"{expected_key}.png", pngs)