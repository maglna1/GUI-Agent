# AGENT

## 项目简介

本项目探索基于真实桌面环境的 Computer Use Agent 工作流。`record` 负责将录制视频、输入日志和截图转换为结构化日志与 trace；`execution` 负责任务初始化、参数化调用和执行，并通过 Midscene computer use 操作本地 Chrome、堡垒机、远程桌面或企业内网页系统。

项目不以 browser-use、Playwright、Puppeteer 或 CDP 作为执行底座。主执行路径围绕 Midscene computer use 展开。

## 规范

1. 开发过程、文档、提交说明和面向用户的回复均使用中文；代码标识、API、命令、路径和第三方专有名词可以保留英文。
2. 当前项目处于开发探索阶段，不通过兜底、静默跳过、硬编码成功路径或伪造结果掩盖执行缺陷；不确定、不可执行或模型能力不足时应显式失败并保留诊断信息。
3. 不为单一演示用例构造特化逻辑。样例可验证链路，但任务契约、目录和执行器设计必须面向后续业务流程。
4. Agent 应区分创建、长期修改和单次调用。长期修改必须先展示 YAML 原值、新值和原因并等待确认；未经确认不得修改、自动重试或操作电脑。
5. `execution` 全面使用 TypeScript。`execution/cua` 保存转换、任务解析、CLI 和公开工具 API；`execution/executors` 只保存 Midscene 适配与 customActions。持久化 JSON 契约只在文件边界通过 Ajv 校验，Midscene YAML 最终由 Midscene parser 校验。
6. `task.yaml` 是唯一长期执行事实源，不维护自定义 flow、route、overrides、proposal 或 history。`task.json` 保存输入定义和录制默认值；本次参数只进入运行快照。
7. Skill 内的 `execution/projects` 是只读 builtin catalog，用户任务只写入 `<CUA_DATA_ROOT>/projects`；运行快照、结果、报告和截图只写入 `<CUA_DATA_ROOT>/runs/<run-id>`。TypeScript 核心在进程内直接调用 Midscene API，不启动额外 runner 进程。
8. 每个 trace step 对应一个 `step-NNN | <operation-type>` Midscene task；输入 ID 为 `step-NNN-input`。不得重编号、复用编号、打乱顺序或启用 `continueOnError`。
9. 上层 Agent 必须显式选择执行模式：稳定录制任务使用 `task run`，需要统一规划时使用 `act run --scene/--task`，无录制使用 `act run --prompt`。失败后不得自动切换、修改任务或重试。
10. 第一版不实现 computer use 并发锁。上层调用方必须保证真实桌面操作串行执行，不得把执行器描述为并发安全。
11. TypeScript 主流程应保持可顺读。单次使用且只做参数转发的函数默认不抽取；只有复用、隔离 I/O/第三方边界、承载独立业务规则或显著降低复杂度时才抽象。函数通常不超过约 200 行，但不得为满足行数机械拆出无意义调用层。
