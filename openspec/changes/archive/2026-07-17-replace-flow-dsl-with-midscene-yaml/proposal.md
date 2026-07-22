## Why

当前执行链在 trace 与 Midscene 之间维护了自定义 `midscene-flow.json`、resolved flow、route 分发器和 aiAct prompt 组合器，同一动作被重复建模和校验，增加了维护成本，也偏离了 Midscene 已提供的 YAML 契约。项目仍处于开发探索阶段，应直接收敛到 trace 生成 Midscene YAML 的最短链路，让人、Agent、未来前端和 Midscene 共同修改或消费同一份任务文件。

## What Changes

- **BREAKING**：以任务根目录的 `task.yaml` 取代 `midscene-flow.json`，不提供旧资产迁移、兼容读取或执行兜底。
- trace converter 只根据结构化 `operation` 和录制时间生成 Midscene YAML；字段缺失或动作不支持时立即失败，不从自然语言关键词推测动作。
- Python 使用 `task.json` 声明输入名称、中文说明和录制默认值，并以严格占位符解析生成本次 `resolved-task.yaml`；不再生成 resolved flow JSON。
- TypeScript 缩减为 Midscene 运行适配器：注册 `KeyboardTypeText`，创建 ComputerAgent，然后调用 `agent.runYaml()`；删除 route runner、resolved-flow 契约和任务型 aiAct prompt 组合器。
- 无录制自然语言操作通过 Python 生成临时 Midscene YAML，并复用同一个 YAML runner；录制任务不再存在另一套“拼接全部步骤后调用 aiAct”的执行链。
- 清理旧模型、JSON Schema、测试、命令和文档，只保留当前架构需要的代码；禁止 fallback、自动模式切换、隐藏错误和针对单一示例的规则。
- 将示例任务重新由 trace 生成 `task.yaml`，新任务输入全部来源于 trace 中的结构化 input operation。

## Capabilities

### New Capabilities

- `midscene-yaml-tasks`：定义 canonical Midscene YAML 任务、严格参数解析、统一 YAML runner 和运行报告契约。

### Modified Capabilities

- `trace-to-midscene-flow`：将 trace 转换目标从自定义 JSON flow 改为 Midscene YAML，并移除 route/evidence 执行副本。
- `python-task-core`：将 Python 的解析、检查和执行边界改为 resolved task YAML，不再维护 flow Pydantic 模型。
- `local-task-skills`：任务 Skill 以 `task.yaml` 为可编辑契约，并简化任务目录与调用方式。
- `ai-act-execution`：删除录制任务 prompt 二次组合器，仅保留由自然语言生成临时 YAML 的通用 aiAct 能力。
- `agent-task-calibration`：长期修改直接作用于 canonical `task.yaml`，确认后验证，不再引用 step route 或 JSON flow。

## Impact

- 影响 `execution/cua` 的模型、转换、任务解析、CLI 和报告协议。
- 影响 `execution/executors` 的全部 runner，仅保留环境、ComputerAgent 和键盘自定义动作相关实现。
- 删除 `midscene-flow.schema.json`、`resolved-flow.schema.json`、aiAct 专用结果契约及对应测试。
- 新增 Python YAML 依赖，并继续保留 Node.js、TypeScript 与 `@midscene/computer` 作为 Midscene computer use 的薄适配层。
- `execution/projects` 中现有任务资产会直接重建，不保证旧命令和旧文件可用。
