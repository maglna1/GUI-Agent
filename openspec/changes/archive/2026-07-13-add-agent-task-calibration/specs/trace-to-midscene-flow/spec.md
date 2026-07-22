## MODIFIED Requirements

### Requirement: 按工作流名称组织项目产物
系统 SHALL 将转换后的 CUA 工作流组织为 `execution/projects/<project-name>/` 下的可调用任务包，并为 source、基础 IR、任务配置、校准、生成资产和执行报告提供独立区域。

#### Scenario: 为转换创建项目目录
- **WHEN** 项目 `air-tickets-demo` 的 ShowUI-Aloha trace 被转换
- **THEN** 转换输出 SHALL 放在 `execution/projects/air-tickets-demo/` 下
- **AND** 项目目录 SHALL 包含或文档化 `source/`、`ir/`、`config/`、`calibration/`、`generated/` 和 `reports/`

### Requirement: Converter 生成 Midscene flow IR
系统 SHALL 将 ShowUI-Aloha trace 数据转换为结构化基础 `midscene-flow.json`，初始化不存在的任务配置，并保留已经存在的人工任务配置和校准。

#### Scenario: Trace 转换成功
- **WHEN** converter 收到一个具名项目的有效 ShowUI-Aloha trace
- **THEN** 它 SHALL 写入 `execution/projects/<project-name>/ir/midscene-flow.json`
- **AND** flow SHALL 包含 `schemaVersion`、`project`、`source` 和 `steps`
- **AND** 每个 step SHALL 包含稳定 `id`、源 trace 引用、intent、timing、evidence、route strategy 和 fallback 信息
- **AND** converter SHALL 仅在任务配置不存在时按 input route 初始化输入定义

#### Scenario: Trace operation 转换为 Midscene prompt
- **WHEN** trace step 包含结构化 `caption.operation`
- **THEN** converter SHALL 优先使用 `operation.type` 选择 Midscene 执行动作
- **AND** converter SHALL 将 `operation.prompt` 作为对应 Midscene 动作的 prompt 来源
- **AND** 当 `operation.type` 为 `input` 时，converter SHALL 将 `operation.locatePrompt` 作为目标输入框定位来源
- **AND** converter SHALL NOT 通过扫描 `caption.action` 中的自然语言关键词作为主路径生成 route

### Requirement: 通用 runner 消费 Midscene flow IR
系统 SHALL 提供通用 Midscene runner，通过共享 resolver 消费基础 IR、已确认校准和本次输入合并后的 resolved flow。

#### Scenario: Runner 执行受支持策略
- **WHEN** runner 读取到包含受支持 `keyboard`、`input`、`tap`、`act` 或 `wait` strategy 的 resolved flow
- **THEN** 它 SHALL 将这些 step 路由到对应 Midscene computer use 操作
- **AND** 它 SHALL 使用已配置 run directory 生成 Midscene 执行报告
- **AND** 它 SHALL 在初始化 Midscene 前保存本次 resolved flow 快照

#### Scenario: Runner 按 IR timing 执行前等待
- **WHEN** runner 执行包含 `timing.waitBeforeMs` 的 flow step
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
- **WHEN** runner 读取到不受支持或 `manual-review` strategy 的 flow step
- **THEN** 它 SHALL 给出清晰错误，标识 step id 和原因
- **AND** 它 SHALL NOT 静默跳过或执行猜测出来的桌面动作

#### Scenario: 检查与执行共用解析结果
- **WHEN** 相同项目和输入分别用于 flow inspect 与 flow run
- **THEN** 两者 SHALL 使用相同解析和验证逻辑
- **AND** 基础 IR、任务配置和已确认校准 SHALL NOT 被运行过程修改
