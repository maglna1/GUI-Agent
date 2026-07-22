import { mkdir, writeFile } from 'node:fs/promises';
import { randomBytes } from 'node:crypto';
import path from 'node:path';
import type { ExecutorResult, JsonObject, ResolvedTaskResult, TaskCatalogRoots } from '../contracts/types.js';
import { executeMidsceneYaml, type MidsceneYamlExecutionOptions } from '../../executors/midscene-yaml.js';
import { resolveTask } from './tasks.js';
import { validateYamlDocument, writeYamlDocument } from './yaml-task.js';

export const aiActContext = `文本输入必须遵守以下规则：
1. 仅使用 KeyboardTypeText 输入 ASCII 文本，不使用默认 Input 或剪贴板。
2. 待输入文本包含 KeyboardTypeText 不支持的字符时直接失败，不切换输入动作。
3. 不得因为定位失败或一般执行失败改用其他输入方式。`;

export interface ExecutionOptions {
  scene: string;
  task: string;
  catalog: TaskCatalogRoots;
  runsRoot: string;
  inputs?: Record<string, string>;
  dryRun?: boolean;
  executor?: typeof executeMidsceneYaml;
}

export interface TaskRun {
  resolved: ResolvedTaskResult;
  resolvedTaskPath: string;
  executorResult: ExecutorResult;
}

export interface RecordedTaskAiActRun extends TaskRun {
  promptPath: string;
  aiActYamlPath: string;
}

function requiredString(value: unknown, field: string, context: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${context} 的 ${field} 必须是非空字符串`);
  return value.trim();
}

function renderAction(action: JsonObject, context: string): string | undefined {
  if (Object.hasOwn(action, 'sleep')) {
    if (Object.keys(action).length !== 1) throw new Error(`${context} 的 sleep 不能与其他字段组合`);
    if (!Number.isInteger(action.sleep)) throw new Error(`${context} 的 sleep 必须是整数`);
    return undefined;
  }
  const supported = ['ai', 'aiDoubleClick', 'aiTap', 'aiWaitFor', 'KeyboardPress', 'KeyboardTypeText'];
  const names = supported.filter((name) => Object.hasOwn(action, name));
  if (names.length !== 1) {
    throw new Error(`${context} 必须且只能包含一个受支持动作，当前字段：${Object.keys(action).sort().join(', ') || '空动作'}`);
  }
  const name = names[0];
  const allowed = new Set(name === 'aiWaitFor' ? [name, 'timeout'] : [name]);
  const unexpected = Object.keys(action).filter((key) => !allowed.has(key));
  if (unexpected.length) throw new Error(`${context} 包含无法解释的字段：${unexpected.sort().join(', ')}`);
  const value = action[name];
  if (name === 'ai' || name === 'aiTap' || name === 'aiWaitFor') return requiredString(value, name, context);
  if (name === 'aiDoubleClick') return `双击以下描述对应的目标：${JSON.stringify(requiredString(value, name, context))}`;
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${context} 的 ${name} 必须是对象`);
  const parameters = value as JsonObject;
  if (name === 'KeyboardPress') {
    return `按下 ${JSON.stringify(requiredString(parameters.keyName, 'KeyboardPress.keyName', context))} 键`;
  }
  const locate = requiredString(parameters.locate, 'locate', context);
  if (typeof parameters.value !== 'string') throw new Error(`${context} 的 KeyboardTypeText.value 必须是字符串`);
  const mode = parameters.mode ?? 'replace';
  if (!['replace', 'append', 'typeOnly', 'clear'].includes(String(mode))) {
    throw new Error(`${context} 的 KeyboardTypeText.mode 不受支持：${String(mode)}`);
  }
  if (mode === 'clear') return `使用 KeyboardTypeText 清空 ${JSON.stringify(locate)}`;
  const modeText = { replace: '替换输入', append: '追加输入', typeOnly: '直接输入' }[mode as 'replace'];
  return `使用 KeyboardTypeText 在 ${JSON.stringify(locate)} 中${modeText} ${JSON.stringify(parameters.value)}`;
}

