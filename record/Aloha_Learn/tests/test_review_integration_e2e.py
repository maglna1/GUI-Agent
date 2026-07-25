import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components_sync import IconRecord
from review_server import run_review_session


def _records():
    return [
        IconRecord(filename="record_memory_icon_1.0s_crop.png", action="LClick at",
                   coords=(100, 200), current_software="Chrome", base="1.0s"),
        IconRecord(filename="record_memory_icon_2.0s_crop.png", action="LClick at",
                   coords=(300, 400), current_software="Chrome", base="2.0s"),
        IconRecord(filename="record_memory_icon_3.0s_crop.png", action="LClick at",
                   coords=(500, 600), current_software="Chrome", base="3.0s"),
    ]


def _write_icons(screenshots_dir: Path, records):
    icons = screenshots_dir / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    for r in records:
        (icons / r.filename).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def _http(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=payload, headers=headers)
    r = conn.getresponse()
    raw = r.read().decode("utf-8")
    conn.close()
    return r.status, (json.loads(raw) if raw else {})


class EndToEndReviewTest(unittest.TestCase):
    def test_full_flow_writes_dest_components_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _write_icons(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()

            port_holder: dict = {}
            import review_server as rs
            orig = rs.ThreadingHTTPServer
            class Cap(orig):
                def __init__(self, addr, handler):
                    super().__init__(addr, handler)
                    port_holder["port"] = self.server_address[1]
            rs.ThreadingHTTPServer = Cap

            result_holder: dict = {}
            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=10,
                )
            t = threading.Thread(target=runner, daemon=True)
            t.start()
            try:
                for _ in range(200):
                    if "port" in port_holder:
                        break
                    time.sleep(0.02)
                port = port_holder["port"]

                # 1. GET queue
                status, queue = _http(port, "GET", "/api/queue")
                self.assertEqual(status, 200)
                self.assertEqual(len(queue["icons"]), 3)

                # 2. POST decisions: skip[1], edit[2] to "custom_btn", accept[0]
                decisions = {
                    records[1].filename: {"action": "skip"},
                    records[2].filename: {"action": "edit", "label": "Custom Btn"},
                }
                # records[0] left as accept (default)
                # We need to explicitly include accept for records[0]:
                decisions[records[0].filename] = {"action": "accept"}
                status, _ = _http(port, "POST", "/api/decisions", {
                    "decisions": decisions, "manual_mode": False,
                })
                self.assertEqual(status, 200)

                # 3. POST finish
                status, finish = _http(port, "POST", "/api/finish")
                self.assertEqual(status, 200)
                self.assertEqual(finish["applied"]["accepted"], 1)
                self.assertEqual(finish["applied"]["edited"], 1)
                self.assertEqual(finish["applied"]["skipped"], 1)
                self.assertIn("label_0", finish["keys_added"])
                self.assertIn("custom_btn", finish["keys_added"])
                self.assertNotIn("label_1", finish["keys_added"] + finish["keys_updated"])
            finally:
                rs.ThreadingHTTPServer = orig

            t.join(timeout=5)

            # 4. Verify dest/components.json
            comp_path = dest / "components.json"
            self.assertTrue(comp_path.exists())
            data = json.loads(comp_path.read_text(encoding="utf-8"))
            self.assertIn("label_0", data)
            self.assertIn("custom_btn", data)
            self.assertNotIn("label_1", data)
            # Verify entry shape
            entry = data["label_0"]
            self.assertEqual(entry["type"], "icon")
            self.assertEqual(entry["source"], "learn_batch")
            self.assertEqual(entry["icon_file"], "components/label_0.png")
            self.assertEqual(entry["seen_count"], 1)
            self.assertEqual(entry["consecutive_misses"], 0)
            self.assertTrue(entry["base_memory"])

            # 5. Verify PNGs copied
            self.assertTrue((dest / "components" / "label_0.png").exists())
            self.assertTrue((dest / "components" / "custom_btn.png").exists())
            self.assertFalse((dest / "components" / "label_1.png").exists())


if __name__ == "__main__":
    unittest.main()
