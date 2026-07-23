import os
import sys
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screenshot_processor import VideoScreenshotExtractor, ComponentsLLMError
from components_sync import IconRecord


class IconCropSizeConstructorTest(unittest.TestCase):
    def test_zero_arg_constructor_uses_default_icon_crop_size(self):
        ext = VideoScreenshotExtractor()
        self.assertEqual(ext.icon_crop_size, 30)

    def test_explicit_icon_crop_size_kwarg_is_stored(self):
        ext = VideoScreenshotExtractor(icon_crop_size=80)
        self.assertEqual(ext.icon_crop_size, 80)

    def test_existing_positional_args_still_work(self):
        # All 6 pre-existing positional params passed; icon_crop_size must default.
        ext = VideoScreenshotExtractor(1920, 1080, 95, 256, 30, 6)
        self.assertEqual(ext.icon_crop_size, 30)
        self.assertEqual(ext.target_width, 1920)
        self.assertEqual(ext.crop_size, 256)

    def test_existing_kwargs_still_work(self):
        ext = VideoScreenshotExtractor(target_width=1280, crop_size=200)
        self.assertEqual(ext.target_width, 1280)
        self.assertEqual(ext.crop_size, 200)
        self.assertEqual(ext.icon_crop_size, 30)


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

    def _synthetic_frame(self, w=1920, h=1080):
        # 非均匀图案化 BGR 帧：每个像素为 (x % 256, y % 256, (x + y) % 256)。
        # 这样能产生唯一且可预测的像素值，使点击点周围 50x50 邻域可识别，
        # 若源取错则会得到一张完全不同的图。
        ys, xs = np.indices((h, w), dtype=np.uint16)
        b = (xs % 256).astype(np.uint8)
        g = (ys % 256).astype(np.uint8)
        r = ((xs + ys) % 256).astype(np.uint8)
        return np.stack([b, g, r], axis=-1)

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
            expected_ts = abs(action["timestamp"] - 0.1)  # 与 screenshot_processor.py 中的处理一致
            expected_base = f"{expected_ts:.3f}s"

            frame = self._synthetic_frame()
            with patch.object(VideoScreenshotExtractor, "_get_frame_at",
                              return_value=frame):
                updated = self._run_one_action(ext, action, screenshots_path)

            # 1. 图标 PNG 文件存在于 screenshots/icons/ 下
            icon_path = screenshots_path / "icons" / f"record_memory_icon_{expected_base}_crop.png"
            self.assertTrue(icon_path.exists(), f"missing icon at {icon_path}")

            # 2. 图标为合法的 icon_crop_size×icon_crop_size PNG（无损、尺寸准确）
            icon = cv2.imread(str(icon_path), cv2.IMREAD_UNCHANGED)
            self.assertIsNotNone(icon)
            self.assertEqual(icon.shape[0], ext.icon_crop_size)
            self.assertEqual(icon.shape[1], ext.icon_crop_size)

            # 2.5. 像素级精确断言：直接对图案化帧调用 _crop_with_black_padding
            # 得到期望图标。这样可以一次性验证：(a) 图标源自原始帧
            # （而非带红 X 的 crop_img），(b) 源坐标正确，(c) PNG 往返无损。
            expected_icon = ext._crop_with_black_padding(
                frame, action["coords"][0]["x"], action["coords"][0]["y"],
                crop_size=ext.icon_crop_size,
            )
            self.assertEqual(icon.shape, expected_icon.shape)
            self.assertTrue(
                np.array_equal(icon, expected_icon),
                "icon PNG pixels must equal a direct _crop_with_black_padding of the frame",
            )

            # 3. 现有的 JPG 同名文件仍然产生
            self.assertTrue((screenshots_path / f"{expected_base}.jpg").exists())
            self.assertTrue((screenshots_path / f"{expected_base}.crop.jpg").exists())

            # 4. JSON schema 未变：仅有 screenshot_full 和 screenshot_crop，不含 screenshot_icon
            self.assertIn("screenshot_full", updated[0])
            self.assertIn("screenshot_crop", updated[0])
            self.assertNotIn("screenshot_icon", updated[0])

    def test_edge_click_icon_has_black_padding_for_out_of_frame_region(self):
        # 非常靠近左上角的点击：源区域部分落在 1920x1080 帧之外，
        # 因此 _crop_with_black_padding 必须用纯 (0, 0, 0) 像素填补缺失区域，
        # 而落在帧内的部分保留图案化像素。
        with tempfile.TemporaryDirectory() as tmp:
            screenshots_path = Path(tmp)
            ext = VideoScreenshotExtractor()
            action = self._build_action(3.50, 2, 3)  # 紧贴角落的微小点击
            expected_ts = abs(action["timestamp"] - 0.1)
            expected_base = f"{expected_ts:.3f}s"

            frame = self._synthetic_frame()
            with patch.object(VideoScreenshotExtractor, "_get_frame_at",
                              return_value=frame):
                self._run_one_action(ext, action, screenshots_path)

            icon_path = screenshots_path / "icons" / f"record_memory_icon_{expected_base}_crop.png"
            icon = cv2.imread(str(icon_path), cv2.IMREAD_UNCHANGED)

            # 形状必须严格为 icon_crop_size×icon_crop_size×3。
            self.assertEqual(icon.shape, (ext.icon_crop_size, ext.icon_crop_size, 3))

            # 直接计算期望裁剪结果：因为 (2, 3) 紧贴角点，顶部和左侧应带有黑色 padding。
            expected_icon = ext._crop_with_black_padding(
                frame, 2, 3, crop_size=ext.icon_crop_size,
            )
            # 期望裁剪结果的顶部行和左侧列必须分别为纯黑。
            # 使用与切片同形状的零数组才能正确通过 np.array_equal 形状比对。
            self.assertTrue(
                np.array_equal(expected_icon[0, :], np.zeros_like(expected_icon[0, :])),
                "expected crop's top row must be pure black (out-of-frame padding)",
            )
            self.assertTrue(
                np.array_equal(expected_icon[:, 0], np.zeros_like(expected_icon[:, 0])),
                "expected crop's left column must be pure black (out-of-frame padding)",
            )
            # 加载出的 PNG 必须与计算得到的期望图标逐像素一致。
            self.assertTrue(
                np.array_equal(icon, expected_icon),
                "edge-click icon PNG must match _crop_with_black_padding output exactly",
            )

            # 帧内区域（例如图标中心）应为非零图案化像素 —— 确认不全黑，
            # 且采样的内部像素与图案化帧在该位置的取值一致。
            half = ext.icon_crop_size // 2
            center = icon[half, half]
            self.assertFalse(
                np.array_equal(center, np.zeros(3, dtype=np.uint8)),
                "center of icon should be non-zero (in-frame patterned source)",
            )
            # 点击 (2, 3) 且 icon_crop_size=ext.icon_crop_size，half=ext.icon_crop_size // 2，
            # 因此图标中心对应帧像素 (2, 3)，按构造规则为 (b=2, g=3, r=5)。
            self.assertTrue(
                np.array_equal(center, np.array([2, 3, 5], dtype=np.uint8)),
                f"icon center must equal frame[3,2]=(2,3,5) BGR; got {center.tolist()}",
            )

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


