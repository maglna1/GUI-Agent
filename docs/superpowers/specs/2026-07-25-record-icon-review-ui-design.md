# Record Icon Review UI — Design Spec

- **Branch**: `feat/record-memory-icon-crop`
- **Date**: 2026-07-25
- **Status**: Draft

## Context

`feat/record-memory-icon-crop` 分支当前在 `record/Aloha_Learn/screenshot_processor.py:process_project()` 末尾自动调用视觉模型（`_request_component_labels`）为每张 `screenshots/icons/record_memory_icon_*.png` 生成 snake_case 标签，然后经 `_sync_components_to_dest` upsert 到 `<GUI_AGENT_COMPONENTS_DEST>/components.json` 与 `components/<label>.png`。LLM 失败时整批回退到时间戳键。

> **2026-07-25 后续调整：** `GUI_AGENT_COMPONENTS_DEST` env var 不再被 `process_project()` 读取；review UI **永远开启**，dest 改为 `<project_dir>/components_review_ui_mutimodal_memory_manual/`。`_sync_components_to_dest` 保留为公开库方法，需要时可手动调用。

视觉模型在很多真实截图上会给出"看起来合理但语义错位"的标签（如把"任务栏的开始按钮"标成 `windows_logo`），下游 `cv2.matchTemplate` 因此命中错误组件。本变更为 LLM 自动命名后引入一道**人类审核环节**：每个 icon 在写入 `components.json` 前弹出一个 React 界面，让用户接受 LLM 候选、改写为更准的标签、或显式跳过该图。

不替换 LLM 流程：LLM 仍是默认命名来源；UI 只在写入前增加一道"接受 / 改写 / 跳过"关卡。失败兜底保持 `_request_component_labels` 既有回退时间戳键语义。

## Goals / Non-Goals

**Goals:**

- 在不替换 LLM 流程的前提下，把"每张 icon 是否进入 components.json"和"以什么 label 进入"两件事的最终决定权交给用户。
- 全程本地、不暴露网络：HTTP server 绑 `127.0.0.1`，端口 OS 分配。
- 与现有 `components_sync.py`（`sanitize_label` / `dedup_labels` / `build_component_entry` / `merge_components_json`）零修改复用。
- 失败兜底：用户未在超时前提交时，所有未决定按 `accept` 走，与既有未走 UI 时的行为完全一致。
- 现有 `processed_log_sc.json` schema 不动；`parser.py` / `trace_generator.py` / `log_processor.py` 不动。

**Non-Goals:**

- 不替换 `_request_component_labels` 的调用顺序、参数或回退策略。
- 不引入 FastAPI / Flask / WebSocket / 数据库等新依赖。Python 侧只用 stdlib。
- 不为 UI 单独发布 npm 包；`review-ui/` 留在仓内随 `record/` 一起发布。
- 不实现"对历史 components.json 的批量编辑"。本变更只对**当前 `process_project()` 跑出来的这一批**生效。
- 不支持远程访问或多用户并发。Server 单进程、单客户端。
- 不实现"LLM 候选离线缓存 / 编辑历史 / 撤销栈"。

**无环境变量依赖:**

- Review UI **永远开启**，不读任何 env var。
- dest 固定为 `<project_dir>/components_review_ui_mutimodal_memory_manual/`，跟随每个 project。
- 之前用于触发 LLM 自动同步的 `GUI_AGENT_COMPONENTS_DEST` env var 在 `process_project()` 中**不再读取**；`_sync_components_to_dest` 保留为公开方法，需要时可手动调用（不推荐，新流程以 review UI 为准）。

## Architecture

### 新增 / 修改文件

```
record/Aloha_Learn/
├── screenshot_processor.py        # 修改: process_project() 末尾插入 review session
├── components_sync.py             # 不动
├── review_server.py               # 新增: stdlib HTTP server + 静态托管 + 3 个 API
└── review-ui/                     # 新增: Vite + React + TypeScript
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── types.ts
        ├── api/client.ts
        ├── lib/sanitize.ts
        ├── store/reducer.ts
        ├── components/
        │   ├── TopBar.tsx
        │   ├── IconGrid.tsx
        │   ├── IconCard.tsx
        │   ├── IconDetail.tsx
        │   ├── SubmitConfirm.tsx
        │   └── DoneScreen.tsx
        └── styles.css
```

