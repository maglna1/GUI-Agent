# Sync Record Icons → Components 实施计划

> **面向智能体执行者：** 必选子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务执行本计划。步骤使用 checkbox（`- [ ]`）语法进行追踪。

**目标（Goal）：** 在 `VideoScreenshotExtractor.process_project()` 末尾自动同步该轮 default-click icon 到 harness 的 `components/` 与 `components.json`，icon 键由视觉模型实时命名；LLM 失败软回退到 timestamp 键。

**架构（Architecture）：** 新增独立纯函数模块 `record/Aloha_Learn/components_sync.py`（`IconRecord` / `ComponentEntry` dataclass + `sanitize_label` / `dedup_labels` / `build_component_entry` / `merge_components_json` 四个纯函数）；`screenshot_processor.py` 在 `process_project()` 末尾新增编排逻辑（读 `GUI_AGENT_COMPONENTS_DEST` env var → 列举 icons → 调视觉模型 → sanitize → 拷贝 PNG → upsert 写 `components.json`），新增 `_request_component_labels` / `_sync_components_to_dest` / `_load_components_json` / `_apply_components_updates` 私有方法。LLM 客户端复用 `trace_generator.py` 的 `requests.post` 模式（`OPENAI_*` env var 与 `api_keys.json`）。

**技术栈（Tech Stack）：** Python 3、OpenCV（`cv2`）、`requests`（已存在 `record/pyproject.toml`）、`unittest`（与仓库既有测试风格一致）、`openai`-兼容 chat completions API。

## 全局约束（Global Constraints）

逐字摘自 `openspec/changes/sync-record-icons-to-components/specs/record-icons-to-components-sync/spec.md`：

- 触发 env var：`GUI_AGENT_COMPONENTS_DEST`（路径字符串）。未设置 / 空串 → 不同步；非空 → 末尾同步。
- 同步范围：仅 default-click icon（`screenshots/icons/record_memory_icon_*.png`）；`DragStart` / 无坐标 / `CONFIG` / `Active Window` 不产生 dest 端条目。
- LLM 调用：每轮 record 调 1 次视觉模型；复用 `OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` / `OPENAI_VERIFY_SSL`（与 `trace_generator.py:_call_openai` 同模式，使用 `requests.post` 而非 `openai` SDK）。凭证回退：env var → `record/Aloha_Learn/config/api_keys.json::OPENAI_API_KEY` → env var `MIDSCENE_MODEL_API_KEY`。
- LLM 输入：每轮该 batch 全部 icon 内联 base64 + 元数据（action / coords / software / timestamp）。
- LLM 输出：JSON object `{filename: snake_case_label}`。
- LLM 失败软回退：捕获 `ComponentsLLMError` → 整批走 timestamp 键（`record_memory_icon_<sanitized_base>_crop`），不抛错；`meta.components_fallback_to_timestamp = True`。
- Label 规范：`sanitize_label` 规范为 `[a-z0-9_]` snake_case、最长 30 字符；空 / 全非法字符 → 抛 `ValueError`（由调用方 fallback 到 timestamp 键）。
- 同 batch 重名：`dedup_labels` 自动加 `_2` / `_3` 后缀。
- JSON upsert：保留 `learned_at`、刷新 `last_seen = now`、`seen_count += 1`、`consecutive_misses = 0`、`base_memory = true`。
- 必备字段：`type="icon"`、`source="learn_batch"`、`icon_file="components/<label>.png"`、`label` = basename；`base_memory: true` 一律为 true。
- PNG 完整性：`dest/components/<label>.png` 与源 `screenshots/icons/record_memory_icon_*.png` 字节等同（无损拷贝）。
- dest 不可写：抛 `RuntimeError` 中止 `process_project()`（与既有 `full_ok` / `crop_ok` 失败语义对齐）。
- `dest/components.json` 损坏 / 缺失：警告 + 当空 dict；不抛错。
- `processed_log_sc.json` schema 不变。
- `VideoScreenshotExtractor.__init__` 签名不变（env var 在 `process_project()` 内读）。
- `process_project()` 返回的 `meta` 必含 `components_synced` / `components_dest` / `components_keys_added` / `components_keys_updated` / `components_fallback_to_timestamp`。
- 修改文件：`record/Aloha_Learn/screenshot_processor.py`、`record/Aloha_Learn/tests/test_screenshot_processor.py`。
- 新建文件：`record/Aloha_Learn/components_sync.py`、`record/Aloha_Learn/tests/test_components_sync.py`。
- 不修改：`parser.py` / `trace_generator.py` / `log_processor.py` / harness 任何文件。
- 不新增依赖（`requests` 已在 `pyproject.toml`）。

---

## 文件结构（File Structure）

| 文件 | 状态 | 职责 |
|---|---|---|
| `record/Aloha_Learn/components_sync.py` | 新建 | `IconRecord` / `ComponentEntry` dataclass + 4 个纯函数（sanitize / dedup / build / merge） |
| `record/Aloha_Learn/tests/test_components_sync.py` | 新建 | 纯函数单元测试 |
| `record/Aloha_Learn/screenshot_processor.py` | 修改 | 新增 `ComponentsLLMError` + 4 个私有方法；`process_project()` 末尾触发同步 + `meta` 字段扩展 |
| `record/Aloha_Learn/tests/test_screenshot_processor.py` | 修改 | 新增 `ComponentSyncTest`（mock LLM + 临时 dest） |

不创建其他文件。

---

## Task 1：纯函数模块骨架 + `sanitize_label` + `IconRecord` dataclass

**Files:**
- Create: `record/Aloha_Learn/components_sync.py`
- Create: `record/Aloha_Learn/tests/test_components_sync.py`

**Interfaces:**
- Consumes: 无。
- Produces:
  - `IconRecord` dataclass（`filename: str`、`action: str`、`coords: tuple[int, int]`、`current_software: str`、`base: str`）
  - `def sanitize_label(raw: str) -> str`：转小写、空白→`_`、`/`→`-`、删 `\\:?*`、截 30 字符；空 / 全非法字符 → 抛 `ValueError`

- [ ] **Step 1：编写失败的测试**

新建 `record/Aloha_Learn/tests/test_components_sync.py`：

```python
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from components_sync import IconRecord, sanitize_label


class SanitizeLabelTest(unittest.TestCase):
    def test_lowercases_and_replaces_spaces_with_underscores(self):
        self.assertEqual(sanitize_label("Start Button"), "start_button")

    def test_replaces_slashes_and_backslashes_with_dash(self):
        self.assertEqual(sanitize_label("a/b\\c"), "a-b-c")

    def test_strips_special_chars(self):
        self.assertEqual(sanitize_label("a:b?c*d"), "abcd")

    def test_truncates_to_30_chars(self):
        long = "a" * 50
        self.assertEqual(len(sanitize_label(long)), 30)

    def test_combined(self):
        # 空白 + 特殊字符 + 长度截断；输入 35 字符经清理后更长，截到 30
        self.assertEqual(sanitize_label("Clone Repository Tab  "), "clone_repository_tab")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            sanitize_label("")

    def test_all_special_chars_raises(self):
        with self.assertRaises(ValueError):
            sanitize_label("///??**")


class IconRecordTest(unittest.TestCase):
    def test_constructs_and_exposes_fields(self):
        r = IconRecord(
            filename="record_memory_icon_10.854s_crop.png",
            action="LClick at",
            coords=(820, 450),
            current_software="Explorer",
            base="10.854s",
        )
        self.assertEqual(r.filename, "record_memory_icon_10.854s_crop.png")
        self.assertEqual(r.action, "LClick at")
        self.assertEqual(r.coords, (820, 450))
        self.assertEqual(r.current_software, "Explorer")
        self.assertEqual(r.base, "10.854s")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2：运行测试确认失败**

在仓库根目录运行：

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync -v
```

预期：`ModuleNotFoundError: No module named 'components_sync'`，全部测试 ERROR。

- [ ] **Step 3：实现 `components_sync.py` 骨架 + `IconRecord` + `sanitize_label`**

