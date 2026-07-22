# Record

本目录是 CUA 项目的录制处理域，当前保留 ShowUI-Aloha 中与教学录制处理相关的 Learn 能力，用于把录制资源转换为结构化操作日志和 trace。

在当前 CUA 项目中，ShowUI-Aloha 不作为最终执行器，也不承担回放流程。执行能力位于 `../execution`，当前底座是 Midscene computer use。

## 当前保留的能力

- 读取录制产生的视频和输入日志。
- 解析鼠标、键盘、窗口切换等原始事件。
- 从录制视频中抽取关键截图和局部 crop。
- 调用 OpenAI 兼容接口生成语义化 trace，并为每一步输出面向 Midscene 的最小 `operation` 动作结构；`LDoubleClick` 录制事件生成 `doubleClick`，input 操作需要同时输出完整动作 `prompt` 和只用于定位输入框的 `locatePrompt`。
- trace 生成 prompt 会约束 `operation.prompt` 按“目标视觉特征 + 所在区域 + 相对锚点 + 动作意图”组织，以提升弱视觉模型下 Midscene computer use 的定位稳定性；当前不新增额外 schema 字段。

## 已移除的能力

原上游项目中的 `Aloha_Act`、Actor、Executor、回放入口和执行演示视频已从本仓库删除。

后续如果需要执行 trace，应将 Learn 产物放入 `execution/projects/<scene>/<task>/source/`，首次初始化为任务 `task.yaml` 和 `task.json`，再交由 `execution` 的通用 runner 执行。

## 环境配置

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

`.env` 中配置 OpenAI 兼容接口：

```text
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
OPENAI_MODEL=minimax-m3
OPENAI_API_KEY=replace-me
OPENAI_VERIFY_SSL=true
ALOHA_TRACE_TEMPERATURE=0.2
```

真实 `.env` 不会提交到 git。

公司内网 OpenAI 兼容端点使用无法由本机信任链验证的证书时，可以临时设置：

```text
OPENAI_VERIFY_SSL=false
```

该配置只影响 trace 生成器的 OpenAI 兼容请求，并会关闭对应的证书告警。默认必须保持 `true`；如果公司能够提供 CA 证书，应优先通过 `REQUESTS_CA_BUNDLE=<CA 文件路径>` 建立信任链，而不是关闭验证。

## 运行 Learn 流程

安装依赖：

```powershell
uv sync
```

基于示例录制生成结构化日志和 trace：

```powershell
uv run python Aloha_Learn\parser.py Aloha_Learn\projects\air_tickets
```

生成物会落在对应 project 目录下，主要包括：

- `{project}_processed_log.json`
- `{project}_processed_log_sc.json`
- `{project}_trace.json`

这些产物当前用于分析和任务初始化，不作为最终执行入口。其中 trace 会包含面向 Midscene 的最小 `operation` 动作结构，后续由 `execution` 初始化任务根目录的 `task.yaml` 和 `task.json`。对于双击操作，trace 使用 `operation.type=doubleClick`；对于 input 操作，`operation.prompt` 表示完整输入动作，`operation.locatePrompt` 表示目标输入框，两者不能混用。

为了降低弱模型生成短 prompt 或歧义 prompt 的概率，`Aloha_Learn/default_prompt.json` 会要求模型为 Midscene prompt 提供足量定位信息：目标视觉特征、所在区域、相对锚点和动作意图。对于列表项、下拉候选、表格行、多个相似输入框等场景，prompt 应明确可见文本、所在容器和相对位置。