### 数据流（一次 `process_project()`）

1. `process_actions()` 跑完，icon PNG 已落盘到 `screenshots/icons/`。
2. `_request_component_labels(records, screenshots_dir)` 调 LLM；失败则整批回退时间戳键（既有行为不变）。
3. **新增**：`run_review_session(records, label_map, screenshots_dir, dest)` —— 把 LLM 候选连同 icons 打包成 queue JSON，在 `127.0.0.1:0` 起 HTTP server，`webbrowser.open()` 自动开浏览器，**阻塞**等 `/api/finish`（最长 30 分钟）。
4. UI 渲染网格 → 用户逐图决策 → 点"提交" → POST `/api/finish`。
5. Server 按决定分桶（accept / edit / skip），edit 走既有的 `sanitize_label`；整批"全手动"打开时，未显式 edit 的图全部按 skip 处理。
6. Server 把分桶结果回给 Python；Server 关闭。
7. Python 把过滤后的 additions 喂给既有的 `_apply_components_updates(...)`，复用 upsert 逻辑（不重写）。
8. `meta` 新增：`review_decisions: {accepted, edited, skipped}`、`review_manual_mode: bool`、`review_timed_out: bool`、`review_sanitize_fallback: int`。

### 关键边界

- Python 阻塞发生在 `process_project()` 末尾、`_apply_components_updates` 调用之前。
- Server 端口由 OS 分配（避免冲突），启动后 stdout 打印实际端口与 `http://127.0.0.1:<port>/`。
- Server 只绑 `127.0.0.1`，不暴露网络。
- 静态文件由 server 读 `review-ui/dist/` 托管；如未构建则 `process_project()` 直接 `RuntimeError("review-ui/dist missing; run `npm --prefix record/Aloha_Learn/review-ui run build`")`，不静默跳过（与 `AGENT.md` 第 2 条一致）。
- `processed_log_sc.json` schema 不动；`trace_generator.py` / `parser.py` 不动。

## API Contracts

### 端点

| 端点 | 方法 | 作用 |
|---|---|---|
| `/{path}` | GET | 静态资源（`/icons/...` 走 `screenshots/icons/`，`/*` 走 `review-ui/dist/`） |
| `/api/queue` | GET | 一次性返回完整 queue |
| `/api/decisions` | POST | 增量更新中间态，UI 每次改动后调用，幂等 |
| `/api/finish` | POST | 校验完整性，分桶后返回结果，关闭 server |

### `GET /api/queue` 响应

```json
{
  "icons": [
    {
      "filename": "record_memory_icon_10.854s_crop.png",
      "icon_url": "/icons/record_memory_icon_10.854s_crop.png",
      "llm_label": "start_button",
      "is_timestamp_fallback": false,
      "action": "MouseLeftDown at ...",
      "coords": [500, 300],
      "current_software": "Chrome",
      "base": "10.854s"
    }
  ],
  "existing_labels": ["taskbar_search", "browser_tab_close"],
  "dest": "C:\\path\\to\\gui_harness\\memory\\apps\\desktop",
  "manual_mode_default": false
}
```

- `icon_url` 是 server 内的相对路径；UI 端直接 `<img src=icon_url>` 即可。
- `existing_labels` 从 `dest/components.json` 读出来，让 UI 能高亮"已存在"冲突。
- `is_timestamp_fallback=true` 时，UI 给一个 "⏱ fallback" 角标。

### `POST /api/decisions` 请求/响应

```json
// request
{
  "decisions": {
    "record_memory_icon_10.854s_crop.png": {"action": "accept"},
    "record_memory_icon_11.012s_crop.png": {"action": "edit", "label": "search box"},
    "record_memory_icon_11.234s_crop.png": {"action": "skip"}
  },
  "manual_mode": false
}
```

```json
// response 200
{"ok": true, "count": 3}
```

