import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screenshot_processor import VideoScreenshotExtractor


class IconCropSizeConstructorTest(unittest.TestCase):
    def test_zero_arg_constructor_uses_default_icon_crop_size(self):
        ext = VideoScreenshotExtractor()
        self.assertEqual(ext.icon_crop_size, 50)

    def test_explicit_icon_crop_size_kwarg_is_stored(self):
        ext = VideoScreenshotExtractor(icon_crop_size=80)
        self.assertEqual(ext.icon_crop_size, 80)

    def test_existing_positional_args_still_work(self):
        # All 6 pre-existing positional params passed; icon_crop_size must default.
        ext = VideoScreenshotExtractor(1920, 1080, 95, 256, 30, 6)
        self.assertEqual(ext.icon_crop_size, 50)
        self.assertEqual(ext.target_width, 1920)
        self.assertEqual(ext.crop_size, 256)

    def test_existing_kwargs_still_work(self):
        ext = VideoScreenshotExtractor(target_width=1280, crop_size=200)
        self.assertEqual(ext.target_width, 1280)
        self.assertEqual(ext.crop_size, 200)
        self.assertEqual(ext.icon_crop_size, 50)


class SavePngHelperTest(unittest.TestCase):
    def setUp(self):
        self.ext = VideoScreenshotExtractor()

    def test_save_png_writes_file_and_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "icons", "sample.png")
            img = np.zeros((50, 50, 3), dtype=np.uint8)
            img[10:20, 10:20] = (0, 0, 255)  # BGR red square for content sanity

            ok = self.ext._save_png(path, img)

            self.assertTrue(ok)
            self.assertTrue(os.path.exists(path))
            # Round-trip to confirm it's a real PNG (cv2.IMREAD_COLOR keeps BGR).
            loaded = cv2.imread(path, cv2.IMREAD_COLOR)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.shape, (50, 50, 3))
            # Pixel we wrote should still be red.
            self.assertTrue(np.array_equal(loaded[15, 15], np.array([0, 0, 255])))

    def test_save_png_creates_missing_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = os.path.join(tmp, "a", "b", "c", "icon.png")
            img = np.zeros((50, 50, 3), dtype=np.uint8)

            ok = self.ext._save_png(nested, img)

            self.assertTrue(ok)
            self.assertTrue(os.path.exists(nested))


class DefaultClickIconSaveTest(unittest.TestCase):
    def _build_action(self, ts, x, y):
        return {
            "timestamp": ts,
            "action": "LClick at",
            "coords": [{"x": x, "y": y}],
            "current_software": "Explorer",
        }

    def _synthetic_frame(self, w=1920, h=1080, color=(200, 150, 100)):
        # Solid-color BGR frame. The exact color makes content assertions trivial.
        return np.zeros((h, w, 3), dtype=np.uint8)
        # Note: solid zero is fine; we only check shape and absence of red X.

    def _run_one_action(self, ext, action, screenshots_path):
        return ext.process_actions(
            [action],
            video_path="ignored",
            screenshots_path=screenshots_path,
            need_scaling=False,
            scale_x=1.0,
            scale_y=1.0,
        )

    def test_default_click_produces_icon_png_in_icons_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            screenshots_path = Path(tmp)
            ext = VideoScreenshotExtractor()
            action = self._build_action(10.954, 820, 450)
            expected_ts = abs(action["timestamp"] - 0.1)  # mirrors line 132
            expected_base = f"{expected_ts:.3f}s"

            with patch.object(VideoScreenshotExtractor, "_get_frame_at",
                              return_value=self._synthetic_frame()):
                updated = self._run_one_action(ext, action, screenshots_path)

            # 1. Icon PNG file exists in screenshots/icons/
            icon_path = screenshots_path / "icons" / f"record_memory_icon_{expected_base}_crop.png"
            self.assertTrue(icon_path.exists(), f"missing icon at {icon_path}")

            # 2. Icon is a valid 50x50 PNG (lossless, exact size)
            icon = cv2.imread(str(icon_path), cv2.IMREAD_UNCHANGED)
            self.assertIsNotNone(icon)
            self.assertEqual(icon.shape[0], 50)
            self.assertEqual(icon.shape[1], 50)

            # 3. Existing JPG siblings still produced
            self.assertTrue((screenshots_path / f"{expected_base}.jpg").exists())
            self.assertTrue((screenshots_path / f"{expected_base}.crop.jpg").exists())

            # 4. JSON schema unchanged: only screenshot_full and screenshot_crop, no screenshot_icon
            self.assertIn("screenshot_full", updated[0])
            self.assertIn("screenshot_crop", updated[0])
            self.assertNotIn("screenshot_icon", updated[0])

    def test_drag_action_does_not_produce_icon(self):
        with tempfile.TemporaryDirectory() as tmp:
            screenshots_path = Path(tmp)
            ext = VideoScreenshotExtractor()
            drag_action = {
                "timestamp": 5.0,
                "action": "DragStart at",
                "coords": [{"x": 100, "y": 100}],
                "path": [{"x": 100, "y": 100}, {"x": 200, "y": 200}],
                "current_software": "Explorer",
            }

            with patch.object(VideoScreenshotExtractor, "_get_frame_at",
                              return_value=self._synthetic_frame()):
                self._run_one_action(ext, drag_action, screenshots_path)

            icons_dir = screenshots_path / "icons"
            produced = icons_dir.exists() and any(icons_dir.glob("*.png"))
            self.assertFalse(produced, "DragStart must not produce an icon PNG")

    def test_no_coordinate_action_does_not_produce_icon(self):
        with tempfile.TemporaryDirectory() as tmp:
            screenshots_path = Path(tmp)
            ext = VideoScreenshotExtractor()
            scroll_action = {
                "timestamp": 7.0,
                "action": "Wheel at",
                "coords": [{"x": 500, "y": 500}],
                "current_software": "Explorer",
            }

            with patch.object(VideoScreenshotExtractor, "_get_frame_at",
                              return_value=self._synthetic_frame()):
                self._run_one_action(ext, scroll_action, screenshots_path)

            icons_dir = screenshots_path / "icons"
            self.assertFalse(
                icons_dir.exists() and any(icons_dir.glob("record_memory_icon_*.png")),
                "scroll/wheel actions must not produce icon PNGs",
            )


if __name__ == "__main__":
    unittest.main()