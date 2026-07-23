# 任务清单

## 1. components_sync 纯函数模块

- [ ] 1.1 新建 `record/Aloha_Learn/components_sync.py`：`IconRecord` dataclass（filename / action / coords / current_software / base）。
- [ ] 1.2 `ComponentEntry` dataclass 或 dict-typed NamedTuple，承载 `{type, source, icon_file, label, learned_at, last_seen, seen_count, consecutive_misses, base_memory}`。
- [ ] 1.3 `sanitize_label(raw: str) -> str`：转小写、空白→`_`、`/`→`-`、删 `\\:?*`、截 30 字符；空 / 全非法字符 → 抛 `ValueError`。
- [ ] 1.4 `dedup_labels(labels: list[str]) -> list[str]`：同 batch 内去重，加 `_2` / `_3` 后缀。
- [ ] 1.5 `build_component_entry(*, label, icon_file, learned_at, last_seen, seen_count, base_memory=True) -> dict`：返回完整 entry。
- [ ] 1.6 `merge_components_json(existing: dict, additions: dict, now_str: str) -> dict`：upsert 语义；保留 learned_at、累加 seen_count、重置 consecutive_misses。

## 2. ComponentsLLMError 与异常

- [ ] 2.1 新增 `class ComponentsLLMError(Exception)` 在 `screenshot_processor.py`（与既有 `RuntimeError` 风格一致）。
- [ ] 2.2 `_request_component_labels(records)` 抛出 `ComponentsLLMError` 的场景：网络错 / 4xx 5xx / JSON 解析失败 / 缺键 / 含未知键。

## 3. screenshot_processor 编排

- [ ] 3.1 `process_project()` 在 `screenshots_dir` 拿到后、`updated_actions` 写到 JSON 前，读取 `os.environ.get("GUI_AGENT_COMPONENTS_DEST", "").strip()`。
- [ ] 3.2 若 dest 为空 / None：`meta["components_synced"] = False`，继续既有逻辑。
- [ ] 3.3 若 dest 非空：构造 `icon_records = [(filename, action_meta), ...]` —— 列举 `screenshots_dir/icons/record_memory_icon_*.png` 并匹配 action metadata（按 base 对应 timestamp）。
- [ ] 3.4 调用 `_request_component_labels(icon_records, dest)`；成功 → label_map；抛 `ComponentsLLMError` → 回退到 `{fn: stem_to_label(fn) for fn in filenames}`。
- [ ] 3.5 `filename_to_safe = dedup_labels([sanitize_label(l) for l in label_map.values()])`（按 records 顺序对齐）。
- [ ] 3.6 `_load_components_json(dest)`：`json.load` 现有 `components.json`（缺失 / 损坏 → `{}`，后者加 warning）。
- [ ] 3.7 `_apply_components_updates(dest, existing, filename_to_safe, screenshots_dir)`：`os.makedirs(dest/components, exist_ok=True)`；逐个 `shutil.copyfile(screenshots_dir/icons/<fn>, dest/components/<safe>.png)`；构造 entries 走 `build_component_entry` + `merge_components_json`；`json.dump` 写回 `dest/components.json`。
- [ ] 3.8 同步成功后填充 meta：`components_synced`、`components_dest`、`components_keys_added`、`components_keys_updated`、`components_fallback_to_timestamp`。
- [ ] 3.9 dest 不可写 / 单个 PNG 拷贝失败 → 抛 `RuntimeError` 中止 `process_project()`（与现有 icon 写入失败语义对齐）。

## 4. LLM 客户端封装

- [ ] 4.1 在 `screenshot_processor.py` 新增 `_request_component_labels(records, dest)` 方法：读 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL`（与 `trace_generator.py` 同样使用 `openai` SDK）。
- [ ] 4.2 构造 multimodal message：system prompt 说明任务与输出约束；user message 含每条 icon 的 `{text: "<fn> | action=<X> | coords=<x,y> | software=<Y> | timestamp=<Z>s", image_url: "data:image/png;base64,<...>"}`。
- [ ] 4.3 `response_format={"type": "json_object"}`；校验返回 JSON object 键集 ⊆ 输入文件名集合；不符 → 抛 `ComponentsLLMError`。
- [ ] 4.4 任何 `openai.OpenAIError` / `requests.RequestException` / `json.JSONDecodeError` → 抛 `ComponentsLLMError`（由上层回退）。

## 5. 单元测试

- [ ] 5.1 新建 `record/Aloha_Learn/tests/test_components_sync.py`：
  - `SanitizeLabelTest` 覆盖空白 / 特殊字符 / 截断 / 空值。
  - `DedupLabelsTest` 覆盖重复 / 后缀冲突。
  - `BuildComponentEntryTest` 覆盖字段格式 / `base_memory=True` 一律为真。
  - `MergeComponentsJsonTest` 覆盖 upsert / 新增 / 不动其他 entry / 损坏输入回退。
- [ ] 5.2 在 `test_screenshot_processor.py` 新增 `ComponentSyncTest`：
  - `test_sync_runs_when_env_var_set_with_mocked_llm` —— mock `_request_component_labels` 返回正常映射，验证 dest/components/ 文件 + components.json + meta。
  - `test_sync_skipped_when_env_var_unset` —— 验证不调 LLM、不创建 dest 文件、meta.components_synced=False。
  - `test_sync_skipped_when_env_var_empty_string` —— 同上。
  - `test_sync_falls_back_to_timestamp_keys_when_llm_raises` —— mock LLM 抛 `ComponentsLLMError`；验证 dest/components/<timestamp>.png 与 components.json 键名格式。
  - `test_sync_handles_partial_llm_response` —— LLM 返回缺键；缺失 icon 走 timestamp，其余正常。
  - `test_sync_raises_runtimeerror_when_dest_unwritable` —— patch `shutil.copyfile` 抛 `OSError`；验证 `process_project()` 抛 `RuntimeError`。
  - `test_sync_treats_corrupt_components_json_as_empty` —— 写入 `{"invalid":}`；验证 warning + 空 dict 起步。
  - `test_sync_upserts_existing_keys` —— 预置 `components.json` 含某 key；mock LLM 返回同 key；验证 seen_count += 1、learned_at 保留。
- [ ] 5.3 旧测试（`IconCropSizeConstructorTest` / `SavePngHelperTest` / `DefaultClickIconSaveTest`）零回归 —— `process_project()` 测试中不设 env var 即可。

## 6. 文档与 OpenSpec

- [ ] 6.1 `openspec/changes/sync-record-icons-to-components/` 保留 4 个 artifact 直至本变更走完 apply + archive。
- [ ] 6.2 `record/README.md` 若枚举每点击产物则追加 icon-sync 说明；否则保持不动。
- [ ] 6.3 `openspec validate sync-record-icons-to-components --json` 验证通过。

## 7. 集成验证（手动）

- [ ] 7.1 设置 `GUI_AGENT_COMPONENTS_DEST=E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components`。
- [ ] 7.2 跑 `record_icon_click`（env var 在场），验证 dest/components/ 新增 9 个 `<label>.png` + components.json 增 9 条 entry（`type=icon, source=learn_batch, base_memory=true`）。
- [ ] 7.3 跑 `record_icon_click` 第二次（env var 仍在场），验证既有 key 走 upsert（`seen_count + 1`）。
- [ ] 7.4 跑 `record_icon_click` 时临时把 `OPENAI_MODEL` 改成不支持视觉的模型，验证全部 icon 落到 timestamp 键、`meta.components_fallback_to_timestamp = True`。
- [ ] 7.5 `processed_log_sc.json` schema 不变（无 `components_synced` 等字段）。