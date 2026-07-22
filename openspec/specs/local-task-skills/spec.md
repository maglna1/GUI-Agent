# local-task-skills Specification

## Purpose
TBD - created by archiving change simplify-local-task-skills. Update Purpose after archive.
## Requirements
### Requirement: 任务目录使用精简 YAML 资产
每个任务 SHALL 包含 `task.yaml`、`task.json`、任务指令文件和可选 `source/`；任务目录不得保存运行报告。Skill 内置任务 SHALL 位于只读 builtin catalog，用户任务 SHALL 位于数据根的 user catalog。

#### Scenario: Agent 发现任务
- **WHEN** Agent 通过 Executor Skill 查询场景或任务
- **THEN** Skill SHALL 从内置与用户 catalog 返回任务清单、canonical YAML 和 task CLI
- **AND** 每个结果 SHALL 标明来源、实际路径和是否可写
- **AND** Skill SHALL NOT 要求维护 route、override、proposal、history 或任务内 reports 文件

#### Scenario: 用户沉淀新任务
- **WHEN** Agent 从 trace 初始化此前不存在的任务
- **THEN** 系统 SHALL 在用户 catalog 创建精简任务资产
- **AND** 系统 SHALL NOT 向 Skill 内置 catalog 添加或修改文件

#### Scenario: 内置与用户任务标识冲突
- **WHEN** 相同 scene/task 标识同时存在于内置与用户 catalog
- **THEN** 任务发现和执行 SHALL 显式失败并报告两个来源
- **AND** 系统 SHALL NOT 静默选择任一任务

### Requirement: 任务输入声明录制默认值
`task.json` SHALL 为每个 trace input 保存输入 ID、中文标签、可选说明和录制默认值，不保存 JSON 字段绑定。

#### Scenario: 未提供本次输入
- **WHEN** 调用者未覆盖某项输入
- **THEN** resolver SHALL 使用 `task.json` 中的录制默认值

### Requirement: execution 发布单元只包含当前实现
execution Skill 安装包 SHALL 包含 TypeScript 核心、Midscene YAML runner、只读内置项目任务、引用文档、编译运行入口和必要契约，不得包含 Python 环境、用户任务、运行时可变数据或已删除架构的代码与说明。

#### Scenario: 安装 Skill
- **WHEN** 执行可重复安装或 staging 命令
- **THEN** 本机 Skill 副本 SHALL 与明确的当前发布文件集合一致
- **AND** 安装包 SHALL NOT 包含 Python 源码与锁文件、node_modules、用户 data root、reports、midscene_run、缓存、真实环境文件、测试或旧 flow 文件

### Requirement: Agent 显式选择电脑操作执行模式
执行器 Skill SHALL 向上层 Agent 说明录制 YAML 逐 task 执行、录制任务整体 aiAct 和无录制自然语言 aiAct 三种调用方式，并禁止隐式切换。

#### Scenario: 页面稳定的已录制任务
- **WHEN** 用户调用已有录制任务且页面状态与流程稳定
- **THEN** Skill SHALL 推荐使用 `cua task run --scene <scene> --task <task>` 以降低规划成本

#### Scenario: 需要统一规划的已录制任务
- **WHEN** 用户调用已有录制任务并明确希望由 aiAct 统一规划完整步骤
- **THEN** Skill SHALL 使用 `cua act run --scene <scene> --task <task>` 并传入用户明确提供的本次输入

#### Scenario: 无录制自然语言任务
- **WHEN** 用户要求操作电脑但没有可用任务资产
- **THEN** Skill SHALL 使用 `cua act run --prompt <要求>`

#### Scenario: 执行失败
- **WHEN** 任一执行模式失败
- **THEN** Skill SHALL 报告原始错误并等待用户决定
- **AND** Skill SHALL NOT 自动切换模式、自动修改 YAML 或自动重试

