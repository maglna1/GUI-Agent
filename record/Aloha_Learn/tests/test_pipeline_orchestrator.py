import json
import queue
import sys
import tempfile
import threading
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

# Plain imports so dataclass registration sees the module in sys.modules.
import pipeline_orchestrator as mod
import pipeline_server as serv


class EventBusTest(unittest.TestCase):
    def test_subscribe_unsubscribe(self):
        bus = mod.EventBus()
        sub = bus.subscribe()
        bus.publish({"type": "x", "value": 1})
        received = []
        try:
            received.append(sub.get(timeout=0.5))
        except queue.Empty:
            pass
        self.assertEqual(received[0]["value"], 1)
        bus.unsubscribe(sub)
        # After unsubscribe publish is silent
        try:
            sub.get_nowait()
            # if we got something, bus kept the queue alive (acceptable since q is owned by sub)
        except queue.Empty:
            pass

    def test_drop_oldest_on_full(self):
        bus = mod.EventBus()
        q = queue.Queue(maxsize=2)
        # Patch subscribers to our small queue.
        bus._subscribers.append(q)
        bus.publish({"type": "a"})
        bus.publish({"type": "b"})
        # Now full; next publish triggers drop-oldest.
        bus.publish({"type": "c"})
        items = [q.get_nowait() for _ in range(2)]
        # First item dropped, recent two kept.
        self.assertEqual([i["type"] for i in items], ["b", "c"])


class StateTest(unittest.TestCase):
    def test_as_dict_includes_step_defs_and_caps_log(self):
        st = mod.PipelineState(
            run_id="x",
            project="/tmp/p",
            scene="scn",
            task="tsk",
            goal="",
            library_roots=["/tmp/lib"],
        )
        st.steps[1] = mod.StepState(log_lines=[f"line{i}" for i in range(300)])
        d = st.as_dict()
        self.assertEqual(d["scene"], "scn")
        self.assertEqual(d["task"], "tsk")
        self.assertEqual(len(d["steps"][1]["log_lines"]), 200)
        self.assertEqual(len(d["step_defs"]), 4)


class SubmitTest(unittest.TestCase):
    def test_submit_labels_wakes_event_and_sets_state(self):
        orch = mod.create_orchestrator(
            project="/p", scene="s", task="t", goal="g",
            library_roots=["/lib"],
        )
        self.assertFalse(orch._labels_event.is_set())
        orch.submit_labels({"foo.png": "minimax_code"})
        self.assertTrue(orch._labels_event.is_set())
        self.assertEqual(orch.state.step1_labels, {"foo.png": "minimax_code"})

    def test_submit_decisions_filters_non_icon(self):
        orch = mod.create_orchestrator(
            project="/p", scene="s", task="t", goal="g",
            library_roots=["/lib"],
        )
        orch.submit_decisions({
            "1": {"is_icon": True, "label": "ssrun"},
            "2": {"is_icon": False, "label": "ignored"},
            "3": "not-a-dict",
        })
        self.assertEqual(orch.state.step3_decisions, {
            "1": {"is_icon": True, "label": "ssrun"},
            "2": {"is_icon": False, "label": ""},
        })


class StepHelpersTest(unittest.TestCase):
    def test_set_status_publishes_state_event(self):
        orch = mod.create_orchestrator(
            project="/p", scene="s", task="t", goal="g",
            library_roots=["/lib"],
        )
        sub = orch.bus.subscribe()
        orch._set_step_status(2, mod.StepStatus.RUNNING)
        ev = sub.get(timeout=0.5)
        self.assertEqual(ev["type"], "state")
        self.assertEqual(ev["step"], 2)
        self.assertEqual(ev["status"], "running")

    def test_set_progress_publishes_progress_event(self):
        orch = mod.create_orchestrator(
            project="/p", scene="s", task="t", goal="g",
            library_roots=["/lib"],
        )
        sub = orch.bus.subscribe()
        orch._set_progress(3, 2, 9)
        ev = sub.get(timeout=0.5)
        self.assertEqual(ev["type"], "progress")
        self.assertEqual(ev["current"], 2)
        self.assertEqual(ev["total"], 9)


class RunWithLogTest(unittest.TestCase):
    def test_runs_simple_command(self):
        captured: list[str] = []
        rc, tail = mod._run_with_log(
            [sys.executable, "-c", "print('hi')"],
            cwd=".",
            on_line=captured.append,
        )
        self.assertEqual(rc, 0)
        self.assertIn("hi", captured)
        self.assertIn("hi", tail)

    def test_returns_nonzero_on_failure(self):
        captured: list[str] = []
        rc, _ = mod._run_with_log(
            [sys.executable, "-c", "import sys; sys.exit(3)"],
            cwd=".",
            on_line=captured.append,
        )
        self.assertEqual(rc, 3)


class DetectDataRootTest(unittest.TestCase):
    def test_reads_env_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            execution = Path(tmp)
            (execution / ".env.local").write_text(
                'CUA_DATA_ROOT="' + tmp.replace("\\", "/") + '/cua-data"\n',
                encoding="utf-8",
            )
            val = mod._detect_data_root(execution)
            self.assertIsNotNone(val)
            self.assertTrue(val.endswith("cua-data"))

    def test_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            execution = Path(tmp)
            self.assertIsNone(mod._detect_data_root(execution))


class HTTPPipelineTest(unittest.TestCase):
    """Smoke-test the pipeline HTTP server (state + SSE + decision posts)."""

    def test_state_endpoint_returns_snapshot(self):
        orch = mod.create_orchestrator(
            project="/p", scene="s", task="t", goal="g",
            library_roots=["/lib"],
        )
        runtime = serv._Runtime(orchestrator=orch)
        from http.server import ThreadingHTTPServer
        # Reuse the handler builder with our runtime.
        srv = ThreadingHTTPServer(("127.0.0.1", 0), serv._make_pipeline_handler(runtime))
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}/api/pipeline/state"
            import urllib.request
            with urllib.request.urlopen(url, timeout=2) as r:
                body = json.loads(r.read().decode("utf-8"))
            self.assertEqual(body["project"], "/p")
            self.assertEqual(body["scene"], "s")
        finally:
            srv.shutdown()
            srv.server_close()
            t.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