新建 `record/Aloha_Learn/components_sync.py`：

```python
"""Pure helpers for syncing record-flow icons into harness components/.

This module deliberately holds zero I/O and zero state — every function is a
pure mapping from inputs to outputs so it can be unit-tested in isolation.
The orchestrator lives in screenshot_processor.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


#: 30 chars matches gui_harness/planning/learn.py:224's LABEL_MAX_LEN.
_LABEL_MAX_LEN = 30


@dataclass(frozen=True)
class IconRecord:
    """Metadata for one icon file produced by the default-click branch."""

    filename: str
    action: str
    coords: tuple
    current_software: str
    base: str


# Pre-compiled character-class stripper: backslash, colon, question mark, asterisk.
_SPECIAL_CHARS_RE = re.compile(r"[\\:?*]")


def sanitize_label(raw: str) -> str:
    """Normalize a free-form label to snake_case, lowercased, alnum+underscore.

    Rules (verbatim from spec):
    - lowercase
    - whitespace -> "_"
    - "/" -> "-"
    - strip "\\", ":", "?", "*"
    - truncate to 30 chars

    Raises ValueError when the resulting label is empty (caller should fall back
    to a timestamp key).
    """
    if not raw:
        raise ValueError("label is empty")

    s = raw.strip().lower()
    s = s.replace("\\", "-").replace("/", "-")
    s = _SPECIAL_CHARS_RE.sub("", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    s = s[:_LABEL_MAX_LEN].rstrip("_")

    if not s:
        raise ValueError(f"label '{raw}' has no safe characters after sanitization")
    return s
```

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync -v
```

预期：9 个测试全部通过（`SanitizeLabelTest` 7 个 + `IconRecordTest` 1 个 + module import OK）。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/components_sync.py record/Aloha_Learn/tests/test_components_sync.py
git commit -m "feat(sync): add components_sync module skeleton with sanitize_label"
```

---

## Task 2：纯函数 `dedup_labels`

**Files:**
- Modify: `record/Aloha_Learn/components_sync.py`（追加 `dedup_labels`）
- Modify: `record/Aloha_Learn/tests/test_components_sync.py`（追加 `DedupLabelsTest`）

**Interfaces:**
- Consumes: `sanitize_label` 已存在。
- Produces: `def dedup_labels(labels: list[str]) -> list[str]`：同 batch 内去重，重复者加 `_2` / `_3` 后缀，直到与已出现的 label 不冲突。

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_components_sync.py` 追加：

```python
from components_sync import dedup_labels


class DedupLabelsTest(unittest.TestCase):
    def test_no_duplicates_returns_unchanged(self):
        self.assertEqual(
            dedup_labels(["start_button", "taskbar_search", "settings_gear"]),
            ["start_button", "taskbar_search", "settings_gear"],
        )

    def test_simple_duplicates_get_numeric_suffix(self):
        self.assertEqual(
            dedup_labels(["foo", "foo", "bar"]),
            ["foo", "foo_2", "bar"],
        )

    def test_suffix_collides_with_existing_label(self):
        # "x", "x_2", "x" -> third one must skip to "x_3"
        self.assertEqual(
            dedup_labels(["x", "x_2", "x"]),
            ["x", "x_2", "x_3"],
        )

    def test_empty_list(self):
        self.assertEqual(dedup_labels([]), [])
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync.DedupLabelsTest -v
```

预期：4 个测试因 `ImportError: cannot import name 'dedup_labels'` 失败。

- [ ] **Step 3：实现 `dedup_labels`**

向 `record/Aloha_Learn/components_sync.py` 追加：

```python
def dedup_labels(labels):
    """Append _2/_3/... suffixes to duplicates so each returned label is unique.

    Order-preserving: first occurrence wins without suffix; later collisions get
    suffixes that avoid clashing with already-seen labels.
    """
    seen = set()
    out = []
    for label in labels:
        candidate = label
        suffix = 2
        while candidate in seen:
            candidate = f"{label}_{suffix}"
            suffix += 1
        seen.add(candidate)
        out.append(candidate)
    return out
```

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync -v
```

预期：13 个测试全部通过（Task 1 的 9 个 + 本任务 4 个）。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/components_sync.py record/Aloha_Learn/tests/test_components_sync.py
git commit -m "feat(sync): add dedup_labels helper"
```

---

## Task 3：纯函数 `build_component_entry` + `ComponentEntry` dataclass

**Files:**
- Modify: `record/Aloha_Learn/components_sync.py`（追加 `ComponentEntry` + `build_component_entry`）
- Modify: `record/Aloha_Learn/tests/test_components_sync.py`（追加 `BuildComponentEntryTest`）

**Interfaces:**
- Consumes: 已存在 `sanitize_label`、`dedup_labels`。
- Produces:
  - `ComponentEntry` dataclass（与 harness 既有 schema 字段一一对应：`type`、`source`、`icon_file`、`label`、`learned_at`、`last_seen`、`seen_count`、`consecutive_misses`、`base_memory`）
  - `def build_component_entry(*, label: str, icon_file: str, learned_at: str, last_seen: str, seen_count: int, base_memory: bool = True) -> dict` —— 返回完整 entry dict；`base_memory` 默认 `True`，调用方永不传 `False`。

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_components_sync.py` 追加：

```python
from components_sync import ComponentEntry, build_component_entry


class BuildComponentEntryTest(unittest.TestCase):
    def test_returns_full_schema_with_all_fields(self):
        e = build_component_entry(
            label="start_button",
            icon_file="components/start_button.png",
            learned_at="2026-07-23 11:00:00",
            last_seen="2026-07-23 11:05:00",
            seen_count=3,
        )
        self.assertEqual(e, {
            "type": "icon",
            "source": "learn_batch",
            "icon_file": "components/start_button.png",
            "label": "start_button",
            "learned_at": "2026-07-23 11:00:00",
            "last_seen": "2026-07-23 11:05:00",
            "seen_count": 3,
            "consecutive_misses": 0,
            "base_memory": True,
        })

    def test_default_base_memory_is_true(self):
        e = build_component_entry(
            label="x",
            icon_file="components/x.png",
            learned_at="t",
            last_seen="t",
            seen_count=1,
        )
        self.assertTrue(e["base_memory"])

    def test_explicit_base_memory_true_is_honored(self):
        e = build_component_entry(
            label="x",
            icon_file="components/x.png",
            learned_at="t",
            last_seen="t",
            seen_count=1,
            base_memory=True,
        )
        self.assertTrue(e["base_memory"])

    def test_consecutive_misses_is_always_zero(self):
        # Upsert always resets to 0; callers should never set a non-zero value.
        e = build_component_entry(
            label="x",
            icon_file="components/x.png",
            learned_at="t",
            last_seen="t",
            seen_count=5,
        )
        self.assertEqual(e["consecutive_misses"], 0)


class ComponentEntryTest(unittest.TestCase):
    def test_constructs(self):
        e = ComponentEntry(
            type="icon",
            source="learn_batch",
            icon_file="components/x.png",
            label="x",
            learned_at="t",
            last_seen="t",
            seen_count=1,
            consecutive_misses=0,
            base_memory=True,
        )
        self.assertEqual(e.label, "x")
        self.assertEqual(e.seen_count, 1)
        self.assertTrue(e.base_memory)
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync.BuildComponentEntryTest record.Aloha_Learn.tests.test_components_sync.ComponentEntryTest -v
```

预期：5 个测试因 `ImportError: cannot import name 'ComponentEntry' / 'build_component_entry'` 失败。

- [ ] **Step 3：实现 `ComponentEntry` + `build_component_entry`**

向 `record/Aloha_Learn/components_sync.py` 追加：

