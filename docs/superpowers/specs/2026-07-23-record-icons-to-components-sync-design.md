# Record Icons → Components Sync 设计

> **设计文档（design spec）**：本文件记录 `sync-record-icons-to-components` 功能的完整设计、决策与取舍。它既是 writing-plans 阶段的输入，也作为 OpenSpec 变更 `openspec/changes/sync-record-icons-to-components/` 的事实源。

**日期**：2026-07-23
**作者**：本仓开发流程产出（brainstorming → writing-plans → subagent-driven-development）
**OpenSpec 变更名**：`sync-record-icons-to-components`
**设计能力（capability）**：`record-icons-to-components-sync`

---

## 1. 目标（Goal）

让 record 流程在每次 `process_project()` 跑完后，自动把该轮产出的 `screenshots/icons/record_memory_icon_*.png` 复制到 harness 的 `components.json` 所在目录（默认目标：`gui_harness/memory/apps/desktop/components/`），同时按 harness 既有 schema 维护对应的 `components.json`，使下游 memory / matchTemplate 流程无需额外导入步骤即可消费到这些 icon。

设计目标：

1. **零额外运行步骤**：用户跑一次 `process_project()` 就能拿到同步后的 components（env var 配置即触发）。
2. **语义键**：icon 不再以时间戳命名，而是由视觉模型对每个 30×30 crop 实时给出 snake_case 内容标签。
3. **可恢复**：LLM 失败时降级到时间戳键同步，不中断 record 主流程。
4. **可配置 + 可关闭**：目标路径通过 `GUI_AGENT_COMPONENTS_DEST` env var 设置；不设 = 不同步（"一键关闭"）。
5. **JSON 写幂等**：同一 key 重复出现时按 harness 现有 17 条 desktop 组件的 upsert 语义处理。

## 2. 上下文（Context）

### 2.1 现有产出

`VideoScreenshotExtractor.process_actions()` 在默认点击分支（`screenshot_processor.py:189-205`）针对每个带坐标、非 `DragStart` / 无坐标分支 / `CONFIG` / `Active Window` 的动作生成一张 `icon_crop_size × icon_crop_size` 的 PNG，路径为 `{project_dir}/screenshots/icons/record_memory_icon_{base}_crop.png`，其中 `base = f"{abs(timestamp-0.1):.3f}s"`（例如 `10.854s`）。该产物由 commit `9928b09`（feat(record): default icon_crop_size to 30）引入；JSON schema 维持原状。

### 2.2 下游消费方（harness 侧）

目标 `gui_harness/memory/apps/desktop/` 现有产物：

- `components.json` — UTF-8 dict，键为 snake_case 内容标签（如 `clone_repo_tab`），值含 `{type, source, icon_file, label, learned_at, last_seen, seen_count, consecutive_misses, base_memory}`
- `components/*.png` — 与 key 同名的扁平文件
- 现有 17 条 entry 全部为 `source="learn_batch"`、`base_memory=true`，由 `gui_harness/planning/learn.py:_learn_one_screen` 写入

下游 reader：

- `gui_harness/memory/app_memory.py:load_components` — 加载 `components.json`
- `gui_harness/memory/app_memory.py:quick_template_check` 与 `match_component` — 用 `cv2.matchTemplate` 把 `app_dir / comp["icon_file"]` 与当前帧比对
- `gui_harness/planning/component_memory.py:match_memory_components` — 直接 glob `components/*.png`
- `gui_harness/planning/component_memory.py:_update_activity` — 在每次 match 后递增 `seen_count`，重置 `consecutive_misses`，并在 ≥ 30 时遗忘

`base_memory: true` 是 load-bearing 字段：让 entry 不被 `app_memory.forget_stale_components` 当作短暂组件清理。新写入必须保留此字段。

### 2.3 配置机制现状

