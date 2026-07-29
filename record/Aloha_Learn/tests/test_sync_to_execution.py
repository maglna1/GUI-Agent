import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_to_execution.py"
sys.path.insert(0, str(SCRIPT.parent.parent))  # record/Aloha_Learn

# Import the module explicitly via spec so we can patch sys.argv / find it.
import importlib.util

spec = importlib.util.spec_from_file_location("sync_to_execution", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _write_record_project(project_dir: Path, name: str = "demo_proj") -> None:
    """Create the two source files the sync script requires."""
    (project_dir / f"{name}_trace.json").write_text('{"trajectory": []}', encoding="utf-8")
    (project_dir / f"{name}_processed_log_sc.json").write_text('[]', encoding="utf-8")


class _SyncHarness:
    """Build a fake repo layout with record/, execution/.env.local, and an
    isolated cua-data dir. Returns paths the caller can patch into mod._resolve_*.
    """

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp.name)
        self.record_root = self.repo_root / "record"
        self.execution_root = self.repo_root / "execution"
        self.data_root = self.repo_root / "cua-data"
        for p in (self.record_root, self.execution_root, self.data_root):
            p.mkdir(parents=True, exist_ok=True)
        (self.execution_root / ".env.local").write_text(
            f'CUA_DATA_ROOT="{self.data_root}"\n', encoding="utf-8"
        )
        self.projects_root = self.record_root / "Aloha_Learn" / "projects"
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def project(self, name: str) -> Path:
        p = self.projects_root / name
        p.mkdir(parents=True, exist_ok=True)
        _write_record_project(p, name)
        return p

    def cleanup(self) -> None:
        self.tmp.cleanup()


class SyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.h = _SyncHarness()
        self.addCleanup(self.h.cleanup)

        # Patch record_root / repo_root discovery inside the module by
        # overriding the script_path it uses.
        fake_script = self.h.record_root / "Aloha_Learn" / "scripts" / "sync_to_execution.py"
        fake_script.parent.mkdir(parents=True, exist_ok=True)
        fake_script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

        # Re-point the module's __file__ by reloading from fake_script so
        # all path math starts from the fake repo layout.
        spec = importlib.util.spec_from_file_location(
            "sync_to_execution_test", fake_script
        )
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_sync_copies_files(self) -> None:
        project = self.h.project("demo_proj")
        rc = self.mod.sync(
            "demo_proj", "demo_scene", "demo_task",
            data_root=str(self.h.data_root),
        )
        self.assertEqual(rc, 0)
        target = self.h.data_root / "projects" / "demo_scene" / "demo_task" / "source"
        self.assertTrue((target / "showui-trace.json").is_file())
        self.assertTrue((target / "processed-log-sc.json").is_file())
        self.assertEqual(
            (target / "showui-trace.json").read_bytes(),
            (project / "demo_proj_trace.json").read_bytes(),
        )

    def test_refuses_when_target_exists_without_force(self) -> None:
        self.h.project("demo_proj")
        target = self.h.data_root / "projects" / "demo_scene" / "demo_task" / "source"
        target.mkdir(parents=True, exist_ok=True)
        (target / "showui-trace.json").write_text("PRESERVE\n", encoding="utf-8")

        rc = self.mod.sync(
            "demo_proj", "demo_scene", "demo_task",
            data_root=str(self.h.data_root),
        )
        self.assertEqual(rc, 2)
        # Original preserved.
        self.assertEqual(
            (target / "showui-trace.json").read_text(encoding="utf-8"),
            "PRESERVE\n",
        )

    def test_force_overwrites_existing(self) -> None:
        self.h.project("demo_proj")
        target = self.h.data_root / "projects" / "demo_scene" / "demo_task" / "source"
        target.mkdir(parents=True, exist_ok=True)
        (target / "showui-trace.json").write_text("STALE\n", encoding="utf-8")

        rc = self.mod.sync(
            "demo_proj", "demo_scene", "demo_task",
            data_root=str(self.h.data_root),
            force=True,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(
            (target / "showui-trace.json").read_text(encoding="utf-8"),
            '{"trajectory": []}',
        )

    def test_missing_project_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.mod.sync(
                "ghost_proj", "demo_scene", "demo_task",
                data_root=str(self.h.data_root),
            )

    def test_resolves_explicit_project_path(self) -> None:
        p = self.h.project("alpha")
        rc = self.mod.sync(
            str(p), "any_scene", "any_task",
            data_root=str(self.h.data_root),
        )
        self.assertEqual(rc, 0)

    def test_missing_data_root_errors(self) -> None:
        self.h.project("demo_proj")
        # Wipe env file and pass a non-existent --data-root.
        (self.h.execution_root / ".env.local").unlink()
        cwd = os.getcwd()
        try:
            # Need an explicit non-existent path that isn't the default fallback.
            fake_data_root = self.h.repo_root / "does_not_exist"
            with self.assertRaises(FileNotFoundError):
                self.mod.sync(
                    "demo_proj", "demo_scene", "demo_task",
                    data_root=str(fake_data_root),
                )
        finally:
            os.chdir(cwd)

    def test_target_dir_created_if_missing(self) -> None:
        self.h.project("demo_proj")
        target = self.h.data_root / "projects" / "fresh_scene" / "fresh_task" / "source"
        self.assertFalse(target.exists())
        rc = self.mod.sync(
            "demo_proj", "fresh_scene", "fresh_task",
            data_root=str(self.h.data_root),
        )
        self.assertEqual(rc, 0)
        self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main()