- 幂等：同一 filename 后写覆盖前写。
- 中间态：用户每次改一个 card 就 POST 一次，浏览器崩了不丢。
- Server 不校验 `edit.label` 的合法性（不在这步 sanitize）；校验在 `/api/finish` 做。

### `POST /api/finish` 行为

1. 校验：所有 icon 必须有 decision（`accept` / `edit` / `skip`），缺失返回 400 + `{missing: [filenames]}`。
2. `manual_mode=true` 时，把所有 `accept` 强制改写成 `skip`（用户没显式 edit 的就丢掉）。
3. 对 `edit.label` 调 `sanitize_label`；失败 → 该图降级为 `accept` LLM 候选（或 LLM 失败时用时间戳键）。
4. 构造最终 `additions`（只含 `accept` + `edit` 通过 sanitize 的），调既有的 `merge_components_json` + 拷 PNG 逻辑。
5. 返回：

```json
{
  "applied": {"accepted": 12, "edited": 3, "skipped": 2, "sanitize_fallback": 1},
  "keys_added": ["search_box", "..."],
  "keys_updated": ["start_button", "..."]
}
```

6. 关闭 server（`self.server.shutdown()` + join）。

### `decision.action` 枚举

- `"accept"` — 用 LLM 候选
- `"edit"` — 用 `decision.label`（必填），先 sanitize
- `"skip"` — 不进 components.json

### `manual_mode` 语义

- UI 顶部 toggle。打开时，所有未显式 `edit` 的图都按 `skip` 处理。
- 关闭时，`accept` / `edit` / `skip` 都按字面生效。

## UI Structure

### 单页布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  Record Icon Review                                  [全手动 ☐]      │
│  共 17 张 · 12 accept · 3 edit · 2 skip                              │
│  [全部接受]                          [提交]                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐              │
│  │  IMG   │ │  IMG   │ │  IMG   │ │  IMG   │ │  IMG   │  ...         │
│  │ start_ │ │ search │ │ close_ │ │ task_  │ │ ...    │              │
│  │ button │ │ _box   │ │ tab    │ │ bar    │ │        │              │
│  │ ✓ ✎ ⨯  │ │ ✓ ✎ ⨯  │ │ ✓ ✎ ⨯  │ │ ✓ ✎ ⨯  │ │        │              │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 组件树

- `<App />` — 顶层；首次挂载拉 `/api/queue`，维护 `useReducer` 全局状态。
- `<TopBar />` — 全手动 toggle、计数器、"全部接受"按钮、"提交"按钮。
- `<IconGrid />` — 响应式 CSS grid（4-6 列），渲染 `<IconCard />` 列表。
- `<IconCard />` — 单张图 + 标签 + 三按钮；点击图片 → 打开 `<IconDetail />` modal。
- `<IconDetail />` — 大图 + 可编辑 label input + "保存"/"跳过"/"取消" 按钮。
- `<SubmitConfirm />` — 提交前显示汇总（accept N / edit N / skip N），确认 → POST `/api/finish`。
- `<DoneScreen />` — 提交后只读统计页，显示 `applied`。

### state 模型（`useReducer`）

```ts
type Decision = { action: "accept" } | { action: "edit"; label: string } | { action: "skip" };
type State = {
  icons: Icon[];                              // from /api/queue
  decisions: Record<string, Decision | null>; // filename -> 当前决定
  manualMode: boolean;                        // 全手动 toggle
  submitting: boolean;
};
```

actions: `SET_QUEUE`, `SET_DECISION(filename, decision)`, `SET_MANUAL_MODE`, `SET_SUBMITTING`, `RESET`, `APPLY_BULK_ACCEPT`, `APPLY_BULK_SKIP`。

### 交互细节

