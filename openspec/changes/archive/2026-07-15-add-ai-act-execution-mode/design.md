## Context

当前 Python 核心负责解析任务、应用本次输入并生成 resolved flow，TypeScript 适配器负责消费该快照并逐步调用 Midscene。该路径适合已录制且页面稳定的流程，但没有无录制自然语言入口，也不能将录制步骤整体交给 Midscene 规划。新能力需要跨越 Python CLI、持久化契约、TypeScript Midscene 适配器和 Agent Skill，同时不能改变现有确定性 runner 的语义。

Midscene 1.10.0 的 `aiAct` 会自行进行多轮规划和重规划。ComputerDevice 默认动作空间包含基于剪贴板的 `Input`，项目另有通过物理键盘事件输入 ASCII 的 `KeyboardTypeText`。公司堡垒机场景不能依赖外部剪贴板，因此两者的使用边界必须写入 `aiActContext`，但不能通过失败后回退掩盖问题。

## Goals / Non-Goals

**Goals:**

- 为无录制自然语言任务和有录制完整任务提供一次 `aiAct` 调用入口。
- 让任务模式复用现有 resolver 和 resolved flow，确保参数语义与 `flow inspect/run` 一致。
- 以确定性规则从 resolved flow 组合最小、可检查的有序步骤 prompt。
- 保留 prompt、执行结果和 Midscene 报告，原样暴露执行失败。
- 复用 resolved flow 校验与键盘动作绑定，避免两个 runner 演化出不同契约。

**Non-Goals:**

- 不实现确定性流程失败后的自动或半自动接管。
- 不实现步骤区间、从指定步骤继续或页面状态推断。
- 不修改 canonical flow，不在执行过程中生成校准或重试。
- 不移除 Midscene 默认 `Input`，不承诺非 ASCII 文本在堡垒机环境可用。
- 不自动执行真实桌面 smoke test。

## Decisions

### 1. 两种执行模式显式并列

保留 `cua flow run`，新增 `cua act run`。上层 Agent 或用户必须显式选择，不根据错误自动切换。这样失败语义可诊断，也避免一次调用在成本、规划方式和副作用上发生隐式变化。

备选方案是让 `flow run` 失败后调用 `aiAct`，但这会重复已完成动作并掩盖确定性路径缺陷，因此不采用。

### 2. Python 管理业务输入，TypeScript 只消费执行输入

自然语言模式由 Python 在 `execution/reports/<run-id>/` 写入 prompt 文件；任务模式由 Python 复用 resolver，在任务报告目录写入 resolved flow。TypeScript 只接收 `--prompt-file` 或 `--resolved-flow`，不读取 task manifest、canonical flow 或本次参数。

这保持 Python 为业务事实来源，同时让 TypeScript 仅承担 Midscene SDK 适配。两个来源在 TypeScript 参数层必须且只能提供一个。

### 3. 录制任务 prompt 只包含有序执行指令

prompt 固定以“请严格按以下步骤顺序完成电脑操作：”开头，随后按 flow 顺序输出 `step-id: 指令`。不加入 goal、intent、evidence 或 timing，避免弱模型受到重复或相互冲突的上下文干扰。

route 映射是确定性的：`tap/act` 使用 prompt；`input` 渲染当前 value，缺少占位符时显式追加；`keyboard` 转为按键指令；`wait` 优先 prompt，否则 condition；`manual-review` 和未知 route 立即失败。

### 4. 共享契约读取器与 Agent 创建器

抽取小型 resolved flow 读取校验模块，两个 runner 均使用同一份 Ajv schema。抽取支持 `KeyboardTypeText` 的 ComputerAgent 创建器，集中注册 custom action 并绑定底层 `keyboardPress`。

这些模块不生成新 flow、不转换业务对象，只减少 SDK 边界重复。现有 runner 的步骤执行和等待行为保持不变。

### 5. 输入动作通过上下文约束，不做运行时回退

`aiActContext` 明确要求 ASCII 文本优先且只能使用 `KeyboardTypeText`；仅当文本包含该动作不支持的字符时允许使用默认 `Input`；不得因定位失败或一般执行失败切换到默认 `Input`。动作空间保留 `Input`，以允许非 ASCII 的显式能力边界。

该约束依赖规划模型遵循 prompt，因此保留 Midscene 报告以检查实际动作。执行器不在运行时替规划器改写动作，也不自动重试。

### 6. aiAct 结果独立落盘并严格校验

新增 `AiActExecutorResult` Pydantic 契约和 Schema，记录模式、场景/任务、prompt 路径、源文件、dry-run、aiAct 返回值、状态、错误和完成时间。TypeScript 即使失败也尽力写结果；Python 对非零退出、无效结果、模式或路径不一致立即失败并保留原始错误。

### 7. execution 目录作为 Skill 发布单元

将 `SKILL.md`、`agents/` 和 `references/` 放入 `execution/` 根目录，使 Skill 的说明、契约、CLI、执行器和项目资产处于同一交付边界。安装脚本使用 Git 跟踪文件构建副本，不复制 `.env.local`、依赖目录、缓存或报告，避免发布元数据与实现分离后发生版本漂移。

## Risks / Trade-offs

- [规划模型不遵循 `aiActContext`] → 保留 Midscene 报告和最终 prompt，不做静默纠正；后续可基于真实报告评估动作空间裁剪。
- [完整任务一次规划成本较高或中途偏离] → 由调用方显式选择确定性 flow 或 aiAct；本轮不混合两种模式。
- [非 ASCII 默认 Input 依赖剪贴板] → 文档明确能力边界，失败原样暴露。
- [长流程 prompt 过长] → 第一版仅组合执行指令并剔除证据、意图、目标和 timing；后续以实际任务规模评估分段。

## Migration Plan

1. 添加共享 TypeScript 组件并让现有 runner 复用，验证其行为不变。
2. 添加 aiAct runner、prompt 组合测试和 dry-run 契约测试。
3. 添加 Python 模型、Schema、CLI 与子进程协议测试。
4. 更新 Skill 和文档，重新安装本机 Skill 副本。
5. 运行完整验证；真实桌面测试仅在用户明确指定目标后执行。

回滚时可删除 `act` 入口和 aiAct 适配器；现有 `flow run` 与任务资产无需迁移。

## Open Questions

- 后续是否需要按步骤区间或从失败步骤开始调用 aiAct，将依据真实长流程报告另行设计。
- 是否最终从动作空间移除默认 `Input`，取决于内网模型对 `aiActContext` 的遵循度和非 ASCII 输入需求。
