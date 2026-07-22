## 1. 顶层目录迁移

- [x] 1.1 将 `showui-aloha/` 重命名为 `record/`
- [x] 1.2 将 `CUA_midscene/` 重命名为 `execution/`
- [x] 1.3 更新忽略规则、项目配置和代码中的跨目录默认路径

## 2. 执行器代码组织

- [x] 2.1 将 `execution/src/flow/execution/` 移动为 `execution/src/executors/` 并修正 import
- [x] 2.2 将执行器测试移动为 `execution/tests/executors/` 并更新 npm scripts
- [x] 2.3 运行 execution 类型检查和全部测试

## 3. 文档、Skill 与规格

- [x] 3.1 更新根 README、AGENT、record README、execution README 和项目 README
- [x] 3.2 更新 `cua-midscene` Skill、任务契约和本机安装副本
- [x] 3.3 更新主规格和当前活跃 OpenSpec change 中的有效路径，不改写 archive 历史

## 4. 验证与提交

- [x] 4.1 验证旧目录和非历史旧路径引用已经清除
- [x] 4.2 运行 record 测试、execution convert/validate/inspect/dry-run、Skill 与 OpenSpec 校验
- [x] 4.3 按目录迁移和文档规格拆分中文小步提交并推送
