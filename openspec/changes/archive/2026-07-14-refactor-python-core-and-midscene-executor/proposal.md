## Why

当前 `execution` 的 TypeScript 代码同时承担 Midscene SDK 适配、trace 转换、任务包解析、参数合并、校准和 CLI，持久化 JSON 契约与进程内部 VO 也混合在同一组 interface 中。随着项目明确以 Python 为主体技术栈，并计划让 Agent 与未来前端复用任务能力，需要趁现有功能边界已经稳定时收缩 TypeScript 职责，建立可独立验证的 Python 核心与薄 Midscene 执行适配层。

## What Changes

- 在 `execution` 中建立 Python 应用核心，承载 trace 转换、任务发现、配置验证、参数解析、校准、resolved flow 构建和统一 CLI。
- 使用 Python dataclass 或普通类型表达仅在进程内部使用的领域对象和 VO；使用 Pydantic 表达需要落盘或跨进程传输的任务契约。
- 从 Pydantic 模型生成 JSON Schema，覆盖基础 IR、项目配置、已确认校准、校准建议和 resolved flow 等稳定文件边界，不为内部 VO 生成 Schema。
- 将 TypeScript 收缩为 Midscene 执行适配层，只消费经过 Python 校验和解析的 `resolved-flow.json`，注册 customActions、映射 route、执行 computer use 并输出执行结果。
- 保留当前项目目录和 JSON 业务语义，迁移 `air-tickets-demo` 作为兼容样例，并让 inspect 与 run 继续共享同一套确定性解析逻辑。
- 将面向人和 Agent 的主要命令统一为 Python CLI；Python 在运行命令中通过明确的子进程协议调用 Node.js Midscene 执行器。
- 借迁移整理现有模块、测试和依赖边界，删除被 Python 实现替代的 TypeScript 转换、任务和校准代码，不进行与本次职责拆分无关的功能扩展。
- **BREAKING**：现有以 `npm run flow:*`、`npm run project:*` 和 `npm run calibration:*` 暴露的业务 CLI 将由 Python CLI 取代；npm 仅保留 Midscene 执行器开发、校验和测试入口。

## Capabilities

### New Capabilities

- `python-task-core`: 定义 Python 任务核心、Pydantic 持久化模型、生成式 JSON Schema、统一 CLI 与 Python/Node 执行边界。

### Modified Capabilities

- `trace-to-midscene-flow`: 将 trace 转换、resolved flow 构建和 runner 消费边界调整为 Python 主体与 TypeScript Midscene 薄执行器，同时保持既有 IR 和执行行为。

## Impact

- 受影响代码：`execution/src/flow`、`execution/src/executors`、`execution/tests`、`execution/package.json`，以及新增的 Python 包、Python 测试和 Schema 生成目录。
- 受影响接口：开发者、Agent Skill 和文档中的项目查询、转换、校准、inspect、validate、run 命令。
- 新增依赖：Python 侧的 Pydantic、CLI 与测试依赖；Node.js 侧继续保留 `@midscene/computer` 及执行器所需依赖。
- 数据兼容：`execution/projects/<project-name>` 的基础 IR、配置、校准、建议和报告目录保持不变；迁移必须验证现有 `air-tickets-demo` 能在不人工改写资产的情况下解析和 dry-run。
- 外部系统：Midscene computer use、ShowUI-Aloha 录制处理和 Codex Skill 的职责不变；本次不开发前端、不引入新的模型调用，也不改变失败暴露原则。
