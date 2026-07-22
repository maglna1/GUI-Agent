import { mkdir, open, stat } from 'node:fs/promises';
import path from 'node:path';
import type {
  JsonObject,
  ProcessedLogStep,
  SceneManifest,
  ShowuiTrace,
  ShowuiTraceOperation,
  TaskCatalogRoots,
  TaskInputDefinition,
  TaskManifest,
} from '../contracts/types.js';
import {
  readProcessedLog,
  readSceneManifest,
  readShowuiTrace,
  writeJsonFile,
} from '../contracts/validation.js';
import { requireIdentifier } from '../task/tasks.js';
import { writeYamlDocument } from '../task/yaml-task.js';

export const minRecordedWaitMs = 200;
export const maxRecordedWaitMs = 30_000;

export interface ConvertOptions {
  scene: string;
  task: string;
  goal: string;
  catalog: TaskCatalogRoots;
  conversionCommand: string;
  recordingPreparationCommand?: string;
  traceGenerationCommand?: string;
}

async function pathExists(sourcePath: string): Promise<boolean> {
  try {
    await stat(sourcePath);
    return true;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return false;
    throw error;
  }
}

async function writeTextIfMissing(sourcePath: string, content: string): Promise<void> {
  await mkdir(path.dirname(sourcePath), { recursive: true });
  try {
    const file = await open(sourcePath, 'wx');
    try {
      await file.writeFile(content, 'utf8');
    } finally {
      await file.close();
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
  }
}

export function sceneSkillContent(scene: string): string {
  return `---
name: ${scene}
description: 发现和调用 ${scene} 场景中的本地 CUA 任务。
---

# ${scene} 场景

运行 \`npm run cua -- task list --scene ${scene} --json\` 发现任务，再按需读取目标任务的 \`SKILL.md\`、\`task.json\` 和 \`task.yaml\`。
`;
}

export function taskSkillContent(scene: string, task: string): string {
  return `---
name: ${task}
description: 调用和维护 ${scene}/${task} 本地 CUA 任务。
---

# ${task} 任务

本文件属于 Executor 管理的用户任务数据包，不作为独立 GDE Claw Skill 注册。使用 \`npm run cua -- task describe --scene ${scene} --task ${task} --json\` 读取输入定义和 \`origin\`、\`writable\`。

本任务的执行流程是 \`task.yaml\`，输入契约是 \`task.json\`，\`source/\` 是只读录制证据。调用、校准和执行模式遵循执行器根 \`SKILL.md\`；本文件只提供任务特有信息，不覆盖根 Skill 的确认与只读规则。
`;
}

function requiredOperationText(value: string | null | undefined, field: string, step: number): string {
  const normalized = value?.trim() ?? '';
  if (!normalized) throw new Error(`trace step ${step} 的 operation.${field} 不能为空`);
  return normalized;
}

export function clampRecordedWaitMs(recordedGapMs: number): number {
  if (recordedGapMs < minRecordedWaitMs) return 0;
  return Math.min(recordedGapMs, maxRecordedWaitMs);
}

function actionFromOperation(
  operation: ShowuiTraceOperation,
  step: number,
): { action: JsonObject; input?: [string, TaskInputDefinition] } {
  if (operation.type === 'click' || operation.type === 'doubleClick') {
    const prompt = requiredOperationText(operation.prompt, 'prompt', step);
    return { action: { [operation.type === 'click' ? 'aiTap' : 'aiDoubleClick']: prompt } };
  }
  if (operation.type === 'input') {
    const prompt = requiredOperationText(operation.prompt, 'prompt', step);
    const locate = requiredOperationText(operation.locatePrompt, 'locatePrompt', step);
    const value = requiredOperationText(operation.value, 'value', step);
    const inputId = `step-${String(step).padStart(3, '0')}-input`;
    return {
      action: {
        KeyboardTypeText: { locate, value: `{{${inputId}}}`, mode: 'replace' },
      },
      input: [inputId, { type: 'string', label: locate, description: prompt, default: value }],
    };
  }
  if (operation.type === 'keyboard') {
    return { action: { KeyboardPress: { keyName: requiredOperationText(operation.key, 'key', step) } } };
  }
  const condition = requiredOperationText(operation.condition, 'condition', step);
  return {
    action: {
      aiWaitFor: operation.prompt?.trim() || condition,
      timeout: 15_000,
    },
  };
}

export function buildTaskAssets(
  trace: ShowuiTrace,
  processedSteps: ProcessedLogStep[],
  options: ConvertOptions,
): { document: JsonObject; manifest: TaskManifest } {
  if (!trace.trajectory.length) throw new Error('trace trajectory 不能为空');
  if (trace.trajectory.length !== processedSteps.length) {
    throw new Error(`trace step 数量 ${trace.trajectory.length} 与 processed log 数量 ${processedSteps.length} 不一致`);
  }
  const tasks: JsonObject[] = [];
  const inputs: Record<string, TaskInputDefinition> = {};
  let previousTimestamp: number | undefined;
  let previousStep = 0;

  trace.trajectory.forEach((traceStep, index) => {
    const step = traceStep.step_idx;
    if (step <= previousStep) throw new Error('trace step_idx 必须为正整数、唯一且按轨迹顺序严格递增');
    const flow: JsonObject[] = [];
    if (previousTimestamp !== undefined) {
      const gap = Math.max(0, Math.floor((processedSteps[index].timestamp - previousTimestamp) * 1000 + 0.5));
      const wait = clampRecordedWaitMs(gap);
      if (wait) flow.push({ sleep: wait });
    }
    const mapped = actionFromOperation(traceStep.caption.operation, step);
    flow.push(mapped.action);
    tasks.push({ name: `step-${String(step).padStart(3, '0')} | ${traceStep.caption.operation.type}`, flow });
    if (mapped.input) inputs[mapped.input[0]] = mapped.input[1];
    previousTimestamp = processedSteps[index].timestamp;
    previousStep = step;
  });

  return {
    document: {
      computer: {},
      agent: { groupName: options.task, groupDescription: options.goal, generateReport: true },
      tasks,
    },
    manifest: {
      schemaVersion: '0.2',
      scene: options.scene,
      task: options.task,
      title: options.task,
      description: options.goal,
      goal: options.goal,
      source: {
        tracePath: 'source/showui-trace.json',
        processedLogPath: 'source/processed-log-sc.json',
        conversionCommand: options.conversionCommand,
        ...(options.recordingPreparationCommand
          ? { recordingPreparationCommand: options.recordingPreparationCommand }
          : {}),
        ...(options.traceGenerationCommand ? { traceGenerationCommand: options.traceGenerationCommand } : {}),
      },
      inputs,
    },
  };
}

export async function convertTrace(options: ConvertOptions): Promise<string> {
  if (!options.catalog.userProjectsRoot) throw new Error('初始化任务需要用户 projects 目录');
  const scene = requireIdentifier(options.scene, 'scene');
  const task = requireIdentifier(options.task, 'task');
  if (!options.goal.trim()) throw new Error('goal 必须是非空字符串');
  const userProjects = path.resolve(options.catalog.userProjectsRoot);
  const taskRoot = path.resolve(userProjects, scene, task);
  const builtinTask = path.resolve(options.catalog.builtinProjectsRoot, scene, task);
  if (await pathExists(path.join(builtinTask, 'task.json'))) throw new Error(`内置任务不可覆盖：${builtinTask}`);

  const taskYamlPath = path.join(taskRoot, 'task.yaml');
  const taskManifestPath = path.join(taskRoot, 'task.json');
  const existing: string[] = [];
  for (const candidate of [taskYamlPath, taskManifestPath]) if (await pathExists(candidate)) existing.push(candidate);
  if (existing.length) throw new Error(`任务资产已存在，拒绝覆盖：${existing.join(', ')}`);

  const sourceRoot = path.join(taskRoot, 'source');
  const [trace, processedSteps] = await Promise.all([
    readShowuiTrace(path.join(sourceRoot, 'showui-trace.json')),
    readProcessedLog(path.join(sourceRoot, 'processed-log-sc.json')),
  ]);
  const assets = buildTaskAssets(trace, processedSteps, options);
  const builtinScenePath = path.join(options.catalog.builtinProjectsRoot, scene, 'scene.json');
  const sceneManifest: SceneManifest = (await pathExists(builtinScenePath))
    ? await readSceneManifest(builtinScenePath)
    : {
        schemaVersion: '0.1',
        scene,
        title: scene,
        description: `${scene} 场景任务集合`,
      };

  await mkdir(taskRoot, { recursive: true });
  await writeYamlDocument(taskYamlPath, assets.document);
  await writeJsonFile(taskManifestPath, assets.manifest);
  const sceneRoot = path.dirname(taskRoot);
  if (!(await pathExists(path.join(sceneRoot, 'scene.json')))) {
    await writeJsonFile(path.join(sceneRoot, 'scene.json'), sceneManifest);
  }
  await writeTextIfMissing(path.join(sceneRoot, 'SKILL.md'), sceneSkillContent(scene));
  await writeTextIfMissing(path.join(taskRoot, 'SKILL.md'), taskSkillContent(scene, task));
  return taskYamlPath;
}
