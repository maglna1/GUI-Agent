## Why

`execution` 当前以 Python 承载任务转换、目录发现、参数解析和执行编排，再通过子进程调用 TypeScript Midscene runner；这造成双运行时、重复契约和不必要的进程协议。后续执行器将作为 GDE Claw 的 TypeScript 工具交付，因此现在适合将执行核心统一到 TypeScript，同时收紧而不扩大运行时校验范围。

## What Changes

- **BREAKING**：将 `execution/cua` 中的 Python CLI、trace 转换、任务发现、输入解析、YAML 投影、aiAct prompt 组合和执行编排迁移为 TypeScript。
- **BREAKING**：删除 Python 运行时、`pyproject.toml`、`uv.lock`、Pydantic 模型以及 Python 调用 TypeScript runner 的子进程协议；公开命令改由 Node.js CLI 提供。
- 保持 `projects/<scene>/<task>`、`task.yaml`、`task.json`、外部 `CUA_DATA_ROOT` 和统一 run directory 的现有业务结构与语义。
- 将 Midscene runner 提取为可直接导入的 TypeScript API，CLI 和未来 GDE Claw 工具调用共享同一核心，不再通过环境变量在父子进程间传递本次运行状态。
- 在读取 trace、任务清单和执行结果等文件边界使用 JSON Schema 与 Ajv 做最小运行时校验；TypeScript 内部对象不建立与 Pydantic 等价的重型运行时模型。
- 不复制 Midscene 完整 action 类型系统；本项目只校验稳定步骤、输入占位符和自定义动作等自有约束，最终 YAML 语法继续由 Midscene parser 校验。
- 将现有 Python 测试迁移为 TypeScript 测试，并以当前 CLI JSON、任务资产和 Schema 作为迁移期间的行为基线。
- 同步更新执行器 Skill、安装脚本、README、AGENT 规范和发布文件集合，移除所有 Python 命令及过期边界说明。

## Capabilities

### New Capabilities
- `typescript-task-core`：定义 TypeScript 核心对任务转换、发现、解析、投影、执行编排、CLI 和可导入工具 API 的职责及运行时校验边界。

### Modified Capabilities
- `python-task-core`：移除 Python 核心、Pydantic 契约和 Python/TypeScript 子进程执行协议。
- `trace-to-midscene-flow`：将 trace 到 Midscene YAML 的转换器实现约束改为 TypeScript，同时保持确定性转换行为。
- `midscene-yaml-tasks`：取消 Python 向 runner 提供 resolved YAML 的边界，改为 TypeScript 核心直接调用共享 Midscene 执行 API。
- `cua-data-layout`：将 Midscene 输出目录从子进程环境变量传递改为单次调用显式配置，并保持运行资产隔离。
- `local-task-skills`：发布单元改为纯 TypeScript 执行器，安装内容不再包含 Python 环境和源码。
- `ai-act-execution`：aiAct 的解析、投影与执行改为同进程 TypeScript 调用，同时维持现有互斥来源和失败语义。

## Impact

- 主要影响 `execution/cua/`、`execution/executors/`、`execution/tests/`、`execution/package.json`、TypeScript 配置、安装脚本和执行器 Skill 文档。
- 新增直接依赖 `@midscene/core`、YAML 解析库、Ajv 及 JSON Schema 辅助依赖；移除 Python、uv、Pydantic、PyYAML 和 pytest 运行依赖。
- CLI 命令入口从 `uv run cua ...` 迁移为 npm 开发入口和可发布的 `cua` Node.js bin；命令参数、JSON 输出和退出语义应保持兼容。
- 迁移不兼容保留 Python fallback，也不自动读取旧实现作为运行时兜底；旧实现仅可在迁移测试阶段用于结果对照，完成后必须删除。