- record 仓目前无 JSON config 文件，唯一外部配置是 `.env`（被 `parser.py:5,52` 与 `trace_generator.py:4,27-28` 读取）。
- `screenshot_processor.py` 自身不读任何 env var；trace generator 读 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL` / `ALOHA_TRACE_TEMPERATURE`。
- 本次新增的 env var `GUI_AGENT_COMPONENTS_DEST` 与上述风格一致。

## 3. 范围与非范围（Scope）

### 3.1 范围内

- 每次 `process_project()` 结束后，若 `GUI_AGENT_COMPONENTS_DEST` 非空，自动同步。
- 同步范围：当前 record run 产出的全部 default-click icon（不含 DragStart、无坐标动作、CONFIG、Active Window —— 与既有 icon 写入策略一致）。
- icon 文件原样（无损 PNG）复制到目标 `components/`。
- `components.json` 按既有 schema 增量更新；upsert 语义。
- env var 缺失 / 空串 → 不同步。

### 3.2 非范围

- **不**改 harness 侧代码（不同仓）。
- **不**改 `processed_log_sc.json` schema。
- **不**改既有 icon 命名（仍为 `record_memory_icon_{base}_crop.png`）。
- **不**为 record 上游新增 label 字段（icon 内容标签完全由 LLM 生成，不依赖人工）。
- **不**做模板匹配 / 增量识别（这些属于 harness runtime 的 `component_memory` 职责）。

## 4. 决策（Decisions）

### 决策 1：内联进 `screenshot_processor.py`（方案 A）

理由：

- `process_project()` 已是 record flow 的中心；新增同步逻辑作为它末尾的一段编排最直接。
- 现有测试直接覆盖 `process_project` 行为；新增 test 类同位置追加，无需新建 CLI。
- `parser.py` 完全不动 —— env var 在 `process_project()` 顶部读，调用方无感知。

否决方案 B（独立 `ComponentSyncer` 模块 + DI）：本仓 record 子树仍以单文件为中心，过早拆分无收益；当前改动 ~80 行编排 + ~120 行纯函数（搬到独立小模块），整体可控。

否决方案 C（独立 CLI 命令）：与「record 自动」语义有偏差；要求用户在意识里理解这是两阶段组装。

### 决策 2：env var only 配置 Dst

新增 env var `GUI_AGENT_COMPONENTS_DEST`：字符串路径。语义：

- 未设置 / 空串 → 不同步；`meta.components_synced = False`
- 非空 → 末尾同步；`meta.components_dest = dest`

理由：

- 与既有 `.env` 实践对齐（`parser.py` / `trace_generator.py` 已读 `.env`）。
- 0 配置即可"一键关闭"。
- 不引入新配置文件；不污染 `screenshot_processor.py` 的构造函数（保持向后兼容：所有现有 `VideoScreenshotExtractor()` 调用方零影响）。

### 决策 3：单次批量 LLM 调用

每轮 record 末了调一次视觉模型，一次性传入该轮全部 icon + 元数据，要求返回 `{filename.png: snake_case_label}` JSON object。

理由：

- 成本 = 1 次 API call，与 icon 数量无关；`record_icon_click` 9 个 icon → 1 次；1000 个 icon → 仍 1 次。
- LLM 能看到跨 icon 上下文，避免重复命名（"系统设置" 与 "设置" 不再各占一个 key）。
- prompt 长度可控（image base64 体积为唯一变量）。

LLM 输入：

- system prompt：声明任务（"为下列每张点击 crop 命名一个 snake_case 内容标签"）+ 输出格式约束（30 字符、字符集、JSON object）
- user message：`content` 数组：
  - 文字说明："以下为 9 张 default-click icon，对应 metadata 如下……"
  - 对每个 icon：一条 `{type: "text", text: "<filename> | action=<X> | coords=<x,y> | software=<Y> | timestamp=<Z>s"}` 紧接着一条 `{type: "image_url", image_url: {url: "data:image/png;base64,<...>"}}`
- response_format: `{type: "json_object"}`（OpenAI 强制 JSON 输出）

LLM 输出校验：

- 必须是合法 JSON object，键集 ⊆ 输入文件名集合
- 缺失键 → 该 icon 走 timestamp fallback（不影响同 batch 其他 icon）
- 键集出现未知文件名 → 警告 + 忽略

模型与凭证：复用 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL`，与 `trace_generator.py` 完全一致。如用户当前 `OPENAI_MODEL` 不支持视觉，调用必然失败 → 整批走 timestamp 回退，`meta.components_fallback_to_timestamp = True`，不抛错。

