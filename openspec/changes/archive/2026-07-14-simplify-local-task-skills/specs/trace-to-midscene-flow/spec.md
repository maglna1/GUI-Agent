## MODIFIED Requirements

### Requirement: 按工作流名称组织项目产物
系统 SHALL 将转换后的 CUA 工作流组织为 `execution/projects/<scene>/<task>/` 下的本地任务包，并在任务根目录提供 flow、任务清单、任务 Skill、source 和 reports。

#### Scenario: 为转换创建项目目录
- **WHEN** 场景 `browser-demo` 中的任务 `air-tickets-demo` 首次转换 record trace
- **THEN** 转换输出 SHALL 放在 `execution/projects/browser-demo/air-tickets-demo/` 中
- **AND** 任务目录 SHALL 包含 `source/`、`midscene-flow.json`、`task.json`、`SKILL.md` 和 `reports/` 路径或这些路径的文档化占位
- **AND** 场景目录 SHALL 包含 `scene.json` 和场景 `SKILL.md`

### Requirement: Converter 生成 Midscene flow IR
Python converter SHALL 将 ShowUI-Aloha trace 数据初始化为任务根目录的结构化 `midscene-flow.json`，并禁止静默覆盖已有任务 flow。

#### Scenario: Trace 转换成功
- **WHEN** converter 收到有效 scene、task、goal 和 ShowUI-Aloha trace，且目标 flow 尚不存在
- **THEN** 它 SHALL 写入 `execution/projects/<scene>/<task>/midscene-flow.json`
- **AND** flow SHALL 包含 `schemaVersion`、`scene`、`task`、`source` 和 `steps`
- **AND** 每个 step SHALL 包含稳定 `id`、源 trace 引用、intent、timing、evidence 和 route strategy
- **AND** 输出 SHALL 通过 Python Pydantic 模型和生成的 JSON Schema 验证

#### Scenario: 目标 flow 已存在
- **WHEN** converter 目标任务已经存在 `midscene-flow.json`
- **THEN** converter SHALL 清晰失败并保留现有文件
- **AND** converter SHALL NOT 自动覆盖、合并或创建兼容副本

#### Scenario: Trace operation 转换为 Midscene prompt
- **WHEN** trace step 包含结构化 `caption.operation`
- **THEN** converter SHALL 仅使用 `operation.type` 选择 Midscene 执行动作
- **AND** converter SHALL 将 `operation.prompt` 作为对应 Midscene 动作的 prompt 来源
- **AND** 当 `operation.type` 为 `input` 时，converter SHALL 将 `operation.locatePrompt` 作为目标输入框定位来源
- **AND** converter SHALL NOT 通过扫描 `caption.action`、`expectation` 或原始录制动作中的自然语言关键词生成 route
- **AND** 当 `caption.operation` 缺失、类型未知或必需字段缺失时，converter SHALL 标明 trace step 并直接失败

#### Scenario: Trace 生成失败暴露
- **WHEN** 模型在一次纠错重试后仍未生成完整可执行 operation，或某个录制动作缺少可读取截图
- **THEN** trace 生成 SHALL 标明 step 或录制动作并直接失败
- **AND** trace 生成 SHALL NOT 写入 unknown operation、静默跳过该动作或猜测替代动作

### Requirement: 通用 runner 消费 Midscene flow IR
系统 SHALL 先由 Python 核心从 canonical Midscene flow 和本次参数构建 resolved flow，再由 TypeScript Midscene 执行器消费其中的可执行 steps。

#### Scenario: Runner 执行受支持策略
- **WHEN** TypeScript 执行器读取到包含受支持 `keyboard`、`input`、`tap`、`act` 或 `wait` strategy 的 resolved flow
- **THEN** 它 SHALL 将这些 step 路由到对应 Midscene computer use 操作
- **AND** 它 SHALL 使用已配置 run directory 生成 Midscene 执行报告
- **AND** 它 SHALL NOT 自行读取 canonical flow、任务清单或本次参数

#### Scenario: Runner 按 IR timing 执行前等待
- **WHEN** runner 执行包含 `timing.waitBeforeMs` 的 resolved flow step
- **THEN** runner SHALL 在执行该 step 的 route 前等待指定毫秒数
- **AND** runner SHALL NOT 在定位失败后默认调用 `aiWaitFor` 进行兜底重试
- **AND** `aiWaitFor` SHALL 只来自显式 `wait` strategy 或后续明确标记的页面跳转等待策略

#### Scenario: Runner 使用键盘事件执行文本输入
- **WHEN** runner 执行 `input` strategy
- **THEN** 它 SHALL 调用 Midscene 自定义 `KeyboardTypeText` action
- **AND** runner SHALL 将 input route 的 `locatePrompt` 传给 `KeyboardTypeText` 的 `locate` 字段
- **AND** `KeyboardTypeText` SHALL 通过 Midscene 定位管线定位目标输入区域并通过键盘事件输入文本
- **AND** 它 SHALL NOT 使用依赖剪贴板粘贴的 `aiInput`
- **AND** 当输入文本包含当前键盘映射不支持的字符时，它 SHALL 给出清晰错误并停止执行

#### Scenario: Runner 遇到不受支持策略
- **WHEN** runner 读取到不受支持或 `manual-review` strategy 的 resolved flow step
- **THEN** 它 SHALL 给出清晰错误，标识 step id 和原因
- **AND** 它 SHALL NOT 静默跳过或执行猜测出来的桌面动作

#### Scenario: 检查与执行共用解析结果
- **WHEN** 相同场景、任务和输入分别用于 flow inspect 与 flow run
- **THEN** 两者 SHALL 使用相同解析和验证逻辑
- **AND** canonical flow 和任务清单 SHALL NOT 被运行过程修改

## REMOVED Requirements

### Requirement: 生成脚本是派生产物
**Reason**: 当前执行器直接消费 flow，不再维护未使用的 `generated/` 脚本目录和版本关系。

**Migration**: 删除现有 `generated/` 占位目录；如未来需要代码生成，以新的独立变更重新定义产物契约。
