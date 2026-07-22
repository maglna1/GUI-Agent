## MODIFIED Requirements

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
