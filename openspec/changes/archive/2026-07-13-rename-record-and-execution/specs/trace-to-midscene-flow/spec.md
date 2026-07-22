## MODIFIED Requirements

### Requirement: 按工作流名称组织项目产物
系统 SHALL 将转换后的 CUA 工作流资产组织在 `execution/projects/<project-name>/` 下，并为 source 输入、Midscene IR、任务配置、校准、生成执行资产和执行报告提供独立区域。

#### Scenario: 为转换创建项目目录
- **WHEN** 项目 `air-tickets-demo` 的 record trace 被转换
- **THEN** 转换输出 SHALL 放在 `execution/projects/air-tickets-demo/` 下
- **AND** 项目目录 SHALL 包含 `source/`、`ir/`、`config/`、`calibration/`、`generated/`、`reports/` 路径或这些路径的文档化占位

### Requirement: ShowUI-Aloha 保持为录制处理器
系统 SHALL 将 `record/` 视为录制派生日志、截图和 trace 产物的上游生产方，而不是 Midscene 执行或回放组件。

#### Scenario: Converter 消费录制处理输出
- **WHEN** execution converter 处理一次教学录制
- **THEN** 它 SHALL 将 `record/` 中的 ShowUI-Aloha Learn 输出作为 source artifact 读取
- **AND** 它 SHALL 在 `execution/` 下写入执行侧产物
- **AND** 它 SHALL NOT 依赖 `Aloha_Act`、ShowUI-Aloha Actor、ShowUI-Aloha Executor 或 ShowUI-Aloha replay 代码

#### Scenario: Trace prompt 约束 Midscene 定位描述
- **WHEN** ShowUI-Aloha Learn 生成 trace
- **THEN** trace 生成 prompt SHALL 要求 `operation.prompt` 包含目标视觉特征、所在区域、相对锚点和动作意图中的至少 3 类信息
- **AND** 对 `input` 操作，`operation.locatePrompt` SHALL 只描述目标输入框本身，但也应包含足量视觉定位信息
- **AND** 系统 SHALL NOT 为该定位增强新增额外 operation schema 字段

### Requirement: Converter 生成 Midscene flow IR
系统 SHALL 将 record trace 数据转换为结构化 `midscene-flow.json` 产物，并供 execution 中的 Midscene 工具消费。

#### Scenario: Trace 转换成功
- **WHEN** converter 收到一个具名项目的有效 trace
- **THEN** 它 SHALL 写入 `execution/projects/<project-name>/ir/midscene-flow.json`
- **AND** flow SHALL 包含 `schemaVersion`、`project`、`source` 和 `steps`
- **AND** 每个 step SHALL 包含稳定 `id`、源 trace 引用、intent、timing、evidence、route strategy 和 fallback 信息

#### Scenario: Trace operation 转换为 Midscene prompt
- **WHEN** trace step 包含结构化 `caption.operation`
- **THEN** converter SHALL 优先使用 `operation.type` 选择 Midscene 执行动作
- **AND** converter SHALL 将 `operation.prompt` 作为对应 Midscene 动作的 prompt 来源
- **AND** 当 `operation.type` 为 `input` 时，converter SHALL 将 `operation.locatePrompt` 作为目标输入框定位来源
- **AND** converter SHALL NOT 通过扫描 `caption.action` 中的自然语言关键词作为主路径生成 route

### Requirement: 生成脚本是派生产物
系统 SHALL 将未来生成的 Midscene 脚本视为从 `midscene-flow.json` 派生出的产物，而不是源事实。

#### Scenario: 后续生成脚本
- **WHEN** 为某个项目创建生成的 `run.ts`
- **THEN** 它 SHALL 放在 `execution/projects/<project-name>/generated/` 下
- **AND** 它 SHALL 引用生成时使用的 flow 或 metadata 版本
- **AND** 工作流变更 SHALL 先更新 source trace 输入或 `midscene-flow.json`，再重新生成脚本
