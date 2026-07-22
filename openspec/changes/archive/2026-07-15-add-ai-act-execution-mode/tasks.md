## 1. TypeScript 执行边界

- [x] 1.1 抽取 resolved flow Ajv 读取校验组件并让现有 flow runner 复用
- [x] 1.2 抽取 KeyboardTypeText 注册和 keyboardPress 绑定组件并让现有 flow runner 复用
- [x] 1.3 实现录制任务 aiAct prompt 的确定性组合与单元测试
- [x] 1.4 实现 `run-midscene-ai-act.ts` 的互斥输入、dry-run、执行和结果落盘
- [x] 1.5 增加 aiAct TypeScript 契约测试并确认 dry-run 不初始化设备

## 2. Python CLI 与持久化契约

- [x] 2.1 新增 `AiActExecutorResult` Pydantic 模型并生成 JSON Schema
- [x] 2.2 实现自然语言和任务两种 aiAct 子进程调用及报告目录规则
- [x] 2.3 新增 `cua act run` CLI、互斥参数校验和机器可读输出
- [x] 2.4 增加 Python 模型、协议、resolver 复用和 CLI 失败测试

## 3. Agent Skill 与文档

- [x] 3.1 更新执行器 Skill 和任务契约，说明三种显式调用模式及禁止自动切换
- [x] 3.2 更新根 README、execution README、命令示例和结果契约说明
- [x] 3.3 重新安装并验证本机 `cua-midscene` Skill 副本
- [x] 3.4 将 `execution/` 调整为完整 Skill 发布单元并验证安装包内容

## 4. 综合验证

- [x] 4.1 运行 Python 测试、TypeScript 类型检查和全部 executor 测试
- [x] 4.2 运行 Schema 漂移、Skill 和 OpenSpec 严格校验
- [x] 4.3 确认未自动执行真实桌面 smoke test且工作区不包含无关改动
