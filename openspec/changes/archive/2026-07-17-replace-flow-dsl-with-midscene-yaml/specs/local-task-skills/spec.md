## ADDED Requirements

### Requirement: 任务目录使用精简 YAML 资产
每个任务 SHALL 包含 `task.yaml`、`task.json`、`SKILL.md` 和 `source/`，运行时可创建不纳入版本管理的 `reports/`。

#### Scenario: Agent 发现任务
- **WHEN** Agent 读取场景或任务 Skill
- **THEN** Skill SHALL 指向任务清单、canonical YAML 和 task CLI
- **AND** Skill SHALL NOT 要求维护 route、override、proposal 或 history 文件

### Requirement: 任务输入声明录制默认值
`task.json` SHALL 为每个 trace input 保存输入 ID、中文标签、可选说明和录制默认值，不保存 JSON 字段绑定。

#### Scenario: 未提供本次输入
- **WHEN** 调用者未覆盖某项输入
- **THEN** resolver SHALL 使用 `task.json` 中的录制默认值

### Requirement: execution 发布单元只包含当前实现
execution Skill 安装包 SHALL 包含 Python 核心、YAML runner、项目任务、引用文档和必要契约，不得包含已删除架构的代码或说明。

#### Scenario: 安装 Skill
- **WHEN** 执行可重复安装命令
- **THEN** 本机 Skill 副本 SHALL 与仓库当前文件一致
- **AND** 安装包 SHALL NOT 包含 node_modules、reports 或旧 flow 文件

## REMOVED Requirements

### Requirement: 本地任务按场景和任务组织
**Reason**: 目录层级保持不变但由新的精简任务目录要求覆盖。
**Migration**: 继续使用 `projects/<scene>/<task>`。

### Requirement: 任务 flow 是唯一长期执行事实源
**Reason**: `midscene-flow.json` 被 `task.yaml` 替代。
**Migration**: 重新从 trace 生成 YAML。

### Requirement: 任务参数定义不复制默认值
**Reason**: 新设计将录制默认值集中在 `task.json`，以便 canonical YAML 使用命名占位符。
**Migration**: 从 trace input operation 重新生成输入定义。

### Requirement: 本地任务资产不依赖应用级历史
**Reason**: 该约束被精简目录与直接编辑 YAML 的要求覆盖。
**Migration**: 不创建 history、override 或 proposal 目录。

### Requirement: Agent 显式选择电脑操作执行模式
**Reason**: 录制任务只执行 YAML，无录制任务只使用 prompt 模式，不再有两种录制任务执行器。
**Migration**: 使用 `task run` 或 `act run --prompt`。

### Requirement: execution 是完整执行器 Skill 发布单元
**Reason**: 由更新后的发布单元要求替代，以清理旧实现。
**Migration**: 重新安装 execution Skill。