```python
@dataclass(frozen=True)
class ComponentEntry:
    """One entry in the harness components.json — mirrors the schema of the
    existing 17 desktop/ entries (see gui_harness/memory/apps/desktop/components.json).
    """

    type: str
    source: str
    icon_file: str
    label: str
    learned_at: str
    last_seen: str
    seen_count: int
    consecutive_misses: int
    base_memory: bool


def build_component_entry(
    *,
    label: str,
    icon_file: str,
    learned_at: str,
    last_seen: str,
    seen_count: int,
    base_memory: bool = True,
) -> dict:
    """Construct a full component entry dict.

    base_memory defaults to True and is load-bearing: harness uses it to skip
    freshly-imported icons from automatic forgetting. Never set to False.
    """
    return ComponentEntry(
        type="icon",
        source="learn_batch",
        icon_file=icon_file,
        label=label,
        learned_at=learned_at,
        last_seen=last_seen,
        seen_count=seen_count,
        consecutive_misses=0,
        base_memory=base_memory,
    ).__dict__
```

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync -v
```

预期：18 个测试全部通过。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/components_sync.py record/Aloha_Learn/tests/test_components_sync.py
git commit -m "feat(sync): add ComponentEntry dataclass and build_component_entry"
```

---

## Task 4：纯函数 `merge_components_json`

**Files:**
- Modify: `record/Aloha_Learn/components_sync.py`（追加 `merge_components_json`）
- Modify: `record/Aloha_Learn/tests/test_components_sync.py`（追加 `MergeComponentsJsonTest`）

**Interfaces:**
- Consumes: 已存在 `build_component_entry`。
- Produces: `def merge_components_json(existing: dict, additions: dict[str, tuple[dict, str]], now_str: str) -> tuple[dict, list[str], list[str]]`：返回 `(merged_dict, keys_added, keys_updated)`。其中 `additions` 的 value 是 `(entry_dict, source_filename)`；upsert 语义：同 key 保留 `learned_at`、`seen_count += 1`、`last_seen = now_str`、`consecutive_misses = 0`；新 key 全字段写入。

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_components_sync.py` 追加：

```python
from components_sync import merge_components_json


def _entry(label, learned_at="2026-07-23 11:00:00", last_seen="2026-07-23 11:00:00", seen_count=1):
    return {
        "type": "icon",
        "source": "learn_batch",
        "icon_file": f"components/{label}.png",
        "label": label,
        "learned_at": learned_at,
        "last_seen": last_seen,
        "seen_count": seen_count,
        "consecutive_misses": 0,
        "base_memory": True,
    }


class MergeComponentsJsonTest(unittest.TestCase):
    def test_add_new_keys(self):
        existing = {}
        additions = {
            "foo": (_entry("foo"), "record_memory_icon_10.854s_crop.png"),
            "bar": (_entry("bar"), "record_memory_icon_11.054s_crop.png"),
        }
        merged, added, updated = merge_components_json(existing, additions, "2026-07-23 12:00:00")
        self.assertEqual(set(merged.keys()), {"foo", "bar"})
        self.assertEqual(added, ["foo", "bar"])
        self.assertEqual(updated, [])
        # New entries use the new now_str for both learned_at and last_seen
        self.assertEqual(merged["foo"]["learned_at"], "2026-07-23 12:00:00")
        self.assertEqual(merged["foo"]["last_seen"], "2026-07-23 12:00:00")
        self.assertEqual(merged["foo"]["seen_count"], 1)

    def test_upsert_existing_key_preserves_learned_at_and_increments_seen_count(self):
        existing = {
            "foo": _entry("foo", learned_at="2026-07-23 11:00:00", seen_count=5),
        }
        additions = {
            "foo": (_entry("foo", seen_count=1), "record_memory_icon_10.854s_crop.png"),
        }
        merged, added, updated = merge_components_json(existing, additions, "2026-07-23 12:00:00")
        self.assertEqual(added, [])
        self.assertEqual(updated, ["foo"])
        self.assertEqual(merged["foo"]["learned_at"], "2026-07-23 11:00:00")  # preserved
        self.assertEqual(merged["foo"]["last_seen"], "2026-07-23 12:00:00")  # refreshed
        self.assertEqual(merged["foo"]["seen_count"], 6)  # incremented

    def test_upsert_resets_consecutive_misses(self):
        # Even if existing entry has stale consecutive_misses, write resets it
        existing = {"foo": _entry("foo", seen_count=2)}
        existing["foo"]["consecutive_misses"] = 15
        additions = {
            "foo": (_entry("foo", seen_count=1), "record_memory_icon_10.854s_crop.png"),
        }
        merged, _, _ = merge_components_json(existing, additions, "2026-07-23 12:00:00")
        self.assertEqual(merged["foo"]["consecutive_misses"], 0)

    def test_existing_keys_not_in_additions_are_untouched(self):
        existing = {
            "keep_me": _entry("keep_me", seen_count=7),
        }
        additions = {
            "new_one": (_entry("new_one"), "record_memory_icon_11.054s_crop.png"),
        }
        merged, added, updated = merge_components_json(existing, additions, "2026-07-23 12:00:00")
        self.assertEqual(merged["keep_me"]["seen_count"], 7)  # unchanged
        self.assertEqual(merged["keep_me"]["learned_at"], "2026-07-23 11:00:00")  # unchanged
        self.assertEqual(added, ["new_one"])
        self.assertEqual(updated, [])
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync.MergeComponentsJsonTest -v
```

预期：4 个测试因 `ImportError: cannot import name 'merge_components_json'` 失败。

- [ ] **Step 3：实现 `merge_components_json`**

向 `record/Aloha_Learn/components_sync.py` 追加：

```python
def merge_components_json(existing, additions, now_str):
    """Upsert component entries into an existing components.json dict.

    Args:
        existing: dict mapping label -> entry dict (loaded from disk; may be empty).
        additions: dict mapping label -> (new_entry_dict, source_filename). The
            source_filename is informational only (used for diagnostics in
            callers' logs); it does not appear in the final JSON.
        now_str: timestamp string ("YYYY-MM-DD HH:MM:SS") used for last_seen on
            every entry and for learned_at on new keys.

    Returns:
        (merged_dict, keys_added, keys_updated) — keys_added is the list of
        labels that were newly inserted; keys_updated is the list of labels
        that were upserted into a pre-existing entry.
    """
    merged = dict(existing)
    keys_added = []
    keys_updated = []

    for label, (new_entry, _src_filename) in additions.items():
        prior = merged.get(label)
        if prior is None:
            # New key: use now_str for both learned_at and last_seen.
            entry = dict(new_entry)
            entry["learned_at"] = now_str
            entry["last_seen"] = now_str
            entry["seen_count"] = int(entry.get("seen_count", 1))
            entry["consecutive_misses"] = 0
            entry["base_memory"] = True
            merged[label] = entry
            keys_added.append(label)
        else:
            # Upsert: preserve learned_at, refresh last_seen, increment seen_count,
            # reset consecutive_misses. Carry forward type/source/icon_file/label
            # from the prior entry (they're the contract — only activity changes).
            entry = dict(prior)
            entry["last_seen"] = now_str
            entry["seen_count"] = int(prior.get("seen_count", 0)) + 1
            entry["consecutive_misses"] = 0
            entry["base_memory"] = True
            merged[label] = entry
            keys_updated.append(label)

    return merged, keys_added, keys_updated
```

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync -v
```

预期：22 个测试全部通过。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/components_sync.py record/Aloha_Learn/tests/test_components_sync.py
git commit -m "feat(sync): add merge_components_json upsert helper"
```

---

## Task 5：`ComponentsLLMError` + `_request_component_labels`（LLM 客户端）

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py`（新增异常类 + `_request_component_labels` 方法）
- Modify: `record/Aloha_Learn/tests/test_screenshot_processor.py`（新增 LLM 客户端相关测试）

**Interfaces:**
- Consumes: `trace_generator.py:_call_openai` 已有的 `requests.post(url, headers, json, timeout, verify)` 模式；`IconRecord` from `components_sync`。
- Produces:
  - `class ComponentsLLMError(Exception)` —— 编排层捕获后回退。
  - `VideoScreenshotExtractor._request_component_labels(self, records: list[IconRecord], screenshots_dir: Path) -> dict[str, str]` —— 单次 LLM 调用返回 `{filename: raw_label}`；任何失败抛 `ComponentsLLMError`。

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 顶部 import 块追加：

