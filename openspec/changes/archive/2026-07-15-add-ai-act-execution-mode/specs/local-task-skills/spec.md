## ADDED Requirements

### Requirement: Agent 显式选择电脑操作执行模式
执行器 Skill SHALL 向上层 Agent 说明确定性 flow、录制任务 aiAct 和无录制自然语言 aiAct 三种调用方式，并禁止隐式切换。

#### Scenario: 页面稳定的已录制任务
- **WHEN** 用户调用已有录制任务且页面状态与流程稳定
- **THEN** Skill SHALL 推荐使用 `cua flow run` 逐步执行以降低规划成本

#### Scenario: 需要统一规划的已录制任务
- **WHEN** 用户调用已有录制任务并明确希望由 aiAct 统一规划完整步骤
- **THEN** Skill SHALL 使用 `cua act run --scene <scene> --task <task>`

#### Scenario: 无录制自然语言任务
- **WHEN** 用户要求操作电脑但没有可用任务资产
- **THEN** Skill SHALL 使用 `cua act run --prompt <要求>`

#### Scenario: 执行失败
- **WHEN** 任一执行模式失败
- **THEN** Skill SHALL 报告原始错误并等待用户决定
- **AND** Skill SHALL NOT 自动切换模式、自动修改 flow 或自动重试

### Requirement: execution 是完整执行器 Skill 发布单元
系统 SHALL 将执行器 Skill 入口、Agent 元数据、参考契约、运行代码和本地任务资产组织在 `execution/` 目录内，使其可作为单一 Skill 包发布。

#### Scenario: 构建本机 Skill 副本
- **WHEN** 开发者运行 Skill 安装脚本
- **THEN** 安装包 SHALL 包含受版本管理的 `execution/SKILL.md`、运行代码、Schema、项目资产、Agent 元数据和参考契约
- **AND** 安装包 SHALL NOT 包含环境密钥、本地依赖、缓存或运行报告

#### Scenario: Agent 从安装包调用执行器
- **WHEN** Agent 加载已安装的 `cua-midscene` Skill
- **THEN** Agent SHALL 将包含 `SKILL.md`、`pyproject.toml` 和 `package.json` 的目录作为执行根目录
- **AND** Agent SHALL NOT 依赖外层 CUA 仓库才能发现 CLI 或执行器
