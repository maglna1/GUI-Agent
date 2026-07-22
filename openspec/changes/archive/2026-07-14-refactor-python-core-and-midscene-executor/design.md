## Context

`record` 已经使用 Python 完成录制日志、截图和 trace 的处理，而 `execution` 目前以 `@midscene/computer` 为起点全部使用 TypeScript。随着任务包、参数覆盖、人工校准和 Agent Skill 加入，TypeScript 层已经不再只是执行器：`src/flow/contracts` 同时描述落盘 JSON 与内部中间对象，`src/flow/conversion` 和 `src/flow/task` 承担了与 Midscene SDK 无关的业务逻辑，CLI 也全部通过 npm 暴露。

项目已经明确以 Python 为主体技术栈，但仍需要使用官方 Node.js Midscene SDK、`agentForComputer` 和 customActions。重构必须保持现有项目资产、确定性合并顺序、失败暴露原则和 computer use 执行语义，不能用兼容兜底同时维护两套实现，也不能借语言迁移改变 route 判断规则。

## Goals / Non-Goals

**Goals:**

- 让 Python 成为 trace 转换、任务包、校准、参数解析、resolved flow 和 CLI 的唯一业务实现。
- 让 TypeScript 只承担 Midscene SDK 适配、customActions、route 执行和执行结果输出。
- 区分进程内部 VO、持久化文件模型和跨进程执行 DTO，避免所有类型都被强制 JSON 化。
- 由 Pydantic 模型生成可复现的 JSON Schema，使 Python、TypeScript、Agent 和未来前端共享稳定文件契约。
- 保持 `execution/projects/<project-name>` 资产格式与现有执行行为，使用 `air-tickets-demo` 验证迁移等价性。
- 通过一次受控迁移删除被替代的 TypeScript 业务代码和过时 npm 入口，形成清晰目录。

**Non-Goals:**

- 本次不修改 `record` 的 trace 生成算法或模型 prompt。
- 本次不开发前端、不增加服务端 API，也不改变 Skill 的校准确认规则。
- 本次不重写 Midscene SDK、不以 Python 桌面自动化库替代 Midscene。
- 本次不新增 route strategy、不改变输入定位、键盘映射或等待策略。
- 本次不为只在 Python 进程内使用的 VO 生成 JSON Schema。

## Decisions

### Decision: Python 核心与 TypeScript 执行适配器并列组织

目标目录如下：

```text
execution/
├── cua/
│   ├── domain/
│   ├── models/
│   ├── conversion/
│   ├── task/
│   └── cli/
├── executors/
│   ├── keyboard-type-action.ts
│   └── run-midscene-flow.ts
├── schemas/
├── projects/
├── tests/
│   ├── python/
│   └── executors/
├── pyproject.toml
├── uv.lock
└── package.json
```

`execution/cua` 是 Python 应用核心；`execution/executors` 直接承载 TypeScript Midscene 适配器，不再增加 `executors/midscene` 层级。Node 依赖仍由 `execution/package.json` 管理，但 npm scripts 只服务于执行器构建、环境检查和测试。

备选方案是保留现有 TS task 层，仅用 Python 包装 CLI。该方案会形成两套领域模型，并让 Python 主体仍依赖 Node 完成纯 JSON 处理，因此不采用。

### Decision: Python 类型按内部模型和边界模型分层

路径集合、解析选项、合并上下文、校准验证结果等只在 Python 内部使用的对象采用 dataclass、枚举、Protocol 或普通类型，不导出 Schema。基础 IR、`project.json`、`flow-overrides.json`、校准 proposal/history 和 `resolved-flow.json` 使用 Pydantic 模型，在读取边界执行严格验证。

这避免把所有 VO 设计成可序列化 DTO，同时让人可编辑文件在进入业务逻辑前获得一致、可定位的错误。使用普通 dataclass 解析全部 JSON 的备选方案缺少稳定的运行时校验和 Schema 生成能力，因此只用于内部对象。

### Decision: Pydantic 是持久化契约的事实来源

`execution/schemas` 中的 JSON Schema 从 Pydantic 模型确定性生成并纳入 Git，文件头或构建元数据标明不得手工编辑。测试重新生成 Schema 并比较内容，发现漂移即失败。TypeScript executor 直接以 JSON Schema 和 Ajv 校验 `resolved-flow.json`，只在执行器内部声明映射 Midscene 动作所需的最小类型，不再生成或提交 TypeScript DTO。

第一版 Schema 至少覆盖：

- `midscene-flow.schema.json`
- `project.schema.json`
- `flow-overrides.schema.json`
- `calibration-proposal.schema.json`
- `resolved-flow.schema.json`

内部 `TaskProjectPaths`、CLI 解析结果、`ResolvedFlowResult` 等不生成 Schema。TypeScript 侧只读取 `resolved-flow.json`；JSON Schema 是跨进程运行时契约的唯一权威。执行器内部类型不作为公开契约，也不复制 Python 的 source、evidence、校准等非执行字段。

