## MODIFIED Requirements

### Requirement: Midscene 输出绑定本次运行
TypeScript 执行编排 SHALL 为每次调用显式提供绝对 run directory，并在本次执行结束后恢复进程原有的 Midscene 报告目录配置。

#### Scenario: 实际运行生成 Midscene 报告
- **WHEN** Midscene runner 创建报告、截图或日志
- **THEN** 这些文件 SHALL 位于 `<run-dir>/midscene/`
- **AND** 静态环境文件中的同名配置 SHALL NOT 将其重定向到共享 Skill 目录

#### Scenario: 执行结束或失败
- **WHEN** Midscene 实际执行成功、失败或抛出异常
- **THEN** 执行器 SHALL 销毁本次 Agent
- **AND** 执行器 SHALL 在 `finally` 中恢复调用前的环境值
