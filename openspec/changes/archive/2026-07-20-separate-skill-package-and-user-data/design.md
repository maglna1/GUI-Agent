## Context

`execution/` 既是 Skill 发布根，也是当前任务根和 Node 子进程工作目录。Python 通过 `projects/<scene>/<task>/reports` 保存任务运行，通过 `execution/reports` 保存自然语言运行；Midscene 又根据进程工作目录和静态 `MIDSCENE_RUN_DIR=midscene_run` 保存原生报告。安装后的 Skill 因此既要可升级又要可写，用户任务、运行证据和产品文件没有独立生命周期。

当前 CLI 已支持单一 `--projects-root`，但该参数无法同时表达 Skill 内置只读任务与用户外部可写任务。Python 在创建子进程前掌握任务来源和 run directory，适合作为全部路径解析与运行编排的唯一边界。

## Goals / Non-Goals

**Goals:**

- 让安装后的 Skill 目录保持只读和可替换，运行时不向其中写入用户任务、报告、缓存或环境密钥。
- 用一个可配置的 `CUA_DATA_ROOT` 管理用户任务、运行报告和缓存，并允许 CLI 对本次调用显式覆盖。
- 同时发现 Skill 内置任务和用户任务，明确来源与可写性，禁止同标识静默遮蔽。
- 将 Python 投影文件、执行结果和 Midscene 原生报告统一到一个 run directory。
- 保持 `task.yaml` 为唯一长期执行事实源，任务仍由 Executor Skill 通过 CLI 发现和管理，而不是注册为 GDE Claw 独立 Skill。

**Non-Goals:**

- 不实现任务版本历史、Git 同步、云端同步、数据库或多用户权限系统。
- 不实现内置任务 clone 命令；本轮只保证内置任务只读且用户新任务写入外部目录。
- 不实现报告 UI、上传、脱敏或自动保留策略，只建立可独立清理的目录边界。
- 不实现 GDE Claw ZIP 上传协议或最终内置 Runtime，只使当前 Skill 发布单元具备正确的只读/可写边界。
- 不兼容读取旧任务目录中的 `reports/`，也不迁移历史 `execution/reports` 或 `midscene_run`。

## Decisions

### 1. 单一数据根派生用户可写目录

引入 `CUA_DATA_ROOT`，并从中固定派生：

```text
<data-root>/
├── projects/
├── runs/
└── cache/
```

解析优先级为显式 `--data-root`、进程环境变量 `CUA_DATA_ROOT`、Skill 根目录的 `.env.local`、Skill 根目录的 `.env`。环境文件只作为开发和现场配置来源，真实文件不进入 Git 或 Skill 包；未来 GDE Claw 可直接注入进程环境而无需环境文件。

数据根必须解析为绝对路径。需要读写用户数据的命令在缺少配置、路径不可创建或不可写时立即失败，不退回当前工作目录或 Skill 根目录。选择一个根变量而不是分别配置 projects/runs/cache，是为了减少现场配置面；内部路径仍以值对象集中计算，未来可在不改变任务契约的情况下增加高级覆盖。

### 2. 内置与用户任务使用双 catalog

Skill 内现有 `execution/projects` 保留为 builtin catalog，随 Skill 版本发布并视为只读。`<data-root>/projects` 是 user catalog，`task init-from-trace` 及后续用户创建能力只写该目录。

发现命令同时扫描两个 catalog，并为场景和任务返回 `origin: builtin|user`、`writable` 和实际路径。相同 scene/task 标识同时存在时立即失败，避免用户文件静默替换产品资产。内置任务需要长期修改时，本轮由用户以不同标识准备外部副本；自动 clone 不在范围内。

没有选择把用户任务写回 Skill，是因为 Skill 升级、卸载、签名、只读安装和多 Agent 共享都要求产品文件与用户数据分离。没有把每个任务注册成 GDE Claw Skill，是因为任务数量可能持续增长，当前 Executor 已提供按需发现和读取任务指令的入口。

### 3. CLI 以 data root 取代单 projects root

