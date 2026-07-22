## ADDED Requirements

### Requirement: Python CLI 合并内置与用户任务目录
Python CLI SHALL 从固定 Skill 内置 catalog 和数据根 user catalog 发现任务，并对查询结果暴露来源、可写性和实际资产路径。

#### Scenario: 列出混合任务 catalog
- **WHEN** 内置和用户目录包含不同标识的有效任务
- **THEN** `scene list` 与 `task list` SHALL 返回两类任务的合并结果
- **AND** 排序 SHALL 确定且不依赖文件系统遍历顺序

#### Scenario: 创建用户任务
- **WHEN** 调用 `task init-from-trace`
- **THEN** Python SHALL 只以 user projects root 解析目标和 source
- **AND** 内置任务目录 SHALL 不可作为创建目标

## MODIFIED Requirements

### Requirement: Python 核心解析和编排 YAML 任务
Python 核心 SHALL 承载双 catalog 任务发现、trace 转换、输入解析、resolved task YAML 生成、外部 run directory 创建、子进程调用和结果校验。

#### Scenario: 执行本地任务
- **WHEN** 用户通过 CLI 运行内置或用户录制任务
- **THEN** Python SHALL 读取所选任务清单和 canonical YAML、解析输入并在统一外部 run directory 写入本次运行快照
- **AND** Python SHALL 调用单一 TypeScript YAML runner
- **AND** Python SHALL NOT 向任务目录或 Skill 根目录写入运行产物

### Requirement: Python CLI 提供 aiAct 统一入口
Python 核心 SHALL 通过 `cua act run` 暴露自然语言和录制 YAML 任务两种显式 aiAct 调用方式，并复用现有任务 resolver、统一外部 run root 与 YAML runner。

#### Scenario: 直接自然语言调用
- **WHEN** 用户只提供非空 `--prompt`
- **THEN** Python SHALL 在 `<data-root>/runs/<run-id>/` 保存临时 aiAct YAML 和执行结果
- **AND** Python SHALL 调用统一 Midscene YAML runner

#### Scenario: 录制任务调用
- **WHEN** 用户提供完整的 scene/task 和可选稀疏输入
- **THEN** Python SHALL 使用与 `task inspect` 相同的 resolver 生成 resolved task YAML
- **AND** Python SHALL 在 `<data-root>/runs/<run-id>/` 保存 resolved YAML、最终 prompt、临时 aiAct YAML 和执行结果

#### Scenario: 非法调用来源
- **WHEN** 用户混用 `--prompt` 与任务参数、遗漏 scene/task 任一项、提供空 prompt 或未知输入
- **THEN** Python SHALL 在创建 run directory 或启动 Midscene runner 前失败并给出明确错误
