## 1. 整体 prompt 投影

- [x] 1.1 新增 resolved task YAML 到有序中文 aiAct prompt 的确定性渲染器
- [x] 1.2 覆盖受支持动作、参数值、步骤顺序、忽略 sleep 和未知动作失败测试

## 2. CLI 与执行编排

- [x] 2.1 恢复 `act run --scene/--task`、稀疏输入和互斥来源校验
- [x] 2.2 在任务报告目录保存 resolved YAML、prompt、临时 aiAct YAML并复用统一 runner
- [x] 2.3 验证 dry-run 不创建设备，执行失败不切换模式或修改任务

## 3. Skill、文档与验证

- [x] 3.1 更新根 README、execution README、执行器 Skill 与任务契约中的三种显式模式
- [x] 3.2 运行 Python、TypeScript、Schema、Skill 与 OpenSpec 验证并重新安装本机 Skill
- [x] 3.3 全局检查不存在旧 flow、专用 TS aiAct runner、fallback 或自动切换实现，完成中文小步提交
