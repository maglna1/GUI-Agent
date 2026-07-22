## ADDED Requirements

### Requirement: Python CLI 提供 aiAct 统一入口
Python 核心 SHALL 通过 `cua act run` 暴露自然语言和录制任务两种显式 aiAct 调用方式，并复用现有任务解析能力。

#### Scenario: 直接自然语言调用
- **WHEN** 用户提供 `--prompt` 且不提供 scene/task 来源
- **THEN** Python SHALL 在 `execution/reports/<run-id>/` 保存源 prompt 和执行结果
- **AND** Python SHALL 调用 TypeScript aiAct 执行器

#### Scenario: 录制任务调用
- **WHEN** 用户提供完整的 `--scene` 和 `--task` 及可选稀疏输入
- **THEN** Python SHALL 使用与 `flow inspect` 相同的 resolver 和输入绑定生成 resolved flow
- **AND** Python SHALL 在任务自身 `reports/<run-id>/` 保存 resolved flow、最终 prompt 和执行结果

#### Scenario: 非法调用来源
- **WHEN** 用户混用 `--prompt` 与任务参数、遗漏 scene/task 任一项、提供空 prompt 或未知输入
- **THEN** Python SHALL 在启动 TypeScript 执行器之前失败并给出明确错误

### Requirement: aiAct 执行结果使用持久化契约
系统 SHALL 使用 Pydantic `AiActExecutorResult` 作为 Python 与 TypeScript 间 aiAct 结果的事实来源，并生成纳入版本管理的 JSON Schema。

#### Scenario: 校验成功结果
- **WHEN** TypeScript aiAct 执行器以零退出码返回结果
- **THEN** Python SHALL 验证 mode、scene/task、prompt 路径、源文件、dry-run、状态和完成时间
- **AND** Python SHALL 暴露可选的 aiAct 返回值

#### Scenario: 子进程或契约失败
- **WHEN** TypeScript 返回非零退出码、非法结果或失败状态
- **THEN** Python SHALL 保留原始错误并以失败状态结束
- **AND** Python SHALL NOT 调用确定性 runner 或修改任务资产
