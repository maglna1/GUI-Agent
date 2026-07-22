## ADDED Requirements

### Requirement: Converter 直接生成 Midscene YAML
Python converter SHALL 只根据 ShowUI-Aloha trace 的结构化 operation 与录制时间生成任务根目录的 `task.yaml`。

#### Scenario: 转换受支持的 trace
- **WHEN** trace 包含 click、input、keyboard 或 wait operation
- **THEN** converter SHALL 分别生成 `aiTap`、`KeyboardTypeText`、`KeyboardPress` 或 `aiWaitFor` action
- **AND** 录制间隔 SHALL 以裁剪后的 `sleep` action 表达

#### Scenario: trace 信息不足
- **WHEN** operation 缺失、类型未知或必填字段为空
- **THEN** converter SHALL 失败且不写出半成品 `task.yaml`
- **AND** converter SHALL NOT 从其他自然语言字段猜测动作

### Requirement: 新输入完全来源于 trace input operation
converter SHALL 为每个结构化 input operation 生成稳定输入 ID、中文说明、录制默认值和 YAML 占位符。

#### Scenario: 初始化多个输入
- **WHEN** trace 依次包含三个 input operation
- **THEN** `task.json` SHALL 声明三个由对应 trace step ID 派生的输入
- **AND** `task.yaml` SHALL 在对应 `KeyboardTypeText.value` 中引用这些输入

### Requirement: 每个 trace step 保留为独立 Midscene task
converter SHALL 将每个 trace step 按原顺序生成一个 Midscene `tasks[]` 项，并使用 `step-NNN | <operation-type>` 作为稳定名称。

#### Scenario: 步骤包含录制等待
- **WHEN** 某一步与前一步存在需要保留的录制间隔
- **THEN** converter SHALL 将裁剪后的 `sleep` 放在该步骤 task 的 flow 首位
- **AND** 本步骤的交互动作 SHALL 紧随其后

#### Scenario: trace step 标识非法
- **WHEN** step ID 非正整数、重复或未按轨迹顺序严格递增
- **THEN** converter SHALL 失败且不写出任务资产

## REMOVED Requirements

### Requirement: 按工作流名称组织项目产物
**Reason**: 项目产物已改为 Midscene YAML 任务，不再包含自定义 flow IR。
**Migration**: 使用新 capability 定义的 `projects/<scene>/<task>/task.yaml` 结构。

### Requirement: ShowUI-Aloha 保持为录制处理器
**Reason**: 该职责不变但已由根目录架构约束覆盖，不再在 flow capability 中重复维护。
**Migration**: record 继续只负责录制与 trace 生成。

### Requirement: Converter 生成 Midscene flow IR
**Reason**: 自定义 flow IR 被 Midscene YAML 替代。
**Migration**: 重新从 trace 生成 `task.yaml`，不迁移旧 JSON。

### Requirement: Flow step 保留源证据
**Reason**: 执行 YAML 不复制 evidence，原始证据只保留在任务 `source/`。
**Migration**: 查阅 `source/showui-trace.json` 与截图。

### Requirement: Flow step 被路由到执行策略
**Reason**: route 层已删除，trace operation 直接映射 Midscene action。
**Migration**: 修改 trace operation 或 canonical `task.yaml`。

### Requirement: 通用 runner 消费 Midscene flow IR
**Reason**: runner 改为直接调用 `agent.runYaml()`。
**Migration**: 使用 `cua task run` 执行 `task.yaml`。
