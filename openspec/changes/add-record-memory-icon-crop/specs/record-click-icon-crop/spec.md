## ADDED Requirements

### Requirement: 默认点击产物附带原始 30×30 PNG

在 `VideoScreenshotExtractor.process_actions()` 的默认点击处理分支中，系统 SHALL 在围绕点击坐标完成 256×256 黑边填充裁剪之后、绘制半透明白边与红色 X 标记之前，再以同样的点击坐标为中心生成一张 `icon_crop_size` 大小的原始裁剪并以 PNG 格式落盘。

#### Scenario: 普通点击记录落盘 icon
- **WHEN** 一个动作包含坐标、不属于 `DragStart at` 且 `path` 长度 < 2、不属于 `scroll` / `wheel` / `hotkey` / `type` / `press` 系列
- **THEN** 系统 SHALL 在 `{project_dir}/screenshots/icons/` 下写入 `record_memory_icon_{base}_crop.png`
- **AND** 该 PNG SHALL 来自未经任何图形叠加的原始帧（即绘制红色 X 之前的 `draw_frame`）
- **AND** 该 PNG SHALL 不包含白色描边、红色 X 标记或任何其他标注

#### Scenario: 时间戳与既有产物同源
- **WHEN** 系统为某动作生成 icon 文件名
- **THEN** `{base}` SHALL 与该动作的 `{base}.jpg` 和 `{base}.crop.jpg` 使用完全相同的时间戳字符串（即 `f"{timestamp:.3f}s"`，其中 `timestamp = abs(action.timestamp - 0.1)`）
- **AND** 文件名 SHALL 形如 `record_memory_icon_10.854s_crop.png`

#### Scenario: 边缘点击仍产生完整 icon 图像
- **WHEN** 点击坐标距离帧边缘不足 `icon_crop_size / 2` 像素
- **THEN** icon SHALL 仍为完整 `icon_crop_size × icon_crop_size` 图像
- **AND** 缺失区域 SHALL 使用与 256×256 crop 一致的黑色填充

#### Scenario: 子目录自动创建
- **WHEN** `{project_dir}/screenshots/icons/` 目录尚不存在
- **THEN** 系统 SHALL 在写入 icon PNG 之前自动创建该目录

### Requirement: icon_crop_size 可配置且向后兼容

`VideoScreenshotExtractor.__init__` SHALL 接受新增的 `icon_crop_size` 关键字参数，默认值为 `30`；既有调用形式 SHALL 继续合法而不抛错。

#### Scenario: 默认实例化保持兼容
- **WHEN** 调用方执行 `VideoScreenshotExtractor()` 不传任何参数
- **THEN** 系统 SHALL 使用 `icon_crop_size=30` 默认值
- **AND** SHALL NOT 抛出 `TypeError`

#### Scenario: 自定义 icon 尺寸
- **WHEN** 调用方传入 `icon_crop_size=N`（N 为正偶数）
- **THEN** icon 输出图像 SHALL 为 `N × N`
- **AND** 边缘黑色填充 SHALL 同步生效以保证完整尺寸

#### Scenario: 已有的位置参数调用保持兼容
- **WHEN** 调用方以位置参数形式传入前 6 个参数（例如 `VideoScreenshotExtractor(1920, 1080, 95, 256, 30, 6)`）
- **THEN** 系统 SHALL NOT 抛出 `TypeError`
- **AND** `icon_crop_size` SHALL 取默认值 `30`

### Requirement: icon 落盘失败应中止流程

icon PNG 写入失败 SHALL 与既有 `screenshot_full` / `screenshot_crop` 写入失败语义一致——抛出 `RuntimeError` 并中止 `process_actions()`。

#### Scenario: 目录不可写时抛错
- **WHEN** `{project_dir}/screenshots/icons/` 目录无法创建或写入
- **THEN** 系统 SHALL 抛出 `RuntimeError`，消息中包含当前动作的时间戳与动作名
- **AND** 后续动作 SHALL NOT 被处理
- **AND** 该动作的 `screenshot_full` / `screenshot_crop` SHALL NOT 被写入 JSON

### Requirement: JSON schema 保持不变

`{project}_processed_log_sc.json` 中每个动作的 `screenshot_full` / `screenshot_crop` 字段 SHALL 保持不变；icon 文件 SHALL NOT 以新字段形式出现在该 JSON 中。

#### Scenario: 不新增 JSON 字段
- **WHEN** 系统为某默认点击动作产出 icon PNG
- **THEN** `processed_log_sc.json` 中该动作 SHALL 仅包含原有的 `screenshot_full` 与 `screenshot_crop` 两个字段
- **AND** SHALL NOT 出现 `screenshot_icon` 或任何其他新增键

#### Scenario: 下游消费者无须变更
- **WHEN** `trace_generator.py` 等下游消费者读取 `processed_log_sc.json`
- **THEN** 它们 SHALL 继续按既有 `screenshot_full` / `screenshot_crop` 字段工作
- **AND** SHALL NOT 被要求识别 icon 文件路径

### Requirement: 仅默认点击分支产出 icon

`DragStart at` 分支、无坐标动作分支、`CONFIG` 与 `Active Window` 跳过项 SHALL NOT 生成 icon 文件。

#### Scenario: 拖拽动作无 icon
- **WHEN** 动作以 `DragStart at` 开头且 `path` 长度 ≥ 2
- **THEN** `{project_dir}/screenshots/icons/` 下 SHALL NOT 出现该动作对应的 `record_memory_icon_*.png`

#### Scenario: 键盘与滚动动作无 icon
- **WHEN** 动作文本包含 `scroll` / `wheel` / `hotkey` / `type` / `press`
- **THEN** 系统 SHALL NOT 在 `screenshots/icons/` 下生成 icon

#### Scenario: CONFIG 与 Active Window 无 icon
- **WHEN** 动作为 `CONFIG` 或以 `Active Window` 开头
- **THEN** 系统 SHALL NOT 生成 icon
- **AND** SHALL NOT 调用 `_save_png`