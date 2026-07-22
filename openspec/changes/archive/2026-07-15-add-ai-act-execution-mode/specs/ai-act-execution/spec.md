## ADDED Requirements

### Requirement: aiAct 支持互斥的自然语言与录制任务来源
系统 SHALL 提供独立 Midscene aiAct 执行器，并要求每次调用只使用自然语言 prompt 文件或 resolved flow 其中一种来源。

#### Scenario: 无录制自然语言执行
- **WHEN** 调用方提供非空自然语言 prompt 文件
- **THEN** 执行器 SHALL 将该文本作为最终 prompt 调用一次 `agent.aiAct()`
- **AND** 执行器 SHALL NOT 读取任务资产或启动确定性 flow runner

#### Scenario: 有录制任务执行
- **WHEN** 调用方提供通过契约验证的 resolved flow
- **THEN** 执行器 SHALL 按 steps 原顺序组合最终 prompt 并调用一次 `agent.aiAct()`
- **AND** 执行器 SHALL NOT 读取 canonical flow、task manifest 或 source 证据

#### Scenario: 输入来源不唯一
- **WHEN** 调用方同时提供两种来源或均未提供
- **THEN** 执行器 SHALL 在初始化 ComputerDevice 之前失败

### Requirement: 录制任务 prompt 仅包含有序执行指令
系统 SHALL 使用确定性 route 映射构造录制任务 prompt，并排除不参与执行的上下文。

#### Scenario: 组合多种 route
- **WHEN** resolved flow 包含 tap、input、keyboard、act 和 wait step
- **THEN** 最终 prompt SHALL 以固定中文标题开头并按 step id 原顺序逐行输出完整执行指令
- **AND** input SHALL 使用本次 resolved value 渲染占位符，缺少占位符时显式追加输入内容
- **AND** wait SHALL 优先使用 route prompt，缺失时使用 condition

#### Scenario: 排除辅助信息
- **WHEN** resolved flow 同时包含 goal、intent、evidence 和 timing
- **THEN** 最终 prompt SHALL NOT 包含这些辅助信息

#### Scenario: 不可自动执行的 route
- **WHEN** resolved flow 包含 manual-review 或未知 route
- **THEN** prompt 组合 SHALL 立即失败且不得初始化 ComputerDevice

### Requirement: aiAct 输入动作遵守无剪贴板约束
系统 SHALL 注册 `KeyboardTypeText` 并通过 `aiActContext` 约束规划器的文本输入动作选择。

#### Scenario: ASCII 输入
- **WHEN** 任务需要输入 `KeyboardTypeText` 支持的 ASCII 文本
- **THEN** 上下文 SHALL 要求规划器优先且仅使用 `KeyboardTypeText`

#### Scenario: 不支持字符
- **WHEN** 文本包含 `KeyboardTypeText` 不支持的字符
- **THEN** 上下文 SHALL 允许规划器使用 Midscene 默认 `Input`
- **AND** 执行器 SHALL NOT 承诺该动作在无法传递剪贴板的环境成功

#### Scenario: 一般执行失败
- **WHEN** 定位失败或其他一般执行错误发生
- **THEN** 执行器 SHALL NOT 因该错误改用默认 `Input`、确定性 runner 或自动重试

### Requirement: aiAct dry-run 与报告可诊断
系统 SHALL 在不操作电脑的 dry-run 中完成全部静态验证，并为实际或 dry-run 调用保存机器可读结果和最终 prompt。

#### Scenario: dry-run
- **WHEN** 调用方提供 `--dry-run`
- **THEN** 执行器 SHALL 校验输入并输出最终 prompt
- **AND** 执行器 SHALL NOT 初始化 ComputerDevice 或调用模型

#### Scenario: 执行成功
- **WHEN** `agent.aiAct()` 成功完成
- **THEN** 系统 SHALL 保存最终 prompt、aiAct 返回值和成功结果
- **AND** 实际执行 SHALL 保留 Midscene 报告

#### Scenario: 执行失败
- **WHEN** 输入无效、`agent.aiAct()` 失败或结果契约无效
- **THEN** 系统 SHALL 保存或暴露原始错误并以非成功状态结束
- **AND** 系统 SHALL NOT 自动修改任务或切换执行模式
