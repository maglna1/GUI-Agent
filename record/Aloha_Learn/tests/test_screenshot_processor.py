import unittest
from pathlib import Path
import sys

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


if __name__ == "__main__":
    unittest.main()
