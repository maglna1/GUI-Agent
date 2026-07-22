# Record Click Icon Crop 实施计划

> **面向智能体执行者：** 必选子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务执行本计划。步骤使用 checkbox（`- [ ]`）语法进行追踪。

**目标（Goal）：** 在录制流程中，为每次点击额外落盘一张 50×50 的原始 PNG icon 缩略图，作为既有截图产物的同级补充；保持构造器向后兼容、JSON schema 不变。

**架构（Architecture）：** 扩展 `VideoScreenshotExtractor`，新增可选的 `icon_crop_size` 构造参数（默认 50）以及 `_save_png` 辅助方法。在 `process_actions()` 的默认点击分支中，于既有 256×256 黑边填充裁剪完成之后、绘制红色 X 之前，使用未修改的 `draw_frame` 重新裁出 `icon_crop_size × icon_crop_size` 的小图，写入 `screenshots/icons/record_memory_icon_{base}_crop.png`。icon 文件名复用现有 `base = "{timestamp:.3f}s"` 字符串，与 `{base}.jpg` / `{base}.crop.jpg` 同源。JSON schema 与其他分支保持原样。

**技术栈（Tech Stack）：** Python 3、OpenCV（`cv2`）、`unittest`（与仓库既有测试风格一致）。

## 全局约束（Global Constraints）

逐字摘自 `openspec/changes/add-record-memory-icon-crop/specs/record-click-icon-crop/spec.md`：

- 新增构造参数：`icon_crop_size`（默认 `50`），追加在 `__init__` 参数列表**末尾**，位于 `x_thick=6` 之后。
- 新增辅助方法：`_save_png(self, path, img)`，与 `_save_jpg` 行为一致但不带 JPEG 质量参数（PNG 无损）。
- 插入位置：`process_actions()` 默认点击分支（行 184 起的 `else:` 块）中，位于 `crop_img = self._crop_with_black_padding(...)`（行 192）**之后**、红色 X 绘制块（行 193+）**之前**。
- 文件命名：`record_memory_icon_{base}_crop.png`，其中 `base` 是行 133 既有 `f"{timestamp:.3f}s"` 值（icon 与 `{base}.jpg`、`{base}.crop.jpg` 共享同一时间戳字符串）。
- 保存目录：`{project_dir}/screenshots/icons/`。
- 内容：以点击坐标为中心的原始帧区域；不含任何标注、不含白色描边、不含红色 X。数据源必须是 `draw_frame`（即未被修改的 `frame.copy()`）。
- 边缘填充：与 `_crop_with_black_padding` 完全一致的语义——黑色填充，保证边缘点击仍产出完整 `icon_crop_size × icon_crop_size` 图像。
- 失败处理：icon 写入失败时抛出 `RuntimeError`，消息包含动作时间戳与动作名，并中止 `process_actions()` 剩余动作。
- JSON schema：`processed_log_sc.json` 仅保留 `screenshot_full` 与 `screenshot_crop`；不新增 `screenshot_icon` 等字段。
- 分支覆盖：icon **仅**在默认点击分支产出。`DragStart at`（行 149-180）、无坐标动作（`scroll` / `wheel` / `hotkey` / `type` / `press`，行 181-183）、`CONFIG` 与 `Active Window`（行 123）**均不**产出 icon。
- 向后兼容：`screenshot_processor.py:358` 与 `parser.py:67` 现有的 `VideoScreenshotExtractor()` 零参调用必须继续工作，无须修改。
- 修改的唯一文件：`record/Aloha_Learn/screenshot_processor.py`。新增测试文件：`record/Aloha_Learn/tests/test_screenshot_processor.py`。

---

## 文件结构（File Structure）

| 文件 | 状态 | 职责 |
|---|---|---|
| `record/Aloha_Learn/screenshot_processor.py` | 修改 | 新增 `icon_crop_size` 参数、`_save_png` 辅助方法、默认点击分支中的 icon 落盘段 |
| `record/Aloha_Learn/tests/test_screenshot_processor.py` | 新建 | 构造器向后兼容、`_save_png`、默认点击分支产出 icon 的端到端测试 |

不创建或不修改其他文件。`openspec/changes/add-record-memory-icon-crop/` 下的 artifact 在变更归档前保持不变。

---

