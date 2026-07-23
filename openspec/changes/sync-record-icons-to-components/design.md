## 上下文

完整设计文档：`docs/superpowers/specs/2026-07-23-record-icons-to-components-sync-design.md`。本文件是 OpenSpec 变更所需的设计摘要，包含决策、错误处理与迁移要点。完整数据流、详细错误处理表与测试策略见 spec 文档。

## 目标 / 非目标

**目标：**

- record 流程在 `process_project()` 末了自动把 default-click icon 同步到 `GUI_AGENT_COMPONENTS_DEST` 指向目录。
- icon 键由视觉模型实时给出 snake_case 内容标签；LLM 失败时回退到时间戳键。
- `components.json` 按 harness 现有 schema 增量写入，upsert 语义与 `_update_activity` 行为对齐。
- 调用方零感知（env var 在 `process_project()` 内读）。

**非目标：**

- 不改 harness 侧代码。
- 不改 `processed_log_sc.json` schema。
- 不为 record 上游新增 label 字段。
- 不做模板匹配 / 增量识别（属于 harness runtime 的 `component_memory` 职责）。

## 决策

### 决策 1：内联进 `screenshot_processor.py`

新增 `_sync_components_to_dest` / `_request_component_labels` / `_apply_components_updates` 方法；`process_project()` 末尾触发。纯逻辑（sanitize / merge）抽到 `components_sync.py`。

**理由：** `process_project()` 已是 record flow 中心；零下游改动。

### 决策 2：env var only 配置 Dst

`GUI_AGENT_COMPONENTS_DEST`：字符串路径。未设置 / 空串 → 不同步；非空 → 末尾同步。

**理由：** 与现有 `.env` 实践对齐；零配置即可"一键关闭"。

### 决策 3：单次批量 LLM 调用

每轮 record 末了调一次视觉模型，传入该轮全部 icon + 元数据，要求返回 `{filename: snake_case_label}` JSON object。复用 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL`。

**理由：** 1 次 API call；LLM 能看到跨 icon 上下文避免重复命名。

### 决策 4：LLM 失败软回退到时间戳键

LLM 任何异常（网络 / 4xx 5xx / JSON 解析失败 / schema 不符）一律不抛错；该 batch 所有 icon 改用 timestamp 键同步（`record_memory_icon_<sanitized_base>_crop`）。

**理由：** LLM 是外部依赖；网络抖动不该让 record 失败；至少保留 sync 的图片搬运价值。

### 决策 5：JSON upsert 语义

写入（key 不存在）：`learned_at = last_seen = now`、`seen_count = 1`、`consecutive_misses = 0`、`base_memory = true`。更新（key 已存在）：保留 `learned_at`、`last_seen = now`、`seen_count += 1`、`consecutive_misses = 0`。

**理由：** 与 harness `component_memory._update_activity` 行为对齐。`base_memory: true` 一律写入，避免 record 产出的 icon 被当作短暂组件清理。

### 决策 6：纯逻辑拆出 `components_sync.py`

承载 `sanitize_label` / `dedup_labels` / `build_component_entry` / `merge_components_json` 纯函数，便于单测；编排层留在 `screenshot_processor.py`。

## 风险 / 取舍

- **LLM 视觉模型不可用**：`OPENAI_MODEL` 不支持 vision → 自动回退；`meta.components_fallback_to_timestamp = True`。
- **dest 与 harness runtime 并发写**：本次同步任务不并发运行（人工触发）；并发场景下 `.bak` 轮转可兜底。
- **LLM 命名重复**：`dedup_labels` 加 `_2` / `_3` 后缀；用户可事后人工编辑。
- **磁盘增长**：每 icon ~2-11 KB（与现有 17 条 desktop 一致）；sync 不引入额外存储。

## 迁移计划

纯增量、无破坏性：

1. 部署后既有 record session 在 `GUI_AGENT_COMPONENTS_DEST` 设值时自动同步；未设值则保持原行为（仅写 `screenshots/icons/`）。
2. 既有 `dest/components.json` 与 `dest/components/` 目录不受影响；新条目以 upsert 方式追加。
3. 回滚 = 撤销 commit + 不设 env var；dest 上的同步产物可保留或人工清理。

## 开放问题

无。命名、触发、JSON schema、错误边界、env var 名称、LLM 凭证、upsert 语义均已与用户确认。