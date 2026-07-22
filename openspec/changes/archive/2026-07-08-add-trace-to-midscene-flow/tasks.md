## 1. 项目目录与样例资产

- [x] 1.1 在 `CUA_midscene/projects/<project-name>/` 下建立 source、ir、generated、reports 的项目产物目录约定
- [x] 1.2 创建第一个样例项目目录，并放置或引用 ShowUI-Aloha air-ticket 示例 trace、processed log 和截图资源
- [x] 1.3 为样例项目补充 README，说明 source、IR、生成产物和报告的职责边界

## 2. Midscene Flow IR 定义

- [x] 2.1 在 `CUA_midscene/src/` 中定义 `midscene-flow.json` 对应的 TypeScript 类型
- [x] 2.2 定义 flow 顶层字段：`schemaVersion`、`project`、`goal`、`source`、`steps`
- [x] 2.3 定义 step 字段：稳定 `id`、源 trace 引用、intent、evidence、route、fallback
- [x] 2.4 定义受支持 route strategy：`keyboard`、`input`、`tap`、`act`、`wait`、`manual-review`

## 3. Trace 到 Flow 的 Converter

- [x] 3.1 新增 converter 入口，读取 ShowUI-Aloha trace 并输出项目级 `ir/midscene-flow.json`
- [x] 3.2 将 trace caption 中的 observation、think、action、expectation 映射到 flow step 的 intent 和 evidence
- [x] 3.3 实现第一版保守路由规则，将明确 typing、click、wait 等行为映射到对应 route strategy
- [x] 3.4 对无法确定的步骤输出 `manual-review`，并保留原始 trace 证据
- [x] 3.5 在转换前校验 source artifact 路径存在，失败时给出清晰错误

## 4. 通用 Midscene Runner

- [x] 4.1 新增 runner 入口，读取 `midscene-flow.json` 并初始化 Midscene computer use agent
- [x] 4.2 实现 `keyboard`、`input`、`tap`、`act`、`wait` strategy 到 Midscene 操作的映射
- [x] 4.3 遇到 `manual-review` 或不受支持 strategy 时 fail fast，并输出 step id 与原因
- [x] 4.4 将 Midscene report 归档到项目级 reports 或已配置 run directory

## 5. 验证与文档

- [x] 5.1 为 converter 增加最小验证，确认样例 trace 可以生成符合结构的 `midscene-flow.json`
- [x] 5.2 为 runner 增加最小验证，确认不受支持 strategy 会清晰失败
- [x] 5.3 更新根 README 和 `CUA_midscene/README.md`，说明 ShowUI-Aloha、Midscene converter、runner 和项目产物目录的关系
- [x] 5.4 运行 TypeScript 类型检查，确认新增代码通过 `npm run typecheck`

## 6. 中文 Trace 生成约束

- [x] 6.1 更新 ShowUI-Aloha Learn 默认 prompt，要求 trace caption 字段值使用中文
- [x] 6.2 更新 trace 生成时的最终提示，保持 JSON 字段名不变但要求字段值中文化
- [x] 6.3 验证 prompt JSON 可解析，并确认 Python trace generator 语法检查通过

## 7. 生成命令与模型使用记录

- [x] 7.1 在 Midscene flow 类型中记录生成命令和各阶段模型使用情况
- [x] 7.2 在 converter 输出的 `midscene-flow.json` 中写入 trace 生成、flow 转换和 flow 执行命令
- [x] 7.3 在项目 README 中说明 trace 生成使用模型、flow 转换不使用模型、runner 执行使用 Midscene 视觉模型
- [x] 7.4 将命令记录改为分阶段语义，明确转换命令和执行命令的职责边界
- [x] 7.5 从核心 IR 类型和 `midscene-flow.json` 中移除模型使用字段，仅在文档中说明模型使用边界

## 8. 目录清理

- [x] 8.1 删除早期未按当前结构组织的 `google-search.ts` 与 `aloha-air-tickets.ts`
- [x] 8.2 清理 `package.json` 中对应的 `google` 与 `aloha:air` 脚本入口
- [x] 8.3 更新 README 与 OpenSpec design，移除旧实验脚本引用
- [x] 8.4 移除 `.env.example` 中已无对应脚本使用的 `GOOGLE_SEARCH_QUERY`

## 9. 通用命令体系

- [x] 9.1 将 Midscene npm scripts 改为 `flow:convert` 和 `flow:run` 参数驱动入口
- [x] 9.2 更新 flow 命令元数据，记录带 `--project` 的转换与执行命令
- [x] 9.3 更新所有 README，说明新项目通过替换 `--project <project-name>` 复用同一套命令

## 10. 录制键盘输入解析

- [x] 10.1 修复 ShowUI-Aloha Learn 对 `NUMPAD_0` 至 `NUMPAD_9` 的解析，确保小键盘数字合并为 `Type` 动作
- [x] 10.2 增加回归测试，覆盖网管录制中通过小键盘输入 `47405` 的场景