## Task 1: 构造器新增向后兼容的 `icon_crop_size` 参数

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py:11-17`（`__init__` 签名与函数体）
- Create: `record/Aloha_Learn/tests/test_screenshot_processor.py`

**Interfaces:**
- Consumes: 无（无前置任务）。
- Produces: `VideoScreenshotExtractor.icon_crop_size: int` 属性，默认 `50`。既有位置参数与关键字参数调用必须保持有效。

- [ ] **Step 1：编写失败的测试文件**

新建 `record/Aloha_Learn/tests/test_screenshot_processor.py`：

```python
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
```

- [ ] **Step 2：运行测试确认失败**

在仓库根目录运行：

```bash
python -m unittest record.Aloha_Learn.tests.test_screenshot_processor -v
```

预期：4 个测试因 `AttributeError: 'VideoScreenshotExtractor' object has no attribute 'icon_crop_size'` 而失败。

- [ ] **Step 3：向 `__init__` 增加参数与赋值**

将 `record/Aloha_Learn/screenshot_processor.py` 第 11-17 行：

```python
    def __init__(self, target_width=1920, target_height=1080, jpeg_quality=95, crop_size=256, x_size=30, x_thick=6):
        self.target_width = target_width
        self.target_height = target_height
        self.jpeg_quality = jpeg_quality
        self.crop_size = crop_size
        self.x_size = x_size
        self.x_thick = x_thick
```

改为：

```python
    def __init__(self, target_width=1920, target_height=1080, jpeg_quality=95, crop_size=256, x_size=30, x_thick=6, icon_crop_size=50):
        self.target_width = target_width
        self.target_height = target_height
        self.jpeg_quality = jpeg_quality
        self.crop_size = crop_size
        self.x_size = x_size
        self.x_thick = x_thick
        self.icon_crop_size = icon_crop_size
```

- [ ] **Step 4：运行测试确认通过**

运行：

```bash
python -m unittest record.Aloha_Learn.tests.test_screenshot_processor -v
```

预期：4 个测试全部通过（`test_zero_arg_constructor_uses_default_icon_crop_size`、`test_explicit_icon_crop_size_kwarg_is_stored`、`test_existing_positional_args_still_work`、`test_existing_kwargs_still_work`）。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(record): add icon_crop_size constructor parameter (default 50)"
```

---

## Task 2: 新增 `_save_png` 辅助方法

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py:58-60` 之后（紧接 `_save_jpg` 插入）
- Modify: `record/Aloha_Learn/tests/test_screenshot_processor.py`（追加新测试类）

**Interfaces:**
- Consumes: 已设置 `self.icon_crop_size` 的 `VideoScreenshotExtractor` 实例。
- Produces: `VideoScreenshotExtractor._save_png(self, path: str, img: numpy.ndarray) -> bool`，行为与 `_save_jpg` 镜像但不带质量参数；返回 `cv2.imwrite` 的结果；按需创建父目录。

- [ ] **Step 1：编写失败的 `_save_png` 测试**

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 追加：

```python
import os
import tempfile

import cv2
import numpy as np


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
```

（新增的 `import os, tempfile, cv2, numpy as np` 应合并到任务 1 已有的导入块中，详见 Step 3。）

- [ ] **Step 2：运行测试确认失败**

运行：

```bash
python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.SavePngHelperTest -v
```

预期：两个新测试因 `AttributeError: 'VideoScreenshotExtractor' object has no attribute '_save_png'` 而失败。

- [ ] **Step 3：新增 `_save_png` 方法**

先合并 `record/Aloha_Learn/tests/test_screenshot_processor.py` 顶部的导入块为：

```python
import os
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from screenshot_processor import VideoScreenshotExtractor
```

（任务 1 已导入 `unittest`、`Path`、`sys`；新增项为 `os`、`tempfile`、`cv2`、`numpy as np`。）

随后在 `record/Aloha_Learn/screenshot_processor.py` 中**紧接** `_save_jpg`（第 60 行之后、`_safe_crop` 第 62 行之前）插入：

```python
    def _save_png(self, path, img):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return cv2.imwrite(path, img)
```

- [ ] **Step 4：运行测试确认通过**

运行：

```bash
python -m unittest record.Aloha_Learn.tests.test_screenshot_processor -v
```

预期：全部 6 个测试通过——任务 1 的 4 个构造器测试 + 任务 2 新增的 2 个 `_save_png` 测试。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(record): add _save_png helper for icon crops"
```

---