### 决策 4：LLM 失败软回退到时间戳键

LLM 任何异常（网络 / 4xx 5xx / JSON 解析失败 / schema 不符）一律不抛错；该 batch 所有 icon 改用 timestamp 键同步，键名 = `record_memory_icon_<sanitized_base>_crop`（即把 `.` 替成 `_`）。

理由：

- LLM 是外部依赖；网络抖动不该让 record 失败。
- 至少 sync 把图片复制过去 + 落盘到 `components.json`，harness 仍能 template-match，只是标签不语义。
- 用户可在事后重跑（同一 key 走 upsert → 重新走 LLM），或人工编辑 `components.json`。

### 决策 5：JSON upsert 语义

每个 label key：

- 写入（key 不存在）：新增 entry，`learned_at = last_seen = now`，`seen_count = 1`，`consecutive_misses = 0`，`base_memory = true`
- 更新（key 已存在）：保留 `learned_at`，刷新 `last_seen = now`，`seen_count += 1`，`consecutive_misses = 0`

理由：与 harness 既有 `component_memory._update_activity` 行为对齐（match 一次 → seen_count + 1 + consecutive_misses 重置）。`base_memory: true` 一律写入（永不写入 false），避免 harness 把 record 流产出的 icon 当短暂组件清理。

### 决策 6：纯逻辑拆出 `components_sync.py`

为避免 `screenshot_processor.py` 长出 200+ 行新逻辑，新增独立模块 `record/Aloha_Learn/components_sync.py`，承载：

- `dataclass IconRecord(filename, action, coords, current_software, base)`
- `dataclass ComponentEntry(...)` —— 一个标准 entry
- `def sanitize_label(raw: str) -> str` —— 转 snake_case、删非法字符、截 30 字符
- `def dedup_labels(labels: list[str]) -> list[str]` —— 同 batch 内去重
- `def build_component_entry(label, learned_at=None, last_seen=None, seen_count=1, ...) -> dict`
- `def merge_components_json(existing: dict, additions: dict, now_str: str) -> dict` —— 纯函数，可单测

`screenshot_processor.py` 只做编排（收集 records → 调 LLM → 调上面这些函数 → 写盘）。

理由：纯函数独立模块边界清晰；LLM client 与 HTTP 错误处理留在 `screenshot_processor.py`（编排层）。

## 5. 数据流（Data Flow）

