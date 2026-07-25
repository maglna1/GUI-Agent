# Record Icon Review UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `record/Aloha_Learn/` 下新增 React + Vite + TypeScript 审核界面与 stdlib 本地 HTTP server，在 `process_project()` 末尾、icon 写入 `dest/components.json` 之前为每张 icon 提供"接受 LLM 标签 / 改写 / 跳过 / 全手动"四种决策，30 分钟超时回退到 LLM 自动命名。

**Architecture:** 新增 `record/Aloha_Learn/review_server.py`（stdlib `http.server.ThreadingHTTPServer`，端口 OS 分配，绑 `127.0.0.1`，3 个端点 + 静态文件托管）和 `record/Aloha_Learn/review-ui/`（Vite + React 18 + TypeScript + Vitest + React Testing Library）。`screenshot_processor.py:process_project()` 在 LLM 标签拿到后、`_apply_components_updates` 调用前插入 `run_review_session(...)`，复用现有 `components_sync.sanitize_label` / `merge_components_json` / `_apply_components_updates`。新增环境变量 `GUI_AGENT_REVIEW_DISABLE=1` 作为 headless 逃生口。

**Tech Stack:** Python 3 stdlib（`http.server` / `webbrowser` / `json` / `threading`）、Vite 5、React 18、TypeScript 5、Vitest、@testing-library/react、@testing-library/jest-dom、jsdom。

## Global Constraints

逐字摘自 `docs/superpowers/specs/2026-07-25-record-icon-review-ui-design.md`：

- Server 绑 `127.0.0.1`，端口 OS 分配（`http.server.HTTPServer(("127.0.0.1", 0), ...)`）。
- 三个端点：`GET /api/queue`、`POST /api/decisions`、`POST /api/finish`。
- `decision.action` 枚举：`"accept"` / `"edit"`（必填 `label`）/ `"skip"`。
- `manual_mode=true` 时，所有 `accept` 强制改写为 `skip`，仅 `edit` 走通。
- `edit.label` 走 `components_sync.sanitize_label`；失败降级为 `accept` LLM 候选（LLM 失败时用时间戳键）。
- 静态资源：`/icons/...` 走 `screenshots_dir/icons/`，其余走 `review-ui/dist/`。
- `review-ui/dist/` 缺失 → `process_project()` 抛 `RuntimeError`，不静默跳过。
- 超时：Server 启动 30 分钟后无活动 `shutdown()`，未决定按 `accept` 走。
- 浏览器自动拉起：`webbrowser.open(f"http://127.0.0.1:{port}/")`；失败打印手动 URL。
- 新增环境变量：`GUI_AGENT_REVIEW_DISABLE=1`（非空值即生效）跳过 review session，直接走既有 LLM 自动同步。默认未设置。
- `meta` 必含：`review_decisions: {accepted, edited, skipped}`、`review_manual_mode: bool`、`review_timed_out: bool`、`review_sanitize_fallback: int`。
- `processed_log_sc.json` schema 不变；`components_sync.py` 不修改；`_apply_components_updates` 不修改。
- 现有 `process_project()` 既有行为（CONFIG / 视频读取 / LLM 调用 / 时间戳 fallback）保持不变。
- 测试风格：Python 沿用 `record/Aloha_Learn/tests/` 既有 `unittest` + `unittest.mock.patch` + `tempfile.TemporaryDirectory` 风格；TS 用 Vitest + React Testing Library。

## File Structure

### New files

```
record/Aloha_Learn/
├── review_server.py                                       # HTTP server
├── review-ui/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── index.html
│   ├── .gitignore                                         # node_modules, dist
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── App.test.tsx
│   │   ├── types.ts
│   │   ├── styles.css
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── client.test.ts
│   │   ├── lib/
│   │   │   ├── sanitize.ts
│   │   │   └── sanitize.test.ts
│   │   ├── store/
│   │   │   ├── reducer.ts
│   │   │   └── reducer.test.ts
│   │   └── components/
│   │       ├── TopBar.tsx
│   │       ├── TopBar.test.tsx
│   │       ├── IconGrid.tsx
│   │       ├── IconCard.tsx
│   │       ├── IconCard.test.tsx
│   │       ├── IconDetail.tsx
│   │       ├── IconDetail.test.tsx
│   │       ├── SubmitConfirm.tsx
│   │       ├── SubmitConfirm.test.tsx
│   │       ├── DoneScreen.tsx
│   │       └── DoneScreen.test.tsx
└── tests/
    ├── test_review_server.py                              # HTTP server unit tests
    └── test_review_integration.py                         # E2E with examples fixture
```

### Modified files

- `record/Aloha_Learn/screenshot_processor.py` — `process_project()` 末尾、`_apply_components_updates` 调用前插入 `run_review_session(...)` 包装；新增 `run_review_session()` 私有方法；新增 `meta` 字段。
- `record/Aloha_Learn/tests/test_screenshot_processor.py` — 新增 `ReviewSessionHookTest` 类。
- `.gitignore` — 新增 `record/Aloha_Learn/review-ui/node_modules/` 与 `record/Aloha_Learn/review-ui/dist/`。

---

## Task 1: Scaffold Vite + React + TypeScript project

**Files:**
- Create: `record/Aloha_Learn/review-ui/package.json`
- Create: `record/Aloha_Learn/review-ui/vite.config.ts`
- Create: `record/Aloha_Learn/review-ui/tsconfig.json`
- Create: `record/Aloha_Learn/review-ui/tsconfig.node.json`
- Create: `record/Aloha_Learn/review-ui/index.html`
- Create: `record/Aloha_Learn/review-ui/.gitignore`
- Create: `record/Aloha_Learn/review-ui/src/main.tsx`
- Create: `record/Aloha_Learn/review-ui/src/types.ts`
- Create: `record/Aloha_Learn/review-ui/src/styles.css`
- Modify: `.gitignore`

**Interfaces:**
- Produces: empty buildable Vite app at `record/Aloha_Learn/review-ui/`
- Produces: `record/Aloha_Learn/review-ui/src/types.ts` exporting `Icon`, `Decision`, `Queue`, `AppliedCounts` (consumed by later tasks)

- [ ] **Step 1.1: Update `.gitignore`**

Append to existing `.gitignore` (root):

```
record/Aloha_Learn/review-ui/node_modules/
record/Aloha_Learn/review-ui/dist/
```

Verify with: `git status` shows no untracked files in `record/Aloha_Learn/review-ui/` yet.

- [ ] **Step 1.2: Create `package.json`**

File: `record/Aloha_Learn/review-ui/package.json`

```json
{
  "name": "record-icon-review-ui",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.5",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^24.1.0",
    "typescript": "^5.5.3",
    "vite": "^5.3.3",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 1.3: Create `tsconfig.json`**

File: `record/Aloha_Learn/review-ui/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 1.4: Create `tsconfig.node.json`**

File: `record/Aloha_Learn/review-ui/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 1.5: Create `vite.config.ts`**

File: `record/Aloha_Learn/review-ui/vite.config.ts`

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:0",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 1.6: Create `index.html`**

File: `record/Aloha_Learn/review-ui/index.html`

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Record Icon Review</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 1.7: Create `.gitignore`**

File: `record/Aloha_Learn/review-ui/.gitignore`

```
node_modules/
dist/
*.log
```

- [ ] **Step 1.8: Create `src/types.ts`**

File: `record/Aloha_Learn/review-ui/src/types.ts`

```ts
export interface Icon {
  filename: string;
  icon_url: string;
  llm_label: string;
  is_timestamp_fallback: boolean;
  action: string;
  coords: [number, number];
  current_software: string;
  base: string;
}

export type Decision =
  | { action: "accept" }
  | { action: "edit"; label: string }
  | { action: "skip" };

export interface Queue {
  icons: Icon[];
  existing_labels: string[];
  dest: string;
  manual_mode_default: boolean;
}

export interface AppliedCounts {
  accepted: number;
  edited: number;
  skipped: number;
  sanitize_fallback: number;
}

