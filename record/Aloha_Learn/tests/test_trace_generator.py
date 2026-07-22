import json
import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trace_generator import TraceGenerator, env_bool


class StubTraceGenerator(TraceGenerator):
    def _call_openai(self, prompt, crop_b64, full_b64):
        return json.dumps(
            {
                "Observation": "局部图中红色 X 位于按钮上。",
                "Think": "用户需要点击该按钮继续。",
                "Action": "点击继续按钮。",
                "Expectation": "页面进入下一步。",
                "Operation": {
                    "type": "click",
                    "prompt": "点击继续按钮",
                },
            },
            ensure_ascii=False,
        )


class RetryTraceGenerator(TraceGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0

    def _call_openai(self, prompt, crop_b64, full_b64):
        self.calls += 1
        if self.calls == 1:
            return json.dumps(
                {
                    "Observation": "",
                    "Think": "",
                    "Action": "",
                    "Expectation": "",
                    "Operation": {"type": "unknown"},
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "Observation": "局部图中红色 X 位于目的地建议项上。",
                "Think": "用户需要选择该目的地。",
                "Action": "点击 Los Angeles 目的地建议项。",
                "Expectation": "目的地被设置为 Los Angeles。",
                "Operation": {
                    "type": "click",
                    "prompt": "点击 Los Angeles 目的地建议项",
                },
            },
            ensure_ascii=False,
        )


class InvalidTraceGenerator(TraceGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0

    def _call_openai(self, prompt, crop_b64, full_b64):
        self.calls += 1
        return json.dumps(
            {
                "Observation": "无法确定目标。",
                "Think": "信息不足。",
                "Action": "继续操作。",
                "Expectation": "页面变化。",
                "Operation": {"type": "unknown"},
            },
            ensure_ascii=False,
        )


class DoubleClickRetryTraceGenerator(TraceGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0

    def _call_openai(self, prompt, crop_b64, full_b64):
        self.calls += 1
        operation_type = "click" if self.calls == 1 else "doubleClick"
        action = "点击文件行。" if self.calls == 1 else "双击文件行。"
        return json.dumps(
            {
                "Observation": "局部图中红色 X 位于 report.xlsx 文件行上。",
                "Think": "用户需要打开该文件。",
                "Action": action,
                "Expectation": "文件被打开。",
                "Operation": {
                    "type": operation_type,
                    "prompt": "双击文件列表中的 report.xlsx 文件行以打开文件",
                },
            },
            ensure_ascii=False,
        )


class TraceGeneratorOperationTest(unittest.TestCase):
    def test_env_bool_is_strict(self):
        with patch.dict(os.environ, {"OPENAI_VERIFY_SSL": "false"}):
            self.assertFalse(env_bool("OPENAI_VERIFY_SSL", True))
        with patch.dict(os.environ, {"OPENAI_VERIFY_SSL": "true"}):
            self.assertTrue(env_bool("OPENAI_VERIFY_SSL", False))
        with patch.dict(os.environ, {"OPENAI_VERIFY_SSL": "invalid"}):
            with self.assertRaisesRegex(ValueError, "OPENAI_VERIFY_SSL 必须是"):
                env_bool("OPENAI_VERIFY_SSL", True)

    def test_openai_request_can_disable_ssl_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt_path = root / "default_prompt.json"
            prompt_path.write_text(json.dumps({"Base Prompt": ""}), encoding="utf-8")
            keys_path = root / "api_keys.json"
            keys_path.write_text("{}", encoding="utf-8")
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}

            with (
                patch("trace_generator.load_dotenv"),
                patch.dict(
                    os.environ,
                    {"OPENAI_API_KEY": "test-key", "OPENAI_VERIFY_SSL": "false"},
                    clear=False,
                ),
                patch("trace_generator.requests.post", return_value=response) as post,
            ):
                generator = TraceGenerator(
                    default_prompt_path=str(prompt_path),
                    api_provider="openai",
                    api_keys_path=str(keys_path),
                )
                generator._call_openai("prompt", None, None)

            self.assertFalse(generator.openai_verify_ssl)
            self.assertFalse(post.call_args.kwargs["verify"])

    def test_sanitize_operation_preserves_input_locate_prompt(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prompt_path = root / "default_prompt.json"
                prompt_path.write_text(json.dumps({"Base Prompt": ""}, ensure_ascii=False), encoding="utf-8")

                generator = StubTraceGenerator(default_prompt_path=str(prompt_path), api_provider="openai")

                self.assertEqual(
                    {
                        "type": "input",
                        "prompt": "在 Chrome 地址栏/搜索栏中输入 {{value}}",
                        "locatePrompt": "Chrome 地址栏/搜索栏",
                        "value": "QATAR AIRWAYS",
                    },
                    generator._sanitize_operation(
                        {
                            "type": "Input",
                            "prompt": " 在 Chrome 地址栏/搜索栏中输入 {{value}} ",
                            "locatePrompt": " Chrome 地址栏/搜索栏 ",
                            "value": " QATAR AIRWAYS ",
                        }
                    ),
                )
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_generate_trace_preserves_operation_field(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prompt_path = root / "default_prompt.json"
                prompt_path.write_text(json.dumps({"Base Prompt": "只输出 JSON。"}, ensure_ascii=False), encoding="utf-8")

                shots_dir = root / "screenshots"
                shots_dir.mkdir()
                (shots_dir / "step.jpg").write_bytes(b"fake-jpeg")

                recording_path = root / "recording.json"
                recording_path.write_text(
                    json.dumps(
                        [
                            {
                                "timestamp": 1.0,
                                "action": "LClick at",
                                "current_software": "Chrome",
                                "screenshot": "step.jpg",
                            }
                        ],
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                output_path = root / "trace.json"
                generator = StubTraceGenerator(default_prompt_path=str(prompt_path), api_provider="openai")
                generator.generate_trace(str(recording_path), str(shots_dir), str(output_path))

                trace = json.loads(output_path.read_text(encoding="utf-8"))

                self.assertEqual(
                    {"type": "click", "prompt": "点击继续按钮"},
                    trace["trajectory"][0]["caption"]["operation"],
                )
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_sanitize_operation_preserves_double_click(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                prompt_path = Path(tmp) / "default_prompt.json"
                prompt_path.write_text(json.dumps({"Base Prompt": ""}), encoding="utf-8")
                generator = StubTraceGenerator(
                    default_prompt_path=str(prompt_path),
                    api_provider="openai",
                )

                self.assertEqual(
                    {
                        "type": "doubleClick",
                        "prompt": "双击 report.xlsx 文件行",
                    },
                    generator._sanitize_operation(
                        {
                            "type": "DoubleClick",
                            "prompt": " 双击 report.xlsx 文件行 ",
                        }
                    ),
                )
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_ldoubleclick_retries_when_model_degrades_it_to_click(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prompt_path = root / "default_prompt.json"
                prompt_path.write_text(
                    json.dumps({"Base Prompt": "只输出 JSON。"}, ensure_ascii=False),
                    encoding="utf-8",
                )
                shots_dir = root / "screenshots"
                shots_dir.mkdir()
                (shots_dir / "step.jpg").write_bytes(b"fake-jpeg")
                recording_path = root / "recording.json"
                recording_path.write_text(
                    json.dumps(
                        [
                            {
                                "timestamp": 1.0,
                                "action": "LDoubleClick at",
                                "current_software": "Explorer",
                                "screenshot": "step.jpg",
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                output_path = root / "trace.json"
                generator = DoubleClickRetryTraceGenerator(
                    default_prompt_path=str(prompt_path),
                    api_provider="openai",
                )

                generator.generate_trace(
                    str(recording_path),
                    str(shots_dir),
                    str(output_path),
                )

                trace = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(2, generator.calls)
                self.assertEqual(
                    {
                        "type": "doubleClick",
                        "prompt": "双击文件列表中的 report.xlsx 文件行以打开文件",
                    },
                    trace["trajectory"][0]["caption"]["operation"],
                )
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_generate_trace_retries_when_operation_is_unknown(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prompt_path = root / "default_prompt.json"
                prompt_path.write_text(json.dumps({"Base Prompt": "只输出 JSON。"}, ensure_ascii=False), encoding="utf-8")

                shots_dir = root / "screenshots"
                shots_dir.mkdir()
                (shots_dir / "step.jpg").write_bytes(b"fake-jpeg")

                recording_path = root / "recording.json"
                recording_path.write_text(
                    json.dumps(
                        [
                            {
                                "timestamp": 1.0,
                                "action": "LClick at",
                                "current_software": "Chrome",
                                "screenshot": "step.jpg",
                            }
                        ],
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                output_path = root / "trace.json"
                generator = RetryTraceGenerator(default_prompt_path=str(prompt_path), api_provider="openai")
                generator.generate_trace(str(recording_path), str(shots_dir), str(output_path))

                trace = json.loads(output_path.read_text(encoding="utf-8"))

                self.assertEqual(2, generator.calls)
                self.assertEqual(
                    {"type": "click", "prompt": "点击 Los Angeles 目的地建议项"},
                    trace["trajectory"][0]["caption"]["operation"],
                )
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_generate_trace_fails_when_retry_still_has_no_executable_operation(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prompt_path = root / "default_prompt.json"
                prompt_path.write_text(json.dumps({"Base Prompt": "只输出 JSON。"}), encoding="utf-8")
                shots_dir = root / "screenshots"
                shots_dir.mkdir()
                (shots_dir / "step.jpg").write_bytes(b"fake-jpeg")
                recording_path = root / "recording.json"
                recording_path.write_text(
                    json.dumps(
                        [{"timestamp": 1.0, "action": "LClick at", "screenshot": "step.jpg"}]
                    ),
                    encoding="utf-8",
                )
                output_path = root / "trace.json"
                generator = InvalidTraceGenerator(default_prompt_path=str(prompt_path), api_provider="openai")

                with self.assertRaisesRegex(RuntimeError, "trace step 1.*纠错重试"):
                    generator.generate_trace(str(recording_path), str(shots_dir), str(output_path))

                self.assertEqual(2, generator.calls)
                self.assertFalse(output_path.exists())
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_generate_trace_fails_instead_of_skipping_step_without_screenshot(self):
        previous_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prompt_path = root / "default_prompt.json"
                prompt_path.write_text(json.dumps({"Base Prompt": "只输出 JSON。"}), encoding="utf-8")
                shots_dir = root / "screenshots"
                shots_dir.mkdir()
                recording_path = root / "recording.json"
                recording_path.write_text(
                    json.dumps([{"timestamp": 1.0, "action": "LClick at"}]),
                    encoding="utf-8",
                )
                output_path = root / "trace.json"
                generator = StubTraceGenerator(default_prompt_path=str(prompt_path), api_provider="openai")

                with self.assertRaisesRegex(RuntimeError, "录制动作缺少截图"):
                    generator.generate_trace(str(recording_path), str(shots_dir), str(output_path))

                self.assertFalse(output_path.exists())
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key


if __name__ == "__main__":
    unittest.main()
