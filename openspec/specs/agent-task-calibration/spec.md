## Purpose

定义可供 Agent 和人工发现、校准、参数化调用与执行的 CUA 任务包契约，以及校准确认和确定性解析要求。
## Requirements
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
