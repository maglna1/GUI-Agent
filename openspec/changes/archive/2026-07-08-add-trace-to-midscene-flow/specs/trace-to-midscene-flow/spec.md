## ADDED Requirements

### Requirement: 按工作流名称组织项目产物
系统 SHALL 将转换后的 CUA 工作流资产组织在 `CUA_midscene/projects/<project-name>/` 下，并为 source 输入、Midscene IR、生成执行资产和执行报告提供独立区域。

#### Scenario: 为转换创建项目目录
- **WHEN** 项目 `air-tickets-demo` 的 ShowUI-Aloha trace 被转换
- **THEN** 转换输出 SHALL 放在 `CUA_midscene/projects/air-tickets-demo/` 下
- **AND** 项目目录 SHALL 包含 `source/`、`ir/`、`generated/`、`reports/` 路径或这些路径的文档化占位

### Requirement: ShowUI-Aloha 保持为录制处理器
系统 SHALL 将 `showui-aloha` 视为录制派生日志、截图和 trace 产物的上游生产方，而不是 Midscene 执行或回放组件。

#### Scenario: Converter 消费 ShowUI-Aloha 输出
- **WHEN** Midscene converter 处理一次教学录制
- **THEN** 它 SHALL 将 ShowUI-Aloha Learn 输出作为 source artifact 读取
- **AND** 它 SHALL 在 `CUA_midscene` 下写入 Midscene 专属产物
- **AND** 它 SHALL NOT 依赖 `Aloha_Act`、ShowUI-Aloha Actor、ShowUI-Aloha Executor 或 ShowUI-Aloha replay 代码

### Requirement: Converter 生成 Midscene flow IR
系统 SHALL 将 ShowUI-Aloha trace 数据转换为结构化 `midscene-flow.json` 产物，并供 Midscene 工具消费。

#### Scenario: Trace 转换成功
- **WHEN** converter 收到一个具名项目的有效 ShowUI-Aloha trace
- **THEN** 它 SHALL 写入 `CUA_midscene/projects/<project-name>/ir/midscene-flow.json`
- **AND** flow SHALL 包含 `schemaVersion`、`project`、`source` 和 `steps`
- **AND** 每个 step SHALL 包含稳定 `id`、源 trace 引用、intent、evidence、route strategy 和 fallback 信息

### Requirement: Flow step 保留源证据
系统 SHALL 在每个 Midscene flow step 中保留足够的源上下文，用于解释该 step 为什么存在以及如何被推导出来。

#### Scenario: 转换后的 step 引用源 trace 上下文
- **WHEN** 一个 trace step 被转换为 Midscene flow step
- **THEN** flow step SHALL 包含原始 trace step index 或 identifier
- **AND** 它 SHALL 包含用于推导该 step 的 trace observation、action 或 expectation
- **AND** 当相关 screenshot 或 crop 路径可用时，它 SHALL 引用这些路径

### Requirement: Flow step 被路由到执行策略
系统 SHALL 在执行前将每个转换后的 step 分类为明确的 Midscene 执行策略。

#### Scenario: 确定性文本输入被路由
- **WHEN** trace step 明确表示向已知字段输入文本
- **THEN** 转换后的 step SHALL 使用 `input` strategy，并携带字段意图和文本值

#### Scenario: 语义点击被路由
- **WHEN** trace step 明确表示点击一个可见 UI 目标
- **THEN** 转换后的 step SHALL 使用 `tap` 或 `act` strategy，并携带自然语言目标指令

#### Scenario: 模糊步骤被标记为需审查
- **WHEN** converter 无法有把握地将 trace step 映射到受支持的执行策略
- **THEN** 转换后的 step SHALL 使用 `manual-review` strategy 或等价的非静默失败标记
- **AND** runner SHALL NOT 在没有明确 fallback 指令时把该 step 执行为任意点击

### Requirement: 通用 runner 消费 Midscene flow IR
系统 SHALL 提供一个 Midscene runner，在生成 TypeScript 脚本成为必要路径之前，直接消费 `midscene-flow.json`。

#### Scenario: Runner 执行受支持策略
- **WHEN** runner 读取到包含受支持 `keyboard`、`input`、`tap`、`act` 或 `wait` strategy 的 flow
- **THEN** 它 SHALL 将这些 step 路由到对应 Midscene computer use 操作
- **AND** 它 SHALL 使用已配置 run directory 生成 Midscene 执行报告

#### Scenario: Runner 遇到不受支持策略
- **WHEN** runner 读取到不受支持或 `manual-review` strategy 的 flow step
- **THEN** 它 SHALL 给出清晰错误，标识 step id 和原因
- **AND** 它 SHALL NOT 静默跳过或执行猜测出来的桌面动作

### Requirement: 生成脚本是派生产物
系统 SHALL 将未来生成的 Midscene 脚本视为从 `midscene-flow.json` 派生出的产物，而不是源事实。

#### Scenario: 后续生成脚本
- **WHEN** 为某个项目创建生成的 `run.ts`
- **THEN** 它 SHALL 放在 `CUA_midscene/projects/<project-name>/generated/` 下
- **AND** 它 SHALL 引用生成时使用的 flow 或 metadata 版本
- **AND** 工作流变更 SHALL 先更新 source trace 输入或 `midscene-flow.json`，再重新生成脚本