export function buildRecordedTaskAiActPrompt(document: JsonObject): string {
  validateYamlDocument(document, 'recorded task aiAct prompt');
  const lines = ['请严格按以下步骤顺序完成电脑操作：'];
  for (const task of document.tasks as JsonObject[]) {
    const taskName = String(task.name).trim();
    const instructions = (task.flow as JsonObject[])
      .map((action, index) => renderAction(action, `${taskName} 的 flow[${index + 1}]`))
      .filter((value): value is string => value !== undefined);
    if (!instructions.length) throw new Error(`${taskName} 没有可用于整体 aiAct 的执行动作`);
    lines.push(`${taskName}:`, ...instructions.map((instruction, index) => `  ${index + 1}. ${instruction}`));
  }
  return `${lines.join('\n')}\n`;
}

export function aiActYamlDocument(
  prompt: string,
  groupName: string,
  groupDescription: string,
  taskName: string,
): JsonObject {
  return {
    computer: {},
    agent: { groupName, groupDescription, generateReport: true, aiActContext },
    tasks: [{ name: taskName, flow: [{ ai: prompt }] }],
  };
}

export async function createRunDirectory(runsRoot: string): Promise<string> {
  const root = path.resolve(runsRoot);
  await mkdir(root, { recursive: true });
  const now = new Date().toISOString().replaceAll(':', '-').replace('.', '-');
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const runDirectory = path.join(root, `${now}-${randomBytes(4).toString('hex')}`);
    try {
      await mkdir(runDirectory);
      return runDirectory;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
    }
  }
  throw new Error(`无法创建唯一运行目录：${root}`);
}

async function execute(
  yamlPath: string,
  runDirectory: string,
  dryRun: boolean,
  executor: typeof executeMidsceneYaml,
): Promise<ExecutorResult> {
  const options: MidsceneYamlExecutionOptions = {
    yamlPath,
    resultPath: path.join(runDirectory, 'execution-result.json'),
    runDirectory,
    dryRun,
  };
  return executor(options);
}

export async function runTask(options: ExecutionOptions): Promise<TaskRun> {
  const resolved = await resolveTask(options);
  const runDirectory = await createRunDirectory(options.runsRoot);
  const resolvedTaskPath = path.join(runDirectory, 'resolved-task.yaml');
  await writeYamlDocument(resolvedTaskPath, resolved.document);
  const executorResult = await execute(
    resolvedTaskPath,
    runDirectory,
    options.dryRun ?? false,
    options.executor ?? executeMidsceneYaml,
  );
  return { resolved, resolvedTaskPath, executorResult };
}

export async function runRecordedTaskAiAct(options: ExecutionOptions): Promise<RecordedTaskAiActRun> {
  const resolved = await resolveTask(options);
  const prompt = buildRecordedTaskAiActPrompt(resolved.document);
  const runDirectory = await createRunDirectory(options.runsRoot);
  const resolvedTaskPath = path.join(runDirectory, 'resolved-task.yaml');
  const promptPath = path.join(runDirectory, 'ai-act-prompt.txt');
  const aiActYamlPath = path.join(runDirectory, 'ai-act-task.yaml');
  await writeYamlDocument(resolvedTaskPath, resolved.document);
  await writeFile(promptPath, prompt, 'utf8');
  await writeYamlDocument(
    aiActYamlPath,
    aiActYamlDocument(prompt, `${options.task}-ai-act`, resolved.manifest.goal, '录制任务整体 aiAct'),
  );
  const executorResult = await execute(
    aiActYamlPath,
    runDirectory,
    options.dryRun ?? false,
    options.executor ?? executeMidsceneYaml,
  );
  return { resolved, resolvedTaskPath, promptPath, aiActYamlPath, executorResult };
}

export async function runPrompt(options: {
  prompt: string;
  runsRoot: string;
  dryRun?: boolean;
  executor?: typeof executeMidsceneYaml;
}): Promise<{ yamlPath: string; executorResult: ExecutorResult }> {
  const prompt = options.prompt.trim();
  if (!prompt) throw new Error('自然语言 prompt 不能为空');
  const runDirectory = await createRunDirectory(options.runsRoot);
  const yamlPath = path.join(runDirectory, 'resolved-task.yaml');
  await writeYamlDocument(
    yamlPath,
    aiActYamlDocument(prompt, 'natural-language-ai-act', '执行无录制自然语言电脑操作', '自然语言电脑操作'),
  );
  const executorResult = await execute(
    yamlPath,
    runDirectory,
    options.dryRun ?? false,
    options.executor ?? executeMidsceneYaml,
  );
  return { yamlPath, executorResult };
}