```
process_project(project_name)
├─ 既有：load actions → scale → process_actions() 写 screenshots/*.jpg + screenshots/icons/*.png
├─ dest = os.environ.get("GUI_AGENT_COMPONENTS_DEST", "").strip() or None
├─ 若 dest is None:
│     meta['components_synced'] = False; return
└─ dest 非空:
      icon_records = [(filename, action_meta) for action in actions
                      if action is default-click and has 'screenshot_*' keys]
      # 注：process_actions 已为 default-click 写入 icon；filename 从 screenshots_dir/icons/ 列举回填
      try:
          label_map = _request_component_labels(icon_records, dest)
          # label_map: {filename: raw_label, ...}
      except ComponentsLLMError as e:
          log.warning("LLM naming failed, falling back to timestamp keys: %s", e)
          label_map = {fn: stem_to_label(fn) for fn in [r[0] for r in icon_records]}
          meta['components_fallback_to_timestamp'] = True
      else:
          meta['components_fallback_to_timestamp'] = False

      # Sanitize + dedup
      safe_labels = dedup_labels([sanitize_label(l) for l in label_map.values()])
      # 但需要保持 filename → safe_label 的对应：
      filename_to_safe = {fn: safe for (fn, _), safe in zip(icon_records, safe_labels)}

      # Load existing components.json (if any)
      existing = _load_components_json(dest)  # {} if missing/corrupt

      # Build new entries + upsert
      now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      updates = {}  # label -> {entry_dict, source_filename}
      for fn, safe_label in filename_to_safe.items():
          prior = existing.get(safe_label)
          entry = build_component_entry(
              label=safe_label,
              icon_file=f"components/{safe_label}.png",
              learned_at=prior["learned_at"] if prior else now_str,
              last_seen=now_str,
              seen_count=(prior["seen_count"] + 1) if prior else 1,
          )
          updates[safe_label] = (entry, fn)

      # Apply: copy PNGs + write JSON
      _apply_components_updates(dest, updates)
      # _apply_components_updates:
      #   1. mkdir dest/components (if missing)
      #   2. for each (label, (entry, src_filename)):
      #        shutil.copyfile(screenshots_dir/icons/src_filename, dest/components/label.png)
      #   3. merged = {**existing, **{label: entry for label, (entry, _) in updates.items()}}
      #   4. json.dump(merged, dest/components.json, ensure_ascii=False, indent=2)

      meta['components_synced'] = True
      meta['components_dest'] = dest
      meta['components_keys_added'] = [l for l in updates if l not in existing]
      meta['components_keys_updated'] = [l for l in updates if l in existing]
```

## 6. 错误处理（Error Handling）

| 场景 | 行为 | meta 字段 |
|---|---|---|
| env var 缺失 / 空串 | 跳过同步 | `components_synced = False` |
| `dest` 不存在 | 自动 `os.makedirs(..., exist_ok=True)` 后建 `dest/components/` | 正常 |
| `dest` 不可写 | 抛 `RuntimeError`，中止 `process_project()` | （异常路径） |
| `dest/components.json` 缺失 | 当空 dict 起步 | 正常 |
| `dest/components.json` 损坏 | 警告日志 + 当空 dict 起步（不掩盖主流程） | 正常（键全部走"新增"分支） |
| 单个 PNG 拷贝失败 | 抛 `RuntimeError`，中止（与现有 icon 写入失败语义对齐） | （异常路径） |
| LLM 调用超时 / 4xx 5xx / 网络错 | 捕获 `ComponentsLLMError` → 整批回退到 timestamp 键 | `components_fallback_to_timestamp = True` |
| LLM 返回非 JSON | 同上 | 同上 |
| LLM 返回 JSON 但缺某些文件 / 含未知文件 | 已知文件正常写入；缺失文件回退到 timestamp；未知键警告 + 忽略 | 部分回退 → `components_fallback_to_timestamp = True`（标记而非绝对值） |
| sanitize_label 输入空 / 全非法字符 | 调用方 fallback 到 timestamp 键（不抛） | 同 LLM 失败 |
| 同 batch 内两个 icon 同 label | `dedup_labels` 自动加 `_2`, `_3` 后缀 | 正常 |
| 现有 `components.json` 同 key 已存在 | upsert（保留 learned_at、累加 seen_count、重置 consecutive_misses） | `components_keys_updated` |

### 6.1 失败边界

- **硬失败**：`dest` 不可写 / 单个 PNG 拷贝失败 / `dest/components/` 不可写。理由：这是用户配置错或权限错；继续 silent 会让用户误以为 sync 成功。
- **软回退**：LLM 任何失败。理由：外部依赖；网络抖动不该让 record 整体失败；至少保留 sync 的图片搬运价值。

## 7. 测试策略（Testing）

### 7.1 单元测试