```python
from unittest.mock import MagicMock

from components_sync import IconRecord
```

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 末尾（`if __name__ == "__main__":` 之前）追加：

```python
class RequestComponentLabelsTest(unittest.TestCase):
    FILENAME = "record_memory_icon_10.854s_crop.png"

    def _records(self):
        return [
            IconRecord(
                filename=self.FILENAME,
                action="LClick at",
                coords=(820, 450),
                current_software="Explorer",
                base="10.854s",
            ),
        ]

    def _setup_icon(self, screenshots_dir):
        """Create one valid PNG at <screenshots_dir>/icons/<FILENAME> so the
        production code's open() call doesn't raise FileNotFoundError."""
        (screenshots_dir / "icons").mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(".png", np.zeros((4, 4, 3), dtype=np.uint8))
        self.assertTrue(ok)
        (screenshots_dir / "icons" / self.FILENAME).write_bytes(bytes(buf))

    def _mock_response(self, content):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={
            "choices": [{"message": {"content": content}}]
        })
        return resp

    def test_returns_label_map_on_success(self):
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_VERIFY_SSL": "true",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                with patch("requests.post", return_value=self._mock_response(
                    f'{{"{self.FILENAME}": "taskbar_search"}}'
                )) as p:
                    ext = VideoScreenshotExtractor()
                    labels = ext._request_component_labels(self._records(), screenshots_dir)

        self.assertEqual(labels, {self.FILENAME: "taskbar_search"})
        called_args, called_kwargs = p.call_args
        self.assertIn("/chat/completions", called_args[0])
        self.assertEqual(called_kwargs["json"]["model"], "gpt-4o")
        self.assertEqual(called_kwargs["timeout"], 120)
        msgs = called_kwargs["json"]["messages"]
        self.assertEqual(len(msgs), 1)
        content = msgs[0]["content"]
        self.assertTrue(any(
            c.get("type") == "text" and "taskbar_search" not in c.get("text", "")
            for c in content
        ), "content must include text metadata (without the LLM-provided label)")
        self.assertTrue(any(c.get("type") == "image_url" for c in content))

    def test_raises_components_llm_error_on_http_failure(self):
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                resp = MagicMock()
                resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))
                with patch("requests.post", return_value=resp):
                    ext = VideoScreenshotExtractor()
                    with self.assertRaises(ComponentsLLMError):
                        ext._request_component_labels(self._records(), screenshots_dir)

    def test_raises_components_llm_error_on_invalid_json(self):
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                with patch("requests.post", return_value=self._mock_response("not json")):
                    ext = VideoScreenshotExtractor()
                    with self.assertRaises(ComponentsLLMError):
                        ext._request_component_labels(self._records(), screenshots_dir)

    def test_raises_components_llm_error_when_missing_input_filenames(self):
        # LLM returns labels for a different file; missing files = error
        with patch.dict(os.environ, {
            "OPENAI_BASE_URL": "https://api.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "sk-test",
        }, clear=False):
            with tempfile.TemporaryDirectory() as tmp:
                screenshots_dir = Path(tmp)
                self._setup_icon(screenshots_dir)
                with patch("requests.post", return_value=self._mock_response(
                    '{"unrelated.png": "foo"}'
                )):
                    ext = VideoScreenshotExtractor()
                    with self.assertRaises(ComponentsLLMError):
                        ext._request_component_labels(self._records(), screenshots_dir)
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.RequestComponentLabelsTest -v
```

预期：4 个测试因 `ImportError: cannot import name 'ComponentsLLMError'` 失败。

- [ ] **Step 3：实现 `ComponentsLLMError` + `_request_component_labels`**

向 `record/Aloha_Learn/screenshot_processor.py` 顶部 import 块追加：

```python
import base64
```

向 `record/Aloha_Learn/screenshot_processor.py` 顶部 import 块（追加在所有现有 import 之后）追加：

```python
class ComponentsLLMError(Exception):
    """Raised when the components-naming LLM call fails for any reason.

    The orchestrator catches this and falls back to timestamp-keyed labels so
    process_project() keeps running.
    """
```

向 `record/Aloha_Learn/screenshot_processor.py` 中 `VideoScreenshotExtractor` 类的 `_save_png` 之后追加新方法：

```python
    def _request_component_labels(self, records, screenshots_dir):
        """Single batched multimodal call to the configured OpenAI-compatible LLM.

        Builds a system prompt instructing the model to assign snake_case
        content labels to each click icon, sends all icons inline as base64
        PNGs plus per-icon metadata, and parses the JSON-object response.

        screenshots_dir is a pathlib.Path pointing at the project's screenshots/
        directory. Icons are read from <screenshots_dir>/icons/<record.filename>.

        Raises ComponentsLLMError on any failure (HTTP, JSON parse, missing
        keys, unknown keys, missing API key/model, empty result).
        """
        api_key = (
            os.environ.get("OPENAI_API_KEY", "")
            or os.environ.get("MIDSCENE_MODEL_API_KEY", "")
        )
        if not api_key:
            raise ComponentsLLMError("OPENAI_API_KEY missing")

        base_url = (
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        )
        model = os.environ.get("OPENAI_MODEL", "")
        if not model:
            raise ComponentsLLMError("OPENAI_MODEL missing")

        verify_ssl = os.environ.get("OPENAI_VERIFY_SSL", "true").lower() not in ("0", "false", "no")

        system_prompt = (
            "You label desktop UI click crops. For each input icon, return a "
            "snake_case content label (lowercase letters, digits, underscores "
            "only; max 30 chars) describing what UI element the click targets. "
            "Respond with a JSON object mapping each input filename to its "
            "label. Do not add commentary or wrap in markdown."
        )

        filenames = [r.filename for r in records]
        content = [{"type": "text", "text": "Icon metadata follows."}]
        for r in records:
            icon_path = screenshots_dir / "icons" / r.filename
            with open(icon_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            content.append({
                "type": "text",
                "text": (
                    f"{r.filename} | action={r.action} | "
                    f"coords=({r.coords[0]},{r.coords[1]}) | "
                    f"software={r.current_software} | timestamp={r.base}"
                ),
            })
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            r = requests.post(url, headers=headers, json=payload,
                              timeout=120, verify=verify_ssl)
            r.raise_for_status()
            body = r.json()
            content_text = body["choices"][0]["message"]["content"]
            parsed = json.loads(content_text)
        except Exception as e:
            raise ComponentsLLMError(f"LLM call/parse failed: {e}") from e

        if not isinstance(parsed, dict):
            raise ComponentsLLMError(f"LLM response is not a JSON object: {type(parsed).__name__}")

        missing = [fn for fn in filenames if fn not in parsed]
        if missing:
            raise ComponentsLLMError(f"LLM response missing filenames: {missing}")
        unknown = [k for k in parsed.keys() if k not in filenames]
        if unknown:
            raise ComponentsLLMError(f"LLM response contains unknown filenames: {unknown}")

        return {fn: str(parsed[fn]) for fn in filenames}
```

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.RequestComponentLabelsTest -v
```

预期：4 个测试全部通过。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(sync): add ComponentsLLMError and _request_component_labels"
```

---

## Task 6：sync 辅助方法（`_load_components_json` + `_apply_components_updates`）

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py`（新增两个私有方法）
- Modify: `record/Aloha_Learn/tests/test_screenshot_processor.py`（追加辅助方法测试）

**Interfaces:**
- Consumes: `merge_components_json` from `components_sync`。
- Produces:
  - `VideoScreenshotExtractor._load_components_json(self, dest: Path) -> dict`：读 `dest/components.json`；缺失 / 损坏 → `{}`（后者写 warning）。
  - `VideoScreenshotExtractor._apply_components_updates(self, dest: Path, existing: dict, additions: dict[str, tuple[str, str]], screenshots_dir: Path, now_str: str) -> tuple[list[str], list[str]]`：拷贝 PNG + upsert + 写 JSON；返回 `(keys_added, keys_updated)`。

> `additions` 形参此处承载 `(safe_label, source_filename)` 元组列表（每个 source_filename 是 `screenshots_dir/icons/` 下的源图标）。内部调用 `build_component_entry` 构造 entry，再交给 `merge_components_json` upsert。

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 追加：

```python
import shutil as _shutil_for_test
from pathlib import Path as _Path_for_test


