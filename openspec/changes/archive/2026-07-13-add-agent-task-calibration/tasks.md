## 1. 任务契约与解析

- [x] 1.1 定义项目配置、flow overrides、校准 proposal、resolved flow 来源摘要的 TypeScript 类型
- [x] 1.2 实现项目文件读取、基础 IR 指纹、结构验证和确定性合并
- [x] 1.3 实现重复 `--input` 与 `--inputs` 文件解析、默认值和稀疏覆盖
- [x] 1.4 增加 resolver 单元测试，覆盖未知参数、失效 step、非法 route 和过期指纹
- [x] 1.5 将 flow 生产代码按 contracts、conversion、task、execution 拆分，并把测试迁移到顶层 tests 目录

## 2. Converter 与项目迁移

- [x] 2.1 修改 converter，在项目配置不存在时从 input routes 初始化输入定义且不覆盖已有配置
- [x] 2.2 为 `air-tickets-demo` 建立 config、calibration、generated、reports 目录契约和示例配置
- [x] 2.3 验证重新转换基础 IR 不会覆盖任务配置或校准

## 3. 通用 CLI 与 runner

- [x] 3.1 实现 `project:list`、`flow:validate` 和 `flow:inspect` 命令及 JSON 输出
- [x] 3.2 实现 `calibration:validate` 和 `calibration:apply`，应用后更新 overrides 并归档 proposal
- [x] 3.3 修改 `flow:run` 使用共享 resolver、支持输入参数并保存 resolved flow 快照
- [x] 3.4 更新 npm scripts 并验证 inspect 与 run 构建相同 resolved flow

## 4. Agent Skill 与文档

- [x] 4.1 使用 skill-creator 模板初始化并编写仓库内 `cua-midscene` Skill、界面元数据和任务契约 reference
- [x] 4.2 提供可重复的本机 Skill 安装方式，并确保安装副本不纳入 Git
- [x] 4.3 更新根 README、execution README、样例 README 和 AGENT.md，准确说明当前任务包、校准审批与参数调用方式

## 5. 完整验证与提交

- [x] 5.1 运行 typecheck、现有键盘/输入定位测试和新增任务解析测试
- [x] 5.2 运行 air-tickets-demo 的 convert、validate、inspect 和 dry-run 验证
- [x] 5.3 运行 Skill 校验和 OpenSpec 全量校验
- [x] 5.4 按任务契约、CLI、Skill/文档拆分中文小步提交并推送