## Task 3: 默认点击分支产出 icon PNG

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py`（在 `process_actions` 的 `else:` 块中插入 icon 落盘段）
- Modify: `record/Aloha_Learn/tests/test_screenshot_processor.py`（追加通过 mock `_get_frame_at` 驱动的端到端测试）

**Interfaces:**
- Consumes: 已设置 `icon_crop_size` 的 `VideoScreenshotExtractor`、BGR `frame` 数组、点击坐标 `(cx_raw, cy_raw)`、行 133 既有的 `base` 字符串与 `screenshots_path` Path 对象。
- Produces: 位于 `screenshots_path / "icons" / f"record_memory_icon_{base}_crop.png"` 的 PNG 文件，内容为以点击坐标为中心的 `icon_crop_size × icon_crop_size` 原始裁剪（边缘附近使用黑边填充）。文件写入成功时不得抛错。不修改 JSON 条目 `ua['screenshot_full']` / `ua['screenshot_crop']`。

- [ ] **Step 1：编写失败的端到端测试**

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 追加：

```python
from unittest.mock import patch


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
```

（`from unittest.mock import patch` 与 `from pathlib import Path` 已在任务 1 / 任务 2 的 Step 3 中导入，按需合并。）

- [ ] **Step 2：运行新增测试确认失败**

运行：

```bash
python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.DefaultClickIconSaveTest -v
```

预期：`test_default_click_produces_icon_png_in_icons_subdir` 因尚未写入 PNG 而失败。两条负向断言（`test_drag_action_does_not_produce_icon`、`test_no_coordinate_action_does_not_produce_icon`）目前是空通过（因为根本就没产出 icon）——实现落地后它们应继续保持通过。

- [ ] **Step 3：在默认点击分支插入 icon 落盘段**

在 `record/Aloha_Learn/screenshot_processor.py` 中定位行 190-194（当前为）：

```python
                # 1) Crop around click with black padding (keeps center fixed, no shifting)
                cx_raw, cy_raw = pt
                crop_img = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.crop_size)

                # 2) Draw semi-transparent X AFTER padding so it's fully visible
```

在 `crop_img = ...` 行**之后**、`# 2) Draw semi-transparent X AFTER padding so it's fully visible` 注释**之前**插入：

```python
                # 1.5) Save small original click crop (no X marker) as PNG for icon memory
                icon_crop = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.icon_crop_size)
                icon_fn = f"record_memory_icon_{base}_crop.png"
                icon_path = screenshots_path / "icons" / icon_fn
                icon_ok = self._save_png(str(icon_path), icon_crop)
                if not icon_ok:
                    raise RuntimeError(f"Could not save icon crop for action at {timestamp}s: {act_str}")

```

插入后该块的整体结构为：

```python
                # 1) Crop around click with black padding (keeps center fixed, no shifting)
                cx_raw, cy_raw = pt
                crop_img = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.crop_size)

                # 1.5) Save small original click crop (no X marker) as PNG for icon memory
                icon_crop = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.icon_crop_size)
                icon_fn = f"record_memory_icon_{base}_crop.png"
                icon_path = screenshots_path / "icons" / icon_fn
                icon_ok = self._save_png(str(icon_path), icon_crop)
                if not icon_ok:
                    raise RuntimeError(f"Could not save icon crop for action at {timestamp}s: {act_str}")

                # 2) Draw semi-transparent X AFTER padding so it's fully visible
```

**禁止触碰** `DragStart` 分支（行 149-180）、无坐标分支（行 181-183）、`CONFIG` / `Active Window` 跳过项（行 123）。

- [ ] **Step 4：运行完整测试文件确认全部通过**

运行：

```bash
python -m unittest record.Aloha_Learn.tests.test_screenshot_processor -v
```

预期：9 个测试全部通过（4 个构造器 + 2 个 `_save_png` + 3 个默认点击）。

- [ ] **Step 5：确认既有测试未回归**

运行仓库整套测试，确保没有破坏既有用例：

```bash
python -m unittest discover -s record/Aloha_Learn/tests -v
```

预期：`test_log_processor.py` 与 `test_trace_generator.py` 中的既有测试与新加的 `test_screenshot_processor.py` 一并通过。

