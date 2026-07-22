## MODIFIED Requirements

### Requirement: execution 发布单元只包含当前实现
execution Skill 安装包 SHALL 包含 TypeScript 核心、Midscene YAML runner、只读内置项目任务、引用文档、编译运行入口和必要契约，不得包含 Python 环境、用户任务、运行时可变数据或已删除架构的代码与说明。

#### Scenario: 安装 Skill
- **WHEN** 执行可重复安装或 staging 命令
- **THEN** 本机 Skill 副本 SHALL 与明确的当前发布文件集合一致
- **AND** 安装包 SHALL NOT 包含 Python 源码与锁文件、node_modules、用户 data root、reports、midscene_run、缓存、真实环境文件、测试或旧 flow 文件
