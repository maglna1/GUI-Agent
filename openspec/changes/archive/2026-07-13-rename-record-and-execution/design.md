## Context

仓库当前使用 `showui-aloha/` 表示录制处理侧，使用 `CUA_midscene/` 表示转换、任务、项目资产和执行侧。前者暴露了上游实现来源，后者把整个执行域绑定到 Midscene。当前执行侧已经包含通用任务契约、校准、参数解析和项目资产，不再只是一个 Midscene 实验目录。

## Goals / Non-Goals

**Goals:**

- 用 `record/` 表达教学录制处理职责。
- 用 `execution/` 表达可扩展的任务执行职责。
- 保持 `execution/projects/` 作为业务任务执行资产目录。
- 将 Midscene 专属代码集中到 `execution/src/executors/`，同时保持 contracts、conversion 和 task 的技术中立性。
- 更新所有当前有效路径引用并保持命令可运行。

**Non-Goals:**

- 不改变 JSON schema、CLI 名称或 npm package name。
- 不引入第二种执行器。
- 不改写 archived OpenSpec change 的历史记录。
- 不重命名 `cua-midscene` Skill；它仍表示当前可调用的 Midscene 执行能力。

## Decisions

### Decision: 顶层使用职责名

`showui-aloha/` 重命名为 `record/`，`CUA_midscene/` 重命名为 `execution/`。相比 `replay`，`execution` 能覆盖录制任务执行、人工校准、参数化调用、未来固化脚本和不同执行器。

### Decision: Midscene 代码直接放入 executors

现有 `src/flow/execution/` 移动为 `src/executors/`，不增加 `src/executors/midscene/`。当前只有 Midscene 一种执行器，增加单一技术子层只会制造无效嵌套；未来出现第二种执行器时再按实际共享边界拆分。

对应测试从 `tests/flow/execution/` 移动到 `tests/executors/`。`src/flow/contracts`、`src/flow/conversion` 和 `src/flow/task` 保持不变，因为它们描述任务契约和通用解析链路。

### Decision: 历史文档不改写

README、Skill、代码、主规格和活跃 change 使用新路径。`openspec/changes/archive/` 中的旧路径是当时设计事实，保留原样。

## Risks / Trade-offs

- **外部脚本仍使用旧工作目录** → README 和 Skill 明确新命令目录；仓库内不保留旧目录兼容链接，避免两套名称长期并存。
- **批量重命名遗漏字符串引用** → 使用全仓 `rg` 排除 `.git`、依赖和 archived changes 后检查旧路径，并运行两侧完整测试。
- **Skill 安装副本仍引用旧路径** → 更新仓库 Skill 后重新运行安装脚本并校验副本。

## Migration Plan

1. 使用 Git 可识别的目录移动重命名两个顶层目录。
2. 移动 executor 代码和测试，更新 package scripts 与相对 import。
3. 更新代码默认命令、README、Skill、AGENT、主规格和活跃 change。
4. 运行 record 测试、execution 类型检查/测试/任务 dry-run、Skill 和 OpenSpec 校验。
5. 按目录迁移与文档规格拆分提交并推送。

## Open Questions

无。
