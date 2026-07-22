## Why

Midscene YAML 重构删除了录制任务的整体 aiAct 入口，只保留逐 task 执行和无录制自然语言 aiAct，导致已录制流程无法在页面偏离固定路径时交由模型统一规划。需要在不恢复旧 flow DSL 和独立 TypeScript runner 的前提下，重新提供原有 `act run --scene/--task` 调用方式。

## What Changes

- 恢复 `cua act run --scene <scene> --task <task>`，并支持现有 `--input`、`--inputs`、`--projects-root` 和 `--dry-run`。
- 保留 `cua act run --prompt <要求>`，两种来源严格互斥且不得自动切换。
- 从参数已解析的 canonical `task.yaml` 确定性生成完整有序步骤 prompt，并将其包装为临时单 `ai` action YAML。
- 复用现有 `run-midscene-yaml.ts`、`ExecutorResult` 和 `KeyboardTypeText` action space，不恢复旧 flow、专用 aiAct runner 或结果契约。
- 在任务报告目录保存 resolved task、最终 prompt、临时 aiAct YAML 和执行结果；未知或无法可靠转换的 YAML action 直接失败。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `ai-act-execution`：恢复录制 YAML 任务作为 aiAct 来源，并改为复用统一 YAML runner。
- `python-task-core`：恢复 `act run` 的任务参数入口和确定性 prompt 组合职责。
- `local-task-skills`：重新向上层 Agent 说明逐步 YAML、录制任务整体 aiAct、无录制自然语言 aiAct 三种显式模式。

## Impact

- 修改 Python CLI、任务执行编排和新增的 prompt 渲染模块。
- 更新 Python 测试、执行器 Skill、README 与任务契约。
- TypeScript runner 和持久化 JSON Schema 不变。
