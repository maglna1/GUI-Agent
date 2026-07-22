## Context

当前 `execution/projects/<project>/` 同时保存基础 IR、项目配置、校准覆盖、校准建议、历史、生成脚本和报告。该结构来自“自动生成 IR 永远不可编辑”的假设，但后续架构已经明确：录制器不进入 GDE Claw 工具，任务 Skill 作为本地资产沉淀；人、Agent 和未来前端都需要共同修改同一份可执行契约。继续保留多层校准会让 Agent 绕过命令直接编辑 JSON，也让默认值分别存在于 flow 和项目配置中。

系统仍需保持两个进程边界：Python 负责本地任务发现、验证、参数解析和执行编排，TypeScript 只负责 Midscene API 适配。当前开发阶段不允许通过旧格式兼容、自动修复或执行兜底掩盖结构问题。

## Goals / Non-Goals

**Goals:**

- 用 `scene/task` 两级目录表达业务场景与具体任务。
- 让任务根目录的 `midscene-flow.json` 成为唯一长期执行事实源。
- 让人、Agent 和未来前端共享同一 JSON 契约，并在修改后统一验证。
- 保留任务参数化调用，同时消除参数默认值的重复存储。
- 保留 Python 到 TypeScript 的 resolved flow 进程边界。
- 删除校准 overrides、proposal、history、指纹和生成脚本等当前无必要机制。

**Non-Goals:**

- 本次不开发前端、数据库、云同步或权限系统。
- 不保存任务 flow 的应用级版本历史；如开发仓库需要版本历史，由 Git 自身承担。
- 不支持旧项目目录、旧 calibration CLI 或旧 JSON 格式的兼容读取。
- 不自动判断或修复错误步骤，也不在执行失败后自动修改并重试。

## Decisions

### 1. 场景和任务采用两级本地目录

目录固定为：

```text
execution/projects/<scene>/
├── scene.json
├── SKILL.md
└── <task>/
    ├── task.json
    ├── SKILL.md
    ├── midscene-flow.json
    ├── source/
    └── reports/
```

场景 Skill 只负责说明场景和路由任务；任务 Skill 只负责一个任务的用途、参数、限制和修改方式。原始证据放在任务自身 `source/`，不会与其他任务混杂。

替代方案是增加 `tasks/`、`evidence/`、`revisions/` 等中间层。它能提供更强分类，但当前本地规模下只会增加路径和 Agent 上下文负担，因此不采用。

### 2. `midscene-flow.json` 是唯一可编辑执行事实源

converter 只在 flow 不存在时初始化它。之后，人、Agent 或前端都直接编辑该文件；编辑必须通过 `flow validate`。若 converter 发现同名 flow 已存在则失败，不提供隐式覆盖或合并。

替代方案是保留 generated IR 加 overrides。该方案利于反复重生成，但用户实际希望确认和修改完整流程，且录制 source 已保留，可在明确删除旧 flow 后重新初始化，因此无需长期维护双层事实源。

### 3. 确认是交互规则，不是持久化数据模型

Agent 收到长期修正要求时，先展示目标 step 的原值、新值和原因，等待用户确认，再直接编辑 flow 并验证。系统不创建 proposal 文件、不保存 apply history，也不计算 IR 指纹。

这保留了“未经确认不得修改”的安全边界，同时避免为一次对话确认设计复杂状态机。未来前端可在界面状态中实现相同确认过程，无需改变任务 JSON。

### 4. 参数定义只保存绑定，默认值只存在于 flow

`task.json` 的输入项包含稳定 ID、中文标签、说明以及 `stepId + field` 绑定，不含 `default`。解析时仅应用本次明确传入的输入；未传入项保持 flow 中原值。inspect 输出可从解析后的 flow 读取有效值，但不会将其回写。

这避免编辑 flow 后仍被旧 `project.json.default` 覆盖的问题，也使直接编辑成为真实有效的操作。

### 5. resolved flow 保留为唯一执行进程边界

Python 读取并验证任务 flow，应用本次稀疏输入，写入 `reports/<run-id>/resolved-flow.json`；TypeScript 只验证并执行该快照。快照记录 scene、task、原 flow 路径和本次输入，但不包含校准来源。

resolved flow 不是额外转换格式，而是同一 flow 在某次调用中的冻结副本。保留它可以确保 inspect 与 run 共用逻辑、执行报告可复现，并避免 TypeScript 读取多个业务文件。

### 6. CLI 使用 scene/task 语义

统一入口调整为 `scene list`、`task list/describe/init-from-trace` 和 `flow validate/inspect/run`。所有任务命令显式传入 `--scene` 与 `--task`。旧 `project` 和 `calibration` 命令直接删除，不提供别名。

## Risks / Trade-offs

- [误编辑 canonical flow] → Pydantic 与 JSON Schema 严格验证，Agent 修改前展示差异，修改后必须执行 `flow validate`。
- [没有应用级历史难以撤销] → 当前本地探索阶段接受该取舍；开发仓库由 Git 管理，未来产品需要审计时再引入独立版本存储。
- [converter 无法覆盖导致重录流程多一步] → 明确要求用户先备份或删除现有 flow，再执行初始化，避免静默丢失人工校准。
- [场景 Skill 和任务 Skill 内容重复] → 场景 Skill 只做路由，任务参数事实源放在 `task.json`，任务 Skill 只补充 Agent 行为约束。
- [破坏旧 CLI 和目录] → 一次性迁移现有示例与全部文档，不保留兼容代码，以便测试尽早暴露遗漏。

## Migration Plan

1. 更新 Python Pydantic 模型和 Schema，建立 scene、task、flow、resolved flow 契约。
2. 简化解析器和 CLI，删除 calibration 模型、命令与文件。
3. 调整 TypeScript 执行契约为 scene/task 标识。
4. 将 `air-tickets-demo` 迁移到 `projects/browser-demo/air-tickets-demo/`，保留 source，删除旧校准与生成目录。
5. 更新仓库 Skill、安装副本、README 和测试。
6. 运行 Python、TypeScript、record、Skill 与 OpenSpec 验证。

回滚通过对应 Git 提交完成；不在运行时代码中提供旧格式回退。

## Open Questions

- 场景和任务资产未来是否需要由 GDE Claw 指定独立用户数据根目录，本次先继续使用仓库内 `execution/projects`。
- 前端引入后是否需要版本号、审计或冲突合并，本次不提前设计。
