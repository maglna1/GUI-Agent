## ADDED Requirements

### Requirement: 用户数据根具有确定配置优先级
系统 SHALL 按显式 CLI 参数、进程环境变量 `CUA_DATA_ROOT`、Skill 根目录 `.env.local`、Skill 根目录 `.env` 的顺序解析用户数据根，并将其规范化为绝对路径。

#### Scenario: CLI 覆盖环境配置
- **WHEN** 调用方同时提供 `--data-root` 和 `CUA_DATA_ROOT`
- **THEN** 系统 SHALL 仅将 `--data-root` 用作本次调用的数据根
- **AND** 系统 SHALL NOT 修改环境文件

#### Scenario: 使用现场环境配置
- **WHEN** 调用方未提供 `--data-root` 且进程环境或环境文件包含 `CUA_DATA_ROOT`
- **THEN** 系统 SHALL 使用最高优先级的非空值
- **AND** 相对路径、不可创建路径或不可写路径 SHALL 在写入前失败并给出明确错误

#### Scenario: 缺少用户数据配置
- **WHEN** 命令需要创建用户任务或运行目录但没有可用数据根
- **THEN** 系统 SHALL 在写入 Skill 或当前工作目录前失败
- **AND** 错误 SHALL 指明 `--data-root` 或 `CUA_DATA_ROOT` 配置方式

### Requirement: 用户可写目录从数据根派生
系统 SHALL 从数据根派生 `projects/`、`runs/` 和 `cache/`，并将用户任务、运行产物和可清理缓存分别限制在对应目录。

#### Scenario: 初始化用户任务
- **WHEN** Agent 从 trace 初始化新任务
- **THEN** 系统 SHALL 将任务写入 `<data-root>/projects/<scene>/<task>/`
- **AND** 系统 SHALL NOT 修改 Skill 内置任务目录

#### Scenario: 创建运行目录
- **WHEN** 任一 dry-run 或实际执行需要保存投影文件
- **THEN** 系统 SHALL 在 `<data-root>/runs/<run-id>/` 创建唯一目录
- **AND** 该目录 SHALL NOT 位于 Skill 根目录或任务根目录内

### Requirement: Skill 安装目录保持运行时只读
系统 SHALL 将 Skill 代码、schemas、references 和内置任务视为可替换发布资产，运行时不得在 Skill 根目录创建用户任务、报告、Midscene 输出、缓存或真实环境配置。

#### Scenario: 执行内置任务
- **WHEN** Agent 从 Skill 内置 catalog 执行任务
- **THEN** canonical 任务资产 SHALL 保持不变
- **AND** 全部本次运行产物 SHALL 写入外部 run directory

#### Scenario: 重新打包 Skill
- **WHEN** 构建或安装当前 Skill 发布单元
- **THEN** 发布内容 SHALL 排除用户数据、运行报告、Midscene 输出、依赖目录、缓存和真实环境文件

### Requirement: Midscene 输出绑定本次运行
Python 执行编排 SHALL 为每个 TypeScript runner 子进程动态设置该次运行专属的绝对 `MIDSCENE_RUN_DIR`。

#### Scenario: 实际运行生成 Midscene 报告
- **WHEN** Midscene runner 创建报告、截图或日志
- **THEN** 这些文件 SHALL 位于 `<run-dir>/midscene/`
- **AND** 静态环境文件中的同名配置 SHALL NOT 将其重定向到共享 Skill 目录
