## ADDED Requirements

### Requirement: Python 核心解析和编排 YAML 任务
Python 核心 SHALL 承载任务发现、trace 转换、输入解析、resolved task YAML 生成、子进程调用和结果校验。

#### Scenario: 执行本地任务
- **WHEN** 用户通过 CLI 运行已录制任务
- **THEN** Python SHALL 读取任务清单和 canonical YAML、解析输入并写入本次运行快照
- **AND** Python SHALL 调用单一 TypeScript YAML runner

### Requirement: Python 不重建 Midscene 动作类型系统
Python SHALL 使用结构化 YAML API 读写任务，但不得为所有 Midscene action 建立平行 Pydantic flow 模型。

#### Scenario: 任务包含 Midscene 原生 action
- **WHEN** `task.yaml` 包含本项目未专门建模但 Midscene 支持的 action
- **THEN** Python SHALL 保留其 YAML 结构
- **AND** 最终动作语法 SHALL 由 Midscene parser 验证

### Requirement: CLI 以 task 命令管理录制任务
Python CLI SHALL 提供 `task init-from-trace`、`task validate`、`task inspect` 和 `task run`，并仅为无录制任务保留 `act run --prompt`。

#### Scenario: 检查任务而不操作电脑
- **WHEN** 用户调用 `task inspect` 或 `task run --dry-run`
- **THEN** 系统 SHALL 输出或保存参数已解析的 YAML
- **AND** 系统 SHALL NOT 初始化设备或调用模型

## REMOVED Requirements

### Requirement: Python 核心承载任务业务能力
**Reason**: 由新的 YAML 任务职责要求完整替代。
**Migration**: 使用新的 task CLI 与 YAML resolver。

### Requirement: 内部类型与持久化契约分离
**Reason**: 不再存在自定义 flow VO 和 resolved flow 持久化模型。
**Migration**: Python 内部仅保留任务清单、执行结果和通用 YAML 数据。

### Requirement: 持久化契约生成可复现 Schema
**Reason**: flow 与 aiAct 专用 JSON Schema 被删除，仅任务清单等稳定 JSON 契约继续生成 Schema。
**Migration**: 使用 task/scene/执行结果 Schema 与 Midscene YAML parser。

### Requirement: resolved flow 是唯一执行进程边界
**Reason**: 执行边界改为 `resolved-task.yaml`。
**Migration**: TS runner 使用 `--yaml` 接收本次快照。

### Requirement: Python CLI 是统一业务入口
**Reason**: 由新的 task CLI 要求替代并移除 flow 命令域。
**Migration**: 将 `flow validate/inspect/run` 改为 `task validate/inspect/run`。

### Requirement: Python CLI 提供 aiAct 统一入口
**Reason**: 录制任务型 aiAct 被删除，`act run` 只接受自然语言 prompt。
**Migration**: 录制任务使用 `task run`；需要 aiAct 时直接在 YAML 中写 `ai` action。

### Requirement: aiAct 执行结果使用持久化契约
**Reason**: 所有模式统一使用 YAML runner 执行结果，不再维护 aiAct 专用结果。
**Migration**: 读取统一 execution result。
