## 背景

`record/Aloha_Learn/screenshot_processor.py` 已经在每次点击产出 `screenshots/icons/record_memory_icon_*.png`（commit `9928b09`），但 harness 侧的 `gui_harness/memory/apps/desktop/components.json` 仍依赖人工触发 `learn.py learn_app_components` 才能纳新。本变更把 record 与 harness 之间的导入步骤自动化：每次 `process_project()` 跑完，把该轮 icon 同步到 `GUI_AGENT_COMPONENTS_DEST` 指向的 **app 目录**（如 `gui_harness/memory/apps/desktop/`，注意不是 `desktop/components/`），同时按 harness 既有 schema 维护 `<dest>/components.json` 与 `<dest>/components/<label>.png`。

图标键不再以时间戳命名，由视觉模型对每张 30×30 crop 实时给出 snake_case 内容标签（例如 `start_button`、`taskbar_search`），与 harness 现有 17 条 desktop 组件键风格一致。LLM 失败时降级到时间戳键同步，保证 sync 不断。

## 变更内容

- `VideoScreenshotExtractor.process_project()` 在末尾读 `GUI_AGENT_COMPONENTS_DEST` 环境变量：未设置 / 空串 → 不同步；非空 → 自动同步该轮全部 default-click icon 到 `<dest>/components/`（PNGs），并增量更新 `<dest>/components.json`。`dest` 是 harness 的 app 目录（如 `desktop/`），不是 `desktop/components/`。
- LLM 调用复用现有 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL`（与 `trace_generator.py` 同源）。每轮 record 调一次视觉模型，传入该轮全部 icon + 元数据（action / coords / current_software / timestamp），要求返回 JSON object `{filename: snake_case_label}`。
- LLM 任何异常（网络 / JSON 解析 / schema 不符）一律捕获，整批回退到时间戳键同步（不抛错）。
- `components.json` 写入采用 upsert：同 key 保留 `learned_at`、`seen_count += 1`、`consecutive_misses = 0`、`last_seen = now`；新 key 全字段写入。新增 entry 一律 `source="learn_batch"`、`base_memory=true`（与 harness 现有 17 条 desktop 组件一致）。
- 新增 `record/Aloha_Learn/components_sync.py`，承载纯逻辑（`sanitize_label` / `dedup_labels` / `build_component_entry` / `merge_components_json`），便于独立单测；`screenshot_processor.py` 仅做编排。
- `process_project()` 返回的 `meta` 增加 `components_synced` / `components_dest` / `components_keys_added` / `components_keys_updated` / `components_fallback_to_timestamp` 字段。
- `processed_log_sc.json` schema 不变。
- `parser.py` / `trace_generator.py` / `log_processor.py` 不动；harness 侧不动（不同仓）。
- 向后兼容：env var 在 `process_project()` 内部读取，所有现有 `VideoScreenshotExtractor()` 调用方零影响。

无破坏性变更。

## 能力（Capabilities）

### 新增能力

- `record-icons-to-components-sync`：定义 record 流程在每次 `process_project()` 结束后，把 default-click icon 自动同步到 `GUI_AGENT_COMPONENTS_DEST` 指向目录的契约，包括触发条件、LLM 调用、JSON 写入、upsert 语义、LLM 失败回退、JSON schema 不变性。

### 修改能力

无。`trace-to-midscene-flow` 与 record 既有 capability 的 JSON schema 与下游契约均不发生 spec 级别变更。

## 影响

- 代码：`record/Aloha_Learn/screenshot_processor.py`（编排 + LLM 调用）、新增 `record/Aloha_Learn/components_sync.py`（纯函数）。
- 测试：新增 `record/Aloha_Learn/tests/test_components_sync.py`；`record/Aloha_Learn/tests/test_screenshot_processor.py` 新增 `ComponentSyncTest`。
- 配置：env var `GUI_AGENT_COMPONENTS_DEST`（路径字符串）。无现有变量变更。
- 产物：dest 目录新增 `components/<label>.png` 文件 + `dest/components.json` 增量条目。
- 下游：harness `cv2.matchTemplate` 流程零改动即可消费新增 icon。
- 调用点：`screenshot_processor.py:374`（CLI）与 `parser.py:70`（library）均通过 `process_project()` 触发；env var 在 `process_project()` 内读，两处自动覆盖。