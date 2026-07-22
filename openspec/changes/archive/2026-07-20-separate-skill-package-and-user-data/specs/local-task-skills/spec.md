## MODIFIED Requirements

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

### Requirement: execution 发布单元只包含当前实现
execution Skill 安装包 SHALL 包含 Python 核心、YAML runner、只读内置项目任务、引用文档和必要契约，不得包含用户任务、运行时可变数据或已删除架构的代码与说明。

#### Scenario: 安装 Skill
- **WHEN** 执行可重复安装或 staging 命令
- **THEN** 本机 Skill 副本 SHALL 与明确的当前发布文件集合一致
- **AND** 安装包 SHALL NOT 包含 node_modules、`.venv`、用户 data root、reports、midscene_run、缓存、真实环境文件、测试或旧 flow 文件
