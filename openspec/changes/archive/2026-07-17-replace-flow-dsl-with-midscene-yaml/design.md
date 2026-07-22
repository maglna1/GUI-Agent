## Context

当前链路为 `trace -> midscene-flow.json -> resolved-flow.json -> TypeScript route runner`，另有一条 `resolved-flow.json -> prompt 组合 -> aiAct runner`。这些层分别复制动作、参数和校验规则，导致 Python 与 TypeScript 都理解业务 DSL。Midscene 1.10.0 已提供 YAML parser、ScriptPlayer 和 `agent.runYaml()`；ScriptPlayer 会从 Agent action space 匹配标准动作及 customActions，因此 `KeyboardTypeText` 可以直接成为 YAML action。

约束包括：主技术栈保持 Python；computer use 仍使用 Midscene 的 Node.js 生态；堡垒机内外剪贴板不互通；开发探索阶段不保留兼容逻辑、fallback 或自动重试；任务资产保存在用户本地并将来由前端和 Agent 共同编辑。

## Goals / Non-Goals

**Goals:**

- 让 `task.yaml` 成为唯一长期执行事实源和人机共同编辑契约。
- 让 trace 的结构化 operation 确定性生成 Midscene 原生动作。
- 让 Python 负责任务发现、输入解析、YAML 解析与运行编排。
- 让 TypeScript 只注册 customAction 并调用 `agent.runYaml()`。
- 保留无剪贴板 ASCII 键盘输入，并减少逐字符 Midscene action 的模型与报告开销。
- 所有缺陷 fail fast，不通过旧文件、默认 route、默认 Input、模式切换或自动重试掩盖。

**Non-Goals:**

- 不迁移或兼容现有 `midscene-flow.json` 和 resolved flow 报告。
- 不提供数据库、前端编辑器、版本历史或校准 proposal 系统。
- 不根据自然语言关键词猜测 trace operation。
- 不实现录制任务失败后的 aiAct 接管。
- 不扩展 `KeyboardTypeText` 的非 ASCII 能力。

## Decisions

### 1. canonical 任务文件采用 Midscene YAML

任务根目录包含 `task.yaml`、`task.json`、`SKILL.md`、`source/` 和本地 `reports/`。`task.yaml` 直接使用 Midscene 的 `computer`、`agent`、`tasks[].flow[]` 结构，不包裹自定义 step、route、evidence 或 source 字段。

选择 YAML 而不是继续维护 JSON IR，是因为 Midscene 已负责动作语法和执行语义；直接编辑 YAML 后无需再次转换。原始证据留在 `source/`，不复制进执行文件。

### 2. trace operation 到 YAML action 一对一映射

- `click` -> `aiTap`
- `input` -> `KeyboardTypeText`，包含 `locate`、占位符 value 和 `mode: replace`
- `keyboard` -> `KeyboardPress`
- `wait` -> `aiWaitFor`
- 录制步骤间隔 -> 前置 `sleep`，按既有 200ms 下限和 30s 上限裁剪

converter 只读取 `caption.operation` 和 processed log 时间，不扫描 observation、think、action、expectation 或原始动作关键词。任一必填字段缺失、operation 未知或 trace 与 processed log 无法对应时，整个转换失败且不写出半成品。

### 3. 录制步骤直接对应 Midscene task

每个 trace step 生成一个 Midscene `tasks[]` 项，任务名固定为 `step-NNN | <operation-type>`。该 task 的 `flow` 包含本步骤的前置录制等待（如有）和本步骤动作。这样不引入自定义 step DSL，也能让人、Agent 和 Midscene 报告使用同一个稳定步骤标识。

trace 中的 step ID 必须为正整数、唯一且按轨迹顺序严格递增；违反约束时转换失败。录制任务解析时也校验 task 名称、顺序和 operation type，不允许 `continueOnError: true`，避免修改 YAML 后步骤引用漂移或失败被跳过。

