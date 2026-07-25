import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from screenshot_processor import VideoScreenshotExtractor


def _write_project(project_dir: Path, n_clicks: int = 1):
    (project_dir / "inputs").mkdir(parents=True)
    (project_dir / "inputs" / "demo.mp4").write_bytes(b"")
    actions = [
        {"action": "CONFIG", "coords": {"0": {"width": 1920, "height": 1080, "scale_factor": 1.0}}},
    ]
    for i in range(n_clicks):
        actions.append({
            "timestamp": 10.954 + i,
            "action": "LClick at",
            "coords": [{"x": 820 + i, "y": 450}],
            "current_software": "Explorer",
        })
    (project_dir / f"{project_dir.name}_processed_log.json").write_text(
        json.dumps(actions), encoding="utf-8"
    )


class ReviewSessionHookTest(unittest.TestCase):
    """After rework: no env var; review session always runs; dest is project-internal."""

    def test_review_session_always_called_no_env_var_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)

            review_return = {
                "accepted": 1, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                "keys_added": ["label_0"], "keys_updated": [],
                "manual_mode": False, "timed_out": False, "port": 54321,
            }

            # Make sure NO review-related env var is set.
            for k in ("GUI_AGENT_COMPONENTS_DEST", "GUI_AGENT_REVIEW_DISABLE"):
                os.environ.pop(k, None)

            ext = VideoScreenshotExtractor()
            with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                with patch("screenshot_processor.run_review_session", return_value=review_return) as mock_review:
                    _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_called_once()
            self.assertEqual(meta["review_decisions"], {
                "accepted": 1, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
            })
            self.assertFalse(meta["review_manual_mode"])
            self.assertFalse(meta["review_timed_out"])
            self.assertEqual(meta["review_port"], 54321)

    def test_dest_is_project_internal_no_env_var_read(self):
        """Dest must be <project_dir>/components_review_ui_mutimodal_memory_manual,
        regardless of any env var (even if a stale GUI_AGENT_COMPONENTS_DEST is set)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)

            review_return = {
                "accepted": 1, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                "keys_added": ["label_0"], "keys_updated": [],
                "manual_mode": False, "timed_out": False, "port": 1,
            }

            # Even with a stale env var pointing elsewhere, dest is project-internal.
            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(tmp / "elsewhere"),
                "GUI_AGENT_REVIEW_DISABLE": "1",
            }, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch("screenshot_processor.run_review_session", return_value=review_return) as mock_review:
                        _, _, meta = ext.process_project(str(project_dir))

            expected_dest = (project_dir / "components_review_ui_mutimodal_memory_manual").resolve()
            self.assertEqual(Path(meta["components_dest"]).resolve(), expected_dest)
            # And the legacy dest path is NOT used.
            self.assertFalse((tmp / "elsewhere" / "components.json").exists())

    def test_no_records_path_still_populates_meta(self):
        """If there are no records (no default-click icons), review session is skipped
        but meta still has dest + zeros."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            # No clicks — only CONFIG action.
            _write_project(project_dir, n_clicks=0)

            ext = VideoScreenshotExtractor()
            with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                with patch("screenshot_processor.run_review_session") as mock_review:
                    _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_not_called()
            expected_dest = (project_dir / "components_review_ui_mutimodal_memory_manual").resolve()
            self.assertEqual(Path(meta["components_dest"]).resolve(), expected_dest)
            self.assertTrue(meta["components_synced"])
            self.assertEqual(meta["components_keys_added"], [])
            self.assertEqual(meta["components_keys_updated"], [])
            self.assertEqual(meta["review_decisions"], {
                "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
            })
            self.assertIsNone(meta["review_port"])


if __name__ == "__main__":
    unittest.main()