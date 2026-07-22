## ADDED Requirements

### Requirement: 项目作为可调用任务包
系统 SHALL 使用项目配置描述任务名称、目标、可调用输入及其录制默认值，并允许 Agent 和人工通过统一 CLI 发现任务。

#### Scenario: Agent 列出可调用任务
- **WHEN** 调用方执行项目列举命令并请求 JSON 输出
- **THEN** 系统 SHALL 返回每个有效项目的名称、说明和输入定义
- **AND** 系统 SHALL NOT 操作电脑或调用模型

### Requirement: 调用输入采用稀疏覆盖
系统 SHALL 将项目输入绑定到既有 flow step 的执行字段，并仅使用本次明确提供的输入覆盖录制默认值。

#### Scenario: 只改变一个输入
- **WHEN** 一个任务声明多个输入且调用方只提供其中一个
- **THEN** resolved flow SHALL 只覆盖该输入绑定的字段
- **AND** 其他字段 SHALL 保持项目中记录的默认值

#### Scenario: 输入无效
- **WHEN** 调用方提供未知输入、重复输入或指向不存在 step 的绑定
- **THEN** 系统 SHALL 在执行前给出清晰错误并停止

### Requirement: 校准与基础 IR 分离
系统 SHALL 将已确认校准保存到独立配置，不得要求人工长期修改可重新生成的基础 IR。

#### Scenario: 重新生成基础 IR
- **WHEN** converter 再次生成 `midscene-flow.json`
- **THEN** 系统 SHALL NOT 覆盖现有项目配置或已确认校准
- **AND** flow 验证 SHALL 检查已有绑定和校准是否仍适用于新 IR

#### Scenario: 人工直接维护校准
- **WHEN** 人工直接编辑 `flow-overrides.json`
- **THEN** 系统 SHALL 允许其修改既有 step 的 route 或 timing
- **AND** flow validate SHALL 拒绝 source、evidence、intent 或未知 step 的修改

### Requirement: Agent 校准需要确认
系统 SHALL 让 Agent 先生成待确认 proposal，并在用户明确确认前禁止其进入已应用校准。

#### Scenario: 校准建议不影响执行
- **WHEN** proposal 仍位于待确认目录
- **THEN** flow inspect 和 flow run SHALL NOT 应用该 proposal

#### Scenario: 应用已确认建议
- **WHEN** 用户明确确认后调用 calibration apply
- **THEN** 系统 SHALL 重新验证 proposal 的 IR 指纹、step 和 patch
- **AND** 系统 SHALL 更新已确认校准并将 proposal 归档到 history

#### Scenario: 建议已经过期
- **WHEN** proposal 的基础 IR 指纹与当前 IR 不同
- **THEN** 系统 SHALL 拒绝应用并要求重新生成建议

### Requirement: Agent Skill 约束任务交互
仓库 SHALL 提供可安装 Codex Skill，指导 Agent 将请求分类为创建、校准或调用，并使用任务 CLI 完成操作。

#### Scenario: Agent 收到长期修正
- **WHEN** 用户说明某个步骤以后都应改变
- **THEN** Skill SHALL 要求 Agent 生成校准建议并展示差异
- **AND** Skill SHALL 禁止 Agent 未经确认直接应用或自动重试

#### Scenario: Agent 收到单次调用要求
- **WHEN** 用户只改变本次任务输入
- **THEN** Skill SHALL 要求 Agent 读取项目输入定义并仅传递明确改变的值

#### Scenario: 生命周期不明确
- **WHEN** Agent 无法判断用户要求仅本次生效还是长期生效
- **THEN** Skill SHALL 要求 Agent 在修改任务前询问用户

### Requirement: 任务解析不调用模型
系统 SHALL 使用确定性逻辑验证并合并基础 IR、已确认校准和本次输入。

#### Scenario: 构建 resolved flow
- **WHEN** flow inspect 或 flow run 构建 resolved flow
- **THEN** 合并顺序 SHALL 为基础 IR、已确认校准、本次输入
- **AND** 该过程 SHALL NOT 调用模型

