## ADDED Requirements

### Requirement: 默认同步触发条件

`VideoScreenshotExtractor.process_project()` 在末尾 SHALL 检查环境变量 `GUI_AGENT_COMPONENTS_DEST`：

- 未设置或值为空字符串 → 跳过同步；`meta["components_synced"] = False`。
- 非空字符串 → 末尾执行同步；`meta["components_synced"] = True`、`meta["components_dest"] = dest`。

#### Scenario: 环境变量未设置
- **WHEN** `GUI_AGENT_COMPONENTS_DEST` 未设置或为空字符串
- **THEN** 系统 SHALL 不调用 LLM、不创建 `dest/components/`、不修改 `dest/components.json`
- **AND** `process_project()` SHALL 仍正常完成既有流程
- **AND** `meta["components_synced"]` SHALL 为 `False`

#### Scenario: 环境变量非空
- **WHEN** `GUI_AGENT_COMPONENTS_DEST` 指向一个可写目录
- **THEN** 系统 SHALL 在该轮所有 default-click icon 写入完成后触发同步
- **AND** `meta["components_dest"]` SHALL 等于该目录的绝对或 env 字面值

### Requirement: 同步范围与现有 icon 写入一致

同步 SHALL 仅覆盖当前 run 产出的 default-click icon（即 `screenshots/icons/record_memory_icon_*.png`）；`DragStart at` 分支、无坐标动作（`scroll` / `wheel` / `hotkey` / `type` / `press`）、`CONFIG` 与 `Active Window` 跳过项 SHALL NOT 产生 dest 端条目。

#### Scenario: 仅 default-click 写入 dest
- **WHEN** 一轮 record 包含 default-click、`DragStart`、scroll、Press、`CONFIG`、Active Window 等多类动作
- **THEN** dest 端 `components.json` SHALL 仅包含 default-click 动作对应的条目
- **AND** dest 端 `components/<label>.png` SHALL 仅含 default-click 动作对应的图片

### Requirement: LLM 实时命名内容标签

