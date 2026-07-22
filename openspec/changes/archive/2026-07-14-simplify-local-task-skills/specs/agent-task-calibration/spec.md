## MODIFIED Requirements

### Requirement: 项目作为可调用任务包
系统 SHALL 使用场景清单与任务清单描述场景、任务名称、目标、可调用输入及字段绑定，并允许 Agent 和人工通过统一 CLI 发现任务。

#### Scenario: Agent 列出可调用任务
- **WHEN** 调用方执行场景内任务列表命令并请求 JSON 输出
- **THEN** 系统 SHALL 返回每个有效任务的名称、说明和输入定义
- **AND** 系统 SHALL NOT 操作电脑或调用模型

### Requirement: 调用输入采用稀疏覆盖
系统 SHALL 将任务输入绑定到已有 flow step 的执行字段，并仅使用本次明确提供的输入覆盖 canonical flow 中的值。

#### Scenario: 只改变一个输入
- **WHEN** 一个任务声明多个输入且调用方只提供其中一个
- **THEN** resolved flow SHALL 只覆盖该输入绑定的字段
- **AND** 其他字段 SHALL 保持 canonical flow 中的当前值

#### Scenario: 输入无效
- **WHEN** 调用方提供未知输入、重复输入或指向不存在 step 的绑定
- **THEN** 系统 SHALL 在执行前给出清晰错误并停止

### Requirement: Agent 校准需要确认
Agent SHALL 在用户明确确认长期修改后直接编辑 canonical flow，并在修改后验证该任务。

#### Scenario: 校准建议不影响执行
- **WHEN** Agent 已形成 step 修改建议但用户尚未确认
- **THEN** Agent SHALL 只展示原值、新值和原因
- **AND** canonical flow SHALL 保持不变

#### Scenario: 应用已确认建议
- **WHEN** 用户明确确认 Agent 展示的修改
- **THEN** Agent SHALL 直接编辑对应任务的 `midscene-flow.json`
- **AND** Agent SHALL 执行 flow 验证并报告结果
- **AND** 系统 SHALL NOT 创建持久化 calibration proposal 或 history

#### Scenario: 建议已经过期
- **WHEN** Agent 展示建议后 canonical flow 在用户确认前已经变化
- **THEN** Agent SHALL 重新读取当前 flow 并重新展示差异
- **AND** Agent SHALL NOT 将基于旧值的修改直接写入当前 flow

### Requirement: Agent Skill 约束任务交互
仓库 SHALL 提供执行器 Skill、场景 Skill 和任务 Skill，指导 Agent 区分创建、长期修改与单次调用。

#### Scenario: Agent 收到长期修正
- **WHEN** 用户说明某个步骤以后都应改变
- **THEN** Skill SHALL 要求 Agent 展示 flow 修改差异并等待确认
- **AND** Skill SHALL 禁止 Agent 未经确认直接修改或自动重试

#### Scenario: Agent 收到单次调用要求
- **WHEN** 用户只改变本次任务输入
- **THEN** Skill SHALL 要求 Agent 读取任务输入定义并只传递明确改变的值
- **AND** Skill SHALL NOT 修改 canonical flow

#### Scenario: 生命周期不明确
- **WHEN** Agent 无法判断用户要求仅本次生效还是长期生效
- **THEN** Skill SHALL 要求 Agent 在修改任务前询问用户

### Requirement: 任务解析不调用模型
系统 SHALL 使用确定性逻辑验证 canonical flow、任务输入绑定和本次输入，并构建 resolved flow。

#### Scenario: 构建 resolved flow
- **WHEN** flow inspect 或 flow run 构建 resolved flow
- **THEN** 合并顺序 SHALL 为 canonical flow、本次输入
- **AND** 该过程 SHALL NOT 调用模型

## REMOVED Requirements

### Requirement: 校准与基础 IR 分离
**Reason**: canonical flow 现在是人、Agent 与前端共同直接修改的唯一执行事实源，独立 overrides 会制造第二份流程事实。

**Migration**: 将已确认且仍有效的修改合并进任务根目录 `midscene-flow.json`，随后删除 `flow-overrides.json`。
