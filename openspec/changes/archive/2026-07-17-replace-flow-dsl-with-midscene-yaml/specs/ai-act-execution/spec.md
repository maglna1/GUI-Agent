## ADDED Requirements

### Requirement: aiAct 只处理无录制自然语言任务
系统 SHALL 仅在没有录制任务资产时通过 `act run --prompt` 创建包含一个 `ai` action 的临时 Midscene YAML。

#### Scenario: 自然语言 dry-run
- **WHEN** 用户提供非空 prompt 并使用 dry-run
- **THEN** 系统 SHALL 输出包含该 prompt 的临时 YAML
- **AND** 系统 SHALL NOT 初始化设备或调用模型

#### Scenario: 自然语言执行失败
- **WHEN** Midscene ai action 执行失败
- **THEN** 系统 SHALL 保留原始错误和报告
- **AND** 系统 SHALL NOT 查找录制任务或切换到逐步模式

## REMOVED Requirements

### Requirement: aiAct 支持互斥的自然语言与录制任务来源
**Reason**: 录制任务不再经过 prompt 二次组合。
**Migration**: 录制任务使用 `task run`，无录制任务使用 `act run --prompt`。

### Requirement: 录制任务 prompt 仅包含有序执行指令
**Reason**: 该 prompt 组合器已删除。
**Migration**: 直接编辑并运行 Midscene YAML；可在 YAML 中显式使用 `ai` action。

### Requirement: aiAct 输入动作遵守无剪贴板约束
**Reason**: 无剪贴板输入改由 YAML 中显式 `KeyboardTypeText` 保证，不再依赖 aiActContext 选择动作。
**Migration**: 录制 input operation 生成 `KeyboardTypeText`。

### Requirement: aiAct dry-run 与报告可诊断
**Reason**: 所有模式改用统一 YAML runner 报告。
**Migration**: 使用统一 execution result 与 resolved task YAML。