- **每张 card 三按钮**：✓ accept（默认色）/ ✎ edit（打开 modal）/ ⨯ skip（灰）。
- **冲突提示**：若 LLM 候选已在 `existing_labels` 中，标签下方红字"已存在（将 upsert）"；用户仍可接受。
- **fallback 角标**：若 `is_timestamp_fallback=true`，标签灰底斜体 + "⏱ LLM 未命名"。
- **edit modal**：textarea（支持中文 / `_` / `-`），输入实时调 `sanitize_label`（前端镜像 Python 实现，规则：lowercase、whitespace→`_`、`/`→`-`、strip `\\:?*`、truncate 30）。底部"保存"按钮 disabled 若 sanitize 后为空。
- **debounce 中间态**：`SET_DECISION` 触发 → 300ms 后 POST `/api/decisions`（不阻塞 UI）。
- **提交校验**：缺决策的图高亮抖动 + 提示"还有 N 张未决定"；全手动模式下，所有未 edit 的图在 UI 上标 ⨯（视觉提示）。
- **提交后**：`<SubmitConfirm />` 关闭 → 跳"已完成"页（只读），显示 `applied` 统计；server 自动关闭。

### 目录

```
review-ui/src/
├── main.tsx
├── App.tsx
├── types.ts                       # Icon, Decision, Queue, FinishResult
├── api/client.ts                  # getQueue, postDecisions, postFinish
├── lib/sanitize.ts                # 与 components_sync.sanitize_label 镜像
├── store/reducer.ts               # useReducer + 状态机
├── components/
│   ├── TopBar.tsx
│   ├── IconGrid.tsx
│   ├── IconCard.tsx
│   ├── IconDetail.tsx
│   ├── SubmitConfirm.tsx
│   └── DoneScreen.tsx
└── styles.css
```

## Error Handling

### Server 侧错误

| 场景 | 行为 |
|---|---|
| `review-ui/dist/` 缺失 | `process_project()` 启动前抛 `RuntimeError("review-ui/dist missing; run `npm --prefix record/Aloha_Learn/review-ui run build`")` |
| 端口 OS 分配失败 | 抛 `RuntimeError` 中止（极少见） |
| 浏览器无法打开（headless 环境） | `webbrowser.open()` 异常被吞，打印 `Open http://127.0.0.1:<port>/ manually`；server 继续运行 |
| `POST /api/finish` 缺决策 | 400 + `{missing: [filenames]}`；UI 抖动高亮 |
| `POST /api/decisions` body 不合法 | 400 + `{error}`；不修改 server 状态 |
| Server 启动后无任何请求 | 30 分钟无活动则 `shutdown()`，Python 收到超时，把所有未决定按 `accept` 处理 |
| LLM 调用失败回退时间戳键 | UI `is_timestamp_fallback=true` 角标；接受时直接用时间戳键，不调 LLM |

### Python 集成错误

| 场景 | 行为 |
|---|---|
| 用户关闭浏览器未提交 | 30 分钟超时 → 全部按 `accept` 走（与既有未走 UI 时的行为一致），meta 标注 `review_timed_out: true` |
| `sanitize_label` 失败 | 该图按 `accept` 处理（既有 `_sync_components_to_dest` 的回退路径） |
| `dest/components.json` 写入失败 | `RuntimeError`，与既有行为一致（process_project 整体失败） |

### UI 错误

| 场景 | 行为 |
|---|---|
| 初次 `GET /api/queue` 失败 | 红色 banner + 重试按钮 |
| `POST /api/decisions` 网络失败 | 静默重试 3 次；最终失败显示"中间态未保存"提示 |
| `POST /api/finish` 失败 | 弹错误提示，state 保留，UI 不退出 |
| 用户编辑中的 label 含非法字符 | 实时显示 sanitize 结果；保存按钮 disabled 若 sanitize 后为空 |

## Testing

### Python 侧测试（`tests/test_review_server.py`）

- `test_serves_queue_payload`：构造 records + label_map，调 `run_review_session`（注入 fake server，绕过浏览器），GET `/api/queue` 验证 icons 字段。
- `test_decisions_endpoint_persists`：POST `/api/decisions` → 再次 GET `/api/queue` 不变；POST `/api/finish` 验证 applied。
- `test_skip_excluded_from_components`：3 张里 skip 1 张，验证 `_apply_components_updates` 只收到 2 个。
- `test_edit_label_sanitized`：传 `"Start Button!"` → 验证 components.json 写入 `start_button`。
- `test_manual_mode_treats_accept_as_skip`：`manual_mode=true` 提交 → `applied.skipped == accept 数`。
- `test_sanitize_fallback_on_edit`：传非法 edit label → 该图降级 accept，`applied.sanitize_fallback == 1`。
- `test_timeout_falls_back_to_accept`：mock 时间到 30 分钟，验证所有未决定按 accept 走。
- `test_static_files_served_from_dist`：mock dist 目录含 `index.html` → GET `/` 返回 200。
- `test_dist_missing_raises`：dist 不存在时 `process_project()` 抛 `RuntimeError`。

