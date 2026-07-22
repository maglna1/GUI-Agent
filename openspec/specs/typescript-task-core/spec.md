# typescript-task-core Specification

## Purpose
TBD - created by archiving change migrate-execution-core-to-typescript. Update Purpose after archive.
## Requirements
### Requirement: TypeScript 核心统一承载任务业务逻辑
TypeScript 核心 SHALL 承载双 catalog 任务发现、trace 转换、输入解析、resolved task YAML 生成、外部 run directory 创建、aiAct prompt 投影和执行编排。

#### Scenario: 执行本地任务
- **WHEN** 用户通过 CLI 或工具 API 运行内置或用户录制任务
- **THEN** TypeScript 核心 SHALL 读取所选任务清单和 canonical YAML、解析输入并在统一外部 run directory 写入本次运行快照
- **AND** TypeScript 核心 SHALL 直接调用共享 Midscene YAML 执行 API
- **AND** 系统 SHALL NOT 向任务目录或 Skill 根目录写入运行产物

### Requirement: TypeScript 核心提供 CLI 与可导入 API
系统 SHALL 以同一组核心函数同时支持 Node.js CLI 和 GDE Claw 等 TypeScript 调用方，不得要求工具调用方模拟 CLI 或启动子进程。

#### Scenario: Agent 直接调用工具 API
- **WHEN** 上层 Agent 以结构化参数调用任务发现、任务执行或 aiAct
- **THEN** API SHALL 返回结构化结果或抛出保留根因的错误
- **AND** API SHALL NOT 通过解析控制台文本传递结果

#### Scenario: 用户调用 CLI
- **WHEN** 用户调用发布的 `cua` bin 或开发期 npm 命令
- **THEN** CLI SHALL 保持现有子命令、参数和 JSON 字段语义
- **AND** 机器可读结果 SHALL 写入 stdout，诊断日志 SHALL 写入 stderr

### Requirement: 运行时校验限制在外部契约边界
系统 SHALL 使用 JSON Schema 与 Ajv 校验从磁盘或外部调用进入系统的自有持久化契约，并 SHALL NOT 为内部值对象建立重复的运行时模型。

#### Scenario: 读取人工修改的任务清单
- **WHEN** `task.json` 缺少必填字段、字段类型错误或包含不允许的字段
- **THEN** 系统 SHALL 在任务解析或设备初始化前失败
- **AND** 错误 SHALL 包含文件路径和字段路径

#### Scenario: 处理 Midscene 原生 action
- **WHEN** `task.yaml` 包含 CUA 未专门建模但 Midscene 支持的 action
- **THEN** CUA SHALL 保留该 YAML 结构
- **AND** 最终动作合法性 SHALL 由 Midscene parser 验证

### Requirement: TypeScript 核心不依赖 Python 运行时
发布后的执行器 SHALL 只依赖 Node.js 运行时及其声明的 npm 依赖，不得调用 Python、uv、Pydantic、PyYAML 或 pytest。

#### Scenario: 安装并调用执行器
- **WHEN** 在没有 Python 项目环境的目标机器安装执行器 Skill
- **THEN** 任务发现、转换、校验、inspect、dry-run 和实际执行入口 SHALL 可由 Node.js 运行
- **AND** 发布文件 SHALL NOT 包含 Python 源码或 Python 锁文件

### Requirement: 迁移不得引入运行时兜底
系统 SHALL 原样暴露转换、契约、YAML、Midscene 和模型错误，不得调用旧 Python 实现、自动切换执行模式或构造兼容结果。

#### Scenario: TypeScript 路径执行失败
- **WHEN** 任一核心或执行器操作失败
- **THEN** 调用 SHALL 以非成功状态结束并保留原始错误
- **AND** 系统 SHALL NOT 调用已删除的 Python 路径或修改任务后重试