每轮 record 末了，系统 SHALL 调用一次视觉模型（复用 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL` 与 `trace_generator.py` 同源），传入该轮全部 icon + 元数据（action / coords / current_software / timestamp），要求返回 `{filename: snake_case_label}` JSON object。

#### Scenario: LLM 返回合法 JSON
- **WHEN** LLM 调用成功且返回 JSON object，键集 ⊆ 输入文件名集合
- **THEN** 系统 SHALL 按返回的 `filename → label` 映射生成 dest 端条目
- **AND** 每个 label SHALL 通过 `sanitize_label` 规范化（snake_case、字符集 `[a-z0-9_]`、最长 30 字符）

#### Scenario: LLM 返回缺键
- **WHEN** LLM 返回的 JSON 缺少某些输入文件名
- **THEN** 系统 SHALL 对缺失键的 icon 走 timestamp 键同步（键名 = `record_memory_icon_<sanitized_base>_crop`）
- **AND** 其余 icon SHALL 按 LLM 返回的 label 正常同步
- **AND** `meta["components_fallback_to_timestamp"]` SHALL 为 `True`

#### Scenario: LLM 返回含未知键
- **WHEN** LLM 返回的 JSON 包含输入集合中不存在的文件名
- **THEN** 系统 SHALL 忽略未知键并继续同步已知键
- **AND** SHALL 输出警告日志说明哪些键被忽略

### Requirement: LLM 失败回退到时间戳键

LLM 调用任何异常（网络错 / 4xx 5xx / 超时 / JSON 解析失败 / schema 不符）SHALL 被捕获并视为整批失败。

#### Scenario: 网络或服务异常
- **WHEN** LLM 调用抛 `requests.RequestException` / HTTP 4xx 5xx / 超时 / 任何网络层异常
- **THEN** 系统 SHALL 不抛错给 `process_project()` 调用方
- **AND** SHALL 将该 batch 全部 icon 改用 timestamp 键同步
- **AND** `meta["components_fallback_to_timestamp"]` SHALL 为 `True`

#### Scenario: JSON 解析失败
- **WHEN** LLM 返回非 JSON 或 JSON 结构不符（不是 object）
- **THEN** 系统 SHALL 走与网络异常相同的回退路径
- **AND** SHALL 输出警告日志说明解析失败

### Requirement: 标签去重与规范化

同 batch 内若 LLM 返回的 label 经过 `sanitize_label` 后仍重复（两个或以上 icon 拿到同一 safe label），系统 SHALL 加 `_2` / `_3` ... 后缀确保每个 dest 端 key 唯一。

#### Scenario: 同一批 LLM 返回重复 label
- **WHEN** LLM 返回 `{"a.png": "foo", "b.png": "foo"}`
- **THEN** dest 端 `components.json` SHALL 含 `"foo"` 与 `"foo_2"` 两个 key
- **AND** `components/foo.png` 与 `components/foo_2.png` SHALL 分别对应两张原图

### Requirement: components.json upsert 语义

`dest/components.json` 写入 SHALL 采用 upsert：

- 写入（key 不存在）：`learned_at = last_seen = now`、`seen_count = 1`、`consecutive_misses = 0`、`base_memory = true`。
- 更新（key 已存在）：保留 `learned_at`、`last_seen = now`、`seen_count += 1`、`consecutive_misses = 0`、`base_memory = true`。

#### Scenario: 新 key
- **WHEN** LLM 返回的新 label 在 `dest/components.json` 中不存在
- **THEN** 系统 SHALL 新增一条 entry，`learned_at` 与 `last_seen` SHALL 等于 `now`，`seen_count` SHALL 为 1
- **AND** 该 entry SHALL 含 `base_memory: true`、`source: "learn_batch"`、`type: "icon"`

#### Scenario: 既有 key 重复出现
- **WHEN** LLM 返回的 label 在 `dest/components.json` 中已存在（先前轮次已写入）
- **THEN** 系统 SHALL 保留原 `learned_at`，刷新 `last_seen = now`
- **AND** `seen_count` SHALL 累加 1，`consecutive_misses` SHALL 重置为 0
- **AND** `meta["components_keys_updated"]` SHALL 包含该 key

### Requirement: dest 端 schema 与 harness 既有 entry 对齐

`dest/components.json` 中每个由 record 同步产生的 entry SHALL 严格遵循 harness 现有 17 条 desktop 组件的 schema：

```json
{
  "type": "icon",
  "source": "learn_batch",
  "icon_file": "components/<label>.png",
  "label": "<label>",
  "learned_at": "YYYY-MM-DD HH:MM:SS",
  "last_seen": "YYYY-MM-DD HH:MM:SS",
  "seen_count": <int>,
  "consecutive_misses": 0,
  "base_memory": true
}
```

#### Scenario: 字段必须完整
- **WHEN** 系统为某 icon 写入 dest 端 entry
- **THEN** 该 entry SHALL 包含上述全部字段，类型与值符合 schema
- **AND** `icon_file` 路径 SHALL 以 `components/` 开头、以 `.png` 结尾
- **AND** `label` SHALL 等于 `icon_file` 的 basename（不含 `.png`）

#### Scenario: base_memory 一律为 true
- **WHEN** 系统写入新 entry 或更新既有 entry
- **THEN** `base_memory` SHALL 一律为 `true`，永不写入 `false`
- **AND** 该字段 SHALL 用于让 harness 不把 record 产出的 icon 当作短暂组件清理

### Requirement: 文件拷贝与 PNG 完整性

`dest/components/<label>.png` SHALL 与源 `screenshots/icons/record_memory_icon_*.png` 字节等同。

#### Scenario: PNG 字节等同
- **WHEN** 系统完成同步
- **THEN** 源文件与目标文件 SHALL 字节等同（无损 PNG，不做 resize / 重编码）
- **AND** 目标文件 SHALL 可被 `cv2.imread` 正常读取为 BGR ndarray

### Requirement: dest 不可写硬失败

`dest` 路径不可写或 `dest/components/` 创建失败 SHALL 抛 `RuntimeError` 并中止 `process_project()`，与既有 `full_ok` / `crop_ok` 写入失败语义对齐。

#### Scenario: dest 不可写
- **WHEN** `dest` 路径不可写（例如权限不足）
- **THEN** 系统 SHALL 抛 `RuntimeError`，消息中包含 `dest` 路径
- **AND** `process_project()` SHALL 中止，不返回 `updated_actions` 与 `meta`

#### Scenario: 单个 PNG 拷贝失败
- **WHEN** `shutil.copyfile` 在某个 icon 上抛 `OSError`
- **THEN** 系统 SHALL 抛 `RuntimeError`，中止同步
- **AND** 之前已成功的拷贝与 JSON 更新 SHALL 保留（破坏性最小）

### Requirement: 现有 dest 内容不受破坏

若 `dest/components.json` 损坏（无效 JSON），系统 SHALL 输出警告日志并将损坏内容视为空 dict，不掩盖 `process_project()` 主流程。

#### Scenario: components.json 损坏
- **WHEN** `dest/components.json` 含无效 JSON
- **THEN** 系统 SHALL 输出 warning log，说明损坏内容已被忽略
- **AND** SHALL 将现有 entry 当作空 dict 处理；新 key 全部走"新增"路径
- **AND** 不抛错，`process_project()` 正常完成

#### Scenario: components.json 缺失
- **WHEN** `dest/components.json` 文件不存在
- **THEN** 系统 SHALL 当作空 dict 起步，正常同步
- **AND** `process_project()` 正常完成

### Requirement: processed_log_sc.json schema 不变

`{project}_processed_log_sc.json` 中每个动作的 `screenshot_full` / `screenshot_crop` 字段 SHALL 保持不变；同步元数据（`components_synced` 等）仅出现在 `process_project()` 返回的 `meta` dict 中，**不**写入该 JSON。

#### Scenario: JSON schema 不变
- **WHEN** 系统完成同步
- **THEN** `{project}_processed_log_sc.json` 中每个动作 SHALL 仅含原有字段（`screenshot_full` / `screenshot_crop` 等）
- **AND** SHALL NOT 出现 `components_synced` / `components_dest` / `components_keys_added` 等任何同步元数据键

### Requirement: 后向兼容

`VideoScreenshotExtractor.__init__` 签名 SHALL 不变；`GUI_AGENT_COMPONENTS_DEST` env var 在 `process_project()` 内部读取。

#### Scenario: 现有调用方零影响
- **WHEN** 调用方以既有方式构造 `VideoScreenshotExtractor()` 并调用 `process_project(name)`，且 env var 未设置
- **THEN** 系统 SHALL NOT 抛出 `TypeError` 或任何新错误
- **AND** SHALL 保持既有 icon 写入与 JSON schema 行为不变

### Requirement: meta 字段可观察

`process_project()` 返回的 `meta` dict SHALL 在同步路径下包含以下字段：

- `components_synced: bool`
- `components_dest: str | None`
- `components_keys_added: list[str]`
- `components_keys_updated: list[str]`
- `components_fallback_to_timestamp: bool`

#### Scenario: 同步成功的 meta
- **WHEN** 同步正常完成（无论 LLM 成功或回退）
- **THEN** `meta["components_synced"]` SHALL 为 `True`
- **AND** `meta["components_dest"]` SHALL 非空
- **AND** `meta["components_keys_added"]` + `meta["components_keys_updated"]` SHALL 覆盖该轮所有 icon

#### Scenario: 同步跳过的 meta
- **WHEN** env var 未设置 / 空串
- **THEN** `meta["components_synced"]` SHALL 为 `False`
- **AND** `meta["components_dest"]` SHALL 为 `None`
- **AND** `meta["components_keys_added"]` 与 `meta["components_keys_updated"]` SHALL 为空 list