`tests/test_components_sync.py`（新）覆盖：

1. `sanitize_label`：
   - `"Start Button"` → `"start_button"`
   - `"a/b\\c:d?e*f"` → `"a-b-cdef"`
   - 截断 31+ 字符至 30
   - 空串 / 全空白 → 抛 `ValueError`
2. `dedup_labels`：`["foo", "foo", "bar"]` → `["foo", "foo_2", "bar"]`；`["x", "x_2", "x"]` → `["x", "x_2", "x_3"]`
3. `build_component_entry`：所有字段格式；`learned_at` / `last_seen` 用 `datetime.now().strftime("%Y-%m-%d %H:%M:%S")`；`base_memory = true` 永远为 true
4. `merge_components_json`：
   - 新 key：新增路径
   - 旧 key：保留 `learned_at`、`seen_count += 1`、`consecutive_misses = 0`、`last_seen` 刷新
   - 不动其他 entry
   - JSON 损坏输入 → `{}` 返回

`tests/test_screenshot_processor.py`（修改，新增 `ComponentSyncTest`）覆盖：

1. env var 在场 + mock LLM 返回正常映射 → 验证 `dest/components/<label>.png` 字节等同源、`components.json` 字段全、`meta` 含 `components_synced/dest/keys_added/keys_updated/fallback_to_timestamp`
2. env var 缺失 → 不调 LLM、不创建 `dest/components/`、`meta.components_synced = False`
3. env var 空串 → 同 #2
4. LLM 抛 `ComponentsLLMError` → 全部 icon 落到 timestamp 键（文件名按 `record_memory_icon_<base>_crop.png` 复制到 `dest/components/`，键名同）；`meta.components_fallback_to_timestamp = True`
5. LLM 返回缺键 → 缺键的 icon 走 timestamp；其余正常；`meta.components_fallback_to_timestamp = True`
6. `dest` 路径不可写（patch `shutil.copyfile` 抛 `OSError`）→ 抛 `RuntimeError`
7. `dest/components.json` 损坏 → 警告 + 当空 dict；新 key 全加入；`meta.components_keys_added` 含所有新 key
8. 既有 key 被新 run 撞到 → upsert；`meta.components_keys_updated` 命中
9. 旧测试（`DefaultClickIconSaveTest` 等）零回归 —— 在 `_sync_components_to_dest` 不被调用的前提下，env var 默认缺失

### 7.2 集成验证（手动）

跑 `record_icon_click`：

```bash
export GUI_AGENT_COMPONENTS_DEST="E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components"
cd record/Aloha_Learn
PYTHONPATH=../.. python -m record.Aloha_Learn.screenshot_processor record_icon_click
```

验证清单：

1. `desktop/components/` 新增 9 个 `<label>.png`
2. `desktop/components.json` 增 9 条 entry：
   - `type="icon"`、`source="learn_batch"`、`base_memory=true`
   - `icon_file="components/<label>.png"`（path 与文件名一致）
   - `label` 等于 `icon_file` basename
   - `learned_at` / `last_seen` 为合法时间字符串
3. 既有 17 条 entry 不动（除非 LLM 给的某 label 与某已有 key 撞名 → 那一条被 upsert，`seen_count +1`）
4. `processed_log_sc.json` schema 不变（不含 `components_synced` 等字段 —— 这些只在 meta 里）
5. `meta.components_synced == True`、`components_dest == dest`

### 7.3 验证脚本

`record/Aloha_Learn/tests/test_components_sync_e2e.py`（可选，跑前手动）：直接驱动 `process_project()`，断言上述清单（仅本地验证用，可不入库）。

## 8. 修改清单（Files Touched）

