## Purpose

定义从 `record` 教学录制产物到 `execution` 中 Midscene computer use 执行流程的转换边界、项目产物组织方式、IR 要求和 runner 行为。
## Requirements
### Requirement: Converter 直接生成 Midscene YAML
TypeScript converter SHALL 只根据 ShowUI-Aloha trace 的结构化 operation 与录制时间生成任务根目录的 `task.yaml`。

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

