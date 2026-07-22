## Why

现有任务包把自动生成 IR、持久校准、校准建议、历史记录和运行快照拆成多层文件，增加了人、Agent 与未来前端共同维护任务的理解成本，也产生了默认值和执行事实源不唯一的问题。当前仍处于本地开发探索阶段，适合将模型收敛为“任务内一个可直接编辑的执行 JSON”，并用场景和任务两级 Skill 支撑发现与调用。

## What Changes

- **BREAKING** 将任务目录从 `execution/projects/<project>/` 调整为 `execution/projects/<scene>/<task>/`，原始 trace、日志和截图继续保存在各自任务的 `source/` 中。
- **BREAKING** 以任务根目录的 `midscene-flow.json` 作为唯一可持久修改的执行事实源，移除 `ir/`、`config/flow-overrides.json`、`calibration/` 和 `generated/` 分层。
- **BREAKING** 移除持久化校准 proposal、apply、history 和 IR 指纹机制；Agent 在对话中展示修改建议，得到用户确认后直接编辑任务 flow 并验证。
- 新增场景清单与场景 Skill；每个任务保留独立 `task.json` 和任务 Skill，供 Agent 按需发现、理解、校准和调用。
- `task.json` 只声明参数 ID、说明和目标字段绑定；未传入参数时直接保留 `midscene-flow.json` 中的录制值，不再保存第二份默认值。
- trace converter 只负责初始化一个尚不存在的任务 flow，发现已有 flow 时直接失败，避免覆盖人工或前端校准结果。
- 保留确定性的运行时稀疏参数覆盖和 `resolved-flow.json` 快照；TypeScript Midscene 执行器仍只消费该执行快照。
- 将 CLI 调整为场景/任务语义，移除 project 和 calibration 命令。

## Capabilities

### New Capabilities

- `local-task-skills`: 定义本地场景、任务 Skill、唯一执行事实源以及人和 Agent 的直接编辑确认规则。

### Modified Capabilities

- `agent-task-calibration`: 用对话确认后直接编辑任务 flow 取代持久化 overrides、proposal 和 history 校准体系。
- `python-task-core`: 简化 Python 契约、解析流程、Schema 与 CLI，使其围绕场景、任务和单一 flow 工作。
- `trace-to-midscene-flow`: 修改任务目录、converter 初始化语义和 runner 输入来源，移除旧项目分层与生成脚本目录要求。

## Impact

- 影响 `execution/cua` 中的模型、转换器、任务解析、项目发现、CLI 和执行协议。
- 影响 `execution/executors` 中 resolved flow 的 TypeScript 契约与运行结果标识。
- 迁移 `air-tickets-demo` 到场景/任务两级目录，并删除旧校准资产。
- 更新 JSON Schema、测试、仓库 Skill、安装脚本及所有相关中文文档。
- 这是本地任务资产格式和 CLI 的破坏性变更，不提供旧目录或旧命令兜底。
