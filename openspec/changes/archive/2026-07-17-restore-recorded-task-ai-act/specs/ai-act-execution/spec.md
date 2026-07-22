## ADDED Requirements

### Requirement: aiAct 支持互斥的自然语言与录制任务来源
系统 SHALL 通过统一 Midscene YAML runner 接受自然语言 prompt 或参数已解析的录制任务 YAML 其中一种来源，并调用一次整体 aiAct。

#### Scenario: 无录制自然语言执行
- **WHEN** 调用方提供非空 `--prompt` 且不提供任务来源
- **THEN** 系统 SHALL 将该文本包装为单 `ai` action 的临时 YAML
- **AND** 系统 SHALL NOT 读取任务资产或启动逐 task 执行

#### Scenario: 有录制任务执行
- **WHEN** 调用方提供完整 scene/task 和可选稀疏输入
- **THEN** 系统 SHALL 解析 canonical `task.yaml` 的本次参数并按 task 原顺序组合最终 prompt
- **AND** 系统 SHALL 将最终 prompt 包装为单 `ai` action 的临时 YAML并通过统一 runner 执行

#### Scenario: 输入来源不唯一
- **WHEN** 调用方混用 `--prompt` 与任务参数、均未提供来源或只提供 scene/task 之一
- **THEN** 系统 SHALL 在解析任务或初始化 ComputerAgent 前失败

### Requirement: 录制任务 prompt 仅包含有序执行指令
系统 SHALL 使用确定性 YAML action 映射构造录制任务 prompt，并保留稳定步骤名称。

#### Scenario: 组合受支持 YAML action
- **WHEN** resolved task 包含 aiTap、KeyboardTypeText、KeyboardPress、aiWaitFor 或 ai action
- **THEN** 最终 prompt SHALL 以固定中文标题开头并按 task 和 flow 原顺序输出完整执行指令
- **AND** KeyboardTypeText SHALL 使用本次 resolved value 并显式要求同名 customAction
- **AND** sleep action SHALL NOT 写入最终 prompt

#### Scenario: 排除辅助信息
- **WHEN** resolved task 与 task manifest 同时包含整体目标、source、录制默认值和等待时间
- **THEN** 最终 prompt SHALL 只包含步骤名称和可执行动作指令

#### Scenario: 不受支持的 YAML action
- **WHEN** resolved task 包含未知动作、空动作或缺失必填动作字段
- **THEN** prompt 组合 SHALL 立即失败且不得初始化 ComputerAgent

### Requirement: aiAct 输入动作遵守无剪贴板约束
系统 SHALL 注册 `KeyboardTypeText` 并通过 aiActContext 禁止使用 Midscene 默认 Input 或剪贴板。

#### Scenario: ASCII 输入
- **WHEN** 任务需要输入 `KeyboardTypeText` 支持的 ASCII 文本
- **THEN** 最终 prompt 和上下文 SHALL 要求规划器使用 `KeyboardTypeText`

#### Scenario: 不支持字符
- **WHEN** 文本包含 `KeyboardTypeText` 不支持的字符
- **THEN** 执行 SHALL 失败并暴露错误
- **AND** 系统 SHALL NOT 改用默认 Input 或剪贴板

#### Scenario: 一般执行失败
- **WHEN** 定位失败或其他执行错误发生
- **THEN** 系统 SHALL NOT 改用其他输入动作、逐 task runner 或自动重试

### Requirement: aiAct dry-run 与报告可诊断
系统 SHALL 在任务报告目录保存本次 resolved YAML、最终 prompt、临时 aiAct YAML 和统一执行结果，并在 dry-run 中完成全部静态验证。

#### Scenario: 录制任务 dry-run
- **WHEN** 调用方对录制任务提供 `--dry-run`
- **THEN** 系统 SHALL 生成并保存全部运行时投影文件
- **AND** runner SHALL 解析临时 YAML但不得初始化 ComputerAgent 或调用模型

#### Scenario: 执行失败
- **WHEN** prompt 组合、YAML runner 或 aiAct 执行失败
- **THEN** 系统 SHALL 保留或暴露原始错误并以非成功状态结束
- **AND** 系统 SHALL NOT 自动修改任务或切换执行模式

## REMOVED Requirements

### Requirement: aiAct 只处理无录制自然语言任务
**Reason**: 统一 YAML runner 已恢复录制任务整体 aiAct 来源，不再只处理无录制自然语言任务。
**Migration**: 无录制任务继续使用 `act run --prompt`；录制任务使用 `act run --scene/--task`。
