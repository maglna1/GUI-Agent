## ADDED Requirements

### Requirement: Midscene YAML 是唯一长期执行事实源
每个录制任务 SHALL 使用任务根目录的 `task.yaml` 表达完整执行流程，人、Agent、未来前端和 Midscene SHALL 共同消费该文件。

#### Scenario: 修改任务动作
- **WHEN** 用户确认需要长期修改某个任务动作
- **THEN** 系统 SHALL 直接修改 `task.yaml` 并重新验证
- **AND** 系统 SHALL NOT 生成另一份长期 flow、route 或 override 契约

### Requirement: 录制任务保留稳定步骤身份
录制任务的每个 `tasks[]` 项 SHALL 使用 `step-NNN | <operation-type>` 名称，并按步骤编号严格递增；整体业务目标 SHALL 写入 `agent.groupDescription` 而非步骤名称。

#### Scenario: 人工修改破坏步骤身份
- **WHEN** task 名称不符合约定、步骤重复、顺序倒置或启用 `continueOnError`
- **THEN** resolver SHALL 在启动 Midscene 前失败

#### Scenario: Midscene 报告执行失败
- **WHEN** 某个录制步骤执行失败
- **THEN** 报告 SHALL 使用稳定 task 名称定位到对应 trace step
- **AND** 后续步骤 SHALL NOT 被继续执行

### Requirement: 输入通过严格占位符解析
系统 SHALL 使用 `task.json` 中的录制默认值和本次稀疏输入解析 `task.yaml` 的命名占位符，并生成本次 resolved task YAML。

#### Scenario: 只覆盖一个输入
- **WHEN** 调用者只提供一个已声明输入
- **THEN** 该输入的所有显式占位符 SHALL 使用本次值
- **AND** 其他输入 SHALL 使用录制默认值
- **AND** canonical `task.yaml` 与 `task.json` SHALL 保持不变

#### Scenario: 输入契约非法
- **WHEN** 存在未知输入、重复输入、非字符串值或未解析占位符
- **THEN** 系统 SHALL 在启动 Midscene 前失败

### Requirement: 单一 TypeScript runner 执行 YAML
TypeScript 执行适配器 SHALL 注册 `KeyboardTypeText`、创建 ComputerAgent 并调用 `agent.runYaml()`，且不得解释业务 step 或 route。

#### Scenario: 执行录制任务
- **WHEN** Python 提供参数已解析的任务 YAML
- **THEN** runner SHALL 将完整 YAML 内容交给 `agent.runYaml()`
- **AND** runner SHALL 在结束时销毁 Agent

#### Scenario: dry-run
- **WHEN** 使用 `--dry-run`
- **THEN** runner SHALL 解析和验证 YAML
- **AND** runner SHALL NOT 创建 ComputerDevice、ComputerAgent 或调用模型

### Requirement: 运行缺陷不得被兜底隐藏
系统 SHALL 原样暴露 YAML 解析、输入解析、Midscene 动作和模型执行错误，不得自动切换模式、修改任务、跳过动作或调用替代输入方式。

#### Scenario: KeyboardTypeText 遇到不支持字符
- **WHEN** 输入包含 `KeyboardTypeText` 不支持的字符
- **THEN** 执行 SHALL 失败并保留原始错误
- **AND** 系统 SHALL NOT 回退到剪贴板 Input

### Requirement: 自然语言任务复用 YAML runner
无录制自然语言操作 SHALL 被包装为包含单个 Midscene `ai` action 的临时 YAML，并通过统一 runner 执行。

#### Scenario: 运行自然语言操作
- **WHEN** 用户调用 `cua act run --prompt <要求>`
- **THEN** Python SHALL 生成临时 YAML 和报告目录
- **AND** 系统 SHALL 使用与录制任务相同的 TS runner
