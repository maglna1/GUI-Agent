# CUA

本项目探索面向真实桌面环境的 Computer Use Agent（CUA）：`record` 将教学录制处理为结构化日志与 trace，`execution` 将 trace 初始化为 Midscene YAML 任务，并通过 Midscene computer use 操作 Chrome、堡垒机、远程桌面或企业内网页系统。

项目不使用 browser-use、Playwright、Puppeteer 或 CDP 作为执行底座。企业内网中“先经过堡垒机，再操作目标网页”的链路必须基于真实屏幕与键盘鼠标事件。

## 目录

```text
CUA/
├── record/                 # 教学录制处理：视频、日志、截图 -> trace
├── execution/              # 可独立发布的 TypeScript CUA Midscene Skill
│   ├── cua/                # 转换、任务解析、CLI 和公开工具 API
│   ├── executors/          # Midscene 适配与 KeyboardTypeText
│   ├── projects/           # 随 Skill 发布的只读内置任务
│   ├── schemas/            # Ajv 在文件边界使用的 JSON Schema
│   ├── SKILL.md            # 执行器 Skill 入口
│   └── references/         # Agent 按需读取的任务契约
└── openspec/               # 规格与变更记录
```

`record` 基于 ShowUI-Aloha Learn，只保留录制处理，不包含 Act、Actor、Executor 或回放能力。`execution` 全面使用 TypeScript：同一核心同时服务 CLI、GDE Claw 工具 API，并在进程内直接调用 Midscene。

## 数据流

```text
教学录制
  -> record：日志、截图、trace
  -> TypeScript converter：task.yaml + task.json
  -> 人、Agent 或未来前端确认后直接维护 task.yaml
  -> TypeScript resolver：<CUA_DATA_ROOT>/runs/<run-id>/resolved-task.yaml
  -> task run：按多个 Midscene task 顺序执行
  -> act run --scene/--task：投影为完整步骤 prompt，再执行单个 ai action

无录制自然语言要求
  -> 临时单 action YAML
  -> 同一个 TypeScript Midscene 执行 API
```

`task.yaml` 是任务唯一长期可执行流程，直接使用 Midscene 原生 YAML action。`task.json` 保存任务说明、trace 来源、输入 ID 和录制默认值；`source/` 是校准时的只读录制证据。系统不维护自定义 route、resolved flow、override、proposal 或 history。

## 快速开始

```powershell
cd execution
npm install
npm run check
$env:CUA_DATA_ROOT = 'C:\path\to\cua-data'

npm run cua -- scene list --json
npm run cua -- task list --scene browser-demo --json
npm run cua -- task describe --scene browser-demo --task air-tickets-demo --json
npm run cua -- task validate --scene browser-demo --task air-tickets-demo
npm run cua -- task inspect --scene browser-demo --task air-tickets-demo --input step-002-input=GOOGLE
npm run cua -- task run --scene browser-demo --task air-tickets-demo --dry-run
npm run cua -- act run --scene browser-demo --task air-tickets-demo --dry-run
npm run cua -- act run --prompt "打开 Chrome 并搜索 GUI agent" --dry-run
```

执行器要求 Node.js `>=18.19.0`，该下限与当前 Midscene `1.10.0` 保持一致。

实际操作电脑时去掉 `--dry-run`。第一版不实现并发锁，上层调用方必须串行发起真实 computer use；查询、转换、inspect 和 dry-run 不操作电脑。

从已放入 user task `source/` 的 trace 初始化任务：

```powershell
npm run cua -- task init-from-trace --scene <scene> --task <task> --goal "<任务目标>"
```

若 `task.yaml` 或 `task.json` 已存在，初始化直接失败，不覆盖人工或前端修改。

## Skill 与用户数据

```text
execution/projects/<scene>/          # 随 Skill 发布，只读
└── <task>/
    ├── task.yaml                    # 唯一长期执行事实源
    ├── task.json                    # 元数据、trace 来源和输入默认值
    ├── SKILL.md
    └── source/                      # trace、日志和截图

<CUA_DATA_ROOT>/
├── projects/<scene>/<task>/         # 用户创建和长期维护的任务数据包
├── cache/
└── runs/<run-id>/
    ├── resolved-task.yaml
    ├── ai-act-prompt.txt            # 仅录制任务整体 aiAct
    ├── ai-act-task.yaml             # 仅录制任务整体 aiAct
    ├── execution-result.json
    └── midscene/                    # Midscene 报告、截图等产物
```

数据根优先级为 `--data-root`、进程 `CUA_DATA_ROOT`、`execution/.env.local`、`execution/.env`。路径必须是 Skill 目录外的绝对路径。发现命令可只读取内置任务；创建、验证和执行必须配置数据根。同一 `scene/task` 在 builtin 与 user 两处重复会显式失败。

trace 每个 step 必须包含结构化 `caption.operation`。converter 不从 observation、think、action、expectation 或关键词猜测动作。click、doubleClick、input、keyboard、wait 分别转换为 `aiTap`、`aiDoubleClick`、`KeyboardTypeText`、`KeyboardPress`、`aiWaitFor`。`KeyboardTypeText` 通过底层键盘事件输入 ASCII，不使用剪贴板。

## 验证与安装

真实密钥只放在 `record/.env` 和 `execution/.env.local`，不得提交。

```powershell
cd execution
npm test
npm run build
```

安装本地 Skill 副本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-cua-midscene-skill.ps1
```
