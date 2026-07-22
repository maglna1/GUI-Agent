## MODIFIED Requirements

### Requirement: Python 核心承载任务业务能力
系统 SHALL 使用 Python 作为 execution 任务业务能力的唯一实现语言，承担 trace 初始化、场景和任务发现、配置验证、参数覆盖、resolved flow 构建和面向人及 Agent 的 CLI。

#### Scenario: inspect 不启动 Node 执行器
- **WHEN** 用户通过 Python CLI inspect 一个有效任务
- **THEN** Python 核心 SHALL 独立读取并解析任务资产、应用本次参数
- **AND** 系统 SHALL 输出 resolved flow
- **AND** 系统 SHALL NOT 启动 Node.js 或 Midscene agent

#### Scenario: 业务错误由 Python 核心暴露
- **WHEN** 任务包含未知参数、失效 step 引用或不合法 route
- **THEN** Python 核心 SHALL 在调用 Midscene 执行器之前失败
- **AND** 错误 SHALL 包含对应场景、任务、step 或字段上下文

### Requirement: 内部类型与持久化契约分离
系统 SHALL 使用 Python 内部类型表达不跨进程且不落盘的领域对象，并使用 Pydantic 模型表达需要落盘或跨进程传递的稳定 JSON 契约。

#### Scenario: 内部 VO 不生成 JSON Schema
- **WHEN** 路径对象、CLI 解析结果、合并上下文或验证结果只在 Python 进程内部使用
- **THEN** 它们 SHALL 使用 dataclass、枚举、Protocol、TypedDict 或普通 Python 类型表达
- **AND** Schema 生成流程 SHALL NOT 为这些内部对象发布 JSON Schema

#### Scenario: 落盘文件在读取时验证
- **WHEN** Python 核心读取 Midscene flow、场景清单、任务清单或 resolved flow
- **THEN** 系统 SHALL 使用对应 Pydantic 模型执行运行时验证
- **AND** 系统 SHALL NOT 将未经验证的字典传入解析或执行流程

### Requirement: 持久化契约生成可复现 Schema
系统 SHALL 从 Pydantic 边界模型确定性生成纳入版本管理的 JSON Schema，并将 Pydantic 模型作为这些契约的事实来源。

#### Scenario: 生成全部公开文件契约
- **WHEN** 开发者运行 Schema 生成命令
- **THEN** 系统 SHALL 为 Midscene flow、场景清单、任务清单和 resolved flow 生成 JSON Schema
- **AND** 生成文件 SHALL 标识其不可手工维护
- **AND** 系统 SHALL NOT 生成 flow overrides 或 calibration proposal Schema

#### Scenario: 检测 Schema 漂移
- **WHEN** Pydantic 模型变化但版本库中的 JSON Schema 尚未更新
- **THEN** Schema 验证测试 SHALL 失败
- **AND** 失败信息 SHALL 指出需要重新生成的契约

#### Scenario: 现有任务资产符合契约
- **WHEN** 系统验证 `browser-demo/air-tickets-demo` 的场景、任务和 flow 资产
- **THEN** 这些资产 SHALL 通过对应 Pydantic 模型和 JSON Schema 验证

### Requirement: resolved flow 是唯一执行进程边界
Python 核心 SHALL 在执行前从 canonical flow 和本次输入生成 resolved flow 快照，TypeScript Midscene 执行器 SHALL 只消费该快照。

#### Scenario: Python 调用 Midscene 执行器
- **WHEN** 用户运行一个通过验证的任务
- **THEN** Python 核心 SHALL 应用本次明确提供的输入并构建 resolved flow
- **AND** Python 核心 SHALL 写入本次运行的 `resolved-flow.json`
- **AND** Python 核心 SHALL 将该文件路径传递给 Node.js Midscene 执行器

#### Scenario: TypeScript 不重新解析任务包
- **WHEN** TypeScript 执行器收到 resolved flow
- **THEN** 它 SHALL 验证执行契约并执行其中的 steps
- **AND** 它 SHALL NOT 读取 `task.json`、canonical flow 或 source 证据
- **AND** 它 SHALL NOT 重新应用参数覆盖

#### Scenario: 子进程执行失败
- **WHEN** Node.js 执行器返回非零退出码、非法结果或 step 执行错误
- **THEN** Python CLI SHALL 以失败状态结束并保留原始诊断信息
- **AND** 它 SHALL NOT 调用旧 TypeScript resolver 或其他执行兜底

### Requirement: Python CLI 是统一业务入口
系统 SHALL 通过 Python `cua` CLI 暴露场景查询、任务查询、trace 初始化、验证、检查和运行能力，并只保留与 Midscene 执行器开发直接相关的 npm 命令。

#### Scenario: Agent 查询和调用任务
- **WHEN** Agent 需要列出、描述、inspect 或运行任务
- **THEN** Skill SHALL 指导 Agent 使用 Python CLI 并显式提供 scene 和 task
- **AND** CLI SHALL 保持稀疏参数覆盖和机器可读输出语义

#### Scenario: 旧业务 npm 命令被移除
- **WHEN** 新场景任务 CLI 完成迁移和验证
- **THEN** 旧业务 npm scripts、`project list` 和全部 `calibration` 命令 SHALL 被移除
- **AND** 文档 SHALL 给出对应场景与任务命令
