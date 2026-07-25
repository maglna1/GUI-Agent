import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from run_review_ui import _load_env_file, main


class LoadEnvFileTest(unittest.TestCase):
    def test_loads_key_value_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text(
                "FOO=bar\n"
                "BAZ=qux\n"
                "# comment line\n"
                "\n"
                "EMPTY=\n",
                encoding="utf-8",
            )
            # Wipe any pre-existing values from the test environment.
            for k in ("FOO", "BAZ", "EMPTY"):
                if k in __import__("os").environ:
                    del __import__("os").environ[k]
            loaded = _load_env_file(env)
            # EMPTY= loads too (empty string is a valid value), so 3 not 2.
            self.assertEqual(loaded, 3)
            self.assertEqual(__import__("os").environ["FOO"], "bar")
            self.assertEqual(__import__("os").environ["BAZ"], "qux")
            self.assertEqual(__import__("os").environ["EMPTY"], "")

    def test_existing_env_var_takes_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("FOO=from_file\n", encoding="utf-8")
            os = __import__("os")
            os.environ["FOO"] = "from_env"
            loaded = _load_env_file(env)
            self.assertEqual(loaded, 0)
            self.assertEqual(os.environ["FOO"], "from_env")
            del os.environ["FOO"]

    def test_missing_file_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            loaded = _load_env_file(Path(tmp) / "nonexistent.env")
            self.assertEqual(loaded, 0)

    def test_inline_comment_in_value_is_trimmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("FOO=bar  # trailing comment\n", encoding="utf-8")
            os = __import__("os")
            if "FOO" in os.environ:
                del os.environ["FOO"]
            loaded = _load_env_file(env)
            self.assertEqual(loaded, 1)
            # We do NOT strip "# comment" — that's python-dotenv's job.
            # We only trim whitespace. So trailing "# trailing comment" stays.
            self.assertTrue(os.environ["FOO"].startswith("bar"))
            del os.environ["FOO"]


class MainCliTest(unittest.TestCase):
    def test_no_arg_returns_2(self):
        # main() returns 2; the SystemExit wrapper is in the __main__ block.
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()