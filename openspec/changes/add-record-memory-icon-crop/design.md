## Context

`record/Aloha_Learn/screenshot_processor.py` 的 `VideoScreenshotExtractor.process_actions()` 在默认点击分支（行 184-213）目前的执行顺序是：

1. 取以点击坐标为中心、带黑边填充的 256×256 crop（`_crop_with_black_padding`）；
2. 在该 crop 上绘制白色描边 + 半透明红色 X；
3. 与原 crop 50% 混合后保存为 `{base}.crop.jpg`；
4. 同时保存全帧 `{base}.jpg`。

用户希望**新增**一张 30×30 的原始裁剪（无任何标注）保存到 `screenshots/icons/`，文件名以 `record_memory_icon_{base}_crop.png` 形式与既有产物同源，便于下游记忆层直接引用。

## Goals / Non-Goals

**Goals:**

- 在不破坏既有 256×256 + 红 X 行为的前提下，为每个默认点击额外落盘一张 30×30 原始 PNG。
- 文件命名与既有产物同源（共享 `base = "{timestamp:.3f}s"`）。
- 落盘位置独立（`screenshots/icons/`），便于命名空间隔离。
- `__init__` 新增参数对既有调用完全向后兼容。

**Non-Goals:**

- 不修改 `{project}_processed_log_sc.json` 的 schema。
- 不在 `DragStart`、无坐标分支、`CONFIG` / `Active Window` 跳过项上产出 icon。
- 不调整现有 256×256 crop 的尺寸、红 X 风格或文件命名。
- 不为 icon 引入尺寸自适应、超分、压缩参数调优等扩展。

## Decisions

### 决策 1：在 `__init__` 末尾追加 `icon_crop_size=30`

```python
def __init__(
    self,
    target_width=1920,
    target_height=1080,
    jpeg_quality=95,
    crop_size=256,
    x_size=30,
    x_thick=6,
    icon_crop_size=30,
):
    ...
    self.icon_crop_size = icon_crop_size
```

**理由：** 末尾追加 + 默认值是 Python 中严格向后兼容的写法。仓库现有两处 `VideoScreenshotExtractor()` 调用点（`screenshot_processor.py:358`、`parser.py:67`）均不传参，未来若有调用方显式传前 6 个参数，新增参数依旧走默认值。

**备选：** 在 `__init__` 中部插入。已被否决——会破坏所有以位置参数调用前 6 个参数的潜在调用方，与仓库现有约定也不一致。

### 决策 2：新增 `_save_png` 镜像 `_save_jpg`

```python
def _save_png(self, path, img):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return cv2.imwrite(path, img)
```

**理由：** PNG 无损，无需 `jpeg_quality` 参数；保持与 `_save_jpg` 相同的 `os.makedirs` 行为（自动建目录）。

### 决策 3：插入点位于默认点击分支 `crop_img = _crop_with_black_padding(...)` 之后、X 绘制之前

```python
# === Default handling (pad crop first, then draw centered semi-transparent X) ===
if pt is None:
    raise ValueError(...)
draw_frame = frame.copy()

# 1) Crop around click with black padding (keeps center fixed, no shifting)
cx_raw, cy_raw = pt
crop_img = self._crop_with_black_padding(draw_frame, cx_raw, cy_raw, crop_size=self.crop_size)

# 1.5) Save small original click crop (no X marker) as PNG for icon memory
icon_crop = self._crop_with_black_padding(
    draw_frame, cx_raw, cy_raw, crop_size=self.icon_crop_size
)
icon_fn = f"record_memory_icon_{base}_crop.png"
icon_path = screenshots_path / "icons" / icon_fn
icon_ok = self._save_png(str(icon_path), icon_crop)
if not icon_ok:
    raise RuntimeError(
        f"Could not save icon crop for action at {timestamp}s: {act_str}"
    )

# 2) Draw semi-transparent X AFTER padding so it's fully visible
...
```

**理由：**

- `draw_frame` 是 `frame.copy()` 的纯净副本（X 尚未绘制），从它裁出 30×30 即可保证 PNG 不带任何标注。
- 直接复用 `_crop_with_black_padding` 而不是把 256×256 crop 再 resize 到 30×30：
  - resize 会经过 256×256 这一中间尺寸，引入额外的插值模糊。
  - resize 不会改变中心像素的"邻域定义"——30×30 crop 应当以原始帧的点击坐标为中心的 15 像素邻域，而非 256×256 crop 中心附近已经过黑边填充的 25 像素邻域。
- 落盘失败立即抛错，与既有 `full_ok` / `crop_ok` 失败语义一致。
- `base` 在循环顶部（第 133 行）已经计算好，新代码可以直接复用。

### 决策 4：JSON schema 保持不变

`{project}_processed_log_sc.json` 中每个动作的 `screenshot_full` / `screenshot_crop` 字段保持不变；icon 文件不通过新字段登记。

**理由：** 本变更刻意保持"仅落盘、prefix 自带语义"的边界。下游若需要按时间戳反查 icon，可通过 `record_memory_icon_{base}_crop.png` 的命名约定直接构造路径，无需 JSON 介入；这也避免了 JSON schema 变更对 `trace_generator.py` 的潜在冲击。

### 决策 5：仅默认点击分支产出 icon

`DragStart at`（行 149-180）、无坐标动作（`scroll` / `wheel` / `hotkey` / `type` / `press`，行 181-183）、`CONFIG` / `Active Window` 跳过项（第 123 行）均不产出 icon。

**理由：** 用户原话"原始的点击的 crop 图片"明确指向"点击"语义。拖拽本质上是按下+移动+松开，不属于简单点击；无坐标动作没有可裁剪的"点击点"。

## Risks / Trade-offs

- **磁盘增长**：30×30 PNG 通常 < 1 KB；1000 次点击 < 1 MB，可接受。
- **I/O 开销**：每次点击多一次 `cv2.imwrite`，与既有两次写入同量级，无显著性能差异。
- **重复裁剪**：默认分支对同一 `(cx_raw, cy_raw)` 调用两次 `_crop_with_black_padding`，一次 256、一次 30。可接受的代价是代码更直白；若未来有性能诉求，可改为单次裁 256 后 resize 30，但会引入前述插值差异。
- **错误传播**：若 `screenshots/icons/` 不可写，会抛 `RuntimeError` 中止整个 `process_actions()`。这与既有 `full_ok` / `crop_ok` 失败一致；下游若希望"icon 失败不影响其余产物"，需要在调用层包 try/except（当前不变更）。

## Migration Plan

本变更为纯增量、无破坏性变更，无需迁移步骤：

1. 部署后既有项目再次走 `process_actions()` 时，会在 `screenshots/icons/` 下产生新文件，旧文件不受影响。
2. 已存在的 `{project}_processed_log_sc.json` 不需重新生成；下游消费者若想引用 icon，可按 `record_memory_icon_<base>_crop.png` 命名约定直接构造路径（其中 `base` 与同目录 `{base}.jpg` / `{base}.crop.jpg` 一致）。
3. 回滚方式：删除新增的 `__init__` 参数与默认点击分支中的 icon 段；现有产物文件可保留或清理（不会影响其他文件加载）。

## Open Questions

无。命名、位置、大小默认值、JSON schema 不变性均已与用户确认。