## Context

当前 canonical 资产是 Midscene `task.yaml`。`task run` 解析本次输入后调用 `agent.runYaml()`，按多个 Midscene task 顺序执行；`act run --prompt` 则生成一个只含 `ai` action 的临时 YAML。YAML 重构时删除了录制任务整体 aiAct prompt 组合器和专用 TS runner，因此无法显式选择“让模型看到全部录制步骤后统一规划”。

约束是：`task.yaml` 仍是唯一长期事实源；不恢复旧 flow DSL、route、第二份长期资产或专用结果 Schema；无剪贴板 ASCII 输入继续依赖已注册的 `KeyboardTypeText`；失败不得触发模式切换或自动重试。

## Goals / Non-Goals

**Goals:**

- 恢复 `act run --scene/--task` 及稀疏输入参数。
- 从 resolved task YAML 确定性生成一次整体 aiAct prompt。
- 复用现有 Python resolver、统一 YAML runner、ComputerAgent 和执行结果契约。
- 保存可检查的 resolved YAML、最终 prompt、临时 aiAct YAML 和执行结果。

**Non-Goals:**

- 不把整体 aiAct prompt 保存为 canonical 任务资产。
- 不支持逐步执行失败后的自动接管。
- 不通过模型解释或补全未知 YAML action。
- 不恢复旧 `run-midscene-ai-act.ts`、resolved flow 或 aiAct 专用结果模型。

## Decisions

### 1. `act run` 接受互斥来源

CLI 保留 `--prompt` 自然语言模式，并恢复完整 `--scene`、`--task` 任务模式。任务模式支持 `--projects-root`、重复 `--input`、`--inputs` 和 `--dry-run`；prompt 模式不得携带任务或输入参数。参数组合在任何任务解析或执行器启动前验证。

选择继续使用 `act run` 而不是新增 `task act`，因为命令域表达的是整体 aiAct 执行策略，scene/task 只负责选择输入来源。`task run` 明确保留为原生 YAML 逐 task 执行。

### 2. Python 从 resolved YAML 渲染最终 prompt

任务模式先调用现有 resolver 应用录制默认值和本次稀疏输入，再按 `tasks[]` 顺序渲染。prompt 固定以“请严格按以下步骤顺序完成电脑操作：”开头，并保留每个 `step-NNN | <operation-type>` 名称。

第一版确定性支持 converter 和当前任务契约能够产生的动作：

- `aiTap`：直接使用其中文执行指令。
- `KeyboardTypeText`：显式描述 locate、resolved value、mode，并要求使用同名 customAction。
- `KeyboardPress`：描述按下的 keyName。
- `aiWaitFor`：描述等待条件。
- `ai`：直接使用其自然语言要求。
- `sleep`：不进入 prompt，因为录制间隔不是整体规划语义。

每个 task 可以包含多个非 sleep action，并按 flow 顺序输出。未知动作、缺失字段、空指令或一个 action 项包含冲突动作时直接失败，不调用模型猜测。整体目标、source、trace evidence 和 timing 不写入最终 prompt。

### 3. 整体 aiAct 仍通过统一 YAML runner

Python 在任务自己的 `reports/<run-id>/` 写入：

- `resolved-task.yaml`：本次参数解析结果。
- `ai-act-prompt.txt`：最终完整 prompt。
- `ai-act-task.yaml`：只包含一个 `ai` action 的临时 Midscene YAML。
- `execution-result.json`：现有 runner 结果。

`ai-act-task.yaml` 使用现有 `AI_ACT_CONTEXT`，要求 ASCII 输入只使用 `KeyboardTypeText`，不使用默认 Input 或剪贴板。随后调用现有 `execute_yaml()` 和 `run-midscene-yaml.ts`；dry-run 只解析临时 YAML，不创建设备或调用模型。

没有恢复专用 TS runner，因为 Midscene YAML 的 `ai` action 已经提供 aiAct 调用语义，现有 runner 也已经注册 customActions。

### 4. 两种模式不自动切换

`task run`、`act run --scene/--task` 和 `act run --prompt` 都是上层 Agent 或用户的显式选择。任一模式失败后原样暴露错误并保留报告，不调用其他模式、不改写 canonical YAML、不自动重试。

## Risks / Trade-offs

- [canonical YAML 包含新 Midscene action] -> prompt renderer 在支持列表外 fail fast，待明确语义后扩展，不做通用字符串猜测。
- [整体 prompt 较长导致模型成本增加] -> 该模式只在调用方显式选择时使用；稳定页面继续推荐 `task run`。
- [aiAct 未按步骤或未选择 customAction] -> prompt 保留稳定步骤名并通过 `aiActContext` 约束；实际规划错误由 Midscene 报告暴露。
- [参数改变后续固定 prompt 语义] -> 仍要求 canonical YAML 显式复用同一占位符，本变更不机械推断关联。

## Migration Plan

1. 新增 prompt renderer 与单元测试。
2. 恢复 CLI 任务来源并复用统一执行编排。
3. 更新 Skill 和文档，安装本机副本并执行 dry-run 验证。

回滚时撤销本变更提交即可；canonical 任务资产格式没有变化。

## Open Questions

无。本轮仅支持完整任务，不增加步骤区间或失败接管。
