import os
import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()