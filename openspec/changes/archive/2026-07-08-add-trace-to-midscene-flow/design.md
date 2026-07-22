## Context

`showui-aloha` 当前只作为教学录制处理器：读取录制资源，抽取截图和交互日志，并生成语义 trace。`CUA_midscene` 是执行侧：负责 Midscene computer use 的环境检查、trace 到 flow 的转换，以及基于 `midscene-flow.json` 的通用 runner。

两者之间缺少一个稳定契约。ShowUI-Aloha trace 描述的是“人类演示了什么”，而 Midscene 执行脚本描述的是“自动化如何在真实桌面上可靠执行”。如果把二者当成同一个产物，要么继续依赖人工翻译，要么会让录制侧过早绑定 Midscene API。

## Goals / Non-Goals

**Goals:**

- 在 `CUA_midscene/projects/<project-name>/` 下定义项目化产物目录。
- 将 ShowUI-Aloha trace 输出转换为面向 Midscene 的 JSON flow 产物。
- 在每个 flow step 中保留足够的源上下文，以支持调试、失败回退和后续重新生成。
- 将 flow step 路由到稳定的 Midscene 操作类别，例如 keyboard action、text input、tap、generic visual action、wait/assertion。
- 在引入 TypeScript 生成脚本之前，先支持一个通用 runner 直接执行 flow。

**Non-Goals:**

- 不让 ShowUI-Aloha 直接生成 Midscene 脚本。
- 不重新引入 ShowUI-Aloha Actor、Executor 或回放组件。
- 不使用 Playwright、Puppeteer、CDP、browser-use 等浏览器自动化协议。
- 不在本次变更中解决所有企业网管流程；第一版只需要用一个样例项目证明转换路径。

## Decisions

### Decision: 在 trace 和脚本之间引入 Midscene flow IR

转换链路应为：

```text
ShowUI-Aloha trace
  -> midscene-flow.json
  -> 通用 Midscene runner
  -> 后续可选生成 run.ts
```

这样第一版实现可检查、可 diff，也不会把转换决策隐藏在生成的 TypeScript 里。IR 会成为可审查产物：人在运行自动化之前，可以对照原始 trace、截图、路由决策和 fallback prompt。

备选方案是直接从 trace 生成 `run.ts`。这个方案 demo 更快，但不利于调试、差异比较和局部重跑，也很难区分“转换错误”和“执行错误”。

### Decision: ShowUI-Aloha 只作为上游生产方

`showui-aloha` 只负责 Learn 输出。Midscene 专属 schema、prompt、routing 和 runner 代码都归属于 `CUA_midscene`。

备选方案是改造 ShowUI-Aloha，让它直接输出 Midscene JSON。这个能力后续可以作为 exporter 出现，但在目标 IR 稳定前会让录制器演进绑定执行策略，不适合作为第一版主路径。

### Decision: 按 project name 组织产物

每个工作流应放在 `CUA_midscene/projects/<project-name>/` 下，并使用 source、IR、generated、reports 等子目录：

```text
projects/<project-name>/
  source/
  ir/
  generated/
  reports/
  README.md
```

这样业务流程资产会聚合在一起。`src/` 保持为工具链代码，`projects/` 保存具体流程产物。

### Decision: 先路由，再执行

converter 不应只复制 trace caption，而应把每一步分类为执行策略：

- `keyboard`：确定性的按键或低层输入。
- `input`：语义文本输入，通常映射到 `aiInput`。
- `tap`：语义点击，通常映射到 `aiTap`。
- `act`：更高层的视觉操作，通常映射到 `aiAct`。
- `wait`：状态等待或断言辅助。
- `manual-review`：不确定步骤，需要人工确认后再执行。

第一版 runner 可以保守实现一部分策略。未知或模糊步骤不应静默变成危险自动化，而应进入 `manual-review` 或明确的视觉 fallback。

## Risks / Trade-offs

- **风险：IR 过于泛化，导致执行不可靠** -> 缓解：每个可执行 step 都必须包含具体 route strategy、源证据和 fallback instruction。
- **风险：converter 过拟合 air-ticket demo** -> 缓解：保持路由规则显式且项目无关，同时允许项目级 metadata 和 override。
- **风险：视觉 fallback 速度慢** -> 缓解：trace action 明确时优先使用确定性 route；复杂或变化 UI 再回退到 `aiAct`。
- **风险：截图和 trace 路径漂移** -> 缓解：source artifact 路径相对 project 目录保存，并在转换或执行前校验存在性。
- **风险：生成脚本过期** -> 缓解：把生成的 `run.ts` 视为 IR 的缓存产物，而不是源事实。

## Migration Plan

1. 使用现有 air-ticket trace 实验创建第一个项目目录。
2. 在 `CUA_midscene/src/` 下新增 converter 和 runner，不移动 ShowUI-Aloha Learn 内部代码。
3. 为样例项目生成 `midscene-flow.json`。
4. 使用通用 runner 执行样例 flow。
5. 在 IR 形态验证稳定后，再用后续变更实现 `generated/run.ts`。

回滚方式直接：删除新增项目资产和 converter/runner 代码；ShowUI-Aloha Learn 侧不受影响。

## Open Questions

- 第一版 converter 只读取 `showui-trace.json`，还是也强制读取 `processed-log.json` 以获得坐标和原始动作时间？
- screenshot reference 应指向 full screenshot、crop image，还是二者都保留？
- 当 step 路由为 `manual-review` 时，runner 应 fail fast、跳过，还是要求显式 override？
- 项目级 route override 应放在 `source/`、`ir/`，还是单独的 `config/` 目录？
