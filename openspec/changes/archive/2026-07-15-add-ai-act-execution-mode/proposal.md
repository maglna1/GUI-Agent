## Why

当前执行器只能按录制生成的 resolved flow 逐步调用 Midscene，能够降低规划成本，但无法覆盖没有录制资产的自然语言任务，也无法让 Midscene 对一段已录制完整流程进行统一规划。需要新增一种显式的 `aiAct` 执行模式，同时保留现有确定性流程并禁止失败后的隐式切换。

## What Changes

- 新增独立的 Midscene `aiAct` 执行器，支持直接自然语言和 resolved flow 两种互斥输入。
- 将已录制任务的有效执行步骤按原顺序组合为一条完整中文 prompt，并一次性交给 `agent.aiAct()`。
- 新增 Python `cua act run` 统一入口，复用现有任务解析、参数覆盖和 resolved flow 快照能力。
- 新增 `AiActExecutorResult` 持久化契约与 JSON Schema，分别在全局或任务报告目录保存 prompt、结果和原始错误。
- 抽取 resolved flow 校验及键盘动作绑定的共享 TypeScript 组件，供确定性 runner 和 aiAct runner 复用。
- 更新执行器 Skill 和文档，要求上层 Agent 显式选择执行模式，禁止自动回退、自动修改任务或自动重试。

## Capabilities

### New Capabilities

- `ai-act-execution`: 定义自然语言与录制任务的 Midscene aiAct 执行、prompt 组合、结果落盘和失败语义。

### Modified Capabilities

- `python-task-core`: 增加 `cua act run` 入口、aiAct 结果契约，以及任务模式复用 resolved flow 的要求。
- `local-task-skills`: 增加确定性 flow、录制任务 aiAct 和无录制自然语言 aiAct 三种显式调用方式及选择约束。

## Impact

- 影响 `execution/executors` 下的 Midscene 适配器与共享组件。
- 影响 `execution/cua` 的 CLI、任务执行边界模型和 Schema 生成。
- 新增执行报告契约，但不改变 canonical `midscene-flow.json` 和现有 `flow run` 的行为。
- `execution/` 作为完整 `cua-midscene` Skill 发布单元，包含入口、元数据、契约和运行代码；本机 Skill 副本需要重新安装。