class RequestComponentLabelsTest(unittest.TestCase):
    FILENAME = "record_memory_icon_10.854s_crop.png"

    def _records(self):
        return [
            IconRecord(
                filename=self.FILENAME,
                action="LClick at",
                coords=(820, 450),
                current_software="Explorer",
                base="10.854s",
            ),
        ]

    def _setup_icon(self, screenshots_dir):
        """Create one valid PNG at <screenshots_dir>/icons/<FILENAME> so the
        production code's open() call doesn't raise FileNotFoundError."""
        (screenshots_dir / "icons").mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(".png", np.zeros((4, 4, 3), dtype=np.uint8))
        self.assertTrue(ok)
        (screenshots_dir / "icons" / self.FILENAME).write_bytes(bytes(buf))

    def _mock_response(self, content):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={
            "choices": [{"message": {"content": content}}]
        })
        return resp

    def test_returns_label_map_on_success(self):
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_VERIFY_SSL": "true",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                with patch("requests.post", return_value=self._mock_response(
                    f'{{"{self.FILENAME}": "taskbar_search"}}'
                )) as p:
                    ext = VideoScreenshotExtractor()
                    labels = ext._request_component_labels(self._records(), screenshots_dir)

        self.assertEqual(labels, {self.FILENAME: "taskbar_search"})
        called_args, called_kwargs = p.call_args
        self.assertIn("/chat/completions", called_args[0])
        self.assertEqual(called_kwargs["json"]["model"], "gpt-4o")
        self.assertEqual(called_kwargs["timeout"], 120)
        msgs = called_kwargs["json"]["messages"]
        self.assertEqual(len(msgs), 2)
        # The user message carries the icon metadata + inline images.
        content = msgs[1]["content"]
        self.assertTrue(any(
            c.get("type") == "text" and "taskbar_search" not in c.get("text", "")
            for c in content
        ), "content must include text metadata (without the LLM-provided label)")
        self.assertTrue(any(c.get("type") == "image_url" for c in content))

    def test_raises_components_llm_error_on_http_failure(self):
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                resp = MagicMock()
                resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))
                with patch("requests.post", return_value=resp):
                    ext = VideoScreenshotExtractor()
                    with self.assertRaises(ComponentsLLMError):
                        ext._request_component_labels(self._records(), screenshots_dir)

    def test_raises_components_llm_error_on_invalid_json(self):
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                with patch("requests.post", return_value=self._mock_response("not json")):
                    ext = VideoScreenshotExtractor()
                    with self.assertRaises(ComponentsLLMError):
                        ext._request_component_labels(self._records(), screenshots_dir)

    def test_raises_components_llm_error_when_missing_input_filenames(self):
        # LLM returns labels for a different file; missing files = error
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                with patch("requests.post", return_value=self._mock_response(
                    '{"unrelated.png": "foo"}'
                )):
                    ext = VideoScreenshotExtractor()
                    with self.assertRaises(ComponentsLLMError):
                        ext._request_component_labels(self._records(), screenshots_dir)


