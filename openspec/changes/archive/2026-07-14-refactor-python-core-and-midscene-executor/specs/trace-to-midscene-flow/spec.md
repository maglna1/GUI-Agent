## MODIFIED Requirements

### Requirement: Converter 生成 Midscene flow IR
系统 SHALL 由 Python converter 将 ShowUI-Aloha trace 数据转换为结构化 `midscene-flow.json` 产物，并供后续任务解析与 Midscene 执行链路消费。

#### Scenario: Trace 转换成功
- **WHEN** converter 收到一个具名项目的有效 ShowUI-Aloha trace
- **THEN** 它 SHALL 写入 `execution/projects/<project-name>/ir/midscene-flow.json`
- **AND** flow SHALL 包含 `schemaVersion`、`project`、`source` 和 `steps`
- **AND** 每个 step SHALL 包含稳定 `id`、源 trace 引用、intent、timing、evidence 和 route strategy
- **AND** 输出 SHALL 通过 Python Pydantic 模型和生成的 JSON Schema 验证

#### Scenario: Trace operation 转换为 Midscene prompt
- **WHEN** trace step 包含结构化 `caption.operation`
- **THEN** converter SHALL 仅使用 `operation.type` 选择 Midscene 执行动作
- **AND** converter SHALL 将 `operation.prompt` 作为对应 Midscene 动作的 prompt 来源
- **AND** 当 `operation.type` 为 `input` 时，converter SHALL 将 `operation.locatePrompt` 作为目标输入框定位来源
- **AND** converter SHALL NOT 通过扫描 `caption.action`、`expectation` 或原始录制动作中的自然语言关键词生成 route
- **AND** 当 `caption.operation` 缺失、类型未知或必需字段缺失时，converter SHALL 标明 trace step 并直接失败
- **AND** 当 `operation.type` 为 `input` 时，`operation.locatePrompt` SHALL 是必需字段，converter SHALL NOT 从完整动作 prompt 自动派生该字段

#### Scenario: Trace 生成失败暴露
- **WHEN** 模型在一次纠错重试后仍未生成完整可执行 operation，或某个录制动作缺少可读取截图
- **THEN** trace 生成 SHALL 标明 step 或录制动作并直接失败
- **AND** trace 生成 SHALL NOT 写入 `unknown` operation、静默跳过该动作或把特定 release 文本改写为 click

### Requirement: 通用 runner 消费 Midscene flow IR
系统 SHALL 先由 Python 核心将基础 Midscene flow IR、已确认校准和本次参数解析为 resolved flow，再由 TypeScript Midscene 执行器消费 resolved flow 中的可执行 steps。

#### Scenario: Runner 执行受支持策略
- **WHEN** TypeScript 执行器读取到包含受支持 `keyboard`、`input`、`tap`、`act` 或 `wait` strategy 的 resolved flow
- **THEN** 它 SHALL 将这些 step 路由到对应 Midscene computer use 操作
- **AND** 它 SHALL 使用已配置 run directory 生成 Midscene 执行报告
- **AND** 它 SHALL NOT 自行读取基础 IR、校准文件或本次参数

#### Scenario: Runner 按 IR timing 执行前等待
- **WHEN** runner 执行包含 `timing.waitBeforeMs` 的 resolved flow step
- **THEN** runner SHALL 在执行该 step 的 route 前等待指定毫秒数
- **AND** runner SHALL NOT 在定位失败后默认调用 `aiWaitFor` 进行兜底重试
- **AND** `aiWaitFor` SHALL 只来自显式 `wait` strategy 或后续明确标记的页面跳转等待策略

#### Scenario: Runner 使用键盘事件执行文本输入
- **WHEN** runner 执行 `input` strategy
- **THEN** 它 SHALL 调用 Midscene 自定义 `KeyboardTypeText` action
- **AND** runner SHALL 将 input route 的 `locatePrompt` 传给 `KeyboardTypeText` 的 `locate` 字段
- **AND** `KeyboardTypeText` SHALL 通过 `locate` 字段复用 Midscene 定位管线来定位目标输入区域
- **AND** 它 SHALL 通过键盘事件输入文本
- **AND** 它 SHALL NOT 使用依赖剪贴板粘贴的 `aiInput` 作为 input route 的执行路径
- **AND** 当输入文本包含当前键盘映射不支持的字符时，它 SHALL 给出清晰错误并停止执行

#### Scenario: Runner 遇到不受支持策略
- **WHEN** runner 读取到不受支持或 `manual-review` strategy 的 resolved flow step
- **THEN** 它 SHALL 给出清晰错误，标识 step id 和原因
- **AND** 它 SHALL NOT 静默跳过或执行猜测出来的桌面动作

#### Scenario: 检查与执行共用解析结果
- **WHEN** 相同项目和输入分别用于 flow inspect 与 flow run
- **THEN** 两者 SHALL 使用相同解析和验证逻辑
- **AND** 基础 IR、任务配置和已确认校准 SHALL NOT 被运行过程修改
