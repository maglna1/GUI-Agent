## ADDED Requirements

### Requirement: Agent 修改 canonical YAML 前必须确认
Agent 发现录制任务意图或动作错误时 SHALL 生成 `task.yaml` 修改建议，展示原值、新值和中文原因，并等待用户明确确认后再写入。

#### Scenario: 用户确认长期修改
- **WHEN** 用户确认 Agent 展示的 YAML 差异
- **THEN** Agent SHALL 修改 `task.yaml` 并运行 `task validate`

#### Scenario: 用户尚未确认
- **WHEN** Agent 仅收到问题描述但未得到明确确认
- **THEN** Agent SHALL NOT 修改 canonical YAML 或实际操作电脑

### Requirement: 单次输入不得改写任务
Agent SHALL 将用户明确指定的本次变化作为 `--input` 传入，并保留未指定输入的录制默认值。

#### Scenario: 永久修改与本次输入不明确
- **WHEN** Agent 无法判断用户要求只对本次生效还是以后都生效
- **THEN** Agent SHALL 追问而不得自行选择

## REMOVED Requirements

### Requirement: 项目作为可调用任务包
**Reason**: 由 YAML 任务和精简 Skill 规格覆盖。
**Migration**: 使用 task CLI 发现和调用任务。

### Requirement: 调用输入采用稀疏覆盖
**Reason**: 由新的命名占位符输入要求替代。
**Migration**: 使用 `task.json` 默认值与 `--input`。

### Requirement: Agent 校准需要确认
**Reason**: 旧要求引用 JSON step route，现由 canonical YAML 修改确认要求替代。
**Migration**: 对 `task.yaml` 展示差异并确认。

### Requirement: Agent Skill 约束任务交互
**Reason**: 交互规则已收敛到 YAML 修改和单次输入两类。
**Migration**: 更新 execution 与任务 Skill。

### Requirement: 任务解析不调用模型
**Reason**: 由严格确定性 YAML resolver 规格覆盖。
**Migration**: 参数解析继续完全确定性执行。