用户侧 `--projects-root` 替换为 `--data-root`。查询和执行命令从 data root 与固定 builtin root 构建 catalog；创建命令只取得 user projects root。Python 内部测试可以构造临时 builtin/user roots，不再通过生产 CLI 暴露一个会绕过双 catalog 的单根模式。

这是有意的破坏性收敛，不保留别名或当前目录 fallback。生成的 conversion command、Skill 指令、README 和测试全部使用新参数与环境变量。

### 4. 每次调用只有一个外部 run directory

所有会生成投影或执行结果的命令先在 `<data-root>/runs/<run-id>` 创建唯一目录，再写入 `resolved-task.yaml`、aiAct prompt/YAML 和 `execution-result.json`。任务目录不再包含 `reports/`，`TaskPaths` 也不再暴露报告路径。

run id 使用 UTC 时间前缀加随机后缀，避免多进程在同一毫秒碰撞。dry-run 仍创建 run directory，因为它需要保留最终解析输入和静态校验结果。

### 5. Python 动态约束 Midscene 输出目录

Python 调用 TypeScript runner 时复制当前环境，并为该子进程覆盖绝对 `MIDSCENE_RUN_DIR=<run-dir>/midscene`。TypeScript 继续从环境读取模型配置，但不得根据当前工作目录决定持久化位置；进程环境优先于 dotenv 文件，因此静态 `.env` 不会覆盖本次 run directory。

`.env.example` 新增 `CUA_DATA_ROOT`，删除面向用户的静态 `MIDSCENE_RUN_DIR` 示例。Midscene 目录由执行编排内部管理，不是用户长期配置项。

### 6. 发布包使用明确边界

Skill 发布内容包含 Python/TypeScript 实现、schemas、references、环境示例和 builtin projects。测试、`.venv`、`node_modules`、用户 data root、`reports`、`midscene_run`、缓存与真实环境文件不得进入发布包。

当前 Codex 安装器与后续 ZIP staging 复用同一发布文件选择规则，避免继续把“所有 Git tracked execution 文件”当成产品包定义。GDE Claw 的最终 ZIP 外层结构和依赖安装流程留给后续变更。

## Risks / Trade-offs

- [现有命令依赖 `--projects-root`] → 本轮同步更新 CLI、Skill、文档和测试，并明确不保留兼容别名。
- [未配置 data root 导致原本可运行的查询失败] → builtin-only 查询可不要求可写根；任何用户 catalog 或运行命令缺少配置时给出包含 `CUA_DATA_ROOT` 的明确错误。
- [同名内置与用户任务无法直接覆盖] → 以显式失败换取可诊断性；后续可新增 clone/rename，而不是引入隐式优先级。
- [环境文件解析在 Python 和 Node 间产生差异] → Python 负责数据根和 run 环境，Node 只继承确定后的进程环境；模型变量保持现有 dotenv 行为但不得决定数据路径。
- [Midscene SDK 在目录内生成大量文件] → 每次运行定向到独立子目录，为后续配额和清理提供边界；本轮不实现自动清理。
- [builtin source 截图仍会增大 Skill 包] → 本轮只区分不可变与可变数据，不改变内置 evidence 的裁剪策略。

## Migration Plan

1. 增加数据根配置与目录值对象，更新环境示例和忽略规则。
2. 将任务发现重构为 builtin/user 双 catalog，并让创建命令只写 user root。
3. 将所有运行模式迁移到统一 runs root，动态设置 Midscene 子进程目录。
4. 更新 CLI、Skill、任务契约、README 和安装发布选择规则。
5. 使用临时 data root 重写测试，验证 Skill 根在只读语义下不会产生新文件，并运行 Python、TypeScript、schema 与 OpenSpec 校验。

本轮不自动移动现有报告或用户任务。需要保留的开发任务由开发者手工复制到配置的 user projects；撤销时回退分支即可，历史目录不会被删除。

## Open Questions

无。GDE Claw 最终提供的数据目录变量名、ZIP 结构和依赖安装机制在接入阶段映射到 `CUA_DATA_ROOT` 与统一 CLI，不影响本轮内部契约。