- [ ] **Step 6：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(record): save 50x50 click icon PNG to screenshots/icons/"
```

---

## Task 4: 人工端到端验证（可选但建议）

**Files:** 不修改任何文件；消费集成产物的烟雾测试。

本任务是人工烟雾测试而非自动化。设置此任务以便人工或后续子代理可以用真实视频确认新代码路径运转正常。

- [ ] **Step 1：选定或准备样例项目**

在 `record/Aloha_Learn/projects/` 下挑选任一已经具备 `inputs/<name>.mp4` 与 `<name>_processed_log.json` 的项目；若没有，记录"验证延后到样例就绪后"。

- [ ] **Step 2：端到端运行截图抽取**

```bash
python -m record.Aloha_Learn.screenshot_processor <project_name>
```

预期：无异常。输出中 `Screenshots saved in: <shots_dir>` 一行指向既有 `screenshots/` 目录。

- [ ] **Step 3：核对 icon 产物**

```bash
ls <project_dir>/screenshots/icons/ | head
```

预期：每个默认点击动作至少对应一个 `record_memory_icon_<base>_crop.png`。文件名与 `<project_dir>/screenshots/` 下既有 `<base>.jpg`、`<base>.crop.jpg` 共享同一 `<base>` 前缀。

- [ ] **Step 4：抽查一张 icon 的内容**

```bash
python -c "import cv2; img = cv2.imread('<icon_path>', cv2.IMREAD_UNCHANGED); print(img.shape)"
```

预期：`(50, 50, 3)`。可视化打开（如用图片查看器）应确认 icon 是以点击坐标为中心的原始帧区域、无红色 X 标记；边缘点击情况下缺角处应为纯黑。

- [ ] **Step 5：确认 JSON schema 未变**

```bash
python -c "import json; d = json.load(open('<project_dir>/<project>_processed_log_sc.json')); print(sorted(d[0].keys()))"
```

预期：`['coords', 'current_software', 'screenshot_crop', 'screenshot_full', 'timestamp']`（或类似）——不含 `screenshot_icon`。

- [ ] **Step 6：如有验证产物则提交（否则跳过）**

如果临时写了验证脚本或笔记，按需提交；否则跳过本步。

---

## 自检（Self-Review）

**1. Spec 覆盖：**

- ✅ 默认点击产物附带 50×50 PNG → 任务 3。
- ✅ 文件名 `record_memory_icon_{base}_crop.png` 与 `{base}.jpg` 共用 `base` → 任务 3（Step 3 代码使用 `f"record_memory_icon_{base}_crop.png"`）。
- ✅ 保存目录 `screenshots/icons/` → 任务 3（`screenshots_path / "icons" / icon_fn`）。
- ✅ 边缘点击仍产出完整 icon 图 → 通过复用 `_crop_with_black_padding` 覆盖；任务 4 Step 4 的可视化抽检作为视觉确认。
- ✅ 父目录自动创建 → 任务 2（`_save_png` 中的 `os.makedirs(..., exist_ok=True)`）。
- ✅ `icon_crop_size` 可配置 + 向后兼容 → 任务 1（构造器测试）+ 任务 3（集成消费 `self.icon_crop_size`）。
- ✅ icon 写入失败抛 `RuntimeError` → 任务 3（Step 3 代码：`if not icon_ok: raise RuntimeError(...)`）。
- ✅ JSON schema 未变 → 任务 3（`test_default_click_produces_icon_png_in_icons_subdir` 断言 `screenshot_icon` 不存在）。
- ✅ Drag / 无坐标 / CONFIG / Active Window 不产出 icon → 任务 3（`test_drag_action_does_not_produce_icon`、`test_no_coordinate_action_does_not_produce_icon`）。

**2. 占位符扫描：**

- 没有"TBD"、"TODO"、"implement later"、"fill in details"。
- 没有"add appropriate error handling"之类没有代码的占位——`RuntimeError` 消息具体明确。
- 没有"write tests for the above"——每个测试类都给出具体测试代码。
- 没有"similar to Task N"——每个代码块都自包含。
- 所有路径均为绝对路径。
- 所有命令均给出预期输出。

**3. 类型一致性：**

- `VideoScreenshotExtractor.icon_crop_size` 在任务 1 定义为 `int`（默认 `50`），在任务 3 通过 `self.icon_crop_size` 作为 `int` 消费。
- `_save_png(self, path: str, img: numpy.ndarray) -> bool` 签名在任务 2 与任务 3 中保持一致。
- `screenshots_path / "icons"` 的 Path 算术在生产代码（任务 3）与测试代码中一致使用。
- `base` 在生产代码（既有文件行 133）与集成测试期望值（`expected_base = f"{expected_ts:.3f}s"`）中为同一变量。

未发现不一致。