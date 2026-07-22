## 1. Python YAML 任务核心

- [x] 1.1 引入 YAML 依赖并用精简 Pydantic 模型重建任务清单、输入和统一执行结果契约
- [x] 1.2 实现 Midscene YAML 的结构化读取、严格占位符解析和 resolved task 快照
- [x] 1.3 将 ShowUI trace operation 直接转换为 Midscene YAML action 和 trace 输入定义
- [x] 1.4 重新生成 air-tickets-demo 的 `task.yaml` 与 `task.json` 并删除旧 flow 资产

## 2. Midscene YAML 执行适配器

- [x] 2.1 实现单一 `run-midscene-yaml.ts` 的 dry-run、runYaml 执行和结果落盘
- [x] 2.2 保留并验证 `KeyboardTypeText` customAction 的 YAML 调用与无剪贴板 ASCII 输入
- [x] 2.3 删除 route runner、resolved-flow 契约、录制任务 aiAct prompt 组合器和对应无用依赖

## 3. CLI 与任务调用

- [x] 3.1 将录制任务命令收敛为 `task init-from-trace/validate/inspect/run`
- [x] 3.2 将 `act run` 收敛为无录制 prompt 生成临时 YAML并复用统一 runner
- [x] 3.3 更新任务发现、报告目录和失败协议，确认不存在兼容读取、自动切换或 fallback

## 4. 测试、Skill 与文档

- [x] 4.1 重写 Python converter、resolver、CLI 和执行协议测试并删除旧 flow 测试
- [x] 4.2 重写 TypeScript YAML runner 与 KeyboardTypeText 测试并运行类型检查
- [x] 4.3 更新根 README、execution README、AGENT.md、Skill 与任务契约，删除过时描述
- [x] 4.4 重新安装并验证本机 `cua-midscene` Skill，运行 Schema 漂移与 OpenSpec 严格校验
- [x] 4.5 全局检索并清除旧 flow、route、resolved-flow、fallback 和任务型 aiAct 实现，按阶段完成中文小步提交

## 5. 保留录制步骤身份

- [x] 5.1 更新 converter 与录制任务校验，使每个 trace step 生成一个带稳定名称的 Midscene task
- [x] 5.2 将输入 ID 改为由 trace step ID 派生，并重新生成 air-tickets-demo
- [x] 5.3 更新 Python 测试、文档与 Skill，覆盖步骤顺序、唯一性、输入解析和整体目标
- [x] 5.4 运行 Python、TypeScript、Skill 与 OpenSpec 验证，完成中文小步提交
