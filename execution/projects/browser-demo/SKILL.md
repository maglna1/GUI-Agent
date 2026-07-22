---
name: browser-demo
description: 发现和调用浏览器操作示例场景中的本地 CUA 任务。
---

# 浏览器操作示例场景

本场景用于验证浏览器中的 Midscene computer use 流程。

本目录随 Executor Skill 发布，属于只读 builtin catalog。可以发现和运行其中任务，但不得在这里沉淀用户任务或运行产物。

先运行 `node dist/cua/cli/main.js task list --scene browser-demo --json` 发现任务。只有在用户选择或意图明确匹配某个任务后，才读取对应任务目录中的 `SKILL.md` 和 `task.json`；需要检查或修改动作时再读取 `task.yaml`。

当前任务：

- `air-tickets-demo`：在 Qatar Airways 页面设置单程航班搜索条件。