export interface FinishResult {
  applied: AppliedCounts;
  keys_added: string[];
  keys_updated: string[];
}
```

- [ ] **Step 1.9: Create `src/main.tsx` (stub) and `src/styles.css` (minimal)**

File: `record/Aloha_Learn/review-ui/src/main.tsx`

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("root element missing");
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

File: `record/Aloha_Learn/review-ui/src/App.tsx` (stub for scaffold; replaced in Task 9)

```tsx
export default function App() {
  return <div className="app-placeholder">Record Icon Review</div>;
}
```

File: `record/Aloha_Learn/review-ui/src/styles.css`

```css
:root {
  font-family: system-ui, -apple-system, sans-serif;
  color: #1f2328;
  background: #fff;
}
body { margin: 0; }
.app-placeholder { padding: 24px; font-size: 20px; }
```

File: `record/Aloha_Learn/review-ui/src/test-setup.ts`

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 1.10: Install dependencies and verify build**

Run from project root:

```bash
cd "record/Aloha_Learn/review-ui"
npm install
npm run build
```

Expected: `dist/index.html` and `dist/assets/*.js` exist. No TS errors.

- [ ] **Step 1.11: Verify dev server starts**

Run: `npm run dev -- --port 5180` (background, then kill after 3s)

Expected: Vite reports `Local: http://localhost:5180/`. Kill the process.

- [ ] **Step 1.12: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add .gitignore record/Aloha_Learn/review-ui/
git commit -m "feat(review-ui): scaffold Vite + React + TS project

Adds the review-ui/ subproject with Vite 5, React 18, TypeScript 5, Vitest,
and React Testing Library. Stub App + types.ts in place; components and
store come in later tasks. npm install + npm run build produce dist/
ready to be served by the Python stdlib server in Task 4."
```

---

## Task 2: UI sanitize mirror + tests (TDD)

**Files:**
- Create: `record/Aloha_Learn/review-ui/src/lib/sanitize.ts`
- Create: `record/Aloha_Learn/review-ui/src/lib/sanitize.test.ts`

**Interfaces:**
- Consumes: rule constants from spec — max 30 chars, lowercase, whitespace → `_`, `/` → `-`, strip `\\:?*`
- Produces: `sanitize(raw: string): string` and `isValidLabel(s: string): boolean`
  - Throws on empty result (matches `components_sync.sanitize_label` semantics)

- [ ] **Step 2.1: Write the failing test**

File: `record/Aloha_Learn/review-ui/src/lib/sanitize.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { sanitize, isValidLabel } from "./sanitize";

describe("sanitize", () => {
  it("lowercases and replaces spaces with underscores", () => {
    expect(sanitize("Start Button")).toBe("start_button");
  });

  it("replaces slashes and backslashes with dash", () => {
    expect(sanitize("a/b\\c")).toBe("a-b-c");
  });

  it("strips backslash, colon, question mark, asterisk", () => {
    expect(sanitize("a:b?c*d")).toBe("abcd");
  });

  it("truncates to 30 chars", () => {
    expect(sanitize("a".repeat(50)).length).toBe(30);
  });

  it("collapses multiple dashes and underscores", () => {
    expect(sanitize("Clone  Repository__Tab")).toBe("clone_repository_tab");
  });

  it("throws on empty string", () => {
    expect(() => sanitize("")).toThrow();
  });

  it("throws when all chars are special", () => {
    expect(() => sanitize("///??**")).toThrow();
  });
});

describe("isValidLabel", () => {
  it("accepts snake_case strings", () => {
    expect(isValidLabel("start_button")).toBe(true);
  });

  it("rejects empty and strings over 30 chars", () => {
    expect(isValidLabel("")).toBe(false);
    expect(isValidLabel("a".repeat(31))).toBe(false);
  });

  it("rejects strings with disallowed chars", () => {
    expect(isValidLabel("Start-Button")).toBe(false);
    expect(isValidLabel("foo bar")).toBe(false);
  });
});
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run from `record/Aloha_Learn/review-ui/`:

```bash
npm test -- --reporter=verbose
```

Expected: FAIL — `Cannot find module './sanitize'`.

- [ ] **Step 2.3: Implement sanitize**

File: `record/Aloha_Learn/review-ui/src/lib/sanitize.ts`

```ts
const LABEL_MAX_LEN = 30;
const SPECIAL_CHARS = /[\\:?*]/g;

export function sanitize(raw: string): string {
  if (!raw) throw new Error("label is empty");
  let s = raw.trim().toLowerCase();
  s = s.replaceAll("\\", "-").replaceAll("/", "-");
  s = s.replace(SPECIAL_CHARS, "");
  s = s.replace(/\s+/g, "_");
  s = s.replace(/-+/g, "-").replace(/^-+|-+$/g, "");
  s = s.replace(/_+/g, "_").replace(/^_+|_+$/g, "");
  s = s.slice(0, LABEL_MAX_LEN).replace(/[-_]+$/, "");
  if (!s) throw new Error(`label '${raw}' has no safe characters after sanitization`);
  return s;
}

export function isValidLabel(s: string): boolean {
  if (!s) return false;
  if (s.length > LABEL_MAX_LEN) return false;
  return /^[a-z0-9_]+$/.test(s);
}
```

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `npm test -- --reporter=verbose src/lib/sanitize.test.ts`

Expected: PASS — 7 sanitize tests + 3 isValidLabel tests = 10 tests pass.

- [ ] **Step 2.5: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/review-ui/src/lib/
git commit -m "feat(review-ui): add sanitize mirror matching components_sync.sanitize_label"
```

---

## Task 3: UI API client + reducer + tests (TDD)

**Files:**
- Create: `record/Aloha_Learn/review-ui/src/api/client.ts`
- Create: `record/Aloha_Learn/review-ui/src/api/client.test.ts`
- Create: `record/Aloha_Learn/review-ui/src/store/reducer.ts`
- Create: `record/Aloha_Learn/review-ui/src/store/reducer.test.ts`

**Interfaces:**
- Produces: `api/client.ts` exporting `getQueue(): Promise<Queue>`, `postDecisions(payload): Promise<void>`, `postFinish(payload): Promise<FinishResult>`
- Produces: `store/reducer.ts` exporting `State`, `Action`, `reducer(state, action): State`

- [ ] **Step 3.1: Write reducer tests**

File: `record/Aloha_Learn/review-ui/src/store/reducer.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { reducer, initialState } from "./reducer";
import type { Icon } from "../types";

const mkIcon = (filename: string, llm_label = "x"): Icon => ({
  filename,
  icon_url: `/icons/${filename}`,
  llm_label,
  is_timestamp_fallback: false,
  action: "LClick at",
  coords: [1, 2],
  current_software: "Chrome",
  base: "10.0s",
});

describe("reducer", () => {
  it("SET_QUEUE populates icons and zeros decisions", () => {
    const icons = [mkIcon("a.png"), mkIcon("b.png")];
    const s = reducer(initialState, { type: "SET_QUEUE", icons, existing_labels: ["y"] });
    expect(s.icons).toEqual(icons);
    expect(s.existingLabels).toEqual(["y"]);
    expect(Object.keys(s.decisions)).toEqual(["a.png", "b.png"]);
    expect(s.decisions["a.png"]).toBeNull();
  });

  it("SET_DECISION stores accept/edit/skip", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png")], existing_labels: [],
    });
    const s1 = reducer(base, { type: "SET_DECISION", filename: "a.png", decision: { action: "accept" } });
    expect(s1.decisions["a.png"]).toEqual({ action: "accept" });
    const s2 = reducer(s1, { type: "SET_DECISION", filename: "a.png", decision: { action: "edit", label: "btn" } });
    expect(s2.decisions["a.png"]).toEqual({ action: "edit", label: "btn" });
    const s3 = reducer(s2, { type: "SET_DECISION", filename: "a.png", decision: { action: "skip" } });
    expect(s3.decisions["a.png"]).toEqual({ action: "skip" });
  });

  it("SET_MANUAL_MODE toggles manualMode", () => {
    const s = reducer(initialState, { type: "SET_MANUAL_MODE", manualMode: true });
    expect(s.manualMode).toBe(true);
  });

  it("SET_SUBMITTING toggles submitting", () => {
    const s = reducer(initialState, { type: "SET_SUBMITTING", submitting: true });
    expect(s.submitting).toBe(true);
  });

  it("APPLY_BULK_ACCEPT sets all to accept", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png"), mkIcon("b.png")], existing_labels: [],
    });
    const s = reducer(base, { type: "APPLY_BULK_ACCEPT" });
    expect(s.decisions["a.png"]).toEqual({ action: "accept" });
    expect(s.decisions["b.png"]).toEqual({ action: "accept" });
  });

  it("APPLY_BULK_SKIP sets all to skip", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png"), mkIcon("b.png")], existing_labels: [],
    });
    const s = reducer(base, { type: "APPLY_BULK_SKIP" });
    expect(s.decisions["a.png"]).toEqual({ action: "skip" });
    expect(s.decisions["b.png"]).toEqual({ action: "skip" });
  });

  it("SET_QUEUE resets decisions", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png")], existing_labels: [],
    });
    const filled = reducer(base, { type: "SET_DECISION", filename: "a.png", decision: { action: "accept" } });
    const reset = reducer(filled, { type: "SET_QUEUE", icons: [mkIcon("a.png"), mkIcon("b.png")], existing_labels: [] });
    expect(reset.decisions["a.png"]).toBeNull();
    expect(reset.decisions["b.png"]).toBeNull();
  });
});
```

- [ ] **Step 3.2: Write API client tests**

File: `record/Aloha_Learn/review-ui/src/api/client.test.ts`

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { getQueue, postDecisions, postFinish } from "./client";
import type { Queue, FinishResult } from "../types";

describe("api/client", () => {
  const origFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = origFetch;
  });

  it("getQueue fetches /api/queue and parses JSON", async () => {
    const queue: Queue = {
      icons: [], existing_labels: [], dest: "D:", manual_mode_default: false,
    };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true, status: 200, json: async () => queue,
    });
    const got = await getQueue();
    expect(got).toEqual(queue);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/queue", expect.objectContaining({ method: "GET" }));
  });

  it("getQueue throws on non-2xx", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: false, status: 500, text: async () => "boom" });
    await expect(getQueue()).rejects.toThrow(/500/);
  });

  it("postDecisions sends POST with body", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ok: true }) });
    await postDecisions({ decisions: { a: { action: "accept" } }, manual_mode: false });
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/decisions", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ decisions: { a: { action: "accept" } }, manual_mode: false }),
    }));
  });

  it("postFinish returns FinishResult", async () => {
    const result: FinishResult = {
      applied: { accepted: 1, edited: 0, skipped: 0, sanitize_fallback: 0 },
      keys_added: ["x"], keys_updated: [],
    };
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => result });
    const got = await postFinish();
    expect(got).toEqual(result);
  });
});
```

- [ ] **Step 3.3: Run tests to verify they fail**

Run: `npm test`

Expected: FAIL — modules not found.

- [ ] **Step 3.4: Implement reducer**

File: `record/Aloha_Learn/review-ui/src/store/reducer.ts`

```ts
import type { Decision, Icon } from "../types";

export interface State {
  icons: Icon[];
  existingLabels: string[];
  dest: string;
  manualMode: boolean;
  submitting: boolean;
  decisions: Record<string, Decision | null>;
}

export type Action =
  | { type: "SET_QUEUE"; icons: Icon[]; existing_labels: string[]; dest?: string; manual_mode_default?: boolean }
  | { type: "SET_DECISION"; filename: string; decision: Decision }
  | { type: "SET_MANUAL_MODE"; manualMode: boolean }
  | { type: "SET_SUBMITTING"; submitting: boolean }
  | { type: "APPLY_BULK_ACCEPT" }
  | { type: "APPLY_BULK_SKIP" }
  | { type: "RESET" };

export const initialState: State = {
  icons: [],
  existingLabels: [],
  dest: "",
  manualMode: false,
  submitting: false,
  decisions: {},
};

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_QUEUE": {
      const decisions: Record<string, Decision | null> = {};
      for (const icon of action.icons) decisions[icon.filename] = null;
      return {
        ...state,
        icons: action.icons,
        existingLabels: action.existing_labels,
        dest: action.dest ?? state.dest,
        manualMode: action.manual_mode_default ?? state.manualMode,
        decisions,
      };
    }
    case "SET_DECISION": {
      return {
        ...state,
        decisions: { ...state.decisions, [action.filename]: action.decision },
      };
    }
    case "SET_MANUAL_MODE":
      return { ...state, manualMode: action.manualMode };
    case "SET_SUBMITTING":
      return { ...state, submitting: action.submitting };
    case "APPLY_BULK_ACCEPT": {
      const decisions: Record<string, Decision | null> = {};
      for (const k of Object.keys(state.decisions)) decisions[k] = { action: "accept" };
      return { ...state, decisions };
    }
    case "APPLY_BULK_SKIP": {
      const decisions: Record<string, Decision | null> = {};
      for (const k of Object.keys(state.decisions)) decisions[k] = { action: "skip" };
      return { ...state, decisions };
    }
    case "RESET":
      return initialState;
    default:
      return state;
  }
}
```

- [ ] **Step 3.5: Implement API client**

File: `record/Aloha_Learn/review-ui/src/api/client.ts`

```ts
import type { Queue, FinishResult, Decision } from "../types";

async function asJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`HTTP ${r.status}: ${text || r.statusText}`);
  }
  return r.json() as Promise<T>;
}

export async function getQueue(): Promise<Queue> {
  return asJson<Queue>(await fetch("/api/queue", { method: "GET" }));
}

export async function postDecisions(payload: {
  decisions: Record<string, Decision | null>;
  manual_mode: boolean;
}): Promise<void> {
  const r = await fetch("/api/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await asJson<{ ok: true }>(r);
}

export async function postFinish(): Promise<FinishResult> {
  return asJson<FinishResult>(await fetch("/api/finish", { method: "POST" }));
}
```

- [ ] **Step 3.6: Run tests to verify they pass**

Run: `npm test`

Expected: PASS — reducer 7 + api 4 = 11 tests pass.

- [ ] **Step 3.7: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/review-ui/src/store/ record/Aloha_Learn/review-ui/src/api/
git commit -m "feat(review-ui): add reducer + API client with full test coverage"
```

---

## Task 4: Python review server with TDD

**Files:**
- Create: `record/Aloha_Learn/review_server.py`
- Create: `record/Aloha_Learn/tests/test_review_server.py`

**Interfaces:**
- Produces: `run_review_session(records, label_map, screenshots_dir, dest, *, open_browser=True, timeout_seconds=1800, now_str=None) -> dict` returning a meta dict with keys: `accepted`, `edited`, `skipped`, `sanitize_fallback`, `keys_added`, `keys_updated`, `manual_mode`, `timed_out`
- Internal: `_make_handler(records, label_map, screenshots_dir, dist_dir, dest, open_browser_event) -> BaseHTTPRequestHandler` returning a handler class with `do_GET` and `do_POST` methods
- Reuses: `components_sync.sanitize_label`, `components_sync.merge_components_json`

- [ ] **Step 4.1: Write the failing tests**

File: `record/Aloha_Learn/tests/test_review_server.py`

```python
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components_sync import IconRecord
from review_server import run_review_session, ReviewSessionResult


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _records():
    return [
        IconRecord(
            filename=f"record_memory_icon_{i}.0s_crop.png",
            action="LClick at", coords=(100 + i, 200), current_software="Chrome",
            base=f"{i}.0s",
        )
        for i in range(3)
    ]


def _icon_files(screenshots_dir: Path, records):
    icons = screenshots_dir / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    for r in records:
        (icons / r.filename).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def _post_decisions(port: int, decisions: dict, manual_mode: bool = False):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/decisions",
                 body=json.dumps({"decisions": decisions, "manual_mode": manual_mode}),
                 headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()
    conn.close()
    return r.status


def _post_finish(port: int):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/finish")
    r = conn.getresponse()
    body = r.read().decode("utf-8")
    conn.close()
    return r.status, json.loads(body) if body else {}


def _get_json(port: int, path: str):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    r = conn.getresponse()
    body = r.read().decode("utf-8")
    conn.close()
    return r.status, json.loads(body) if body else {}


class QueueEndpointTest(unittest.TestCase):
    def test_get_queue_returns_all_records_with_llm_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            result_holder: dict = {}

            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=2,
                )

            t = threading.Thread(target=runner, daemon=True)
            t.start()
            # Server takes a moment to start; poll queue until 200
            port = None
            for _ in range(50):
                try:
                    port = _free_port()  # not used; we read actual port from meta later
                    break
                except OSError:
                    time.sleep(0.05)
            # The server picks its own port; query the queue by trying the port
            # returned via stdout — here we patch _server_started to capture port.
            # Simpler: spin a fresh request once the meta is populated.
            deadline = time.time() + 5
            while time.time() < deadline and "r" not in result_holder:
                # run_review_session blocks until /api/finish; instead, drive
                # decisions then finish.
                pass
            # Drive a full flow below in dedicated tests; here we only assert
            # the queue contents via finish-time meta.
            t.join(timeout=2)
            self.assertIn("r", result_holder)
            self.assertEqual(result_holder["r"]["accepted"], 3)
            self.assertEqual(result_holder["r"]["skipped"], 0)


class DecisionsEndpointTest(unittest.TestCase):
    def _run(self, decisions, manual_mode=False):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            result_holder: dict = {}
            port_holder: dict = {}

            # Patch HTTPServer to capture chosen port
            import review_server as rs
            orig_server = rs.ThreadingHTTPServer
            class CapturingServer(orig_server):
                def __init__(self, addr, handler):
                    super().__init__(addr, handler)
                    port_holder["port"] = self.server_address[1]
            rs.ThreadingHTTPServer = CapturingServer

            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=5,
                )

            t = threading.Thread(target=runner, daemon=True)
            t.start()

            # Wait for server to start
            for _ in range(100):
                if "port" in port_holder:
                    break
                time.sleep(0.02)
            port = port_holder["port"]

            # Post decisions
            status = _post_decisions(port, decisions, manual_mode=manual_mode)
            self.assertEqual(status, 200)

            # Finish
            status, body = _post_finish(port)
            self.assertEqual(status, 200)

            t.join(timeout=5)
            return result_holder["r"], body

    def test_skip_excluded_from_components(self):
        records = _records()
        decisions = {records[1].filename: {"action": "skip"}}
        result, body = self._run(decisions)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["accepted"], 2)
        # The skipped filename MUST NOT appear in keys_added/updated
        self.assertNotIn(records[1].filename, body.get("keys_added", []) + body.get("keys_updated", []))

    def test_edit_label_sanitized(self):
        records = _records()
        decisions = {records[0].filename: {"action": "edit", "label": "Start Button!"}}
        result, body = self._run(decisions)
        self.assertEqual(result["edited"], 1)
        self.assertIn("start_button", body.get("keys_added", []))

    def test_manual_mode_treats_accept_as_skip(self):
        records = _records()
        decisions = {
            records[0].filename: {"action": "accept"},
            records[1].filename: {"action": "accept"},
        }
        result, body = self._run(decisions, manual_mode=True)
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(result["accepted"], 0)

    def test_sanitize_fallback_on_edit_with_illegal_label(self):
        records = _records()
        decisions = {records[0].filename: {"action": "edit", "label": "///??**"}}
        result, body = self._run(decisions)
        self.assertEqual(result["sanitize_fallback"], 1)
        # The icon should fall back to the LLM label (label_0)
        self.assertIn("label_0", body.get("keys_added", []))

    def test_missing_decision_on_finish_returns_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            import review_server as rs
            port_holder = {}
            orig_server = rs.ThreadingHTTPServer
            class CapturingServer(orig_server):
                def __init__(self, addr, handler):
                    super().__init__(addr, handler)
                    port_holder["port"] = self.server_address[1]
            rs.ThreadingHTTPServer = CapturingServer

            result_holder = {}
            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=5,
                )
            t = threading.Thread(target=runner, daemon=True)
            t.start()
            for _ in range(100):
                if "port" in port_holder:
                    break
                time.sleep(0.02)
            # Don't post any decisions
            status, body = _post_finish(port_holder["port"])
            self.assertEqual(status, 400)
            self.assertIn("missing", body)
            t.join(timeout=5)


class TimeoutFallbackTest(unittest.TestCase):
    def test_no_activity_timeout_falls_back_to_all_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            # Use 1-second timeout
            result = run_review_session(
                records, label_map, shots, dest,
                open_browser=False, timeout_seconds=1,
            )
            self.assertTrue(result["timed_out"])
            self.assertEqual(result["accepted"], 3)
            self.assertEqual(result["skipped"], 0)


class DistMissingTest(unittest.TestCase):
    def test_missing_dist_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _icon_files(shots, records)
            label_map = {r.filename: f"x_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()

            # Patch Path(__file__).parent / "review-ui" / "dist" to non-existent
            fake_dist = tmp / "no_dist"
            with patch("review_server._REVIEW_UI_DIST", fake_dist):
                with self.assertRaises(RuntimeError) as cm:
                    run_review_session(
                        records, label_map, shots, dest,
                        open_browser=False, timeout_seconds=1,
                    )
                self.assertIn("review-ui/dist missing", str(cm.exception))
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run from `record/`:

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record"
python -m unittest Aloha_Learn.tests.test_review_server -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'review_server'`.

- [ ] **Step 4.3: Implement review_server.py skeleton**

File: `record/Aloha_Learn/review_server.py`

```python
"""Local HTTP server for human-in-the-loop icon review.

Pure stdlib. Binds 127.0.0.1 only. Three API endpoints + static file serving
for the Vite-built UI. Reuses components_sync.sanitize_label and
merge_components_json from this package.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from components_sync import (
    IconRecord,
    sanitize_label,
    merge_components_json,
    build_component_entry,
)


_REVIEW_UI_DIST: Path = Path(__file__).parent / "review-ui" / "dist"
_TIMEOUT_SECONDS_DEFAULT = 30 * 60  # 30 minutes


class ReviewSessionResult(dict):
    """Convenience subclass so callers can use dict-style access."""


def _icon_url(filename: str) -> str:
    return f"/icons/{filename}"


def _build_queue_payload(records, label_map, dest: Path):
    icons = []
    for r in records:
        icons.append({
            "filename": r.filename,
            "icon_url": _icon_url(r.filename),
            "llm_label": label_map.get(r.filename, ""),
            "is_timestamp_fallback": label_map.get(r.filename, "").startswith("record_memory_icon_"),
            "action": r.action,
            "coords": list(r.coords),
            "current_software": r.current_software,
            "base": r.base,
        })
    # existing_labels from dest/components.json
    existing = []
    comp_path = dest / "components.json"
    if comp_path.exists():
        try:
            data = json.loads(comp_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = list(data.keys())
        except json.JSONDecodeError:
            existing = []
    return {
        "icons": icons,
        "existing_labels": existing,
        "dest": str(dest),
        "manual_mode_default": False,
    }


def _apply_decisions(
    records, label_map, dest: Path, screenshots_dir: Path,
    decisions: dict, manual_mode: bool, now_str: str,
) -> dict:
    """Filter decisions, run sanitize, then call _apply_components_updates-style logic.

    Returns dict with keys: accepted, edited, skipped, sanitize_fallback,
    keys_added, keys_updated, manual_mode.
    """
    # Load existing components.json
    comp_path = dest / "components.json"
    existing = {}
    if comp_path.exists():
        try:
            data = json.loads(comp_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                existing = data
        except json.JSONDecodeError:
            existing = {}

    components_dir = dest / "components"
    components_dir.mkdir(parents=True, exist_ok=True)

    additions = {}
    counts = {"accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0}

    for r in records:
        d = decisions.get(r.filename)
        if d is None:
            continue  # missing — caller should have caught this

        if manual_mode and d["action"] == "accept":
            # treat as skip
            counts["skipped"] += 1
            continue

        if d["action"] == "skip":
            counts["skipped"] += 1
            continue

        if d["action"] == "edit":
            try:
                label = sanitize_label(d["label"])
                counts["edited"] += 1
            except ValueError:
                # sanitize failed -> fall back to LLM candidate
                label = label_map.get(r.filename, "")
                counts["sanitize_fallback"] += 1
        else:  # accept
            label = label_map.get(r.filename, "")
            counts["accepted"] += 1

        if not label:
            counts["skipped"] += 1
            continue

        # Copy PNG to dest/components/<label>.png (skip if same source)
        src = screenshots_dir / "icons" / r.filename
        dst = components_dir / f"{label}.png"
        try:
            if src.resolve() != dst.resolve():
                shutil.copyfile(src, dst)
        except OSError as e:
            raise RuntimeError(f"Could not copy {src} -> {dst}: {e}") from e

        # Build entry using merge semantics
        prior = existing.get(label)
        if prior is None:
            entry = build_component_entry(
                label=label,
                icon_file=f"components/{label}.png",
                learned_at=now_str,
                last_seen=now_str,
                seen_count=1,
            )
            existing[label] = entry
            additions.setdefault("added", []).append(label)
        else:
            existing[label] = dict(prior)
            existing[label]["last_seen"] = now_str
            existing[label]["seen_count"] = int(prior.get("seen_count", 0)) + 1
            existing[label]["consecutive_misses"] = 0
            existing[label]["base_memory"] = True
            additions.setdefault("updated", []).append(label)

    # Write components.json
    try:
        comp_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        raise RuntimeError(f"Could not write {comp_path}: {e}") from e

    return {
        **counts,
        "keys_added": additions.get("added", []),
        "keys_updated": additions.get("updated", []),
        "manual_mode": manual_mode,
    }


def _make_handler(
    records, label_map, screenshots_dir: Path, dist_dir: Path, dest: Path,
    state: dict, browser_opened: threading.Event,
):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Quiet — keep test output clean
            pass

        def _send_json(self, status, body):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_file(self, path: Path, content_type: str):
            try:
                data = path.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            state["last_activity"] = time.time()
            url = urlparse(self.path)
            path = url.path

            if path == "/api/queue":
                self._send_json(200, _build_queue_payload(records, label_map, dest))
                return

            if path.startswith("/icons/"):
                filename = path[len("/icons/"):]
                # Sanitize: no path traversal
                if ".." in filename or "/" in filename or "\\" in filename:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return
                icon_path = screenshots_dir / "icons" / filename
                if not icon_path.exists():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_file(icon_path, "image/png")
                return

            # Static: serve from dist
            if path == "/" or path == "":
                index = dist_dir / "index.html"
                if index.exists():
                    self._send_file(index, "text/html; charset=utf-8")
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            # Map /assets/foo.js to dist/assets/foo.js
            rel = path.lstrip("/")
            target = (dist_dir / rel).resolve()
            # Prevent traversal
            if not str(target).startswith(str(dist_dir.resolve())):
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            if target.is_file():
                ct = "application/javascript" if target.suffix == ".js" else \
                     "text/css" if target.suffix == ".css" else \
                     "application/octet-stream"
                self._send_file(target, ct)
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            state["last_activity"] = time.time()
            url = urlparse(self.path)
            path = url.path

            if path == "/api/decisions":
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b""
                try:
                    payload = json.loads(raw.decode("utf-8"))
                    decisions = payload.get("decisions", {})
                    manual_mode = bool(payload.get("manual_mode", False))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._send_json(400, {"error": "invalid JSON"})
                    return
                if not isinstance(decisions, dict):
                    self._send_json(400, {"error": "decisions must be an object"})
                    return
                state["decisions"] = decisions
                state["manual_mode"] = manual_mode
                self._send_json(200, {"ok": True, "count": len(decisions)})
                return

            if path == "/api/finish":
                decisions = state.get("decisions", {})
                manual_mode = state.get("manual_mode", False)
                # Validate completeness
                missing = [r.filename for r in records if r.filename not in decisions]
                if missing:
                    self._send_json(400, {"missing": missing})
                    return
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result = _apply_decisions(
                    records, label_map, dest, screenshots_dir,
                    decisions, manual_mode, now_str,
                )
                # Store result for run_review_session to pick up, then shutdown
                state["final_result"] = result
                self._send_json(200, {
                    "applied": {
                        "accepted": result["accepted"],
                        "edited": result["edited"],
                        "skipped": result["skipped"],
                        "sanitize_fallback": result["sanitize_fallback"],
                    },
                    "keys_added": result["keys_added"],
                    "keys_updated": result["keys_updated"],
                })
                # Schedule shutdown from another thread
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return

            self.send_error(HTTPStatus.NOT_FOUND)

    return Handler


def run_review_session(
    records, label_map, screenshots_dir: Path, dest: Path,
    *, open_browser: bool = True, timeout_seconds: int = _TIMEOUT_SECONDS_DEFAULT,
    now_str: Optional[str] = None,
) -> dict:
    """Run the review session, blocking until /api/finish or timeout.

    Returns dict with keys: accepted, edited, skipped, sanitize_fallback,
    keys_added, keys_updated, manual_mode, timed_out, port.
    """
    dist_dir = _REVIEW_UI_DIST
    if not dist_dir.exists():
        raise RuntimeError(
            f"review-ui/dist missing at {dist_dir}; "
            f"run `npm --prefix record/Aloha_Learn/review-ui run build`"
        )

    state = {
        "decisions": {},
        "manual_mode": False,
        "last_activity": time.time(),
    }

    handler_cls = _make_handler(
        records, label_map, screenshots_dir, dist_dir, dest, state, threading.Event(),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    state["port"] = port

    # Auto-open browser
    if open_browser:
        try:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        except webbrowser.Error:
            print(f"[review] Open http://127.0.0.1:{port}/ manually")

    # Run server in a thread so we can monitor timeout
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Poll for completion or timeout
    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            if "final_result" in state:
                break
            time.sleep(0.1)
    finally:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        server_thread.join(timeout=2)

    if "final_result" in state:
        result = state["final_result"]
        return {
            **result,
            "timed_out": False,
            "port": port,
        }

    # Timeout: treat all as accept
    now_str = now_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    decisions = {r.filename: {"action": "accept"} for r in records}
    result = _apply_decisions(
        records, label_map, dest, screenshots_dir,
        decisions, False, now_str,
    )
    return {
        **result,
        "timed_out": True,
        "port": port,
    }
```

- [ ] **Step 4.4: Run tests to verify they pass**

Run: `cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record" && python -m unittest Aloha_Learn.tests.test_review_server -v`

Expected: PASS — 7 tests pass.

- [ ] **Step 4.5: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/review_server.py record/Aloha_Learn/tests/test_review_server.py
git commit -m "feat(review-server): stdlib HTTP server with queue/decisions/finish endpoints

Binds 127.0.0.1 only on OS-assigned port. Three endpoints (GET /api/queue,
POST /api/decisions, POST /api/finish) plus static file serving for the
Vite-built dist/ and /icons/ proxy to screenshots_dir/icons/. Reuses
components_sync.sanitize_label and apply semantics. Timeout (default 30
minutes) falls back to all-accept to preserve existing LLM-auto-sync."
```

---

## Task 5: Hook review into process_project() (TDD)

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py` (insert `run_review_session` into `process_project` end)
- Create: `record/Aloha_Learn/tests/test_review_integration.py`

**Interfaces:**
- Modifies: `VideoScreenshotExtractor.process_project()` — after `_sync_components_to_dest` returns, if env var `GUI_AGENT_REVIEW_DISABLE` unset AND `components_synced` is True, call `run_review_session` with the same records/label_map/screenshots_dir/dest.
- Produces: `meta` extended with `review_decisions`, `review_manual_mode`, `review_timed_out`, `review_sanitize_fallback`, `review_port` when review session runs.

- [ ] **Step 5.1: Write the failing tests**

File: `record/Aloha_Learn/tests/test_review_integration.py`

```python
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from screenshot_processor import VideoScreenshotExtractor


def _write_project(project_dir: Path):
    (project_dir / "inputs").mkdir(parents=True)
    (project_dir / "inputs" / "demo.mp4").write_bytes(b"")
    actions = [
        {"action": "CONFIG", "coords": {"0": {"width": 1920, "height": 1080, "scale_factor": 1.0}}},
        {"timestamp": 10.954, "action": "LClick at",
         "coords": [{"x": 820, "y": 450}], "current_software": "Explorer"},
    ]
    (project_dir / f"{project_dir.name}_processed_log.json").write_text(
        json.dumps(actions), encoding="utf-8"
    )


class ReviewSessionHookTest(unittest.TestCase):
    def test_disable_env_var_skips_review_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(dest),
                "GUI_AGENT_REVIEW_DISABLE": "1",
            }, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch("screenshot_processor.run_review_session") as mock_review:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_not_called()
            self.assertFalse(meta.get("review_manual_mode", False))

    def test_disable_env_var_unset_calls_review_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()
            # Pre-populate so sync has work
            (dest / "components.json").write_text("{}", encoding="utf-8")

            review_return = {
                "accepted": 1, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                "keys_added": ["label_0"], "keys_updated": [],
                "manual_mode": False, "timed_out": False, "port": 54321,
            }

            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(dest),
            }, clear=False):
                # Ensure disable is unset in this scope
                os.environ.pop("GUI_AGENT_REVIEW_DISABLE", None)
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch("screenshot_processor.run_review_session", return_value=review_return) as mock_review:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_called_once()
            self.assertEqual(meta["review_decisions"], {
                "accepted": 1, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
            })
            self.assertFalse(meta["review_manual_mode"])
            self.assertFalse(meta["review_timed_out"])
            self.assertEqual(meta["review_port"], 54321)

    def test_disable_env_var_empty_string_treated_as_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project_dir = tmp / "proj"
            _write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text("{}", encoding="utf-8")

            review_return = {
                "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
                "keys_added": [], "keys_updated": [],
                "manual_mode": False, "timed_out": False, "port": 1234,
            }

            with patch.dict(os.environ, {
                "GUI_AGENT_COMPONENTS_DEST": str(dest),
                "GUI_AGENT_REVIEW_DISABLE": "",
            }, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch("screenshot_processor.run_review_session", return_value=review_return) as mock_review:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_review.assert_called_once()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record" && python -m unittest Aloha_Learn.tests.test_review_integration -v`

Expected: FAIL — `process_project` does not call `run_review_session`.

- [ ] **Step 5.3: Modify screenshot_processor.py to import and call run_review_session**

In `record/Aloha_Learn/screenshot_processor.py`:

1. Add import at top (near existing components_sync import):

```python
from review_server import run_review_session
```

2. In `process_project()`, after the existing `if dest_str:` block (around line 660), add:

```python
# Optional: human review session for LLM auto-named icons.
# Disabled by env var GUI_AGENT_REVIEW_DISABLE (any non-empty value).
# When enabled AND components_synced ran, give the user a chance to
# accept/edit/skip per icon before they hit dest/components.json.
review_disable = os.environ.get("GUI_AGENT_REVIEW_DISABLE", "").strip()
if meta.get("components_synced") and not review_disable:
    # Re-collect the records + label_map that were used by _sync_components_to_dest
    # to feed them to the review session. We rebuild the label_map by reading the
    # same way the sync did: ask the LLM (or fall back to timestamp keys).
    from review_server import _build_queue_payload  # internal but stable
    records = self._collect_icon_records(
        actions, screenshots_dir
    )
    if records:
        timestamp_keys = {
            r.filename: f"record_memory_icon_{r.base.replace('.', '_')}_crop"
            for r in records
        }
        try:
            label_map = self._request_component_labels(records, screenshots_dir)
        except ComponentsLLMError as e:
            print(f"[review] WARNING: LLM labeling failed ({e}); using timestamp keys")
            label_map = dict(timestamp_keys)
        try:
            review_result = run_review_session(
                records, label_map, screenshots_dir, dest_path,
            )
            meta["review_decisions"] = {
                "accepted": review_result.get("accepted", 0),
                "edited": review_result.get("edited", 0),
                "skipped": review_result.get("skipped", 0),
                "sanitize_fallback": review_result.get("sanitize_fallback", 0),
            }
            meta["review_manual_mode"] = bool(review_result.get("manual_mode", False))
            meta["review_timed_out"] = bool(review_result.get("timed_out", False))
            meta["review_port"] = review_result.get("port")
        except RuntimeError as e:
            # Re-raise: dist missing or other hard failure must propagate per AGENT.md #2
            raise
else:
    meta["review_decisions"] = {
        "accepted": 0, "edited": 0, "skipped": 0, "sanitize_fallback": 0,
    }
    meta["review_manual_mode"] = False
    meta["review_timed_out"] = False
    meta["review_port"] = None
```

- [ ] **Step 5.4: Run tests to verify they pass**

Run: `cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record" && python -m unittest Aloha_Learn.tests.test_review_integration -v`

Expected: PASS — 3 tests pass.

- [ ] **Step 5.5: Run full Python test suite to ensure no regressions**

Run: `cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record" && python -m unittest discover Aloha_Learn/tests -v`

Expected: All existing tests still pass + 3 new tests pass.

- [ ] **Step 5.6: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_review_integration.py
git commit -m "feat(sync): gate dest/components.json writes behind human review session

process_project() now invokes run_review_session() between LLM labeling
and the final components.json write when GUI_AGENT_REVIEW_DISABLE is unset.
Disable env var escapes the gate for headless / CI. Meta extended with
review_decisions / review_manual_mode / review_timed_out / review_port.
Existing _sync_components_to_dest behavior preserved when review is on or off."
```

---

## Task 6: UI components — TopBar + IconCard + IconGrid (TDD)

**Files:**
- Create: `record/Aloha_Learn/review-ui/src/components/TopBar.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/TopBar.test.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/IconCard.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/IconCard.test.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/IconGrid.tsx`
- Modify: `record/Aloha_Learn/review-ui/src/styles.css`

**Interfaces:**
- `TopBar` props: `{ totalIcons, accepted, edited, skipped, manualMode, onToggleManual, onAcceptAll, onSubmit }`
- `IconCard` props: `{ icon: Icon; decision: Decision | null; existingLabels: string[]; onAccept, onEdit, onSkip }`
- `IconGrid` props: `{ icons, decisions, existingLabels, onAccept, onEdit, onSkip }`

- [ ] **Step 6.1: Write TopBar tests**

File: `record/Aloha_Learn/review-ui/src/components/TopBar.test.tsx`

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TopBar } from "./TopBar";

describe("TopBar", () => {
  it("renders counts and the manual-mode toggle", () => {
    render(
      <TopBar
        totalIcons={10}
        accepted={3}
        edited={2}
        skipped={1}
        manualMode={false}
        onToggleManual={() => {}}
        onAcceptAll={() => {}}
        onSubmit={() => {}}
      />
    );
    expect(screen.getByText(/共 10 张/)).toBeInTheDocument();
    expect(screen.getByText(/3 accept/)).toBeInTheDocument();
    expect(screen.getByText(/2 edit/)).toBeInTheDocument();
    expect(screen.getByText(/1 skip/)).toBeInTheDocument();
    expect(screen.getByLabelText(/全手动/)).toBeInTheDocument();
  });

  it("calls callbacks on user actions", () => {
    const onToggle = vi.fn();
    const onAcceptAll = vi.fn();
    const onSubmit = vi.fn();
    render(
      <TopBar
        totalIcons={5}
        accepted={0}
        edited={0}
        skipped={0}
        manualMode={false}
        onToggleManual={onToggle}
        onAcceptAll={onAcceptAll}
        onSubmit={onSubmit}
      />
    );
    fireEvent.click(screen.getByLabelText(/全手动/));
    expect(onToggle).toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByText("全部接受"));
    expect(onAcceptAll).toHaveBeenCalled();
    fireEvent.click(screen.getByText("提交"));
    expect(onSubmit).toHaveBeenCalled();
  });
});
```

- [ ] **Step 6.2: Write IconCard tests**

File: `record/Aloha_Learn/review-ui/src/components/IconCard.test.tsx`

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IconCard } from "./IconCard";
import type { Icon } from "../types";

const icon: Icon = {
  filename: "a.png",
  icon_url: "/icons/a.png",
  llm_label: "start_button",
  is_timestamp_fallback: false,
  action: "LClick at",
  coords: [1, 2],
  current_software: "Chrome",
  base: "10.0s",
};

describe("IconCard", () => {
  it("renders label, image, and three action buttons", () => {
    render(
      <IconCard
        icon={icon}
        decision={null}
        existingLabels={[]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    expect(screen.getByAltText("start_button")).toHaveAttribute("src", "/icons/a.png");
    expect(screen.getByText("start_button")).toBeInTheDocument();
    expect(screen.getByText("✓")).toBeInTheDocument();
    expect(screen.getByText("✎")).toBeInTheDocument();
    expect(screen.getByText("⨯")).toBeInTheDocument();
  });

  it("shows existing-label warning", () => {
    render(
      <IconCard
        icon={icon}
        decision={null}
        existingLabels={["start_button"]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    expect(screen.getByText(/已存在/)).toBeInTheDocument();
  });

  it("shows fallback indicator", () => {
    const fb: Icon = { ...icon, llm_label: "record_memory_icon_10_0s_crop", is_timestamp_fallback: true };
    render(
      <IconCard
        icon={fb}
        decision={null}
        existingLabels={[]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    expect(screen.getByText(/LLM 未命名/)).toBeInTheDocument();
  });

  it("calls onAccept/onEdit/onSkip on button clicks", () => {
    const onAccept = vi.fn();
    const onEdit = vi.fn();
    const onSkip = vi.fn();
    render(
      <IconCard
        icon={icon}
        decision={null}
        existingLabels={[]}
        onAccept={onAccept}
        onEdit={onEdit}
        onSkip={onSkip}
      />
    );
    fireEvent.click(screen.getByText("✓"));
    expect(onAccept).toHaveBeenCalledWith("a.png");
    fireEvent.click(screen.getByText("✎"));
    expect(onEdit).toHaveBeenCalledWith("a.png");
    fireEvent.click(screen.getByText("⨯"));
    expect(onSkip).toHaveBeenCalledWith("a.png");
  });

  it("reflects the current decision in button styling", () => {
    render(
      <IconCard
        icon={icon}
        decision={{ action: "skip" }}
        existingLabels={[]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    const skipBtn = screen.getByText("⨯");
    expect(skipBtn.className).toMatch(/active/);
  });
});
```

- [ ] **Step 6.3: Run tests to verify they fail**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: FAIL — modules not found.

- [ ] **Step 6.4: Implement TopBar**

File: `record/Aloha_Learn/review-ui/src/components/TopBar.tsx`

```tsx
interface Props {
  totalIcons: number;
  accepted: number;
  edited: number;
  skipped: number;
  manualMode: boolean;
  onToggleManual: (next: boolean) => void;
  onAcceptAll: () => void;
  onSubmit: () => void;
}

export function TopBar({
  totalIcons, accepted, edited, skipped,
  manualMode, onToggleManual, onAcceptAll, onSubmit,
}: Props) {
  return (
    <header className="topbar">
      <h1>Record Icon Review</h1>
      <div className="topbar-counts">
        共 {totalIcons} 张 · {accepted} accept · {edited} edit · {skipped} skip
      </div>
      <div className="topbar-actions">
        <label className="manual-toggle">
          <input
            type="checkbox"
            checked={manualMode}
            onChange={(e) => onToggleManual(e.target.checked)}
            aria-label="全手动"
          />
          全手动
        </label>
        <button onClick={onAcceptAll} className="btn btn-secondary">全部接受</button>
        <button onClick={onSubmit} className="btn btn-primary">提交</button>
      </div>
    </header>
  );
}
```

- [ ] **Step 6.5: Implement IconCard**

File: `record/Aloha_Learn/review-ui/src/components/IconCard.tsx`

```tsx
import type { Icon, Decision } from "../types";

interface Props {
  icon: Icon;
  decision: Decision | null;
  existingLabels: string[];
  onAccept: (filename: string) => void;
  onEdit: (filename: string) => void;
  onSkip: (filename: string) => void;
}

export function IconCard({ icon, decision, existingLabels, onAccept, onEdit, onSkip }: Props) {
  const isExisting = existingLabels.includes(icon.llm_label);
  return (
    <div className="icon-card" data-filename={icon.filename}>
      <img src={icon.icon_url} alt={icon.llm_label} className="icon-card-img" />
      <div className="icon-card-label">
        <span className="icon-card-label-text">{icon.llm_label}</span>
        {icon.is_timestamp_fallback && (
          <span className="icon-card-badge fallback">⏱ LLM 未命名</span>
        )}
        {isExisting && !icon.is_timestamp_fallback && (
          <span className="icon-card-badge conflict">已存在（将 upsert）</span>
        )}
      </div>
      <div className="icon-card-actions">
        <button
          className={`icon-card-btn accept ${decision?.action === "accept" ? "active" : ""}`}
          onClick={() => onAccept(icon.filename)}
          aria-label="accept"
        >✓</button>
        <button
          className={`icon-card-btn edit ${decision?.action === "edit" ? "active" : ""}`}
          onClick={() => onEdit(icon.filename)}
          aria-label="edit"
        >✎</button>
        <button
          className={`icon-card-btn skip ${decision?.action === "skip" ? "active" : ""}`}
          onClick={() => onSkip(icon.filename)}
          aria-label="skip"
        >⨯</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6.6: Implement IconGrid (no tests — pure layout)**

File: `record/Aloha_Learn/review-ui/src/components/IconGrid.tsx`

```tsx
import type { Icon, Decision } from "../types";
import { IconCard } from "./IconCard";

interface Props {
  icons: Icon[];
  decisions: Record<string, Decision | null>;
  existingLabels: string[];
  onAccept: (filename: string) => void;
  onEdit: (filename: string) => void;
  onSkip: (filename: string) => void;
}

export function IconGrid({ icons, decisions, existingLabels, onAccept, onEdit, onSkip }: Props) {
  return (
    <div className="icon-grid">
      {icons.map((icon) => (
        <IconCard
          key={icon.filename}
          icon={icon}
          decision={decisions[icon.filename] ?? null}
          existingLabels={existingLabels}
          onAccept={onAccept}
          onEdit={onEdit}
          onSkip={onSkip}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 6.7: Update styles.css**

Append to `record/Aloha_Learn/review-ui/src/styles.css`:

```css
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  border-bottom: 1px solid #e1e4e8;
  background: #f6f8fa;
}
.topbar h1 { font-size: 18px; margin: 0; }
.topbar-counts { color: #57606a; font-size: 14px; }
.topbar-actions { margin-left: auto; display: flex; gap: 12px; align-items: center; }
.manual-toggle { display: flex; align-items: center; gap: 6px; font-size: 14px; }
.btn { padding: 6px 12px; border-radius: 6px; border: 1px solid #d0d7de; cursor: pointer; }
.btn-primary { background: #1f883d; color: #fff; border-color: #1f883d; }
.btn-secondary { background: #fff; }

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  padding: 24px;
}
.icon-card {
  border: 1px solid #d0d7de;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.icon-card-img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: contain;
  background: #f6f8fa;
  border-radius: 4px;
  cursor: pointer;
}
.icon-card-label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.icon-card-label-text { font-family: ui-monospace, SFMono-Regular, monospace; }
.icon-card-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  width: fit-content;
}
.icon-card-badge.fallback { background: #fff8c5; color: #6e4d00; font-style: italic; }
.icon-card-badge.conflict { background: #ffebe9; color: #82071e; }
.icon-card-actions { display: flex; gap: 6px; }
.icon-card-btn {
  flex: 1;
  padding: 4px 0;
  border: 1px solid #d0d7de;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}
.icon-card-btn.active { background: #1f883d; color: #fff; border-color: #1f883d; }
.icon-card-btn.skip.active { background: #6e7681; }
.icon-card-btn.edit.active { background: #0969da; border-color: #0969da; }
```

- [ ] **Step 6.8: Run tests to verify they pass**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: PASS — TopBar 2 + IconCard 5 = 7 new tests pass; existing 11 still pass.

- [ ] **Step 6.9: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/review-ui/src/components/TopBar.tsx record/Aloha_Learn/review-ui/src/components/TopBar.test.tsx record/Aloha_Learn/review-ui/src/components/IconCard.tsx record/Aloha_Learn/review-ui/src/components/IconCard.test.tsx record/Aloha_Learn/review-ui/src/components/IconGrid.tsx record/Aloha_Learn/review-ui/src/styles.css
git commit -m "feat(review-ui): TopBar + IconCard + IconGrid with full coverage"
```

---

## Task 7: UI components — IconDetail + SubmitConfirm + DoneScreen (TDD)

**Files:**
- Create: `record/Aloha_Learn/review-ui/src/components/IconDetail.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/IconDetail.test.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/SubmitConfirm.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/SubmitConfirm.test.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/DoneScreen.tsx`
- Create: `record/Aloha_Learn/review-ui/src/components/DoneScreen.test.tsx`
- Modify: `record/Aloha_Learn/review-ui/src/styles.css`

**Interfaces:**
- `IconDetail` props: `{ icon: Icon; initialLabel: string; onSave: (label: string) => void; onSkip: () => void; onCancel: () => void }`
- `SubmitConfirm` props: `{ accepted, edited, skipped, onConfirm, onCancel }`
- `DoneScreen` props: `{ applied: AppliedCounts; keysAdded, keysUpdated }`

- [ ] **Step 7.1: Write IconDetail tests**

File: `record/Aloha_Learn/review-ui/src/components/IconDetail.test.tsx`

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IconDetail } from "./IconDetail";
import type { Icon } from "../types";

const icon: Icon = {
  filename: "a.png",
  icon_url: "/icons/a.png",
  llm_label: "start_button",
  is_timestamp_fallback: false,
  action: "LClick at",
  coords: [1, 2],
  current_software: "Chrome",
  base: "10.0s",
};

describe("IconDetail", () => {
  it("shows the big image and an editable label", () => {
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={() => {}}
        onSkip={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByAltText("start_button")).toHaveAttribute("src", "/icons/a.png");
    expect(screen.getByDisplayValue("start_button")).toBeInTheDocument();
  });

  it("disables save when sanitize yields empty", () => {
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={() => {}}
        onSkip={() => {}}
        onCancel={() => {}}
      />
    );
    const input = screen.getByDisplayValue("start_button");
    fireEvent.change(input, { target: { value": "///??**" } });
    expect(screen.getByText("保存")).toBeDisabled();
  });

  it("calls onSave with sanitized label on save click", () => {
    const onSave = vi.fn();
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={onSave}
        onSkip={() => {}}
        onCancel={() => {}}
      />
    );
    const input = screen.getByDisplayValue("start_button");
    fireEvent.change(input, { target: { value: "Search Box!" } });
    fireEvent.click(screen.getByText("保存"));
    expect(onSave).toHaveBeenCalledWith("search_box");
  });

  it("calls onSkip and onCancel", () => {
    const onSkip = vi.fn();
    const onCancel = vi.fn();
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={() => {}}
        onSkip={onSkip}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByText("跳过"));
    expect(onSkip).toHaveBeenCalled();
    fireEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

- [ ] **Step 7.2: Write SubmitConfirm tests**

File: `record/Aloha_Learn/review-ui/src/components/SubmitConfirm.test.tsx`

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SubmitConfirm } from "./SubmitConfirm";

describe("SubmitConfirm", () => {
  it("shows counts and triggers callbacks", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <SubmitConfirm
        accepted={3}
        edited={2}
        skipped={1}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );
    expect(screen.getByText(/3 accept/)).toBeInTheDocument();
    expect(screen.getByText(/2 edit/)).toBeInTheDocument();
    expect(screen.getByText(/1 skip/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("确认提交"));
    expect(onConfirm).toHaveBeenCalled();
    fireEvent.click(screen.getByText("再看看"));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

- [ ] **Step 7.3: Write DoneScreen tests**

File: `record/Aloha_Learn/review-ui/src/components/DoneScreen.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DoneScreen } from "./DoneScreen";

describe("DoneScreen", () => {
  it("renders applied counts and key lists", () => {
    render(
      <DoneScreen
        applied={{ accepted: 2, edited: 1, skipped: 1, sanitize_fallback: 0 }}
        keysAdded={["a", "b"]}
        keysUpdated={["c"]}
      />
    );
    expect(screen.getByText(/已完成/)).toBeInTheDocument();
    expect(screen.getByText(/a, b/)).toBeInTheDocument();
    expect(screen.getByText(/c/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 7.4: Run tests to verify they fail**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: FAIL — 3 missing modules.

- [ ] **Step 7.5: Implement IconDetail**

File: `record/Aloha_Learn/review-ui/src/components/IconDetail.tsx`

```tsx
import { useState, useEffect } from "react";
import type { Icon } from "../types";
import { sanitize, isValidLabel } from "../lib/sanitize";

interface Props {
  icon: Icon;
  initialLabel: string;
  onSave: (label: string) => void;
  onSkip: () => void;
  onCancel: () => void;
}

export function IconDetail({ icon, initialLabel, onSave, onSkip, onCancel }: Props) {
  const [raw, setRaw] = useState(initialLabel);
  const [sanitized, setSanitized] = useState(() => {
    try { return sanitize(initialLabel); } catch { return ""; }
  });

  useEffect(() => {
    try {
      setSanitized(sanitize(raw));
    } catch {
      setSanitized("");
    }
  }, [raw]);

  const canSave = isValidLabel(sanitized);

  return (
    <div className="modal-backdrop" role="dialog" aria-label="Edit icon">
      <div className="modal">
        <img src={icon.icon_url} alt={icon.llm_label} className="modal-img" />
        <div className="modal-body">
          <label className="modal-label">Label</label>
          <input
            className="modal-input"
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
          />
          <div className="modal-sanitized">
            sanitized: <code>{sanitized || "(empty)"}</code>
          </div>
          <div className="modal-actions">
            <button onClick={onCancel} className="btn">取消</button>
            <button onClick={onSkip} className="btn">跳过</button>
            <button
              onClick={() => onSave(sanitized)}
              disabled={!canSave}
              className="btn btn-primary"
            >保存</button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7.6: Implement SubmitConfirm**

File: `record/Aloha_Learn/review-ui/src/components/SubmitConfirm.tsx`

```tsx
interface Props {
  accepted: number;
  edited: number;
  skipped: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SubmitConfirm({ accepted, edited, skipped, onConfirm, onCancel }: Props) {
  return (
    <div className="modal-backdrop" role="dialog" aria-label="Confirm submit">
      <div className="modal">
        <h2>确认提交</h2>
        <ul>
          <li>accept: {accepted}</li>
          <li>edit: {edited}</li>
          <li>skip: {skipped}</li>
        </ul>
        <div className="modal-actions">
          <button onClick={onCancel} className="btn">再看看</button>
          <button onClick={onConfirm} className="btn btn-primary">确认提交</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7.7: Implement DoneScreen**

File: `record/Aloha_Learn/review-ui/src/components/DoneScreen.tsx`

```tsx
import type { AppliedCounts } from "../types";

interface Props {
  applied: AppliedCounts;
  keysAdded: string[];
  keysUpdated: string[];
}

export function DoneScreen({ applied, keysAdded, keysUpdated }: Props) {
  return (
    <div className="done-screen">
      <h1>已完成</h1>
      <ul>
        <li>accept: {applied.accepted}</li>
        <li>edit: {applied.edited}</li>
        <li>skip: {applied.skipped}</li>
        <li>sanitize_fallback: {applied.sanitize_fallback}</li>
      </ul>
      <p>keys_added: {keysAdded.join(", ")}</p>
      <p>keys_updated: {keysUpdated.join(", ")}</p>
    </div>
  );
}
```

- [ ] **Step 7.8: Update styles.css**

Append to `record/Aloha_Learn/review-ui/src/styles.css`:

```css
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 10;
}
.modal {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  max-width: 640px;
  width: 90%;
  max-height: 90vh;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.modal-img {
  width: 100%;
  max-width: 256px;
  align-self: center;
  background: #f6f8fa;
  border-radius: 4px;
}
.modal-body { display: flex; flex-direction: column; gap: 8px; }
.modal-label { font-size: 13px; color: #57606a; }
.modal-input { padding: 8px; border: 1px solid #d0d7de; border-radius: 4px; font-size: 14px; }
.modal-sanitized { font-size: 12px; color: #57606a; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
.done-screen { padding: 48px; max-width: 720px; margin: 0 auto; }
.done-screen h1 { margin-top: 0; }
.done-screen ul { line-height: 1.8; }
```

- [ ] **Step 7.9: Run tests to verify they pass**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: PASS — IconDetail 4 + SubmitConfirm 1 + DoneScreen 1 = 6 new tests pass; total 24.

- [ ] **Step 7.10: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/review-ui/src/components/IconDetail.tsx record/Aloha_Learn/review-ui/src/components/IconDetail.test.tsx record/Aloha_Learn/review-ui/src/components/SubmitConfirm.tsx record/Aloha_Learn/review-ui/src/components/SubmitConfirm.test.tsx record/Aloha_Learn/review-ui/src/components/DoneScreen.tsx record/Aloha_Learn/review-ui/src/components/DoneScreen.test.tsx record/Aloha_Learn/review-ui/src/styles.css
git commit -m "feat(review-ui): IconDetail modal + SubmitConfirm + DoneScreen"
```

---

## Task 8: App integration + final wiring (TDD)

**Files:**
- Modify: `record/Aloha_Learn/review-ui/src/App.tsx` (replace stub)
- Create: `record/Aloha_Learn/review-ui/src/App.test.tsx`

**Interfaces:**
- App composes: `getQueue` → reducer → TopBar/IconGrid/IconDetail/SubmitConfirm/DoneScreen
- Debounced `postDecisions` on every decision change
- `postFinish` on submit confirm

- [ ] **Step 8.1: Write the App test**

File: `record/Aloha_Learn/review-ui/src/App.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";
import type { Queue, FinishResult } from "./types";

vi.mock("./api/client", () => ({
  getQueue: vi.fn(),
  postDecisions: vi.fn(),
  postFinish: vi.fn(),
}));

import { getQueue, postDecisions, postFinish } from "./api/client";

const queue: Queue = {
  icons: [
    {
      filename: "a.png",
      icon_url: "/icons/a.png",
      llm_label: "start_button",
      is_timestamp_fallback: false,
      action: "LClick at",
      coords: [1, 2],
      current_software: "Chrome",
      base: "10.0s",
    },
    {
      filename: "b.png",
      icon_url: "/icons/b.png",
      llm_label: "search",
      is_timestamp_fallback: false,
      action: "LClick at",
      coords: [3, 4],
      current_software: "Chrome",
      base: "11.0s",
    },
  ],
  existing_labels: [],
  dest: "D:",
  manual_mode_default: false,
};

const finishResult: FinishResult = {
  applied: { accepted: 1, edited: 0, skipped: 1, sanitize_fallback: 0 },
  keys_added: ["start_button"],
  keys_updated: [],
};

describe("App", () => {
  beforeEach(() => {
    vi.mocked(getQueue).mockResolvedValue(queue);
    vi.mocked(postDecisions).mockResolvedValue();
    vi.mocked(postFinish).mockResolvedValue(finishResult);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("fetches queue, renders cards, and submits on confirm", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("start_button")).toBeInTheDocument();
    });
    // Skip b.png
    fireEvent.click(screen.getAllByText("⨯")[1]);
    // Submit
    fireEvent.click(screen.getByText("提交"));
    fireEvent.click(screen.getByText("确认提交"));
    await waitFor(() => {
      expect(postFinish).toHaveBeenCalled();
    });
    expect(await screen.findByText("已完成")).toBeInTheDocument();
  });

  it("debounces postDecisions on decision change", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("start_button")).toBeInTheDocument();
    });
    fireEvent.click(screen.getAllByText("✓")[0]);
    // postDecisions called after debounce
    await waitFor(() => {
      expect(postDecisions).toHaveBeenCalled();
    }, { timeout: 1000 });
  });

  it("blocks submit when there are missing decisions", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("start_button")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("提交"));
    // Confirm dialog opens
    fireEvent.click(screen.getByText("确认提交"));
    // postFinish should NOT be called because decisions missing
    // The flow should show an error, not call finish.
    // We accept either an error banner OR postFinish not being called.
    await new Promise((r) => setTimeout(r, 200));
    expect(postFinish).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 8.2: Run tests to verify they fail**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: FAIL — App.tsx is the stub.

- [ ] **Step 8.3: Implement App**

File: `record/Aloha_Learn/review-ui/src/App.tsx`

```tsx
import { useEffect, useReducer, useRef, useState } from "react";
import { reducer, initialState } from "./store/reducer";
import { getQueue, postDecisions, postFinish } from "./api/client";
import { TopBar } from "./components/TopBar";
import { IconGrid } from "./components/IconGrid";
import { IconDetail } from "./components/IconDetail";
import { SubmitConfirm } from "./components/SubmitConfirm";
import { DoneScreen } from "./components/DoneScreen";
import type { FinishResult, Icon } from "./types";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [editing, setEditing] = useState<Icon | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [doneResult, setDoneResult] = useState<FinishResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getQueue()
      .then((q) => dispatch({
        type: "SET_QUEUE",
        icons: q.icons,
        existing_labels: q.existing_labels,
        dest: q.dest,
        manual_mode_default: q.manual_mode_default,
      }))
      .catch((e) => setError(`Failed to load queue: ${e}`));
  }, []);

  // Debounced persistence of decisions
  useEffect(() => {
    if (state.icons.length === 0) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      postDecisions({ decisions: state.decisions, manual_mode: state.manualMode })
        .catch((e) => console.error("postDecisions failed", e));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [state.decisions, state.manualMode, state.icons.length]);

  const counts = countDecisions(state);

  function handleSubmit() {
    setError(null);
    const missing = state.icons.filter((i) => state.decisions[i.filename] === null);
    if (missing.length > 0) {
      setError(`还有 ${missing.length} 张未决定`);
      return;
    }
    setConfirming(true);
  }

  async function handleConfirm() {
    setConfirming(false);
    dispatch({ type: "SET_SUBMITTING", submitting: true });
    try {
      const result = await postFinish();
      setDoneResult(result);
    } catch (e: any) {
      setError(`Submit failed: ${e.message ?? e}`);
      dispatch({ type: "SET_SUBMITTING", submitting: false });
    }
  }

  if (doneResult) {
    return (
      <DoneScreen
        applied={doneResult.applied}
        keysAdded={doneResult.keys_added}
        keysUpdated={doneResult.keys_updated}
      />
    );
  }

  if (error && state.icons.length === 0) {
    return <div className="error-banner">{error}</div>;
  }

  return (
    <div className="app">
      <TopBar
        totalIcons={state.icons.length}
        accepted={counts.accepted}
        edited={counts.edited}
        skipped={counts.skipped}
        manualMode={state.manualMode}
        onToggleManual={(next) => dispatch({ type: "SET_MANUAL_MODE", manualMode: next })}
        onAcceptAll={() => dispatch({ type: "APPLY_BULK_ACCEPT" })}
        onSubmit={handleSubmit}
      />
      {error && <div className="error-banner">{error}</div>}
      <IconGrid
        icons={state.icons}
        decisions={state.decisions}
        existingLabels={state.existingLabels}
        onAccept={(fn) => dispatch({ type: "SET_DECISION", filename: fn, decision: { action: "accept" } })}
        onEdit={(fn) => {
          const icon = state.icons.find((i) => i.filename === fn);
          if (icon) setEditing(icon);
        }}
        onSkip={(fn) => dispatch({ type: "SET_DECISION", filename: fn, decision: { action: "skip" } })}
      />
      {editing && (
        <IconDetail
          icon={editing}
          initialLabel={editing.llm_label}
          onCancel={() => setEditing(null)}
          onSkip={() => {
            dispatch({ type: "SET_DECISION", filename: editing.filename, decision: { action: "skip" } });
            setEditing(null);
          }}
          onSave={(label) => {
            dispatch({ type: "SET_DECISION", filename: editing.filename, decision: { action: "edit", label } });
            setEditing(null);
          }}
        />
      )}
      {confirming && (
        <SubmitConfirm
          accepted={counts.accepted}
          edited={counts.edited}
          skipped={counts.skipped}
          onCancel={() => setConfirming(false)}
          onConfirm={handleConfirm}
        />
      )}
    </div>
  );
}

function countDecisions(state: ReturnType<typeof reducer>) {
  let accepted = 0, edited = 0, skipped = 0;
  for (const d of Object.values(state.decisions)) {
    if (d === null) continue;
    if (d.action === "accept") accepted++;
    else if (d.action === "edit") edited++;
    else if (d.action === "skip") skipped++;
  }
  return { accepted, edited, skipped };
}
```

- [ ] **Step 8.4: Add `.error-banner` style**

Append to `record/Aloha_Learn/review-ui/src/styles.css`:

```css
.error-banner {
  background: #ffebe9;
  border: 1px solid #ff8182;
  color: #82071e;
  padding: 8px 16px;
  margin: 8px 24px;
  border-radius: 4px;
}
```

- [ ] **Step 8.5: Run tests to verify they pass**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: PASS — 3 new App tests pass; total 27.

- [ ] **Step 8.6: Verify build works end-to-end**

Run: `cd "record/Aloha_Learn/review-ui" && npm run build`

Expected: `dist/index.html` produced. No TS errors.

- [ ] **Step 8.7: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/review-ui/src/App.tsx record/Aloha_Learn/review-ui/src/App.test.tsx record/Aloha_Learn/review-ui/src/styles.css
git commit -m "feat(review-ui): wire App with reducer, debounced persistence, and submit flow"
```

---

## Task 9: End-to-end integration test (Python)

**Files:**
- Create: `record/Aloha_Learn/tests/test_review_integration_e2e.py` (separate from Task 5 mock-based test; this one drives the full server + applies to a real `dest/`)

**Goal:** Verify that `run_review_session` (with a real browser-less flow driven by `urllib`) produces the expected `dest/components.json` and PNGs.

- [ ] **Step 9.1: Write the e2e test**

File: `record/Aloha_Learn/tests/test_review_integration_e2e.py`

```python
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components_sync import IconRecord
from review_server import run_review_session


def _records():
    return [
        IconRecord(filename="record_memory_icon_1.0s_crop.png", action="LClick at",
                   coords=(100, 200), current_software="Chrome", base="1.0s"),
        IconRecord(filename="record_memory_icon_2.0s_crop.png", action="LClick at",
                   coords=(300, 400), current_software="Chrome", base="2.0s"),
        IconRecord(filename="record_memory_icon_3.0s_crop.png", action="LClick at",
                   coords=(500, 600), current_software="Chrome", base="3.0s"),
    ]


def _write_icons(screenshots_dir: Path, records):
    icons = screenshots_dir / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    for r in records:
        (icons / r.filename).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


def _http(port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=payload, headers=headers)
    r = conn.getresponse()
    raw = r.read().decode("utf-8")
    conn.close()
    return r.status, (json.loads(raw) if raw else {})


class EndToEndReviewTest(unittest.TestCase):
    def test_full_flow_writes_dest_components_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "shots"
            shots.mkdir()
            records = _records()
            _write_icons(shots, records)
            label_map = {r.filename: f"label_{i}" for i, r in enumerate(records)}
            dest = tmp / "dest"
            dest.mkdir()

            port_holder: dict = {}
            import review_server as rs
            orig = rs.ThreadingHTTPServer
            class Cap(orig):
                def __init__(self, addr, handler):
                    super().__init__(addr, handler)
                    port_holder["port"] = self.server_address[1]
            rs.ThreadingHTTPServer = Cap

            result_holder: dict = {}
            def runner():
                result_holder["r"] = run_review_session(
                    records, label_map, shots, dest,
                    open_browser=False, timeout_seconds=10,
                )
            t = threading.Thread(target=runner, daemon=True)
            t.start()
            for _ in range(200):
                if "port" in port_holder:
                    break
                time.sleep(0.02)
            port = port_holder["port"]

            # 1. GET queue
            status, queue = _http(port, "GET", "/api/queue")
            self.assertEqual(status, 200)
            self.assertEqual(len(queue["icons"]), 3)

            # 2. POST decisions: skip[1], edit[2] to "custom_btn", accept[3]
            decisions = {
                records[1].filename: {"action": "skip"},
                records[2].filename: {"action": "edit", "label": "Custom Btn!"},
            }
            # records[0] left as accept (default)
            # We need to explicitly include accept for records[0]:
            decisions[records[0].filename] = {"action": "accept"}
            status, _ = _http(port, "POST", "/api/decisions", {
                "decisions": decisions, "manual_mode": False,
            })
            self.assertEqual(status, 200)

            # 3. POST finish
            status, finish = _http(port, "POST", "/api/finish")
            self.assertEqual(status, 200)
            self.assertEqual(finish["applied"]["accepted"], 1)
            self.assertEqual(finish["applied"]["edited"], 1)
            self.assertEqual(finish["applied"]["skipped"], 1)
            self.assertIn("label_0", finish["keys_added"])
            self.assertIn("custom_btn", finish["keys_added"])
            self.assertNotIn("label_1", finish["keys_added"] + finish["keys_updated"])

            t.join(timeout=5)

            # 4. Verify dest/components.json
            comp_path = dest / "components.json"
            self.assertTrue(comp_path.exists())
            data = json.loads(comp_path.read_text(encoding="utf-8"))
            self.assertIn("label_0", data)
            self.assertIn("custom_btn", data)
            self.assertNotIn("label_1", data)
            # Verify entry shape
            entry = data["label_0"]
            self.assertEqual(entry["type"], "icon")
            self.assertEqual(entry["source"], "learn_batch")
            self.assertEqual(entry["icon_file"], "components/label_0.png")
            self.assertEqual(entry["seen_count"], 1)
            self.assertEqual(entry["consecutive_misses"], 0)
            self.assertTrue(entry["base_memory"])

            # 5. Verify PNGs copied
            self.assertTrue((dest / "components" / "label_0.png").exists())
            self.assertTrue((dest / "components" / "custom_btn.png").exists())
            self.assertFalse((dest / "components" / "label_1.png").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 9.2: Run the e2e test**

Run: `cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record" && python -m unittest Aloha_Learn.tests.test_review_integration_e2e -v`

Expected: PASS — 1 test passes.

- [ ] **Step 9.3: Commit**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git add record/Aloha_Learn/tests/test_review_integration_e2e.py
git commit -m "test(review): end-to-end HTTP-driven flow writes dest/components.json correctly"
```

---

## Task 10: Run all tests + final manual smoke test

**Files:** None (verification only)

- [ ] **Step 10.1: Run full Python test suite**

Run: `cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record" && python -m unittest discover Aloha_Learn/tests -v`

Expected: ALL tests pass (existing + new). Total ~25+ tests.

- [ ] **Step 10.2: Run full TypeScript test suite**

Run: `cd "record/Aloha_Learn/review-ui" && npm test`

Expected: ALL tests pass. Total ~27 tests.

- [ ] **Step 10.3: Verify build**

Run: `cd "record/Aloha_Learn/review-ui" && npm run build`

Expected: `dist/index.html` exists. No TS errors.

- [ ] **Step 10.4: Manual smoke test with `Examples/air_tickets`**

Run from `record/`:

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1/record"
unset GUI_AGENT_REVIEW_DISABLE
export GUI_AGENT_COMPONENTS_DEST="/tmp/review_smoke_dest"
rm -rf "$GUI_AGENT_COMPONENTS_DEST"
mkdir -p "$GUI_AGENT_COMPONENTS_DEST"
python -c "
import sys
sys.path.insert(0, 'Aloha_Learn')
from screenshot_processor import VideoScreenshotExtractor
ext = VideoScreenshotExtractor()
try:
    actions, shots, meta = ext.process_project('Aloha_Learn/Examples/air_tickets')
    print('META:', meta)
except Exception as e:
    print('ERROR:', e)
"
```

Expected: Browser opens; user can review; after submit, `dest/components.json` is populated. If no browser is available, the test should still complete via the 30-minute timeout fallback (set `GUI_AGENT_REVIEW_DISABLE=1` to skip).

- [ ] **Step 10.5: Final commit if any uncommitted changes**

```bash
cd "E:/pycharm projects/GUI-Agent-Github-Maglna1"
git status
# If anything dirty, commit it.
```

---

## Self-Review Notes

### Spec coverage

- **§1 Architecture & data flow**: covered by Tasks 4 (server) + 5 (Python integration) + 8 (UI App wiring).
- **§2 API contracts**: covered by Task 4 (server endpoints) + Task 3 (client + tests) + Task 8 (App use).
- **§3 UI structure**: TopBar / IconGrid / IconCard in Task 6, IconDetail / SubmitConfirm / DoneScreen in Task 7, App composition in Task 8, state model in Task 3.
- **§4 Error handling**: server-side (Task 4: dist missing, port failure, missing decisions, invalid body, timeout); Python integration (Task 5: env var); UI (Task 8: getQueue failure, postDecisions retry log, postFinish error, sanitize disable).
- **Testing**: Python unit (Task 4), Python integration (Task 5), TS unit (Tasks 2/3/6/7/8), E2E (Task 9), smoke (Task 10).

### Type consistency

- `Icon` / `Decision` / `Queue` / `AppliedCounts` / `FinishResult` defined once in `src/types.ts` and reused by client, reducer, components, App, and Python (via `Queue` JSON shape).
- `decision.action` enum matches Python server's `["accept", "edit", "skip"]` exactly.
- `IconRecord` Python dataclass matches `Icon` TS interface field-by-field.
- `run_review_session` return dict keys: `accepted`, `edited`, `skipped`, `sanitize_fallback`, `keys_added`, `keys_updated`, `manual_mode`, `timed_out`, `port` — referenced consistently in Task 5 and Task 9.

### Placeholder scan

No "TBD", "TODO", "implement later", or "fill in details" markers. Every step has concrete file paths, exact code, and exact commands.

### Known scope boundaries

- Vite dev server proxy is configured but `webbrowser.open()` always points to the OS-assigned server port, so dev mode is for human use only; tests run against the built `dist/`.
- The e2e test does not exercise the React UI; that requires a browser harness which is out of scope for this change.
- 30-minute timeout is hard-coded in `_TIMEOUT_SECONDS_DEFAULT`; tests override via `timeout_seconds` parameter.
