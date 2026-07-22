## MODIFIED Requirements

### Requirement: aiAct dry-run 与报告可诊断
系统 SHALL 在统一外部 run directory 保存本次 resolved YAML、最终 prompt、临时 aiAct YAML、统一执行结果和 Midscene 原生输出，并在 dry-run 中完成全部静态验证。

#### Scenario: 录制任务 dry-run
- **WHEN** 调用方对录制任务提供 `--dry-run`
- **THEN** 系统 SHALL 在 `<data-root>/runs/<run-id>/` 生成并保存全部运行时投影文件
- **AND** runner SHALL 解析临时 YAML 但不得初始化 ComputerAgent 或调用模型
- **AND** 系统 SHALL NOT 在任务目录创建 reports

#### Scenario: 自然语言 aiAct
- **WHEN** 调用方执行无录制自然语言要求
- **THEN** 系统 SHALL 在同一 runs root 创建独立 run directory
- **AND** 系统 SHALL NOT 在 Skill 根目录创建 execution reports

#### Scenario: 执行失败
- **WHEN** prompt 组合、YAML runner 或 aiAct 执行失败
- **THEN** 系统 SHALL 在可用时保留本次 run directory 中的诊断产物或暴露原始错误并以非成功状态结束
- **AND** 系统 SHALL NOT 自动修改任务或切换执行模式
