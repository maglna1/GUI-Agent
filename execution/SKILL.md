---
name: cua-midscene
description: 使用本地场景/任务与 Midscene computer use 发现、创建、校准或执行桌面任务。用户要求从录制 trace 创建任务、修正长期步骤、临时改变输入、运行已有任务，或在无录制时直接操作电脑时使用。
---

# CUA Midscene

本目录是完整 TypeScript Skill 交付单元。安装后从 Skill 根目录使用 `node dist/cua/cli/main.js ...`；在源码仓开发时使用 `npm run cua -- ...`。

## 核心事实

- `task.yaml` 是唯一长期执行流程，由人、Agent、前端和 Midscene 共同消费。
- `task.json` 保存任务元数据、输入 ID 和录制默认值，不保存执行步骤。
- `source/` 是校准时的只读录制证据。
- Skill 内 `projects/` 是只读 builtin catalog；用户任务只写入 `<CUA_DATA_ROOT>/projects/`。
- 运行产物只写入 `<CUA_DATA_ROOT>/runs/<run-id>/`。
- 第一版不实现并发锁，实际 computer use 必须由上层串行调用。

数据根优先级为 `--data-root`、进程 `CUA_DATA_ROOT`、`.env.local`、`.env`。创建、验证和执行需要可写数据根。

## 判断意图

- **发现**：列出场景或任务，不读取无关资产。
- **创建/重建**：从 user task 的 `source/` 初始化 `task.yaml` 和 `task.json`。已有资产不得自动覆盖。
- **校准**：提出 `task.yaml` 修改建议，展示原值、新值和原因，等待明确确认。
- **参数契约修改**：长期改变默认值、标签或说明时单独提出 `task.json` 差异并等待确认。
- **单次调用**：只通过已声明的 `--input` 传值，不修改任务资产。
- **执行**：只有用户明确要求操作电脑时才运行非 dry-run 命令。

无法判断“仅本次”还是“以后都使用”时必须询问。

## 发现与创建

1. 运行 `node dist/cua/cli/main.js scene list --json`，再运行 `node dist/cua/cli/main.js task list --scene <scene> --json`。
2. 只读取目标场景和任务的 `SKILL.md`、`task.json`；检查动作时再读取 `task.yaml` 和必要 source。
3. 创建前确认 user task 的 `source/showui-trace.json` 和 `source/processed-log-sc.json` 已存在，且每个 step 有结构化 `caption.operation`。
4. 运行 `node dist/cua/cli/main.js task init-from-trace --scene <scene> --task <task> --goal "<目标>"`，再运行 `task validate`。

转换器不得从 observation、think、action、expectation 或关键词猜测动作；非法 operation 必须直接失败。

## 校准协议

1. 按 `step-NNN | <operation-type>` 定位 `task.yaml` 步骤，必要时只读查看 source。
2. 展示 YAML 位置、原值、新值和中文原因。
3. 确认目标 `origin=user`、`writable=true`；builtin 任务不得修改。
4. 停止并等待用户明确确认。
5. 确认后只修改 user task 的 `task.yaml`，再运行 `node dist/cua/cli/main.js task validate ...`。
6. 除非用户同时要求执行，否则校准完成后不得操作电脑。

校准不得修改 `source/`、`task.json` 或运行报告；不得重编号、打乱 step 或启用 `continueOnError`。参数契约修改是唯一允许单独编辑 `task.json` 的情况。

## 调用与执行

1. 使用 `task describe --json` 读取 input ID 和默认值。
2. 只传用户本次明确改变的输入；未提供项保持录制默认值。
3. 使用 `task inspect ... --input <id>=<value>` 查看 resolved YAML，使用 `task validate` 静态验证。
4. 稳定录制任务默认使用 `task run`；用户明确要求统一规划时使用 `act run --scene/--task`。
5. 无录制时使用 `act run --prompt "<电脑操作要求>"`。

`--dry-run` 不调用模型、不创建设备、不验证页面定位，不得描述为模拟执行。执行失败后报告原始错误并等待决定，不得自动切换模式、修改任务或重试。

同一输入需要影响后续动作时，只能经确认后在 `task.yaml` 中显式复用同一个 `{{input-id}}`；不得机械全文替换或从用户自然语言发明 input ID。

## 约束

- 不使用 browser-use、Playwright、Puppeteer 或 CDP。
- 不在转换、发现、输入解析或 YAML 快照中调用模型。
- 不创建自定义 flow、route、overrides、proposal 或 history。
- 不使用兼容读取、替代动作、静默跳过、自动重试或单用例硬编码掩盖失败。
