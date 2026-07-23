# sync-record-icons-to-components

每次 `process_project()` 跑完后，自动把该轮产出的 click icon 同步到 harness 的 `components.json` 所在目录，键由视觉模型实时给出 snake_case 内容标签。

## 目标

消除 record 完成与 harness 消费之间的手工导入步骤。`process_project()` 一结束，下游 `cv2.matchTemplate` 就能立即看到新增的 icon。

## 环境变量约定

`GUI_AGENT_COMPONENTS_DEST` 应设为 harness 的 **app 目录**（即 `desktop/` 这一层），不是 `desktop/components/`。代码会把：

- `<dest>/components.json` —— 与既有 17 条 desktop 组件同款 schema
- `<dest>/components/<label>.png` —— icon PNG

按兄弟形式落盘。`icon_file` 字段值为相对 `dest` 的 `components/<label>.png`。

正确示例：`GUI_AGENT_COMPONENTS_DEST="E:/pycharm projects/GUI-Agent-Harness-Github/gui_harness/memory/apps/desktop"`

## 制品

- `proposal.md` — 动机与范围
- `design.md` — 实施方案与权衡
- `specs/record-icons-to-components-sync/spec.md` — 规范性需求
- `tasks.md` — 实施步骤清单

完整设计论述见 `docs/superpowers/specs/2026-07-23-record-icons-to-components-sync-design.md`。