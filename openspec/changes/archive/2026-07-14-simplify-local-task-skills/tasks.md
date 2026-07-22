## 1. 契约与模型

- [x] 1.1 将持久化模型调整为 scene、task、canonical flow 和 resolved flow，删除 calibration 与 overrides 模型
- [x] 1.2 让任务输入只保存字段绑定，并使 canonical flow 成为未覆盖输入的唯一默认值来源
- [x] 1.3 更新并验证四类 JSON Schema，删除过时 Schema

## 2. Python 任务核心

- [x] 2.1 将路径与发现逻辑调整为 `projects/<scene>/<task>`，实现 scene list、task list 和 task describe
- [x] 2.2 简化 resolver，仅验证 canonical flow 并应用本次稀疏输入
- [x] 2.3 调整 trace converter 为首次初始化语义，已有 flow 时直接失败
- [x] 2.4 更新 Python CLI，新增 scene/task 命令并删除 project/calibration 命令

## 3. Midscene 执行边界

- [x] 3.1 更新 resolved flow 与 TypeScript 执行结果中的 scene/task 标识
- [x] 3.2 验证 TypeScript runner 只消费 resolved flow，且现有键盘输入和失败暴露行为保持不变

## 4. 示例资产与 Skill

- [x] 4.1 将 `air-tickets-demo` 迁移到 `browser-demo` 场景，保留任务 source 并删除旧校准、配置和生成目录
- [x] 4.2 增加场景 Skill 与任务 Skill，更新执行器 Skill 的发现、修改确认和调用规则
- [x] 4.3 更新 Skill 安装方式并同步本机安装副本

## 5. 文档与验证

- [x] 5.1 更新根 README、execution README、record README、示例文档和 AGENT.md 中的目录与命令
- [x] 5.2 更新 Python 与 TypeScript 测试，覆盖唯一默认值、直接编辑、初始化防覆盖和 scene/task CLI
- [x] 5.3 运行 Python、TypeScript、record、Skill 与 OpenSpec 全量验证并修复发现的问题
- [x] 5.4 按实现阶段完成中文小步提交并确认工作区仅保留无关用户文件
