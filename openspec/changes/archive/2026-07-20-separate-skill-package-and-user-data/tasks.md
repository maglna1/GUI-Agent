## 1. 数据根与配置契约

- [x] 1.1 增加集中式数据路径值对象，按 `--data-root`、进程 `CUA_DATA_ROOT`、`.env.local`、`.env` 解析绝对数据根并派生 projects/runs/cache
- [x] 1.2 为缺失、相对、不可创建和不可写的数据根实现 fail-fast 错误，确保不回退到当前目录或 Skill 根
- [x] 1.3 更新 Python 依赖、`.env.example` 和配置加载测试，新增 `CUA_DATA_ROOT` 并移除静态 `MIDSCENE_RUN_DIR` 用户配置

## 2. 内置与用户任务 Catalog

- [x] 2.1 重构任务路径和发现模型，区分固定 builtin projects 与 data root 下 user projects，并返回 origin、writable 和实际路径
- [x] 2.2 合并 scene/task 列表并实现确定排序、标识冲突显式失败和内置任务只读校验
- [x] 2.3 将 `task init-from-trace` 的目标和 source 解析限定到 user projects，禁止创建或覆盖内置任务
- [x] 2.4 用 `--data-root` 更新全部 CLI 命令、conversion command 和机器可读输出，删除用户侧 `--projects-root` 与当前目录 fallback

## 3. 统一运行目录

- [x] 3.1 从 TaskPaths 移除任务内 reports，使用 UTC 时间前缀与随机后缀在 `<data-root>/runs` 创建唯一 run directory
- [x] 3.2 将 task run、录制任务 aiAct、自然语言 aiAct 和 dry-run 的全部投影与结果迁移到统一 run directory
- [x] 3.3 Python 启动 TypeScript runner 时动态覆盖绝对 `MIDSCENE_RUN_DIR=<run-dir>/midscene`，验证进程环境优先于静态 dotenv
- [x] 3.4 更新 CLI JSON 结果以稳定暴露 run directory 和产物路径，并确认失败时保留已有诊断文件且不修改任务

## 4. Skill 发布边界与文档

- [x] 4.1 将 Skill 内 `execution/projects` 文档化为只读 builtin catalog，并更新顶层 Skill、场景/任务指令和任务契约以使用外部 user catalog
- [x] 4.2 更新根 README、execution README 和 AGENT.md 的目录图、配置优先级、开发命令与报告位置
- [x] 4.3 将 Codex 安装器改为明确发布文件集合并排除 tests、依赖目录、真实环境文件、用户数据和运行产物，为后续 GDE Claw ZIP staging 复用边界

## 5. 验证

- [x] 5.1 重写 Python CLI、resolver、conversion 和执行协议测试，覆盖双 catalog、数据根优先级、冲突、只读内置任务及所有运行模式
- [x] 5.2 增加只读 Skill 语义测试，比较调用前后 Skill 文件树并确认 Midscene 输出环境指向本次外部 run
- [x] 5.3 运行 pytest、schema 漂移检查、TypeScript typecheck/test 和 Skill 安装验证
- [x] 5.4 全局检索并清除任务内 `reports`、`execution/reports`、静态 `midscene_run` 和用户侧 `--projects-root` 的旧契约，执行 OpenSpec 严格校验
