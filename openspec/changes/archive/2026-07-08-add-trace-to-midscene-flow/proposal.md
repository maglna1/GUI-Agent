## Why

当前项目已经通过手写脚本验证了 Midscene computer use，但从 ShowUI-Aloha 教学录制 trace 到可执行 Midscene 流程之间仍然依赖人工翻译。我们需要一个稳定的中间契约，让录制出来的演示可以沉淀为可复用的 CUA 项目资产，同时避免 ShowUI-Aloha 与 Midscene 内部执行细节过早耦合。

## What Changes

- 引入项目级 Midscene flow 产物，将 ShowUI-Aloha trace 信息转换为结构化 JSON。
- 在 `CUA_midscene` 中新增转换边界，消费 ShowUI-Aloha 产物，并输出 `projects/<project-name>/ir/midscene-flow.json`。
- 定义每个 flow step 如何保留源 trace 上下文、证据、执行策略和视觉回退指令。
- 建立 source 录制资源、processed trace 数据、IR、生成脚本和执行报告的项目目录约定。
- 保持 ShowUI-Aloha 专注于录制信息处理和 trace 生成；本次变更不让它直接生成 Midscene 脚本。

## Capabilities

### New Capabilities

- `trace-to-midscene-flow`：将 ShowUI-Aloha 教学 trace 产物转换为面向 Midscene 的 flow 产物，并按具名 CUA 项目组织。

### Modified Capabilities

- 无。

## Impact

- 影响的代码区域：
  - `CUA_midscene/src/`：承载 converter、routing、runner 以及后续 generator 工具。
  - `CUA_midscene/projects/<project-name>/`：承载 source 产物、IR、生成脚本和报告。
  - `showui-aloha/Aloha_Learn/`：仅作为 trace 上游生产方；不新增 Midscene 专属职责。
- 影响的格式：
  - 新增 `midscene-flow.json` IR schema。
  - 新增项目级元数据与产物目录约定。
- 不引入 browser-use、Playwright、Puppeteer、CDP 或 ShowUI-Aloha 回放执行器。
