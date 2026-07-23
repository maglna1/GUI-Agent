## Why

录制流程已经为每次带坐标的点击产出全帧图和带红色 X 标记的 256×256 crop，但下游"记忆层"若想用一个微小的视觉单元直接索引每次点击，目前不得不解码体积相对较大的带标记 crop。本变更新增一张未经任何图形叠加的 30×30 PNG 缩略图，与既有 `{ts}.jpg`、`{ts}.crop.jpg` 同源时间戳、放置于独立子目录，让下游可以直接按路径索引到原始的点击局部画面。

## What Changes

- `VideoScreenshotExtractor` 暴露新增的 `icon_crop_size` 构造参数（默认 `30`），调用方可按需调整。
- 在 `process_actions()` 的默认点击分支中，于 256×256 黑边填充裁剪完成之后、绘制半透明红色 X 标记之前，新增一次 30×30 原始裁剪并以 PNG 落盘到 `screenshots/icons/record_memory_icon_{base}_crop.png`。
- icon 复用 `_crop_with_black_padding` 的边缘黑边填充语义，保证边缘点击仍能产出完整 30×30 图像。
- icon 文件名采用现有 `base = "{timestamp:.3f}s"`，与 `{ts}.jpg`、`{ts}.crop.jpg` 严格同源。
- icon 文件**不**写入 `{project}_processed_log_sc.json`，现有 `screenshot_full` / `screenshot_crop` JSON schema 保持不变。
- 既有调用点（`screenshot_processor.py:358` CLI 入口、`parser.py:67` 流水线入口）以 `VideoScreenshotExtractor()` 形式实例化，无需修改即可继续工作。

无破坏性变更。

## Capabilities

### New Capabilities

- `record-click-icon-crop`：定义 record 流程为每个默认点击产出一张 30×30 原始 PNG icon 的契约，包括落盘位置、命名规则、内容约束与 JSON schema 不变性的明确要求。

### Modified Capabilities

无。`trace-to-midscene-flow` 当前 spec 未枚举截图产物具体形态，JSON schema 与下游契约均不发生 spec 级别变更。

## Impact

- 代码：仅 `record/Aloha_Learn/screenshot_processor.py` 发生修改。
- 调用点：`screenshot_processor.py:358`、`parser.py:67` 的两处 `VideoScreenshotExtractor()` 实例化保持兼容（参数末尾追加、默认值、位置参数与关键字参数均不受影响）。
- 产物：`{project_dir}/screenshots/icons/record_memory_icon_*.png` 文件出现在既有 `screenshots/*.jpg` 旁。
- 测试：仓库内 `record/Aloha_Learn/tests/` 无 `VideoScreenshotExtractor` 的实例化或方法调用，无测试影响。
- 下游：`trace_generator.py` 等下游消费者不读取 icon 文件（本变更刻意如此）。