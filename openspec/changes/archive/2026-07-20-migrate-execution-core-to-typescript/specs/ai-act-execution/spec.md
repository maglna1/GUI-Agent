## MODIFIED Requirements

### Requirement: aiAct 支持互斥的自然语言与录制任务来源
TypeScript 核心 SHALL 通过统一 Midscene YAML 执行 API 接受自然语言 prompt 或参数已解析的录制任务 YAML 其中一种来源，并调用一次整体 aiAct。

#### Scenario: 无录制自然语言执行
- **WHEN** 调用方提供非空 `--prompt` 且不提供任务来源
- **THEN** 系统 SHALL 将该文本包装为单 `ai` action 的临时 YAML
- **AND** 系统 SHALL NOT 读取任务资产或启动逐 task 执行

#### Scenario: 有录制任务执行
- **WHEN** 调用方提供完整 scene/task 和可选稀疏输入
- **THEN** 系统 SHALL 解析 canonical `task.yaml` 的本次参数并按 task 原顺序组合最终 prompt
- **AND** 系统 SHALL 将最终 prompt 包装为单 `ai` action 的临时 YAML并通过统一执行 API 执行

#### Scenario: 输入来源不唯一
- **WHEN** 调用方混用 `--prompt` 与任务参数、均未提供来源或只提供 scene/task 之一
- **THEN** 系统 SHALL 在解析任务或初始化 ComputerAgent 前失败
