## 1. 固化迁移基线

- [x] 1.1 为当前 scene/task 列表、describe、validate、inspect、dry-run 和非法参数输出建立不依赖 Python 实现细节的 CLI fixtures
- [x] 1.2 为 trace 转换后的 `task.yaml`、`task.json`、任务 Skill、resolved YAML 和 aiAct prompt 建立代表性 golden fixtures
- [x] 1.3 记录现有 JSON Schema 的有效与无效样例，并覆盖未知字段、错误类型、缺失字段和重复标识

## 2. 建立 TypeScript 工程与契约边界

- [x] 2.1 调整 `package.json`、TypeScript 配置和测试入口，直接声明 `@midscene/core`、YAML、Ajv 与 `ajv-formats` 依赖
- [x] 2.2 在 `cua/contracts` 定义精简 TypeScript 类型和持久化 JSON Schema 读取器，统一输出包含文件路径与字段路径的中文 Ajv 错误
- [x] 2.3 实现 trace、scene、task 和 execution result 的边界校验，并验证内部函数不会重复执行完整契约校验

## 3. 迁移任务数据与解析核心

- [x] 3.1 将数据根优先级、绝对路径约束、目录派生和写入检查迁移到 TypeScript
- [x] 3.2 将 builtin/user 双 catalog 发现、确定排序、来源标记和重复 scene/task 冲突迁移到 TypeScript
- [x] 3.3 将 YAML 读取写出、稳定 step 身份检查、`continueOnError` 禁止规则和 Midscene parser 最终校验迁移到 TypeScript
- [x] 3.4 将稀疏 `--input`/`--inputs` 解析、默认值合并、严格占位符替换和 resolved task 快照迁移到 TypeScript

## 4. 迁移 trace 转换与任务生成

- [x] 4.1 将结构化 trace operation 到 `aiTap`、`aiDoubleClick`、`KeyboardTypeText`、`KeyboardPress` 和 `aiWaitFor` 的确定性转换迁移到 TypeScript
- [x] 4.2 迁移录制时间间隔裁剪、稳定 step/input ID、整体目标和任务清单生成逻辑
- [x] 4.3 迁移场景与任务 `SKILL.md` 生成，并验证转换失败不会写出半成品资产
- [x] 4.4 使用 golden fixtures 对比 Python 与 TypeScript 转换结果，确认无关键词路由、猜测动作或兼容兜底

## 5. 迁移 aiAct 投影与 Midscene 直接执行

- [x] 5.1 将录制任务有序 aiAct prompt 和无录制 prompt 临时 YAML 生成迁移到 TypeScript
- [x] 5.2 将 YAML runner 重构为接收显式参数并返回结构化结果的可导入 API，复用现有 ComputerAgent 与 `KeyboardTypeText`
- [x] 5.3 实现本次绝对 run directory 设置和 `finally` 环境恢复，明确第一版实际 computer use 由上层串行调用且执行器不实现锁
- [x] 5.4 验证 dry-run 不创建设备或调用模型，实际失败不自动切换模式、不修改任务且始终销毁 Agent

## 6. 建立 Node.js CLI 与工具 API

- [x] 6.1 实现 scene、task 和 act 子命令，保持当前参数互斥、必填规则、退出码和 JSON 字段语义
- [x] 6.2 提供编译后的 package exports 与 `cua` bin，并配置开发期 `npm run cua -- ...` 入口
- [x] 6.3 确保 CLI 机器结果只写 stdout、诊断只写 stderr，Midscene 日志不会破坏 JSON 输出
- [x] 6.4 导出供 GDE Claw 直接调用的任务发现、初始化、inspect、逐 task 执行和 aiAct API，并验证其不启动子进程

## 7. 删除 Python 与更新发布单元

- [x] 7.1 在 TypeScript 行为测试通过后删除 `execution/cua` 下全部 Python 文件和 `tests/python`
- [x] 7.2 删除 `pyproject.toml`、`uv.lock`、Pydantic/PyYAML/pytest 命令及 Python 到 Node.js 执行协议
- [x] 7.3 更新 Skill 安装脚本与 staging 校验，使发布物只包含 TypeScript 源码或编译产物、契约、references 和只读内置任务
- [x] 7.4 更新根 README、execution README、AGENT、Skill 和任务契约，删除 `uv run cua`、Python 核心和子进程边界等过时说明

## 8. 完整验证与收尾

- [x] 8.1 运行 TypeScript 类型检查、契约测试、转换测试、CLI 测试、runner/customAction 测试和 Skill 包测试
- [x] 8.2 对内置 `air-tickets-demo` 完成 init/validate/inspect/task dry-run/act dry-run 链路验证，确认任务资产与目录结构不变
- [x] 8.3 安装本机 `cua-midscene` Skill 副本并验证其命令、references、内置任务和发布排除项
- [x] 8.4 严格验证 OpenSpec change，检索并清除 Python、Pydantic、uv、子进程 runner 和旧命令的代码与文档残留
- [x] 8.5 审查 trace 转换、任务解析和执行编排主路径的调用深度，内联无独立语义的单次使用包装函数，并检查超过约 200 行的函数是否确有保持完整控制流的理由
