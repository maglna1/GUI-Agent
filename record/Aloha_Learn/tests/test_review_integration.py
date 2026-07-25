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


def _write_project(project_dir: Path):
    (project_dir / "inputs").mkdir(parents=True)
    (project_dir / "inputs" / "demo.mp4").write_bytes(b"")
    actions = [
        {"action": "CONFIG", "coords": {"0": {"width": 1920, "height": 1080, "scale_factor": 1.0}}},
        {"timestamp": 10.954, "action": "LClick at",
         "coords": [{"x": 820, "y": 450}], "current_software": "Explorer"},
    ]
    (project_dir / f"{project_dir.name}_processed_log.json").write_text(
        json.dumps(actions), encoding="utf-8"
    )


class ReviewSessionHookTest(unittest.TestCase):
    def test_disable_env_var_skips_review_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(dest),
                "GUI_AGENT_REVIEW_DISABLE": "1",
            }, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch("screenshot_processor.run_review_session") as mock_review:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_not_called()
            self.assertFalse(meta.get("review_manual_mode", False))

    def test_disable_env_var_unset_calls_review_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()
            # Pre-populate so sync has work
            (dest / "components.json").write_text("{}", encoding="utf-8")

            review_return = {
                "accepted": 1, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                "keys_added": ["label_0"], "keys_updated": [],
                "manual_mode": False, "timed_out": False, "port": 54321,
            }

            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(dest),
            }, clear=False):
                # Ensure disable is unset in this scope
                os.environ.pop("GUI_AGENT_REVIEW_DISABLE", None)
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

    def test_disable_env_var_empty_string_treated_as_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            review_return = {
                "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                "keys_added": [], "keys_updated": [],
                "manual_mode": False, "timed_out": False, "port": 1234,
            }

            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(dest),
                "GUI_AGENT_REVIEW_DISABLE": "",
            }, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch("screenshot_processor.run_review_session", return_value=review_return) as mock_review:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_called_once()


if __name__ == "__main__":
    unittest.main()