class LoadComponentsJsonTest(unittest.TestCase):
    def test_returns_empty_when_file_missing(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ext._load_components_json(Path(tmp)), {})

    def test_returns_empty_when_file_corrupt(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "components.json").write_text("{not json")
            self.assertEqual(ext._load_components_json(Path(tmp)), {})

    def test_returns_parsed_dict_when_valid(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "components.json").write_text('{"foo": {"label": "foo"}}')
            self.assertEqual(ext._load_components_json(Path(tmp)), {"foo": {"label": "foo"}})


class ApplyComponentsUpdatesTest(unittest.TestCase):
    def _png_bytes(self):
        ok, buf = cv2.imencode(".png", np.zeros((4, 4, 3), dtype=np.uint8))
        self.assertTrue(ok)
        return bytes(buf)

    def test_copies_pngs_and_writes_json(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src_icons = tmp / "src_icons"
            src_icons.mkdir()
            (src_icons / "icon_a.png").write_bytes(self._png_bytes())
            (src_icons / "icon_b.png").write_bytes(self._png_bytes())
            dest = tmp / "dest"
            dest.mkdir()
            existing = ext._load_components_json(dest)

            # additions: safe_label -> source_filename
            additions = {
                "foo": ("foo", "icon_a.png"),
                "bar": ("bar", "icon_b.png"),
            }
            now_str = "2026-07-23 12:00:00"
            keys_added, keys_updated = ext._apply_components_updates(
                dest, existing, additions, src_icons, now_str,
            )

            self.assertEqual(keys_added, ["foo", "bar"])
            self.assertEqual(keys_updated, [])

            # PNGs were copied with the right names
            self.assertTrue((dest / "components" / "foo.png").exists())
            self.assertTrue((dest / "components" / "bar.png").exists())

            # components.json contains both entries with expected fields
            data = json.loads((dest / "components.json").read_text(encoding="utf-8"))
            self.assertEqual(set(data.keys()), {"foo", "bar"})
            self.assertEqual(data["foo"]["type"], "icon")
            self.assertEqual(data["foo"]["source"], "learn_batch")
            self.assertEqual(data["foo"]["icon_file"], "components/foo.png")
            self.assertEqual(data["foo"]["label"], "foo")
            self.assertEqual(data["foo"]["learned_at"], now_str)
            self.assertEqual(data["foo"]["last_seen"], now_str)
            self.assertEqual(data["foo"]["seen_count"], 1)
            self.assertEqual(data["foo"]["consecutive_misses"], 0)
            self.assertTrue(data["foo"]["base_memory"])

    def test_upsert_preserves_learned_at_and_increments_seen_count(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src_icons = tmp / "src_icons"
            src_icons.mkdir()
            (src_icons / "icon_a.png").write_bytes(self._png_bytes())
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text(json.dumps({
                "foo": {
                    "type": "icon",
                    "source": "learn_batch",
                    "icon_file": "components/foo.png",
                    "label": "foo",
                    "learned_at": "2026-07-23 10:00:00",
                    "last_seen": "2026-07-23 10:00:00",
                    "seen_count": 4,
                    "consecutive_misses": 0,
                    "base_memory": True,
                },
            }))
            existing = ext._load_components_json(dest)
            additions = {"foo": ("foo", "icon_a.png")}
            keys_added, keys_updated = ext._apply_components_updates(
                dest, existing, additions, src_icons, "2026-07-23 12:00:00",
            )
            self.assertEqual(keys_added, [])
            self.assertEqual(keys_updated, ["foo"])
            data = json.loads((dest / "components.json").read_text(encoding="utf-8"))
            self.assertEqual(data["foo"]["learned_at"], "2026-07-23 10:00:00")  # preserved
            self.assertEqual(data["foo"]["last_seen"], "2026-07-23 12:00:00")  # refreshed
            self.assertEqual(data["foo"]["seen_count"], 5)

    def test_runtimeerror_on_unwritable_dest(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src_icons = tmp / "src_icons"
            src_icons.mkdir()
            (src_icons / "icon_a.png").write_bytes(self._png_bytes())
            dest = tmp / "dest_does_not_exist_and_cannot_be_created"
            # Force shutil.copyfile to fail by mocking it
            with patch("screenshot_processor.shutil.copyfile",
                       side_effect=OSError("permission denied")):
                with self.assertRaises(RuntimeError):
                    ext._apply_components_updates(
                        dest, {}, {"foo": ("foo", "icon_a.png")}, src_icons,
                        "2026-07-23 12:00:00",
                    )


class SyncComponentsToDestTest(unittest.TestCase):
    def _png_bytes(self):
        ok, buf = cv2.imencode(".png", np.zeros((4, 4, 3), dtype=np.uint8))
        self.assertTrue(ok)
        return bytes(buf)

    def _setup(self, root):
        """Create a screenshots_dir with one icon and matching action."""
        screenshots_dir = root / "screenshots"
        icons = screenshots_dir / "icons"
        icons.mkdir(parents=True)
        (icons / "record_memory_icon_10.854s_crop.png").write_bytes(self._png_bytes())
        action = {
            "timestamp": 10.954,
            "action": "LClick at",
            "coords": [{"x": 820, "y": 450}],
            "current_software": "Explorer",
            "screenshot_full": "screenshots/10.854s.jpg",
            "screenshot_crop": "screenshots/10.854s.crop.jpg",
        }
        return screenshots_dir, [action]

    def test_returns_meta_with_keys_added_on_success(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            screenshots_dir, actions = self._setup(tmp)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.object(
                ext, "_request_component_labels",
                return_value={"record_memory_icon_10.854s_crop.png": "Taskbar Search"},
            ):
                meta = ext._sync_components_to_dest(actions, screenshots_dir, dest)

            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_dest"], str(dest))
            self.assertEqual(meta["components_keys_added"], ["taskbar_search"])
            self.assertEqual(meta["components_keys_updated"], [])
            self.assertEqual(meta["components_fallback_to_timestamp"], False)

            # dest/components/taskbar_search.png exists, components.json contains the entry
            self.assertTrue((dest / "components" / "taskbar_search.png").exists())
            data = json.loads((dest / "components.json").read_text(encoding="utf-8"))
            self.assertIn("taskbar_search", data)
            self.assertEqual(data["taskbar_search"]["label"], "taskbar_search")
            self.assertEqual(data["taskbar_search"]["icon_file"], "components/taskbar_search.png")

    def test_falls_back_to_timestamp_keys_when_llm_raises(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            screenshots_dir, actions = self._setup(tmp)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.object(
                ext, "_request_component_labels",
                side_effect=ComponentsLLMError("network fail"),
            ):
                meta = ext._sync_components_to_dest(actions, screenshots_dir, dest)

            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_fallback_to_timestamp"], True)
            self.assertEqual(meta["components_keys_added"], ["record_memory_icon_10_854s_crop"])
            # PNG was copied under the timestamp-key name
            self.assertTrue(
                (dest / "components" / "record_memory_icon_10_854s_crop.png").exists()
            )

    def test_skips_non_default_click_actions(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            screenshots_dir = tmp / "screenshots"
            icons = screenshots_dir / "icons"
            icons.mkdir(parents=True)
            # No icon files at all -> sync has nothing to do
            actions = [
                {"timestamp": 10.954, "action": "LClick at",
                 "coords": [{"x": 1, "y": 1}], "current_software": "X"},
                {"timestamp": 11.0, "action": "Wheel at",
                 "coords": [{"x": 1, "y": 1}], "current_software": "X"},
                {"timestamp": 12.0, "action": "DragStart at",
                 "coords": [{"x": 1, "y": 1}], "current_software": "X",
                 "path": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]},
                {"timestamp": 13.0, "action": "CONFIG", "coords": {}},
                {"timestamp": 14.0, "action": "Active Window: Foo",
                 "coords": [{"x": 0, "y": 0}]},
            ]
            dest = tmp / "dest"
            dest.mkdir()

            # LLM should never be called because there are no icons.
            with patch.object(ext, "_request_component_labels") as mock_llm:
                meta = ext._sync_components_to_dest(actions, screenshots_dir, dest)

            mock_llm.assert_not_called()
            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_keys_added"], [])
            self.assertEqual(meta["components_keys_updated"], [])


class ProcessProjectSyncTest(unittest.TestCase):
    """End-to-end: process_project() reads env var and triggers sync."""

    def _write_project(self, project_dir):
        """Create a minimal project with CONFIG + 2 LClick actions."""
        (project_dir / "inputs").mkdir(parents=True)
        # Empty mp4 is fine for this test — _get_frame_at will be mocked.
        (project_dir / "inputs" / "demo.mp4").write_bytes(b"")
        actions = [
            {"action": "CONFIG", "coords": {"0": {"width": 1920, "height": 1080, "scale_factor": 1.0}}},
            {"timestamp": 10.954, "action": "LClick at",
             "coords": [{"x": 820, "y": 450}], "current_software": "Explorer"},
            {"timestamp": 11.054, "action": "Wheel at",
             "coords": [{"x": 500, "y": 500}], "current_software": "Explorer"},
        ]
        (project_dir / f"{project_dir.name}_processed_log.json").write_text(
            json.dumps(actions), encoding="utf-8"
        )

    def test_env_var_unset_skips_sync_and_meta_has_synced_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            self._write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.dict(os.environ, {"GUI_AGENT_COMPONENTS_DEST": ""}, clear=False):
                # Sanity: confirm env var is empty in this test scope
                self.assertEqual(os.environ.get("GUI_AGENT_COMPONENTS_DEST", "").strip(), "")
                ext = VideoScreenshotExtractor()
                # Mock _get_frame_at to skip video decode
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch.object(ext, "_sync_components_to_dest") as mock_sync:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_sync.assert_not_called()
            self.assertEqual(meta["components_synced"], False)
            self.assertIsNone(meta["components_dest"])
            self.assertEqual(meta["components_keys_added"], [])
            self.assertEqual(meta["components_keys_updated"], [])

    def test_env_var_set_triggers_sync_and_meta_is_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            self._write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()

            sync_return = {
                "components_synced": True,
                "components_dest": str(dest),
                "components_keys_added": ["taskbar_search"],
                "components_keys_updated": [],
                "components_fallback_to_timestamp": False,
            }

            with patch.dict(os.environ,
                            {"GUI_AGENT_COMPONENTS_DEST": str(dest)}, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch.object(ext, "_sync_components_to_dest",
                                      return_value=sync_return) as mock_sync:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_sync.assert_called_once()
            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_dest"], str(dest))
            self.assertEqual(meta["components_keys_added"], ["taskbar_search"])
            self.assertEqual(meta["components_fallback_to_timestamp"], False)
            # Pre-existing meta fields still present
            self.assertIn("video_file", meta)
            self.assertIn("saved_log_sc", meta)


if __name__ == "__main__":
    unittest.main()