# CUA Midscene 任务与执行契约

## 目录

```text
<skill-root>/projects/<scene>/       # 只读 builtin catalog
├── scene.json
├── SKILL.md
└── <task>/
    ├── task.yaml
    ├── task.json
    ├── SKILL.md
    └── source/

<CUA_DATA_ROOT>/
├── projects/<scene>/<task>/        # 可写 user catalog
├── cache/
└── runs/<run-id>/
    ├── resolved-task.yaml
    ├── execution-result.json
    └── midscene/
```

`task.yaml` 是唯一长期可执行流程，直接遵循 Midscene YAML。`task.json` 保存元数据、trace 来源、输入 ID、中文说明和录制默认值。`source/` 是只读证据。`resolved-task.yaml` 是本次输入解析后的运行快照，不是另一份长期流程。

## 命令

安装后的 Skill 从根目录运行：

```powershell
node dist/cua/cli/main.js scene list --json
node dist/cua/cli/main.js task list --scene <scene> --json
node dist/cua/cli/main.js task describe --scene <scene> --task <task> --json
node dist/cua/cli/main.js task init-from-trace --scene <scene> --task <task> --goal "<目标>"
node dist/cua/cli/main.js task validate --scene <scene> --task <task>
node dist/cua/cli/main.js task inspect --scene <scene> --task <task> --input <input-id>=<value>
node dist/cua/cli/main.js task run --scene <scene> --task <task> --dry-run
node dist/cua/cli/main.js task run --scene <scene> --task <task>
node dist/cua/cli/main.js act run --scene <scene> --task <task> --input <input-id>=<value>
node dist/cua/cli/main.js act run --prompt "打开 Chrome 并搜索 GUI agent"
```

源码开发入口是对应的 `npm run cua -- ...`。`--input` 可以重复；`--inputs` 必须是字符串值 JSON 对象，两种来源不得重复同一 ID。

## 输入契约

```json
{
  "schemaVersion": "0.2",
  "scene": "browser-demo",
  "task": "air-tickets-demo",
  "title": "Qatar Airways 航班搜索",
  "description": "设置单程航班搜索条件",
  "goal": "完成单程航班搜索",
  "source": {
    "tracePath": "source/showui-trace.json",
    "processedLogPath": "source/processed-log-sc.json",
    "conversionCommand": "node dist/cua/cli/main.js task init-from-trace ..."
  },
  "inputs": {
    "step-002-input": {
      "type": "string",
      "label": "Chrome 地址栏/搜索栏",
      "description": "在地址栏输入搜索词",
      "default": "QATAR AIRWAYS"
    }
  }
}
```

对应 YAML 使用显式占位符：

```yaml
computer: {}
agent:
  groupName: air-tickets-demo
  groupDescription: 完成单程航班搜索
  generateReport: true
tasks:
  - name: step-001 | click
    flow:
      - aiTap: 点击 Chrome 浏览器顶部的地址栏/搜索栏区域以聚焦输入框
  - name: step-002 | input
    flow:
      - sleep: 4101
      - KeyboardTypeText:
          locate: Chrome 地址栏/搜索栏
          value: '{{step-002-input}}'
          mode: replace
  - name: step-003 | keyboard
    flow:
      - KeyboardPress:
          keyName: Enter
  - name: step-004 | doubleClick
    flow:
      - aiDoubleClick: 双击页面中部文件列表里名称为 report.xlsx 的文件行
```

调用只能覆盖已声明 ID。未提供输入使用 `default`；未知、重复、非字符串、未声明、未使用或格式错误的占位符都会在启动 Midscene 前失败。

每个 trace step 对应一个 `step-NNN | <operation-type>` task。step 必须为正整数、唯一并严格递增。click、doubleClick、input、keyboard、wait 分别映射为 `aiTap`、`aiDoubleClick`、`KeyboardTypeText`、`KeyboardPress`、`aiWaitFor`。转换器只读取 `caption.operation` 和 processed log 时间，不从其他文本猜测动作。

## 校准与重建

Agent 校准时必须展示 YAML 位置、原值、新值和原因，等待用户确认后只修改 user catalog 的 `task.yaml` 并运行 `task validate`。builtin 任务、`source/` 和运行产物只读。

长期改变输入默认值、标签或说明属于参数契约修改，必须单独展示 `task.json` 差异并确认。重新生成 trace 属于重建，不是校准；已有任务资产不得自动删除或覆盖。

## 执行边界

TypeScript resolver 写入 `<CUA_DATA_ROOT>/runs/<run-id>/resolved-task.yaml`，随后同进程调用共享 Midscene YAML API。执行器注册 `KeyboardTypeText`、创建 ComputerAgent、调用 `agent.runYaml()`，将结果写入 `execution-result.json`，并把 Midscene 报告定向到 `<run-dir>/midscene`。

`act run --scene/--task` 从相同 resolved YAML 生成 `ai-act-prompt.txt` 和单 `ai` action 的 `ai-act-task.yaml`；sleep 不进入 prompt，未知 action 在创建设备前失败。`act run --prompt` 不读取任务资产。

`task inspect` 不创建 run。`task validate` 和 `--dry-run` 会生成运行投影并经过 Midscene parser，但不调用模型、不创建设备、不验证页面定位，因此不是模拟执行。

第一版不实现并发锁，上层调用方必须串行发起真实 computer use。失败必须原样暴露，不自动切换模式、修改任务、重试或改用剪贴板 Input。
