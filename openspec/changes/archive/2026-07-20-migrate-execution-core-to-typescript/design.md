## Context

当前 `execution` 已经形成清晰的业务资产边界：`task.yaml` 是长期执行事实源，`task.json` 保存任务元数据与输入默认值，`CUA_DATA_ROOT` 隔离用户任务和运行产物，Midscene 负责最终 YAML 执行。但实现被拆在两个运行时中：Python 负责绝大多数业务逻辑，随后通过 `npm exec tsx` 启动 TypeScript runner。该边界增加了安装成本、错误协议、Schema 生成链和运行目录传递复杂度，也不适合后续直接嵌入 TypeScript 编写的 GDE Claw。

本次迁移不改变任务资产结构，不引入数据库或前端，也不重建 Midscene DSL。迁移期间可以运行 Python 与 TypeScript 的对照测试，但最终发布物和运行路径只能保留 TypeScript 实现。

## Goals / Non-Goals

**Goals:**

- 以 TypeScript 统一实现 trace 转换、任务发现、输入解析、YAML 投影、aiAct prompt 组合、执行编排和 CLI。
- 提供可由 CLI 与 GDE Claw 共同调用的稳定 TypeScript API，消除 Python 到 Node.js 的子进程协议。
- 保持现有目录结构、任务资产、CLI 参数、JSON 输出、失败语义和无兜底要求。
- 仅在外部文件边界执行必要的运行时校验，并继续由 Midscene 校验其原生 YAML。
- 完成后删除 Python 源码、依赖、测试和文档残留。

**Non-Goals:**

- 不改变 trace、`task.yaml` 或 `task.json` 的业务形状。
- 不开发任务校准前端、数据库或远程任务仓库。
- 不完整建模 Midscene 的所有 YAML action。
- 不增加失败后自动切换模式、自动重试、兼容旧 flow 或 Python fallback。
- 不在本次迁移中优化模型 prompt 或改变录制步骤生成算法。

## Decisions

### 1. 保持语义目录，替换实现语言

`execution/cua/` 继续表示业务核心，并按 `cli/`、`conversion/`、`contracts/`、`task/` 组织 `.ts` 文件；`execution/executors/` 继续只承载 Midscene、ComputerAgent 和 customActions 适配。这样保留现有职责认知，同时删除 `.py`、`__init__.py` 和 Python 特有模型层。

备选方案是把所有文件平铺到 `src/`，但会丢失当前已经验证过的业务边界，也不利于区分任务领域逻辑与 Midscene SDK 适配。

### 2. CLI 与工具 API 共享同一核心

核心模块暴露显式参数和返回值的函数，例如任务发现、任务解析、trace 初始化、逐 task 执行和整体 aiAct 执行。Node.js CLI 只负责参数解析、stdout/stderr 分流和退出码；GDE Claw 直接导入核心 API，不模拟 CLI，也不启动子进程。

开发期命令使用 `npm run cua -- ...`，发布构建生成 `dist/` 并通过 package `bin` 暴露 `cua`。CLI 的 JSON 结果只能写入 stdout，诊断日志写入 stderr，避免 Midscene 日志破坏机器可读输出。

### 3. Ajv 只校验持久化边界

保留精简的 JSON Schema，使用 Ajv 校验从磁盘或调用方进入系统的 trace、`scene.json`、`task.json` 和执行结果。TypeScript 类型用于内部静态检查，不建立与当前 Pydantic 一一对应的运行时类，也不在内部函数间重复验证相同对象。

`task.yaml` 使用通用 YAML 库进行读取、占位符替换和写出；CUA 只检查稳定 step 名称、输入占位符、禁止 `continueOnError` 以及 `KeyboardTypeText` 等自有约束。最终 YAML 始终通过 Midscene 的 `parseYamlScript()` 校验。选择该边界是为了及时暴露人工或 Agent 编辑错误，同时避免维护第二套 Midscene action 类型系统。

### 4. 直接调用共享 Midscene 执行 API

将现有 runner 重构为可导入函数，接收 YAML 内容、run directory、dry-run 和执行配置，返回结构化结果。CLI 和任务核心直接调用该函数，不再生成子进程命令、读取子进程 stdout 或通过退出码推断结果。

第一版只有一个本地电脑目标，由上层 Agent 或调用方保证实际 computer use 不并发执行。执行器暂不实现进程内或跨进程锁，也不声明并发安全；任务发现、转换、validate、inspect 与 dry-run 不创建设备，不受该调用约束。

