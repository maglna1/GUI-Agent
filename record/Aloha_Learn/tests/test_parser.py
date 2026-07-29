"""parser.py path-resolution test.

Project folder discovery should support:
1. Direct path (absolute or cwd-relative)
2. `<cwd>/projects/<name>`
3. `<script_dir>/projects/<name>` (running parser.py from repo root)
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
LEARN_DIR = SCRIPT_DIR  # record/Aloha_Learn

# parser.py uses absolute imports (`from log_processor import ...`), so the
# learn_dir (where its peers live) must be on sys.path *before* importing.
if str(LEARN_DIR) not in sys.path:
    sys.path.insert(0, str(LEARN_DIR))


def _reload_parser_module() -> None:
    """Re-import parser so its `__file__` lives in the fake learn_dir.

    The test's setUp writes parser.py's source into a temporary directory
    mirroring the real record/Aloha_Learn layout. parser.py derives
    `_resolve_project_dir`'s script_dir from `__file__`, so we need a
    module instance whose `__file__` points inside that temp tree.
    """
    spec = importlib.util.spec_from_file_location(
        "parser_under_test", str(SCRIPT_DIR / "parser.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Stash on the test class for later access.
    ResolveProjectDirTest._parser = module


class ResolveProjectDirTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp.name)
        self.learn_dir = self.repo_root / "Aloha_Learn"
        self.learn_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir = self.learn_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.target = self.projects_dir / "demo_proj"
        self.target.mkdir()
        # Place parser.py in the fake learn_dir so its script_dir points
        # at our temp tree instead of the real one.
        parser_text = SCRIPT_DIR.joinpath("parser.py").read_text(encoding="utf-8")
        self.parser_copy = self.learn_dir / "parser.py"
        self.parser_copy.write_text(parser_text, encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _reimport_with_repo_root(self) -> None:
        spec2 = importlib.util.spec_from_file_location(
            "parser_under_test_reloaded", self.parser_copy
        )
        module = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(module)
        self.__class__._parser = module

    def test_resolves_from_script_dir_projects(self) -> None:
        self._reimport_with_repo_root()
        resolved = self.__class__._parser._resolve_project_dir("demo_proj")
        self.assertEqual(resolved, self.target.resolve())

    def test_resolves_explicit_relative_path_from_repo_root(self) -> None:
        """<cwd>/<project>/Aloha_Learn/projects/<name> works when cwd == repo_root."""
        self._reimport_with_repo_root()
        cwd_save = Path.cwd()
        try:
            os.chdir(self.repo_root)
            resolved = self.__class__._parser._resolve_project_dir(
                "Aloha_Learn/projects/demo_proj"
            )
            self.assertEqual(resolved, self.target.resolve())
        finally:
            os.chdir(cwd_save)

    def test_resolves_explicit_absolute_path(self) -> None:
        self._reimport_with_repo_root()
        resolved = self.__class__._parser._resolve_project_dir(str(self.target))
        self.assertEqual(resolved, self.target.resolve())

    def test_resolves_from_cwd_projects(self) -> None:
        """When invoked with cwd == <...>/projects, bare name resolves there."""
        self._reimport_with_repo_root()
        cwd_save = Path.cwd()
        try:
            os.chdir(self.projects_dir)
            resolved = self.__class__._parser._resolve_project_dir("demo_proj")
            self.assertEqual(resolved, self.target.resolve())
        finally:
            os.chdir(cwd_save)

    def test_raises_with_clear_error(self) -> None:
        self._reimport_with_repo_root()
        with self.assertRaises(FileNotFoundError) as cm:
            self.__class__._parser._resolve_project_dir("ghost_proj")
        msg = str(cm.exception)
        for needle in ("ghost_proj", "Tried"):
            self.assertIn(needle, msg)


if __name__ == "__main__":
    unittest.main()
