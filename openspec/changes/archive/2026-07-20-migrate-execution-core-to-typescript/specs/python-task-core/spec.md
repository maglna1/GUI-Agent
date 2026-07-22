## REMOVED Requirements

### Requirement: Python 核心解析和编排 YAML 任务
**Reason**: 任务业务核心统一迁移到 TypeScript，Python 到 TypeScript 的子进程边界被删除。
**Migration**: 使用 `typescript-task-core` 的直接 Midscene 执行 API 和 Node.js CLI。

### Requirement: Python 不重建 Midscene 动作类型系统
**Reason**: Python 核心整体删除，该约束由 TypeScript 核心继续承担。
**Migration**: TypeScript 仅校验 CUA 自有契约，最终 YAML 交由 Midscene parser。

### Requirement: Python CLI 合并内置与用户任务目录
**Reason**: catalog 发现迁移到 TypeScript CLI 与工具 API。
**Migration**: 使用保持同等目录与冲突语义的 Node.js `cua` 入口。

### Requirement: CLI 以 task 命令管理录制任务
**Reason**: Python CLI 被 Node.js CLI 替代。
**Migration**: 继续使用同名 task 子命令及参数，开发期从 npm 入口调用。

### Requirement: Python CLI 提供 aiAct 统一入口
**Reason**: aiAct 编排迁移到 TypeScript 核心并直接调用共享 runner。
**Migration**: 继续使用 Node.js `cua act run` 或直接导入 TypeScript API。

### Requirement: aiAct 执行结果使用持久化契约
**Reason**: Python 与 TypeScript 子进程之间不再需要执行结果协议。
**Migration**: TypeScript API 直接返回结构化结果；需要落盘的执行结果继续按 JSON 契约保存并在文件边界校验。
