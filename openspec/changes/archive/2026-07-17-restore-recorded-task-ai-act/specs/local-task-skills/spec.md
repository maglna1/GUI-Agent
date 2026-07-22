## ADDED Requirements

### Requirement: Agent 显式选择电脑操作执行模式
执行器 Skill SHALL 向上层 Agent 说明录制 YAML 逐 task 执行、录制任务整体 aiAct 和无录制自然语言 aiAct 三种调用方式，并禁止隐式切换。

#### Scenario: 页面稳定的已录制任务
- **WHEN** 用户调用已有录制任务且页面状态与流程稳定
- **THEN** Skill SHALL 推荐使用 `cua task run --scene <scene> --task <task>` 以降低规划成本

#### Scenario: 需要统一规划的已录制任务
- **WHEN** 用户调用已有录制任务并明确希望由 aiAct 统一规划完整步骤
- **THEN** Skill SHALL 使用 `cua act run --scene <scene> --task <task>` 并传入用户明确提供的本次输入

#### Scenario: 无录制自然语言任务
- **WHEN** 用户要求操作电脑但没有可用任务资产
- **THEN** Skill SHALL 使用 `cua act run --prompt <要求>`

#### Scenario: 执行失败
- **WHEN** 任一执行模式失败
- **THEN** Skill SHALL 报告原始错误并等待用户决定
- **AND** Skill SHALL NOT 自动切换模式、自动修改 YAML 或自动重试