class LoadComponentsJsonTest(unittest.TestCase):
    def test_returns_empty_when_file_missing(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ext._load_components_json(_Path_for_test(tmp)), {})

    def test_returns_empty_when_file_corrupt(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            (_Path_for_test(tmp) / "components.json").write_text("{not json")
            self.assertEqual(ext._load_components_json(_Path_for_test(tmp)), {})

    def test_returns_parsed_dict_when_valid(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            (_Path_for_test(tmp) / "components.json").write_text('{"foo": {"label": "foo"}}')
            self.assertEqual(ext._load_components_json(_Path_for_test(tmp)), {"foo": {"label": "foo"}})


class ApplyComponentsUpdatesTest(unittest.TestCase):
    def _png_bytes(self):
        import cv2 as _cv2_for_test
        import numpy as _np_for_test
        ok, buf = _cv2_for_test.imencode(".png", _np_for_test.zeros((4, 4, 3), dtype=_np_for_test.uint8))
        self.assertTrue(ok)
        return bytes(buf)

    def test_copies_pngs_and_writes_json(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            src_icons = tmp / "src_icons"
            src_icons.mkdir()
            (src_icons / "icon_a.png").write_bytes(self._png_bytes())
            (src_icons / "icon_b.png").write_bytes(self._png_bytes())
            dest = tmp / "dest"
            dest.mkdir()
            existing = ext._load_components_json(dest)

            # additions: safe_label -> source_filename
            additions = {
                "foo": ("foo", "icon_a.png"),
                "bar": ("bar", "icon_b.png"),
            }
            now_str = "2026-07-23 12:00:00"
            keys_added, keys_updated = ext._apply_components_updates(
                dest, existing, additions, src_icons, now_str,
            )

            self.assertEqual(keys_added, ["foo", "bar"])
            self.assertEqual(keys_updated, [])

            # PNGs were copied with the right names
            self.assertTrue((dest / "components" / "foo.png").exists())
            self.assertTrue((dest / "components" / "bar.png").exists())

            # components.json contains both entries with expected fields
            data = json.loads((dest / "components.json").read_text(encoding="utf-8"))
            self.assertEqual(set(data.keys()), {"foo", "bar"})
            self.assertEqual(data["foo"]["type"], "icon")
            self.assertEqual(data["foo"]["source"], "learn_batch")
            self.assertEqual(data["foo"]["icon_file"], "components/foo.png")
            self.assertEqual(data["foo"]["label"], "foo")
            self.assertEqual(data["foo"]["learned_at"], now_str)
            self.assertEqual(data["foo"]["last_seen"], now_str)
            self.assertEqual(data["foo"]["seen_count"], 1)
            self.assertEqual(data["foo"]["consecutive_misses"], 0)
            self.assertTrue(data["foo"]["base_memory"])

    def test_upsert_preserves_learned_at_and_increments_seen_count(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            src_icons = tmp / "src_icons"
            src_icons.mkdir()
            (src_icons / "icon_a.png").write_bytes(self._png_bytes())
            dest = tmp / "dest"
            dest.mkdir()
            (dest / "components.json").write_text(json.dumps({
                "foo": {
                    "type": "icon",
                    "source": "learn_batch",
                    "icon_file": "components/foo.png",
                    "label": "foo",
                    "learned_at": "2026-07-23 10:00:00",
                    "last_seen": "2026-07-23 10:00:00",
                    "seen_count": 4,
                    "consecutive_misses": 0,
                    "base_memory": True,
                },
            }))
            existing = ext._load_components_json(dest)
            additions = {"foo": ("foo", "icon_a.png")}
            keys_added, keys_updated = ext._apply_components_updates(
                dest, existing, additions, src_icons, "2026-07-23 12:00:00",
            )
            self.assertEqual(keys_added, [])
            self.assertEqual(keys_updated, ["foo"])
            data = json.loads((dest / "components.json").read_text(encoding="utf-8"))
            self.assertEqual(data["foo"]["learned_at"], "2026-07-23 10:00:00")  # preserved
            self.assertEqual(data["foo"]["last_seen"], "2026-07-23 12:00:00")  # refreshed
            self.assertEqual(data["foo"]["seen_count"], 5)

    def test_runtimeerror_on_unwritable_dest(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            src_icons = tmp / "src_icons"
            src_icons.mkdir()
            (src_icons / "icon_a.png").write_bytes(self._png_bytes())
            dest = tmp / "dest_does_not_exist_and_cannot_be_created"
            # Force shutil.copyfile to fail by mocking it
            with patch("screenshot_processor.shutil.copyfile",
                       side_effect=OSError("permission denied")):
                with self.assertRaises(RuntimeError):
                    ext._apply_components_updates(
                        dest, {}, {"foo": ("foo", "icon_a.png")}, src_icons,
                        "2026-07-23 12:00:00",
                    )
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.LoadComponentsJsonTest record.Aloha_Learn.tests.test_screenshot_processor.ApplyComponentsUpdatesTest -v
```

预期：3 + 3 = 6 个测试因 `AttributeError` 失败。

- [ ] **Step 3：实现 `_load_components_json` + `_apply_components_updates`**

向 `record/Aloha_Learn/screenshot_processor.py` 中 `VideoScreenshotExtractor` 类追加：

```python
    def _load_components_json(self, dest):
        """Read dest/components.json. Missing or corrupt -> {} (with warning)."""
        json_path = dest / "components.json"
        if not json_path.exists():
            return {}
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print(f"[sync] WARNING: {json_path} is not a JSON object; treating as empty")
                return {}
            return data
        except json.JSONDecodeError as e:
            print(f"[sync] WARNING: {json_path} is corrupt ({e}); treating as empty")
            return {}

    def _apply_components_updates(self, dest, existing, additions, src_icons_dir, now_str):
        """Copy PNGs and upsert dest/components.json.

        Args:
            dest: target components dir (we'll create dest/components/ inside).
            existing: dict loaded from dest/components.json (may be empty).
            additions: dict mapping safe_label -> (safe_label, source_filename).
                The first element duplicates the key for convenience; the
                source_filename lives in src_icons_dir.
            src_icons_dir: directory containing the source PNGs
                (typically <project>/screenshots/icons/).
            now_str: timestamp string ("YYYY-MM-DD HH:MM:SS") for last_seen and
                new learned_at.

        Returns:
            (keys_added, keys_updated) per merge_components_json semantics.
        """
        components_dir = dest / "components"
        try:
            components_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Could not create {components_dir}: {e}") from e

        # Build full entries up-front, then copy PNGs, then upsert+write.
        entry_additions = {}
        for safe_label, source_filename in additions.values():
            src = src_icons_dir / source_filename
            entry = build_component_entry(
                label=safe_label,
                icon_file=f"components/{safe_label}.png",
                learned_at=now_str,
                last_seen=now_str,
                seen_count=1,
            )
            entry_additions[safe_label] = (entry, source_filename)
            dst = components_dir / f"{safe_label}.png"
            try:
                shutil.copyfile(src, dst)
            except OSError as e:
                raise RuntimeError(
                    f"Could not copy {src} -> {dst}: {e}"
                ) from e

        merged, keys_added, keys_updated = merge_components_json(
            existing, entry_additions, now_str,
        )

        json_path = dest / "components.json"
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise RuntimeError(f"Could not write {json_path}: {e}") from e

        return keys_added, keys_updated
```

向 `screenshot_processor.py` 顶部 import 块追加：

```python
import shutil
```

（如果已存在则跳过；不要重复 import。）

向 `screenshot_processor.py` 顶部 import 块追加：

```python
from components_sync import (
    IconRecord,
    build_component_entry,
    merge_components_json,
)
```

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.LoadComponentsJsonTest record.Aloha_Learn.tests.test_screenshot_processor.ApplyComponentsUpdatesTest -v
```

预期：6 个测试全部通过。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(sync): add _load_components_json and _apply_components_updates helpers"
```

---

## Task 7：编排方法 `_sync_components_to_dest`

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py`（新增 `_sync_components_to_dest`）
- Modify: `record/Aloha_Learn/tests/test_screenshot_processor.py`（追加 `ComponentSyncTest`）

**Interfaces:**
- Consumes: `IconRecord`、`sanitize_label`、`dedup_labels`、`build_component_entry`、`merge_components_json`、`_request_component_labels`、`_load_components_json`、`_apply_components_updates`。
- Produces:
  - `VideoScreenshotExtractor._sync_components_to_dest(self, actions: list, screenshots_dir: Path, dest: Path) -> dict`：返回 meta 增量字典（`components_synced=True`、`components_dest`、`components_keys_added`、`components_keys_updated`、`components_fallback_to_timestamp`）。
  - 流程：
    1. 从 `actions` 收集 default-click icon 的 `IconRecord` 列表（按文件名 → action metadata 对齐）
    2. 调 `_request_component_labels(records, screenshots_dir)`；捕获 `ComponentsLLMError` → 整批回退到 timestamp 键
    3. `safe_labels = dedup_labels([sanitize_label(l) for l in label_map.values()])` —— 顺序对齐 records
    4. `_load_components_json(dest)`
    5. `_apply_components_updates(...)`
    6. 返回 meta 增量

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 追加：

```python
class SyncComponentsToDestTest(unittest.TestCase):
    def _png_bytes(self):
        import cv2 as _cv2_for_test
        import numpy as _np_for_test
        ok, buf = _cv2_for_test.imencode(".png", _np_for_test.zeros((4, 4, 3), dtype=_np_for_test.uint8))
        self.assertTrue(ok)
        return bytes(buf)

    def _setup(self, root):
        """Create a screenshots_dir with one icon and matching action."""
        screenshots_dir = root / "screenshots"
        icons = screenshots_dir / "icons"
        icons.mkdir(parents=True)
        (icons / "record_memory_icon_10.854s_crop.png").write_bytes(self._png_bytes())
        action = {
            "timestamp": 10.954,
            "action": "LClick at",
            "coords": [{"x": 820, "y": 450}],
            "current_software": "Explorer",
            "screenshot_full": "screenshots/10.854s.jpg",
            "screenshot_crop": "screenshots/10.854s.crop.jpg",
        }
        return screenshots_dir, [action]

    def test_returns_meta_with_keys_added_on_success(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            screenshots_dir, actions = self._setup(tmp)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.object(
                ext, "_request_component_labels",
                return_value={"record_memory_icon_10.854s_crop.png": "Taskbar Search"},
            ):
                meta = ext._sync_components_to_dest(actions, screenshots_dir, dest)

            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_dest"], str(dest))
            self.assertEqual(meta["components_keys_added"], ["taskbar_search"])
            self.assertEqual(meta["components_keys_updated"], [])
            self.assertEqual(meta["components_fallback_to_timestamp"], False)

            # dest/components/taskbar_search.png exists, components.json contains the entry
            self.assertTrue((dest / "components" / "taskbar_search.png").exists())
            data = json.loads((dest / "components.json").read_text(encoding="utf-8"))
            self.assertIn("taskbar_search", data)
            self.assertEqual(data["taskbar_search"]["label"], "taskbar_search")
            self.assertEqual(data["taskbar_search"]["icon_file"], "components/taskbar_search.png")

    def test_falls_back_to_timestamp_keys_when_llm_raises(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            screenshots_dir, actions = self._setup(tmp)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.object(
                ext, "_request_component_labels",
                side_effect=ComponentsLLMError("network fail"),
            ):
                meta = ext._sync_components_to_dest(actions, screenshots_dir, dest)

            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_fallback_to_timestamp"], True)
            self.assertEqual(meta["components_keys_added"], ["record_memory_icon_10_854s_crop"])
            # PNG was copied under the timestamp-key name
            self.assertTrue(
                (dest / "components" / "record_memory_icon_10_854s_crop.png").exists()
            )

    def test_skips_non_default_click_actions(self):
        ext = VideoScreenshotExtractor()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            screenshots_dir = tmp / "screenshots"
            icons = screenshots_dir / "icons"
            icons.mkdir(parents=True)
            # No icon files at all -> sync has nothing to do
            actions = [
                {"timestamp": 10.954, "action": "LClick at",
                 "coords": [{"x": 1, "y": 1}], "current_software": "X"},
                {"timestamp": 11.0, "action": "Wheel at",
                 "coords": [{"x": 1, "y": 1}], "current_software": "X"},
                {"timestamp": 12.0, "action": "DragStart at",
                 "coords": [{"x": 1, "y": 1}], "current_software": "X",
                 "path": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]},
                {"timestamp": 13.0, "action": "CONFIG", "coords": {}},
                {"timestamp": 14.0, "action": "Active Window: Foo",
                 "coords": [{"x": 0, "y": 0}]},
            ]
            dest = tmp / "dest"
            dest.mkdir()

            # LLM should never be called because there are no icons.
            with patch.object(ext, "_request_component_labels") as mock_llm:
                meta = ext._sync_components_to_dest(actions, screenshots_dir, dest)

            mock_llm.assert_not_called()
            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_keys_added"], [])
            self.assertEqual(meta["components_keys_updated"], [])
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.SyncComponentsToDestTest -v
```

预期：3 个测试因 `AttributeError: '_sync_components_to_dest'` 失败。

- [ ] **Step 3：实现 `_sync_components_to_dest`**

向 `screenshot_processor.py` 中 `VideoScreenshotExtractor` 类追加：

```python
    def _collect_icon_records(self, actions, screenshots_dir):
        """Walk actions + screenshots_dir/icons/ to build IconRecord list.

        Only default-click branches produce icons in this repo's flow
        (see process_actions at line ~189-205). We match each icon file
        to the action whose base (timestamp - 0.1) corresponds to its filename.
        """
        icon_dir = screenshots_dir / "icons"
        if not icon_dir.exists():
            return []

        # Map base -> action for O(1) lookup
        base_to_action = {}
        for a in actions:
            ts = abs(a.get("timestamp", 0) - 0.1)
            base = f"{ts:.3f}s"
            base_to_action[base] = a

        records = []
        for icon_path in sorted(icon_dir.glob("record_memory_icon_*_crop.png")):
            filename = icon_path.name
            # filename = "record_memory_icon_<base>_crop.png"; strip prefix/suffix
            base = filename[len("record_memory_icon_"):-len("_crop.png")]
            if base not in base_to_action:
                continue
            a = base_to_action[base]
            coords_list = a.get("coords", [])
            if not coords_list or not isinstance(coords_list, list):
                continue
            coords = (int(coords_list[0]["x"]), int(coords_list[0]["y"]))
            records.append(IconRecord(
                filename=filename,
                action=str(a.get("action", "")),
                coords=coords,
                current_software=str(a.get("current_software", "")),
                base=base,
            ))
        return records

    def _sync_components_to_dest(self, actions, screenshots_dir, dest):
        """End-to-end sync orchestration; returns the meta-delta dict."""
        records = self._collect_icon_records(actions, screenshots_dir)

        if not records:
            # Nothing to sync but the dest may still need to be touched
            # (e.g. ensure components.json exists). We keep meta consistent.
            return {
                "components_synced": True,
                "components_dest": str(dest),
                "components_keys_added": [],
                "components_keys_updated": [],
                "components_fallback_to_timestamp": False,
            }

        # Ask the LLM for labels; fall back to timestamp keys on any failure.
        fallback = False
        try:
            label_map = self._request_component_labels(records, screenshots_dir)
        except ComponentsLLMError as e:
            print(f"[sync] WARNING: LLM labeling failed ({e}); using timestamp keys")
            label_map = {
                r.filename: r.base.replace(".", "_")
                for r in records
            }
            fallback = True

        # Sanitize + dedup, preserving order alignment with records.
        raw_labels = [label_map[r.filename] for r in records]
        try:
            safe_labels = [
                sanitize_label(l) for l in raw_labels
            ]
        except ValueError as e:
            print(f"[sync] WARNING: sanitize_label failed ({e}); using timestamp keys")
            safe_labels = [r.base.replace(".", "_") for r in records]
            fallback = True

        safe_labels = dedup_labels(safe_labels)

        # Pair safe_label with the source filename for the helper.
        additions = {
            safe: (safe, rec.filename)
            for safe, rec in zip(safe_labels, records)
        }

        existing = self._load_components_json(dest)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keys_added, keys_updated = self._apply_components_updates(
            dest, existing, additions, screenshots_dir / "icons", now_str,
        )

        return {
            "components_synced": True,
            "components_dest": str(dest),
            "components_keys_added": keys_added,
            "components_keys_updated": keys_updated,
            "components_fallback_to_timestamp": fallback,
        }
```

向 `screenshot_processor.py` 顶部 import 块追加：

```python
from datetime import datetime
from components_sync import IconRecord, sanitize_label, dedup_labels
```

（如果 `datetime` 已经 import 则跳过；不要重复 import。）

- [ ] **Step 4：运行测试确认通过**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.SyncComponentsToDestTest -v
```

预期：3 个测试全部通过。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(sync): add _sync_components_to_dest orchestration"
```

---

## Task 8：`process_project()` 集成 + `meta` 字段扩展 + 完整回归

**Files:**
- Modify: `record/Aloha_Learn/screenshot_processor.py`（`process_project()` 末尾触发同步 + `meta` 字段扩展）
- Modify: `record/Aloha_Learn/tests/test_screenshot_processor.py`（追加 `ProcessProjectSyncTest`，跑真实 `process_project` + 临时目录）

**Interfaces:**
- Consumes: 已存在 `_sync_components_to_dest`。
- Produces: `process_project()` 在 `meta` 写盘前同步；env var 缺失 → `meta["components_synced"] = False`；env var 在场 → 调 `_sync_components_to_dest(...)`，把返回 dict 合并到 `meta`。

- [ ] **Step 1：编写失败的测试**

向 `record/Aloha_Learn/tests/test_screenshot_processor.py` 追加：

```python
class ProcessProjectSyncTest(unittest.TestCase):
    """End-to-end: process_project() reads env var and triggers sync."""

    def _write_project(self, project_dir):
        """Create a minimal project with CONFIG + 2 LClick actions."""
        import json as _json
        (project_dir / "inputs").mkdir(parents=True)
        # Empty mp4 is fine for this test — _get_frame_at will be mocked.
        (project_dir / "inputs" / "demo.mp4").write_bytes(b"")
        actions = [
            {"action": "CONFIG", "coords": {"0": {"width": 1920, "height": 1080, "scale_factor": 1.0}}},
            {"timestamp": 10.954, "action": "LClick at",
             "coords": [{"x": 820, "y": 450}], "current_software": "Explorer"},
            {"timestamp": 11.054, "action": "Wheel at",
             "coords": [{"x": 500, "y": 500}], "current_software": "Explorer"},
        ]
        (project_dir / "demo_processed_log.json").write_text(
            _json.dumps(actions), encoding="utf-8"
        )

    def test_env_var_unset_skips_sync_and_meta_has_synced_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            project_dir = tmp / "proj"
            self._write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()

            with patch.dict(os.environ, {"GUI_AGENT_COMPONENTS_DEST": ""}, clear=False):
                # Sanity: confirm env var is empty in this test scope
                self.assertEqual(os.environ.get("GUI_AGENT_COMPONENTS_DEST", "").strip(), "")
                ext = VideoScreenshotExtractor()
                # Mock _get_frame_at to skip video decode
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch.object(ext, "_sync_components_to_dest") as mock_sync:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_sync.assert_not_called()
            self.assertEqual(meta["components_synced"], False)
            self.assertIsNone(meta["components_dest"])
            self.assertEqual(meta["components_keys_added"], [])
            self.assertEqual(meta["components_keys_updated"], [])

    def test_env_var_set_triggers_sync_and_meta_is_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _Path_for_test(tmp)
            project_dir = tmp / "proj"
            self._write_project(project_dir)
            dest = tmp / "dest"
            dest.mkdir()

            sync_return = {
                "components_synced": True,
                "components_dest": str(dest),
                "components_keys_added": ["taskbar_search"],
                "components_keys_updated": [],
                "components_fallback_to_timestamp": False,
            }

            with patch.dict(os.environ,
                            {"GUI_AGENT_COMPONENTS_DEST": str(dest)}, clear=False):
                ext = VideoScreenshotExtractor()
                with patch.object(ext, "_get_frame_at", return_value=np.zeros((1080, 1920, 3), dtype=np.uint8)):
                    with patch.object(ext, "_sync_components_to_dest",
                                      return_value=sync_return) as mock_sync:
                        _, _, meta = ext.process_project(str(project_dir))

            mock_sync.assert_called_once()
            self.assertEqual(meta["components_synced"], True)
            self.assertEqual(meta["components_dest"], str(dest))
            self.assertEqual(meta["components_keys_added"], ["taskbar_search"])
            self.assertEqual(meta["components_fallback_to_timestamp"], False)
            # Pre-existing meta fields still present
            self.assertIn("video_file", meta)
            self.assertIn("saved_log_sc", meta)
```

- [ ] **Step 2：运行测试确认失败**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_screenshot_processor.ProcessProjectSyncTest -v
```

预期：2 个测试因 meta 缺字段 / `_sync_components_to_dest` 未被调 / `components_synced != False` 等失败。

- [ ] **Step 3：在 `process_project()` 末尾触发同步**

定位 `record/Aloha_Learn/screenshot_processor.py` 中的 `process_project()` 方法（行 ~277-357）。在 `meta = {...}` 之前（或 `meta` 写盘之前），插入 env var 检查 + sync 调用 + meta 合并。

修改前（`process_project` 末尾）：

```python
        out_json_sc = project_dir / f"{project_dir.name}_processed_log_sc.json"
        with open(out_json_sc, "w", encoding="utf-8") as f:
            json.dump(updated_actions, f, ensure_ascii=False, indent=2)

        meta = {
            "video_file": str(video_path),
            "log_file": str(log_path),
            "coordinate_scaling": need_scaling,
            "original_resolution": f"{ow}x{oh}" if ow and oh else "unknown",
            "target_resolution": f"{frame_w}x{frame_h}",
            "saved_log_sc": str(out_json_sc)
        }

        return updated_actions, screenshots_dir, meta
```

修改后：

```python
        out_json_sc = project_dir / f"{project_dir.name}_processed_log_sc.json"
        with open(out_json_sc, "w", encoding="utf-8") as f:
            json.dump(updated_actions, f, ensure_ascii=False, indent=2)

        meta = {
            "video_file": str(video_path),
            "log_file": str(log_path),
            "coordinate_scaling": need_scaling,
            "original_resolution": f"{ow}x{oh}" if ow and oh else "unknown",
            "target_resolution": f"{frame_w}x{frame_h}",
            "saved_log_sc": str(out_json_sc)
        }

        # Optional: sync icons to a configured harness components/ dir.
        dest_str = os.environ.get("GUI_AGENT_COMPONENTS_DEST", "").strip()
        if dest_str:
            dest_path = Path(dest_str)
            sync_meta = self._sync_components_to_dest(
                actions, screenshots_dir, dest_path,
            )
            meta.update(sync_meta)
        else:
            meta["components_synced"] = False
            meta["components_dest"] = None
            meta["components_keys_added"] = []
            meta["components_keys_updated"] = []
            meta["components_fallback_to_timestamp"] = False

        return updated_actions, screenshots_dir, meta
```

- [ ] **Step 4：跑全套测试确认零回归**

```bash
PYTHONPATH=. python -m unittest record.Aloha_Learn.tests.test_components_sync record.Aloha_Learn.tests.test_screenshot_processor -v
```

预期：22（纯函数）+ 14（screenshot_processor 全部 test 类，含 RequestComponentLabelsTest、LoadComponentsJsonTest、ApplyComponentsUpdatesTest、SyncComponentsToDestTest、ProcessProjectSyncTest，以及旧的 IconCropSizeConstructorTest / SavePngHelperTest / DefaultClickIconSaveTest） = 36 个测试全部通过。

- [ ] **Step 5：提交**

```bash
git add record/Aloha_Learn/screenshot_processor.py record/Aloha_Learn/tests/test_screenshot_processor.py
git commit -m "feat(sync): wire components sync into process_project end + meta fields"
```

---

## Task 9：手动端到端验证（`record_icon_click`）

**Files:** 不修改任何文件；本任务是手工烟雾测试。

- [ ] **Step 1：准备 dest 备份**

确认 `gui_harness/memory/apps/desktop/components.json` 与 `gui_harness/memory/apps/desktop/components/` 当前状态，便于事后比对：

```bash
cp "E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components.json" \
   /tmp/desktop_components.json.before
cp -r "E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components" \
      /tmp/desktop_components.before
```

- [ ] **Step 2：设置 env var 并跑 record**

```bash
export GUI_AGENT_COMPONENTS_DEST="E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components"
cd record/Aloha_Learn
PYTHONPATH=../.. python -m record.Aloha_Learn.screenshot_processor record_icon_click
```

预期：CLI 正常输出；末尾 `Screenshots saved in: ...`。需要确保 `.env` 中 `OPENAI_MODEL` 与 `OPENAI_API_KEY` 可用且模型支持视觉。

- [ ] **Step 3：核对 dest 端产物**

```bash
diff /tmp/desktop_components.before <(ls "E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components") | head
```

预期：dest 端 `components/` 目录新增 9 个 `<label>.png`（与 `record_icon_click` 产出的 9 个 default-click icon 一一对应），既有 17 个文件不动。

- [ ] **Step 4：核对 `components.json` 增量**

```bash
python -c "import json; d = json.load(open('E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop/components.json')); print('total keys:', len(d)); print('new keys:', sorted(set(d) - set(json.load(open('/tmp/desktop_components.json.before')))))"
```

预期：`total keys >= 26`（17 + 9）；`new keys` 含 9 个 snake_case 标签。每个新 entry 含 `type=icon, source=learn_batch, base_memory=true`，且 `icon_file` 与同名 PNG 对应。

- [ ] **Step 5：核对 `processed_log_sc.json` schema 不变**

```bash
python -c "import json; d = json.load(open('record/Aloha_Learn/projects/record_icon_click/record_icon_click_processed_log_sc.json')); print(sorted(d[0].keys()))"
```

预期：仍为 `['action', 'coords', 'current_software', 'path', 'screenshot_crop', 'screenshot_full', 'timestamp']`，无 `components_synced` 等字段。

- [ ] **Step 6（可选）：重跑同一 record session，验证 upsert**

再跑一次 `python -m record.Aloha_Learn.screenshot_processor record_icon_click`（env var 仍在场）。

预期：9 个原有 key 走 upsert，`seen_count` 从 1 变成 2；`learned_at` 不变；`last_seen` 刷新。

- [ ] **Step 7（可选）：临时把 `OPENAI_MODEL` 设成不支持视觉的模型，验证回退**

```bash
export OPENAI_MODEL="text-only-davinci-002"  # 任何不支持 vision 的字符串
PYTHONPATH=../.. python -m record.Aloha_Learn.screenshot_processor record_icon_click
```

预期：record 仍正常完成；`dest/components/record_memory_icon_*` 等 timestamp 键 PNG 出现；`components.json` 含 timestamp 键 entry。

- [ ] **Step 8（可选）：把改动 commit**

如果临时写了验证脚本，按需提交；否则跳过。

---

## 自检（Self-Review）

**1. Spec 覆盖：**

- ✅ 默认同步触发条件 → Task 8（process_project 末尾 env var 检查 + meta）。
- ✅ 同步范围与现有 icon 写入一致 → Task 7（`_collect_icon_records` 只匹配 `screenshots/icons/record_memory_icon_*_crop.png`）；测试 `test_skips_non_default_click_actions`。
- ✅ LLM 实时命名内容标签 → Task 5（`_request_component_labels`）+ Task 7（编排）。
- ✅ LLM 失败回退到 timestamp 键 → Task 7（`fallback = True` 分支）+ Task 5（`ComponentsLLMError`）+ 测试。
- ✅ 标签去重与规范化 → Task 1（sanitize）+ Task 2（dedup）+ Task 7（组合）。
- ✅ components.json upsert 语义 → Task 4（merge）+ Task 6（apply）+ 测试。
- ✅ dest 端 schema 与 harness 既有 entry 对齐 → Task 3（`build_component_entry`）。
- ✅ 文件拷贝与 PNG 完整性 → Task 6（`shutil.copyfile`）+ 测试（自动验证 PNG 存在）。
- ✅ dest 不可写硬失败 → Task 6（`OSError → RuntimeError`）+ 测试。
- ✅ 现有 dest 内容不受破坏 → Task 6（`_load_components_json` 损坏回退）+ 测试。
- ✅ processed_log_sc.json schema 不变 → Task 8 末尾步骤 5 验证。
- ✅ 后向兼容 → Task 8（env var 在 `process_project` 内读，`__init__` 签名不变）。
- ✅ meta 字段可观察 → Task 8（meta 合并）+ 测试。
- ⚠️ **spec 修订**：spec.md / design.md 当前说 LLM 客户端用 `openai` SDK；但 `trace_generator.py` 与本 plan 都用 `requests.post`。这是 spec 措辞错误，**实施前需要在 commit 前**用 Edit 把 spec 文档里"openai SDK"改成"OpenAI 兼容 API（requests.post 模式）"。

**2. 占位符扫描：**

- 没有"TBD" / "TODO" / "implement later"。
- 没有"add appropriate error handling"之类没有代码的占位 —— 错误处理都用 try/except + raise 显式实现。
- 没有"write tests for the above" —— 每个测试类都给出具体测试代码。
- 没有"similar to Task N" —— 每个代码块都自包含。
- 所有路径均为绝对路径或仓库相对路径。
- 所有命令均给出预期输出。

**3. 类型一致性：**

- `IconRecord` 在 Task 1 定义，在 Task 5 / Task 7 消费，签名一致（`filename / action / coords / current_software / base`）。
- `sanitize_label` 在 Task 1 定义 `(raw: str) -> str`，Task 7 调用一致。
- `dedup_labels` 在 Task 2 定义 `(labels: list[str]) -> list[str]`，Task 7 调用一致。
- `build_component_entry` 在 Task 3 定义（keyword-only 参数），Task 6 / Task 7 调用一致。
- `merge_components_json` 在 Task 4 定义 `(existing, additions, now_str) -> (merged, added, updated)`，Task 6 / Task 7 调用一致。
- `_request_component_labels` 在 Task 5 定义 `(records, screenshots_dir) -> dict[str, str]`，Task 7 调用一致。
- `_apply_components_updates` 在 Task 6 定义 `(dest, existing, additions, src_icons_dir, now_str) -> (added, updated)`，Task 7 调用一致。
- `_sync_components_to_dest` 在 Task 7 定义 `(actions, screenshots_dir, dest) -> dict`（meta 增量），Task 8 调用一致。
- `ComponentsLLMError` 在 Task 5 定义，Task 7 捕获一致。

未发现不一致。

**4. 拆分合理性：**

- Task 1-4 是纯函数模块，每个任务独立可测、独立可 review。
- Task 5-7 是编排层（异常类 + LLM 客户端 + 辅助方法 + 顶层编排），彼此依赖但有清晰接口边界。
- Task 8 是 process_project 集成，是自然终点。
- Task 9 是手动端到端，独立验证。
- 拆分让 reviewer 可以在 Task 4 完成后审纯函数模块、Task 7 完成后审编排、Task 8 完成后审集成。