Midscene 1.10.0 的报告根目录只公开为 `MIDSCENE_RUN_DIR` 环境配置，没有发现实例级目录参数。执行器在创建 Agent 前设置本次绝对目录，并在 `finally` 中销毁 Agent和恢复原环境值。后续只有出现真实并发需求时才单独设计电脑资源调度，不在本次迁移中提前引入锁依赖或手写锁协议。

### 5. 明确依赖所有权

`execution/package.json` 直接声明实际导入的 `@midscene/core`、YAML 库、Ajv 和 `ajv-formats`，不依赖 `@midscene/computer` 的传递依赖。TypeScript 编译产物作为发布运行入口，`tsx` 只用于开发与测试。

### 6. 以行为基线完成一次性迁移

先固化当前有效的 CLI JSON、Schema、示例 trace、resolved YAML 和 aiAct prompt 为 fixtures/golden tests，再逐模块迁移。Python 与 TypeScript 可以在开发测试中并存以比较结果，但生产入口始终只有一个；当 TypeScript 测试达到等价行为后立即删除 Python 实现，不保留运行时切换开关。

### 7. 控制抽象层级并保持执行路径可顺读

迁移不按 Python 文件或函数逐项机械映射 TypeScript 抽象。业务主流程应在少量模块内保持清晰、连续的控制流，避免为了形式上的分层增加只做参数转发、只有一个调用点且没有独立语义的函数。此类逻辑默认保留在调用处或同一文件的主函数中，使 trace 转换、任务解析和执行编排能够沿调用路径直接调试。

函数抽取需要至少满足一项实际价值：被多个调用点复用、隔离明确的 I/O 或第三方边界、承载可独立测试的业务规则、显著降低主流程复杂度。单个函数通常不超过约 200 行；该数字是复杂度警戒线，不是为了达标而继续拆出无意义包装函数的硬性指标。模块边界优先按职责和变化原因划分，不为每个类型、动作或单次步骤建立独立文件。

## Risks / Trade-offs

- [手写 TypeScript 类型与 JSON Schema 可能漂移] → 对每种持久化契约增加有效与无效 fixture 测试，并校验 Schema 文件随契约变更同步更新。
- [多个进程或 Agent 同时控制同一桌面会相互干扰] → 第一版明确不支持并发实际执行，由上层调用方串行调度；执行器不通过不完整的锁实现制造并发安全假象。
- [YAML 库序列化可能改变格式或引号] → 以结构等价和占位符保持为主要断言，并用代表性任务做 golden 测试，不依赖无意义的空白格式。
- [CLI 迁移导致 Agent Skill 调用失效] → 保持参数语义与 JSON 字段，集中替换命令入口，并验证 staging 后安装包中的 Skill。
- [删除 Pydantic 后错误信息质量下降] → Ajv 错误统一转换为包含文件、字段路径和规则的中文诊断，不做类型强制转换。
- [直接导入 Midscene 后日志污染 stdout] → CLI 捕获自身输出协议并将诊断统一写入 stderr；工具 API 直接返回对象，不依赖控制台文本。
- [迁移时照搬旧结构可能形成过深调用链和大量单次使用包装函数] → 代码评审沿主要业务路径检查调用深度、抽象收益和函数规模，删除只做转发且没有独立语义的层级。

## Migration Plan

1. 保存当前 CLI、Schema、任务转换和运行投影的行为 fixtures，并建立 TypeScript 测试框架。
2. 实现 TypeScript contracts、数据根、catalog、YAML 与输入 resolver，逐项通过对照测试。
3. 迁移 trace converter、任务 Skill 生成和 aiAct prompt 组合。
4. 将 Midscene runner 改为直接可调用 API，并实现运行目录临界区和结构化结果。
5. 实现 Node.js CLI、编译入口与 package bin，验证全部命令和错误输出。
6. 删除 Python 源码、测试、`pyproject.toml`、`uv.lock` 和 Python 安装内容。
7. 更新 README、AGENT、Skill、references、安装脚本与 OpenSpec 主规格，完成完整验证。

本项目仍处于开发探索阶段，不承诺旧 Python 安装的原地回滚。若迁移尚未通过完整验证，则回退整个开发分支；一旦合并，运行时不保留 Python fallback。

## Open Questions

- GDE Claw 最终采用源码工作区依赖还是打包后的 npm 包，将影响发布元数据但不影响本次核心 API 设计；本次先同时保证 package export 与 bin 可用。