整体业务目标继续保留在 `task.json.goal`，同时写入 YAML 的 `agent.groupDescription`；场景内任务名写入 `agent.groupName`。它们用于报告和任务整体语义，不再占用某个步骤 task 的名称。

### 4. 输入使用严格命名占位符

每个 trace input operation 使用其步骤 ID 生成输入 ID，例如 `step-002-input`。`task.json` 保存 ID、中文标签、可选说明和录制默认值；`task.yaml` 中 value 使用完整标量 `{{step-002-input}}`。人工或 Agent 可以将同一占位符显式放入后续 prompt，使一次参数覆盖影响所有相关语义。

Python 使用 YAML AST 递归处理字符串标量，支持完整或嵌入式占位符；未知输入、重复输入、未解析占位符和非字符串值立即失败。解析顺序为录制默认值后叠加本次稀疏输入，不回写 canonical 文件。

没有选择“输入 ID 绑定某个 JSON 路径”，因为这会重新引入自定义 flow 模型；也不自动搜索并替换 trace 字面值，因为无法可靠判断后续动作的语义关联。

### 5. 运行边界是 resolved task YAML

Python 将参数解析后的 YAML 写入 `reports/<run-id>/resolved-task.yaml`，随后调用单一 TS runner。runner 接受 `--yaml`、`--result` 和 `--dry-run`：dry-run 解析并检查 YAML，但不创建设备；实际运行创建启用 `KeyboardTypeText` 的 ComputerAgent 并调用一次 `agent.runYaml(content)`，最终始终销毁 Agent。

TS 不读取 scene、task、source、task.json 或 CLI 输入，也不解释动作顺序。结果仅记录状态、源 YAML、dry-run、任务数、完成时间、Midscene 返回值或原始错误。

### 6. 自然语言 aiAct 也通过 YAML runner

`cua act run --prompt` 在独立报告目录生成只包含一个 `ai` action 的临时 YAML，并复用同一 runner。录制任务统一执行其 canonical YAML，不再把 YAML 动作重新翻译为一个大 prompt；如果任务作者希望某部分使用 aiAct，可以直接在 `task.yaml` 中写 `ai` action。

### 7. 删除而非废弃旧实现

删除 flow Pydantic 模型、resolved snapshot、route runner、aiAct prompt builder、Ajv flow schema、旧命令与对应测试。CLI 收敛为 `task init-from-trace`、`task validate`、`task inspect`、`task run` 和无录制 `act run --prompt`。不保留别名或兼容参数。

## Risks / Trade-offs

- [Midscene YAML 契约随版本变化] -> TS runner 使用安装版本的 parser 做 dry-run，Python 只校验本项目生成和参数解析所需的最小结构，测试固定当前 1.10.0 行为。
- [任务 YAML 可表达超出 Python 模型的 Midscene action] -> Python 不重建动作模型，只做通用 YAML 结构和占位符检查，最终语法由 Midscene parser 判定。
- [参数改变后续动作语义但 YAML 未引用占位符] -> 不做错误的自动关联；任务创建后由人、Agent 或未来前端显式在相关 prompt 中复用占位符。
- [逐字符键盘事件仍有延迟] -> customAction 内部直接调用底层 keyboard primitive，每个字符不经过 Midscene 规划；默认延迟保持可配置且不退回剪贴板。
- [破坏性重构不可回滚旧资产] -> 本次明确不提供运行时迁移；Git 分支和提交提供开发期回滚边界。

## Migration Plan

1. 在新分支归档前一变更并建立本变更规格。
2. 先实现 Python YAML 模型、converter、resolver 与示例 `task.yaml`。
3. 再替换 TS runner，删除旧执行链并更新测试。
4. 收敛 CLI、Skill 和文档，生成并安装新的 Skill 包。
5. 运行 Python、TypeScript、Skill 和 OpenSpec 全量验证。

不提供应用内 rollback 或旧资产迁移；需要撤销时回退本分支提交。

## Open Questions

无。本轮不处理参数与后续动作之间的自动语义关联，也不开发前端。
