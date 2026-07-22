## ADDED Requirements

### Requirement: Python CLI 提供 aiAct 统一入口
Python 核心 SHALL 通过 `cua act run` 暴露自然语言和录制 YAML 任务两种显式 aiAct 调用方式，并复用现有任务 resolver 与 YAML runner。

#### Scenario: 直接自然语言调用
- **WHEN** 用户只提供非空 `--prompt`
- **THEN** Python SHALL 在 `execution/reports/<run-id>/` 保存临时 aiAct YAML 和执行结果
- **AND** Python SHALL 调用统一 Midscene YAML runner

#### Scenario: 录制任务调用
- **WHEN** 用户提供完整的 `--scene` 和 `--task` 及可选稀疏输入
- **THEN** Python SHALL 使用与 `task inspect` 相同的 resolver 生成 resolved task YAML
- **AND** Python SHALL 在任务自身 `reports/<run-id>/` 保存 resolved YAML、最终 prompt、临时 aiAct YAML 和执行结果

#### Scenario: 非法调用来源
- **WHEN** 用户混用 `--prompt` 与任务参数、遗漏 scene/task 任一项、提供空 prompt 或未知输入
- **THEN** Python SHALL 在启动 Midscene runner 前失败并给出明确错误

### Requirement: aiAct 执行结果使用持久化契约
系统 SHALL 复用现有 `ExecutorResult` 作为 Python 与统一 TypeScript YAML runner 间的执行结果契约。

#### Scenario: 校验成功结果
- **WHEN** YAML runner 以零退出码返回整体 aiAct 结果
- **THEN** Python SHALL 验证源 YAML 路径、dry-run、状态和完成时间
- **AND** Python SHALL 暴露可选的 Midscene 返回值

#### Scenario: 子进程或契约失败
- **WHEN** TypeScript 返回非零退出码、非法结果或失败状态
- **THEN** Python SHALL 保留原始错误并以失败状态结束
- **AND** Python SHALL NOT 调用逐 task 模式或修改任务资产
