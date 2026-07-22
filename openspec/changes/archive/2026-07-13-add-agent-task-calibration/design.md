## Context

现有转换器把 ShowUI-Aloha trace 直接写成 `ir/midscene-flow.json`，runner 直接执行该文件。这个结构能验证链路，但人工修正会在下一次转换时被覆盖；单次变更输入也只能改 IR。调用方 Agent 尚无稳定契约来区分创建任务、长期校准和单次调用。

项目仍处于探索阶段，要求所有缺陷显式暴露，不允许用自动重试、静默跳过或针对单一 demo 的规则掩盖问题。解析与合并必须保持确定性，不能新增模型依赖。

## Goals / Non-Goals

**Goals:**

- 将项目目录变为可被 Agent 和未来前端共同消费的任务包。
- 保留可重新生成的基础 IR，并把人工修正持久化到独立校准层。
- 支持带录制默认值的稀疏运行参数。
- 让 inspect 与 run 使用同一个 resolved flow 构建器。
- 用待确认 proposal 强制 Agent 在应用长期校准前等待用户确认。
- 提供仓库内可版本化、可安装的 Codex Skill。

**Non-Goals:**

- 本次不实现前端。
- 本次不支持插入、删除或重排 step；这类结构错误要求重新生成 trace。
- 本次不让 Agent 自动判断失败并修改后重试。
- 本次不生成项目专属 TypeScript runner，也不改变 Midscene computer use 底座。

## Decisions

### Decision: 基础 IR、校准和运行输入分离

基础 IR 继续保存在 `ir/midscene-flow.json`，转换器可以覆盖它。`config/flow-overrides.json` 只保存已经确认的 step 执行字段修正，`config/project.json` 声明可调用输入和录制默认值。执行时按基础 IR、校准、运行输入的固定顺序合并。

直接编辑基础 IR 虽然简单，但无法在重新转换后保留修改；把所有修正写回 trace 又会混淆录制证据与执行策略，因此均不作为维护路径。

### Decision: 输入使用显式绑定和稀疏覆盖

每个 input route 在项目配置中获得稳定参数 ID，第一版采用 `<step-id>-value`，并绑定到该 step 的 `route.value`。默认值来自基础 IR。调用方只传本次改变的值；未知参数、重复参数和失效绑定均 fail fast。

转换器只在项目配置不存在时初始化它，后续重新转换不得覆盖人工维护的标签或默认值。验证器负责发现 IR 更新后失效的绑定。

### Decision: 校准 proposal 使用受限领域结构

proposal 记录基础 IR SHA-256 指纹、中文原因和逐 step patch。patch 仅允许修改 `route` 与 `timing`；source、evidence、intent 和 step id 不可修改。相同 strategy 可以局部修改 route，改变 strategy 时必须提供完整合法 route。

Agent 把建议写入 `calibration/proposals/<id>.json`。验证不改变任务；只有用户明确确认后才调用 apply。apply 重新校验指纹和 patch，更新 `flow-overrides.json`，并把 proposal 移入 `calibration/history/`。人工可以直接维护 overrides，但必须运行 flow validate。

### Decision: resolved flow 是每次运行的不可复用快照

统一 resolver 负责读取、验证和深拷贝基础 IR，应用 overrides 和输入后返回 resolved flow 及来源摘要。inspect 只输出结果，run 在初始化 Midscene 前把快照写入被 Git 忽略的 `reports/<run-id>/resolved-flow.json`。运行过程不修改基础 IR、项目配置或校准。

### Decision: CLI 是 Agent、人工与未来前端的共同边界

CLI 提供 `project:list`、`flow:validate`、`flow:inspect`、`flow:run`、`calibration:validate` 和 `calibration:apply`。可机器消费的命令支持 JSON 输出并使用非零退出码报告错误。Skill 只描述分类、确认和命令调用流程，详细契约放在单层 reference 中，不复制执行实现。

### Decision: flow 工程按功能域组织

`src/flow` 下使用 `contracts`、`conversion`、`task` 和 `execution` 分别承载契约、trace 转换、任务解析/校准和 Midscene 执行。测试不与生产文件平铺，统一放在顶层 `tests/flow` 并按相同功能域组织。该结构让依赖方向清晰，也为未来前端复用 task 契约留出稳定入口。

## Risks / Trade-offs

- **基础 IR 更新导致校准失效** → proposal 使用 IR 指纹；flow validate 检查所有 step 引用和 route 合法性，阻止带过期校准执行。
- **运行参数可能包含敏感信息** → resolved flow 只写入已被 Git 忽略的 reports 目录，项目配置只保存录制默认值，不保存临时输入文件。
- **人工直接编辑 overrides 绕过 proposal 审批** → 这是明确保留的高级入口；执行前仍强制验证，Git 负责审查和长期历史。
- **第一版无法修正缺失或多余步骤** → 明确报错并要求重新生成 trace，避免隐式跳过造成错误操作。
- **Skill 安装副本与仓库源文件漂移** → 仓库源文件作为唯一事实，提供可重复覆盖安装方式并运行 Skill 校验。

## Migration Plan

1. 扩展类型并实现任务文件读取、验证、指纹、合并和参数解析。
2. 调整 converter 初始化任务配置但不覆盖已有配置。
3. 接入 inspect、validate、calibration 和 runner CLI。
4. 迁移 `air-tickets-demo`，生成项目配置与空校准文件。
5. 初始化仓库 Skill，更新中文文档并完整验证。

若需要回滚，可让 runner 暂时恢复直接读取基础 IR；新增 config、calibration 和 Skill 文件不会改变 source trace。

## Open Questions

无。前端、结构性 step 编辑和自动失败诊断留给后续变更。
