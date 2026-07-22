## 1. Python 工程与目录边界

- [x] 1.1 在 `execution` 初始化 uv/Python 工程、`cua` 包和 `tests/python`，配置中文友好的 CLI 入口与测试命令
- [x] 1.2 将 TypeScript Midscene 文件迁移到顶层 `execution/executors`，同步 executor 测试路径和 npm scripts
- [x] 1.3 建立 `domain`、`models`、`conversion`、`task`、`cli` 模块边界，确认 Python 核心不导入或启动 Midscene SDK

## 2. Python 模型与生成契约

- [x] 2.1 将 Midscene flow、route、timing、evidence 等落盘结构实现为严格 Pydantic 模型
- [x] 2.2 将 project、input binding、flow overrides、calibration proposal/history 和 resolved flow 实现为严格 Pydantic 模型
- [x] 2.3 将路径、解析选项、合并结果和校准验证结果实现为内部 Python 类型，并验证它们不进入公开 Schema
- [x] 2.4 实现确定性 JSON Schema 生成命令，生成并提交五类公开文件契约
- [x] 2.5 增加 Pydantic 与 JSON Schema 合法/非法 fixture 测试，并验证 Schema 重新生成无漂移

## 3. Trace 转换迁移

- [x] 3.1 将 input locate prompt 派生与测试迁移到 Python，保持现有中文 prompt 处理语义
- [x] 3.2 将 trace 到基础 Midscene flow 的转换逻辑迁移到 Python，并通过 Pydantic 模型输出 IR
- [x] 3.3 保持录制时间差、30 秒上限、operation route、source 和 evidence 的现有转换语义
- [x] 3.4 验证重复转换只覆盖基础 IR，不覆盖已有 project 配置和已确认校准
- [x] 3.5 使用 `air-tickets-demo` 对照迁移前后关键 IR 字段，并记录任何有意差异

## 4. 任务解析、校准与 CLI 迁移

- [x] 4.1 迁移项目路径发现、JSON 读取、基础 IR 指纹和 route/flow/config/override 验证
- [x] 4.2 迁移基础 IR、已确认校准和本次输入的确定性合并及 resolved flow 快照写入
- [x] 4.3 迁移稀疏 `--input`、`--inputs` 参数解析，覆盖未知参数、重复参数和默认值测试
- [x] 4.4 迁移 calibration proposal validate/apply/history，保持指纹、允许字段和 `--confirmed` 约束
- [x] 4.5 实现 `cua project`、`cua flow` 和 `cua calibration` 子命令及机器可读输出
- [x] 4.6 验证 pending proposal 不影响执行，inspect 与 run 使用同一 resolved flow 构建逻辑

## 5. Midscene 薄执行器与进程协议

- [x] 5.1 定义并测试 Python 到 Node 的 resolved flow 路径、退出码、执行结果和日志通道协议
- [x] 5.2 让 TypeScript executor 在创建 agent 前按生成契约验证 resolved flow，且不读取其他任务资产
- [x] 5.3 保留 `KeyboardTypeText`、route 映射、等待时序、报告目录和失败暴露行为
- [x] 5.4 实现 Python `flow run` 对 Node executor 的调用，并在 dry-run 中验证传入快照与 inspect 等价
- [x] 5.5 增加非法 resolved flow、非零退出码、非法执行结果和 step 失败测试，确认不存在旧 TS resolver 兜底

## 6. 清理与文档迁移

- [x] 6.1 删除已被 Python 替代的 TypeScript contracts、conversion、task 代码及其测试
- [x] 6.2 删除业务 npm scripts，只保留 Midscene executor 环境检查、类型检查、构建和测试入口
- [x] 6.3 更新根 README、`execution/README.md`、示例项目 README 和 AGENT 目录规范，准确描述 Python 主体与 TS 执行边界
- [x] 6.4 更新 `skills/cua-midscene` 的命令、任务契约和执行说明，并重新安装和校验本机 Skill 副本

## 7. 完整验证

- [x] 7.1 运行 Python 单元测试、Schema 漂移检查和 `air-tickets-demo` 转换/validate/inspect 测试
- [x] 7.2 运行 TypeScript 类型检查、键盘映射测试、resolved flow 契约测试和 flow dry-run
- [x] 7.3 验证现有项目资产无需人工改写即可执行新链路，运行产物不改写基础 IR、配置或校准文件
- [x] 7.4 扫描并删除文档与代码中的过时 npm 业务命令和旧 TypeScript 模块引用
- [x] 7.5 运行 Skill 校验与 OpenSpec 全量校验，并按功能域完成中文小步提交

## 8. 严格 operation 契约与执行器简化

- [x] 8.1 删除 trace 转换中的正则关键词路由、unknown operation 和 input locatePrompt 自动派生，缺失结构化 operation 时按 step fail fast
- [x] 8.2 从 flow 模型、Schema、示例资产和测试中删除 fallback 字段，确认执行链路不读取或生成动作兜底
- [x] 8.3 删除 resolved-flow TypeScript DTO 生成器、生成文件、npm 命令和依赖，保留 Ajv 运行时校验与执行器内部最小类型
- [x] 8.4 更新 Skill 与中文文档，明确 Agent 在任务创建时通过 project.json 声明参数、调用时只覆盖已声明输入
- [x] 8.5 全仓审计自动猜测、静默跳过和执行重试类兜底，补充失败用例并运行 Python、TypeScript、Schema、Skill 与 OpenSpec 验证
