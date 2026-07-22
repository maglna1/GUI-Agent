## Why

当前 `execution/` 同时承载可发布 Skill、可变任务资产和运行报告，任务执行还会让 Midscene 在 Skill 工作目录生成独立报告。该布局在开发期方便，但无法保证 ZIP 安装目录只读、Skill 升级不覆盖用户任务，也无法统一清理、审计和定位一次运行的全部产物，因此需要在进入 GDE Claw 集成前建立明确的数据边界。

## What Changes

- 引入统一的 `CUA_DATA_ROOT`，从显式 CLI 参数、进程环境或本地环境配置解析用户持久化根目录，并从中派生用户任务、运行报告和缓存目录。
- 将 Skill 内 `projects/` 定义为随版本发布的只读内置任务；用户新建或从 trace 初始化的任务写入 `CUA_DATA_ROOT/projects/`。
- 合并发现内置和用户任务，返回任务来源与可写性；同标识冲突必须显式失败，不静默覆盖内置任务。
- 将任务执行、任务型 aiAct、自然语言 aiAct 及 Midscene 原生报告统一写入 `CUA_DATA_ROOT/runs/<run-id>/`，不再向任务目录或 Skill 根目录写入 `reports/`、`midscene_run/`。
- 每次运行由 Python 创建唯一 run 目录，并向 TypeScript 子进程动态传递该次运行的 Midscene 输出目录。
- 更新 Skill 契约、示例环境配置、安装/打包边界和测试，使运行时可变文件不进入 Skill 交付包。
- **BREAKING**：任务目录不再拥有 `reports/`，现有依赖任务内报告路径或 `execution/reports` 的调用方必须改为统一 run root。

## Capabilities

### New Capabilities

- `cua-data-layout`: 定义 Skill 只读资产、用户持久化任务、统一运行目录、配置优先级和运行时写入边界。

### Modified Capabilities

- `local-task-skills`: 将任务资产区分为 Skill 内置只读任务与外部用户任务，并移除任务目录内运行报告。
- `python-task-core`: 让 CLI 解析统一数据根、合并任务发现，并在外部 run root 编排 Python 与 Midscene 产物。
- `ai-act-execution`: 将自然语言和录制任务 aiAct 的诊断产物迁移到统一外部 run 目录。

## Impact

- 影响 `execution/cua/cli`、`execution/cua/task`、TypeScript YAML runner 子进程环境、`.env.example`、Skill/任务契约文档和对应测试。
- `execution/projects` 继续作为内置任务来源，但不再作为用户新任务的默认写入位置。
- 需要为开发环境和 GDE Claw 约定一个可写的 `CUA_DATA_ROOT`；真实密钥和现场路径仍不得进入 Skill ZIP 或 Git。
- 安装脚本与未来 ZIP 构建必须使用明确的发布边界，并排除用户数据、依赖目录、缓存和运行报告。