| 文件 | 状态 | 关键内容 |
|---|---|---|
| `record/Aloha_Learn/screenshot_processor.py` | 修改 | `process_project()` 末尾触发同步；新增 `_request_component_labels` / `_sync_components_to_dest` / `_load_components_json` / `_apply_components_updates`；`meta` 字段扩展；新增 `ComponentsLLMError` 异常类 |
| `record/Aloha_Learn/components_sync.py` | 新建 | `IconRecord` / `ComponentEntry` dataclass；`sanitize_label` / `dedup_labels` / `build_component_entry` / `merge_components_json` 纯函数 |
| `record/Aloha_Learn/tests/test_components_sync.py` | 新建 | 覆盖纯函数单元测试 |
| `record/Aloha_Learn/tests/test_screenshot_processor.py` | 修改 | 新增 `ComponentSyncTest`（mock LLM + 临时 dest） |
| `openspec/changes/sync-record-icons-to-components/{proposal,design,specs/.../spec,tasks}.md` | 新建 | OpenSpec 变更 artifact（与既有 `add-record-memory-icon-crop` 同结构） |
| `docs/superpowers/plans/2026-07-23-sync-record-icons-to-components.md` | 新建 | writing-plans 阶段产出（不在本次 spec 范围） |

不修改：`parser.py` / `trace_generator.py` / `log_processor.py` / harness 任何文件。

## 9. 兼容性 / 风险（Risks & Migration）

### 9.1 向后兼容

- `VideoScreenshotExtractor.__init__` 签名不变 —— env var 在 `process_project()` 内部读，调用方零感知。
- 现有 6 个 test 类 + 10 个 test case（commit `9928b09` 后状态）零回归。
- `processed_log_sc.json` schema 不变。
- `screenshots/icons/` 下既有 icon 命名不变。

### 9.2 已知风险

| 风险 | 缓解 |
|---|---|
| LLM 返回标签含非 ASCII / 与既有 key 撞名 | `sanitize_label` + `dedup_labels` 处理；最终 schema 仍 snake_case |
| 用户 `OPENAI_MODEL` 不支持视觉 | 自动回退到 timestamp 键；`meta` 标 `fallback_to_timestamp=true`；不抛错 |
| `dest/components.json` 与 harness runtime 写入冲突（harness `_atomic_write_json` 同时跑） | record 写完后 harness 读是 OK；并发写会因 `.bak` 轮转被 `_safe_load_json` 兜底；harness 自己也轮转。我们采用非原子 write（json.dump 单步），并发场景下确实可能产生短暂损坏，但 `_safe_load_json` 会恢复 `.bak`。**本次同步任务不并发运行**（人工触发），风险可接受。 |
| LLM 命名重复率高（同一批 icon 拿到同一 label） | `dedup_labels` 加后缀；用户可事后人工编辑 |
| 用户多次重跑同一 record session | 全部走 upsert；既有 key `seen_count` 递增；icon PNG 内容不变（覆盖写 OK） |

### 9.3 回滚

回滚 = 撤销 commit + 不设 env var。无需清理 `dest` 上的同步产物（harness 仍可消费它们）。

## 10. 开放问题（Open Questions）

无。所有决策均已与用户确认：

- LLM 实时命名 ✓
- 默认同步 + env var 配置（"一键关闭" = 不设）✓
- 单次批量调用 ✓
- LLM 失败回退到时间戳键（仍同步）✓
- upsert learned_at 不动 + 累加 seen_count ✓
- env var only 配置 Dst ✓
- 内联进 `screenshot_processor.py`（方案 A）✓

---

## 11. 自检（Spec Self-Review）

1. **占位符扫描**：无 "TBD" / "TODO" / "fill in details"。
2. **内部一致性**：所有决策与用户问答一致；数据流与错误处理表自洽；测试覆盖与功能需求一一对应。
3. **范围**：单 record-flow 增量；不涉及 harness 侧改动；不涉及 trace_generator / parser 改动；scope 适合单一实现计划。
4. **歧义**：所有 "SHALL" 语句均给出精确数值（30 字符、JSON 字段名、env var 名等）；错误处理表给出每种场景的具体行为。