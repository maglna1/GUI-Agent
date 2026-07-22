## Why

当前顶层目录名 `showui-aloha` 和 `CUA_midscene` 分别绑定上游项目与具体执行技术，不能准确表达录制处理域和可扩展执行域。随着任务校准、参数化调用和未来多执行器规划加入，需要用稳定的职责名称替代技术名称。

## What Changes

- **BREAKING**：将顶层 `showui-aloha/` 重命名为 `record/`。
- **BREAKING**：将顶层 `CUA_midscene/` 重命名为 `execution/`。
- 将 Midscene 专属运行代码从 `src/flow/execution/` 调整到 `src/executors/`，不增加 `midscene/` 子目录。
- 将对应执行测试调整到 `tests/executors/`。
- 更新代码中的默认路径、生成命令、Skill、README、AGENT 和当前 OpenSpec 规格引用。
- 保留 `execution/projects/` 作为各种业务项目 Midscene 执行资产的归属目录。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `trace-to-midscene-flow`：将录制生产方和执行任务包的目录契约改为 `record/` 与 `execution/`。

## Impact

- 影响两个顶层目录及仓库内所有当前路径引用。
- 影响 npm 工作目录、ShowUI-Aloha uv 工作目录和 Codex Skill 命令说明。
- 不改变 trace、flow、项目配置、校准 proposal 或 runner 的 JSON schema。
- 不改写已归档 OpenSpec change 中的历史路径记录。
