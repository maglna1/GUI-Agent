## Why

当前 `midscene-flow.json` 同时承担自动生成产物和执行输入，人工直接修正会在重新转换 trace 时丢失，也缺少区分长期校准与单次调用参数的稳定机制。为了让业务流程真正成为可由 Agent 调用、可审查和可持续维护的任务包，需要把基础 IR、已确认校准、本次输入和执行快照明确分层。

## What Changes

- 为每个 `projects/<project-name>` 增加任务配置、已确认校准、待确认建议和校准历史目录。
- 新增确定性的 flow 解析层，按“基础 IR → 已确认校准 → 本次输入”生成 resolved flow。
- 新增项目列举、flow 验证/检查、校准建议验证/应用等参数驱动 CLI。
- 修改 runner，使其与 inspect 共用解析逻辑，并保存本次 resolved flow 执行快照。
- 将录制输入声明为带默认值的稀疏调用参数，未传参数继续使用录制值。
- 在仓库中交付可安装的 Codex Skill，约束 Agent 将交互分为创建、校准和调用；未经确认不得应用校准。
- 迁移 `air-tickets-demo` 作为完整任务包示例，并更新中文文档。

## Capabilities

### New Capabilities

- `agent-task-calibration`: 定义任务包配置、稀疏参数覆盖、校准建议审批、Agent Skill 和相关 CLI 的行为。

### Modified Capabilities

- `trace-to-midscene-flow`: 将项目目录扩展为任务包，并要求 runner 消费基础 IR、已确认校准和本次输入合并后的 resolved flow。

## Impact

- 影响 `execution/src/flow` 的类型、转换器和任务解析/校准工具，以及 `execution/src/executors` 中的 runner。
- 扩展 `execution/package.json` 的通用 CLI scripts。
- 扩展 `execution/projects/<project-name>` 目录契约并迁移现有示例。
- 新增仓库内 `skills/cua-midscene` Skill 源文件；本机安装副本继续由 `.gitignore` 排除。
- 不引入 browser-use、Playwright、Puppeteer、CDP 或新的运行时模型调用。