### UI 侧测试（Vitest + @testing-library/react）

- `App renders queue after fetch`：mock `getQueue`，验证 N 张 card。
- `clicking accept sets decision to accept` + 计数器 +1。
- `clicking edit opens modal` + 保存后 state 更新。
- `manual toggle changes accept behavior`：toggle 后 accept 视觉变 ⨯。
- `submit button posts /api/finish`：mock fetch，验证调用。
- `sanitize is mirrored correctly`：`"Start Button!"` → `"start_button"`、`"搜索框"` → 空（验证 disable）。
- `missing decision blocks submit`：14/17 决定 → 提交按钮 disabled。

### 端到端

- `tests/test_integration_review.py`：用 `Examples/air_tickets` 项目作为 fixture，跑 `process_project()` 注入 mock server，POST 一组混合决定，验证最终 `dest/components.json` 含预期 keys + PNG 文件就位。
- 真实浏览器手测：`process_project('air_tickets')` → 浏览器开 → 混决策 → 提交 → 验证 `dest/components.json`。

## Risks / Trade-offs

- **30 分钟硬超时**：用户没提交时全部按 accept 走，与既有未走 UI 行为一致；不引入静默丢失。若想"用户必须显式提交否则报错"，需要新增 UI 强制逻辑，但与既有兼容性冲突，本变更不引入。**30 分钟**取自典型 batch（10-50 张 icon × 单图审 5-15 秒）的人类可完成上限；超此即视为"用户离开"，与 AGENT.md 第 2 条"不静默跳过、不伪造成功路径"原则一致——保留 LLM 自动命名结果而非抛错中断。
- **stdio HTML / Vite 静态托管**：把 `review-ui/dist/` 打进 `record/Aloha_Learn/review-ui/dist/`；意味着发布时必须先 `npm run build`，否则 `process_project()` 直接 `RuntimeError`。这是显式失败，符合 `AGENT.md` 第 2 条。
- **label sanitize 镜像双份**：Python 端用 `components_sync.sanitize_label`，前端 `lib/sanitize.ts` 必须保持规则一致；任何修改都要两边同步。本变更通过测试 `test_sanitize_is_mirrored_correctly`（Python + TS 各一份）锁住一致性。
- **server 与浏览器生命周期**：如果用户在 server 关闭前关闭浏览器，30 分钟内重连仍可继续；超过则视为超时。这是合理的"防卡死"边界。
- **进程端口冲突**：用 OS 分配（端口 0）+ 只绑 `127.0.0.1` 规避；不引入端口文件。

## Migration Plan

本变更为纯增量、无破坏性变更：

1. 部署后既有项目再次走 `process_project()` 时，会先自动构建 `review-ui/`（开发者须在改 `review-ui/src` 后跑 `npm --prefix record/Aloha_Learn/review-ui run build`），然后按本规范弹出浏览器供用户决策。
2. 已存在的 `dest/components.json` 不需重新生成；UI 仅影响**当前轮**产出的 icon。
3. 回滚方式：删除 `record/Aloha_Learn/review_server.py` 与 `record/Aloha_Learn/review-ui/`，恢复 `screenshot_processor.py:process_project()` 中 review session 段为直接调用 `_sync_components_to_dest`。
4. Review UI 不能关掉——`process_project()` 总是会调用 `run_review_session`。若环境无浏览器但仍要跑（例如纯 headless CI），可以临时把 `review-ui/dist/` 移走或清空，让 `process_project()` 在 `RuntimeError("review-ui/dist missing")` 时显式失败；或手动调用 `_sync_components_to_dest(...)` 跳过 UI。

## Open Questions

无。