备选方案是手工维护 JSON Schema，再分别生成 Python 和 TypeScript 类型。当前主要开发语言是 Python，Pydantic 模型还承载领域边界校验，以它作为事实来源能减少编辑环节，因此不采用 Schema-first。

### Decision: resolved flow 是唯一 Python/Node 执行边界

Python `run` 命令完成项目发现、基础 IR 校验、校准合并、本次参数覆盖和执行快照写入，再向 Node 执行器传递 `resolved-flow.json` 的绝对路径。TypeScript 不读取 `project.json`、`flow-overrides.json`、proposal 或基础 IR，也不重新合并参数。

执行器在创建 Midscene agent 前验证 resolved flow 契约。验证失败、子进程非零退出、协议输出不合法或某个 step 执行失败均原样失败，不回退到旧 TS resolver。执行器将机器可读结果写入 `execution-result.json`，并用退出码向 Python 报告成功或失败；普通执行日志写入 stderr，Python CLI 的 stdout 保持机器可读 JSON。

### Decision: 统一 Python CLI，删除业务 npm CLI

Python 包提供 `cua` 入口，并保持现有概念：

```text
uv run cua project list --json
uv run cua flow convert --project <name> --goal <goal>
uv run cua flow validate --project <name>
uv run cua flow inspect --project <name> [--input key=value]
uv run cua flow run --project <name> [--input key=value]
uv run cua calibration validate --project <name> --proposal <id>
uv run cua calibration apply --project <name> --proposal <id> --confirmed
```

命令含义、稀疏参数覆盖和确认约束保持不变。Skill、根 README、`execution/README.md` 和项目 README 必须同步切换到 Python CLI。旧业务 npm scripts 在迁移完成后删除，不提供静默转发，以免长期存在双入口；Midscene 环境检查和 executor 测试仍可使用 npm scripts。

### Decision: 分阶段迁移但单一事实实现随步骤切换

先建立模型、Schema 和等价性测试，再迁移 converter、resolver/calibration 和 CLI，最后切换 runner 边界并删除旧 TS 业务模块。每个阶段可以小步提交，但同一能力在任一提交结束时只能有一个被文档认可的事实实现；临时对照代码不能作为运行时兜底。

迁移测试使用当前 JSON 资产作为 fixture，比较关键输出结构和行为，不要求字节级复刻无语义意义的字段顺序。所有错误路径必须 fail fast，并包含项目、step 或字段上下文。

## Risks / Trade-offs

- **Python 与 TypeScript 对 JSON Schema 的支持细节不同** → 约束 Schema 使用双方验证器都支持的特性，以现有 resolved flow 和非法样例做契约测试。
- **迁移时两个实现输出细节漂移** → 在删除 TS 实现前使用同一 fixture 比较 Python 输出、指纹、参数合并和校准结果；差异必须被解释或修正。
- **子进程协议使本地调试链路变长** → resolved flow 和执行结果都保留为报告产物，Python 打印实际执行命令、退出码和报告路径，但不吞掉 Node 错误。
- **Pydantic 模型与生成 Schema 漂移** → Schema 只允许通过生成命令更新，CI/测试验证工作区中的生成结果是最新的。
- **旧 npm 命令被外部脚本调用** → 在 README、Skill 和项目文档中一次性列出新命令，并将移除作为显式 breaking change；不保留隐藏兼容层。

## Migration Plan

1. 在 `execution` 初始化 Python 包、uv 环境、测试结构和 CLI 骨架。
2. 将持久化 TS interface 映射为 Pydantic 模型，将内部类型映射为 Python dataclass/普通类型，并生成首版 Schema。
3. 用现有项目资产建立模型、Schema、确定性指纹、合并和错误路径测试。
4. 迁移 trace converter，验证重新生成基础 IR 不覆盖项目配置和已确认校准。
5. 迁移 task resolver、参数解析、校准 validate/apply 和项目查询 CLI。
6. 定义 resolved flow 子进程契约，收缩 TypeScript runner，使其只执行已解析快照。
7. 切换 `flow run` 到 Python 调度 Node 执行器，完成 dry-run 与可选真实 computer use 验证。
8. 删除被替代的 TS contracts/conversion/task 代码和业务 npm scripts，更新 Skill 与全部中文文档。
9. 运行 Python、TypeScript、Schema、Skill 和 OpenSpec 全量验证，按功能域小步提交。

回滚以 Git 提交为单位；不在运行时保留 Python 失败后调用旧 TS 逻辑的兜底。如果迁移阶段无法达到行为等价，应停止在对应任务并暴露差异，而不是继续切换入口。

## Open Questions

无。Node 执行结果通道已经在实现与契约测试中确定；TypeScript 不再维护生成 DTO。
