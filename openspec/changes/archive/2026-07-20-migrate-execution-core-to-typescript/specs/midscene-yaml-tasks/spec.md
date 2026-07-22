## MODIFIED Requirements

### Requirement: 单一 TypeScript runner 执行 YAML
TypeScript 执行适配器 SHALL 暴露可直接导入的 YAML 执行 API，注册 `KeyboardTypeText`、创建 ComputerAgent 并调用 `agent.runYaml()`，且不得解释业务 step 或 route。

#### Scenario: 执行录制任务
- **WHEN** TypeScript 核心提供参数已解析的任务 YAML 和本次 run directory
- **THEN** 执行 API SHALL 将完整 YAML 内容交给 `agent.runYaml()`
- **AND** 执行 API SHALL 在结束时销毁 Agent 并返回结构化结果

#### Scenario: dry-run
- **WHEN** 使用 `--dry-run`
- **THEN** 执行 API SHALL 解析和验证 YAML
- **AND** 执行 API SHALL NOT 创建 ComputerDevice、ComputerAgent 或调用模型

### Requirement: 自然语言任务复用 YAML runner
无录制自然语言操作 SHALL 被 TypeScript 核心包装为包含单个 Midscene `ai` action 的临时 YAML，并通过统一 runner API 执行。

#### Scenario: 运行自然语言操作
- **WHEN** 用户调用 `cua act run --prompt <要求>` 或对应工具 API
- **THEN** TypeScript 核心 SHALL 生成临时 YAML 和报告目录
- **AND** 系统 SHALL 使用与录制任务相同的 TypeScript runner API
