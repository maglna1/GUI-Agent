#!/usr/bin/env node
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { convertTrace } from '../conversion/showui-trace.js';
import type { JsonObject } from '../contracts/types.js';
import { requireDataPaths, resolveRuntimeLayout } from '../task/data-paths.js';
import { runPrompt, runRecordedTaskAiAct, runTask } from '../task/execution.js';
import { loadRuntimeInputs } from '../task/inputs.js';
import { describeTask, listScenes, listTasks, resolveTask } from '../task/tasks.js';
import { dumpYamlDocument } from '../task/yaml-task.js';

type OptionValue = string | string[] | boolean;
type ParsedOptions = Record<string, OptionValue | undefined>;

export class CliUsageError extends Error {
  readonly exitCode = 2;
}

export const helpText = `CUA 场景、任务与 Midscene YAML 执行工具

用法：cua <scene|task|act> <command> [options]

场景：
  scene list [--data-root <path>] [--json]

任务：
  task list --scene <scene> [--data-root <path>] [--json]
  task describe --scene <scene> --task <task> [--data-root <path>] [--json]
  task init-from-trace --scene <scene> --task <task> --goal <目标> [--data-root <path>]
  task validate|inspect|run --scene <scene> --task <task> [--input key=value] [--inputs <file>]

整体 aiAct：
  act run --prompt <要求> [--dry-run]
  act run --scene <scene> --task <task> [--input key=value] [--dry-run]
`;

const commandOptions: Record<string, { values: string[]; booleans: string[]; repeated?: string[]; required?: string[] }> = {
  'scene list': { values: ['data-root'], booleans: ['json'] },
  'task list': { values: ['scene', 'data-root'], booleans: ['json'], required: ['scene'] },
  'task describe': { values: ['scene', 'task', 'data-root'], booleans: ['json'], required: ['scene', 'task'] },
  'task init-from-trace': {
    values: ['scene', 'task', 'goal', 'data-root', 'recording-preparation-command', 'trace-generation-command'],
    booleans: [],
    required: ['scene', 'task', 'goal'],
  },
  'task validate': {
    values: ['scene', 'task', 'data-root', 'inputs', 'input'],
    booleans: ['json'],
    repeated: ['input'],
    required: ['scene', 'task'],
  },
  'task inspect': {
    values: ['scene', 'task', 'data-root', 'inputs', 'input'],
    booleans: ['json'],
    repeated: ['input'],
    required: ['scene', 'task'],
  },
  'task run': {
    values: ['scene', 'task', 'data-root', 'inputs', 'input'],
    booleans: ['json', 'dry-run'],
    repeated: ['input'],
    required: ['scene', 'task'],
  },
  'act run': {
    values: ['prompt', 'scene', 'task', 'data-root', 'inputs', 'input'],
    booleans: ['dry-run'],
    repeated: ['input'],
  },
};

function parseCommand(argv: string[]): { domain: string; command: string; options: ParsedOptions } {
  if (argv.length < 2) throw new CliUsageError('必须提供 domain 和 command；使用 --help 查看用法');
  const domain = argv[0];
  const command = argv[1];
  const definition = commandOptions[`${domain} ${command}`];
  if (!definition) throw new CliUsageError(`不支持的命令：${domain} ${command}`);
  const options: ParsedOptions = {};
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) throw new CliUsageError(`无法识别参数：${token}`);
    const name = token.slice(2);
    if (definition.booleans.includes(name)) {
      if (options[name] !== undefined) throw new CliUsageError(`参数 --${name} 不能重复提供`);
      options[name] = true;
      continue;
    }
    if (!definition.values.includes(name)) throw new CliUsageError(`无法识别参数：${token}`);
    const value = argv[index + 1];
    if (value === undefined || value.startsWith('--')) throw new CliUsageError(`参数 --${name} 缺少值`);
    if (definition.repeated?.includes(name)) {
      options[name] = [...((options[name] as string[] | undefined) ?? []), value];
    } else {
      if (options[name] !== undefined) throw new CliUsageError(`参数 --${name} 不能重复提供`);
      options[name] = value;
    }
    index += 1;
  }
  for (const required of definition.required ?? []) {
    if (options[required] === undefined) throw new CliUsageError(`必须提供 --${required}`);
  }
  if (domain === 'act') {
    const hasPrompt = options.prompt !== undefined;
    const providedTaskOptions = ['scene', 'task', 'inputs', 'input'].filter((name) => options[name] !== undefined);
    if (hasPrompt && providedTaskOptions.length) {
      throw new CliUsageError(`--prompt 不能与任务参数混用：${providedTaskOptions.map((name) => `--${name}`).join(', ')}`);
    }
    if (!hasPrompt && (options.scene === undefined || options.task === undefined)) {
      throw new CliUsageError('必须提供 --prompt，或同时提供 --scene 和 --task');
    }
  }
  return { domain, command, options };
}

function value(options: ParsedOptions, name: string): string | undefined {
  return options[name] as string | undefined;
}

function json(valueToRender: unknown): string {
  return `${JSON.stringify(valueToRender, null, 2)}\n`;
}

function quoteCommandValue(input: string): string {
  return `"${input.replaceAll('"', '\\"')}"`;
}

function buildConversionCommand(options: ParsedOptions): string {
  const parts = [
    'npm run cua -- task init-from-trace',
    `--scene ${value(options, 'scene')}`,
    `--task ${value(options, 'task')}`,
    `--goal ${quoteCommandValue(value(options, 'goal')!)}`,
  ];
  for (const option of ['data-root', 'recording-preparation-command', 'trace-generation-command']) {
    const optionValue = value(options, option);
    if (optionValue) parts.push(`--${option} ${quoteCommandValue(optionValue)}`);
  }
  return parts.join(' ');
}

export async function runCliCommand(argv: string[]): Promise<string> {
  const { domain, command, options } = parseCommand(argv);
  const layout = await resolveRuntimeLayout(value(options, 'data-root'));

  if (domain === 'scene') {
    const scenes = await listScenes(layout.catalog);
    if (options.json) return json({ scenes });
    return scenes.map((scene) => `${scene.scene}\t${scene.title}\t${scene.description}`).join('\n') + '\n';
  }
  if (domain === 'task' && command === 'list') {
    const scene = value(options, 'scene')!;
    const tasks = await listTasks(scene, layout.catalog);
    if (options.json) return json({ scene, tasks });
    return tasks.map((task) => `${task.task}\t${task.title}\t${task.description}`).join('\n') + '\n';
  }
  if (domain === 'task' && command === 'describe') {
    return json(await describeTask(value(options, 'scene')!, value(options, 'task')!, layout.catalog));
  }
  if (domain === 'task' && command === 'init-from-trace') {
    await requireDataPaths(layout);
    const scene = value(options, 'scene')!;
    const task = value(options, 'task')!;
    const taskYamlPath = await convertTrace({
      scene,
      task,
      goal: value(options, 'goal')!,
      catalog: layout.catalog,
      conversionCommand: buildConversionCommand(options),
      ...(value(options, 'recording-preparation-command')
        ? { recordingPreparationCommand: value(options, 'recording-preparation-command') }
        : {}),
      ...(value(options, 'trace-generation-command')
        ? { traceGenerationCommand: value(options, 'trace-generation-command') }
        : {}),
    });
    return json({ initialized: true, scene, task, taskYamlPath });
  }

  const runtimeInputs = await loadRuntimeInputs(
    value(options, 'inputs'),
    (options.input as string[] | undefined) ?? [],
  );
  if (domain === 'task' && command === 'inspect') {
    const scene = value(options, 'scene')!;
    const task = value(options, 'task')!;
    const resolved = await resolveTask({ scene, task, catalog: layout.catalog, inputs: runtimeInputs });
    if (options.json) {
      return json({
        scene,
        task,
        origin: resolved.origin,
        writable: resolved.writable,
        inputs: resolved.inputs,
        sourceYamlPath: resolved.sourcePath,
        yaml: resolved.document,
      });
    }
    return dumpYamlDocument(resolved.document);
  }
  if (domain === 'task' && (command === 'validate' || command === 'run')) {
    const data = await requireDataPaths(layout);
    const scene = value(options, 'scene')!;
    const task = value(options, 'task')!;
    const run = await runTask({
      scene,
      task,
      catalog: layout.catalog,
      runsRoot: data.runsRoot,
      inputs: runtimeInputs,
      dryRun: command === 'validate' || Boolean(options['dry-run']),
    });
    const payload: JsonObject = {
      scene,
      task,
      origin: run.resolved.origin,
      writable: run.resolved.writable,
      inputs: run.resolved.inputs,
      runDir: path.dirname(run.resolvedTaskPath),
      resolvedTaskPath: run.resolvedTaskPath,
      executor: run.executorResult,
    };
    if (command === 'validate') payload.valid = true;
    return json(payload);
  }
  if (domain === 'act') {
    const data = await requireDataPaths(layout);
    const prompt = value(options, 'prompt');
    if (prompt !== undefined) {
      const run = await runPrompt({ prompt, runsRoot: data.runsRoot, dryRun: Boolean(options['dry-run']) });
      return json({
        mode: 'prompt',
        runDir: path.dirname(run.yamlPath),
        aiActYamlPath: run.yamlPath,
        executor: run.executorResult,
      });
    }
    const scene = value(options, 'scene')!;
    const task = value(options, 'task')!;
    const run = await runRecordedTaskAiAct({
      scene,
      task,
      catalog: layout.catalog,
      runsRoot: data.runsRoot,
      inputs: runtimeInputs,
      dryRun: Boolean(options['dry-run']),
    });
    return json({
      mode: 'recorded-task',
      scene,
      task,
      origin: run.resolved.origin,
      writable: run.resolved.writable,
      inputs: run.resolved.inputs,
      runDir: path.dirname(run.resolvedTaskPath),
      resolvedTaskPath: run.resolvedTaskPath,
      promptPath: run.promptPath,
      aiActYamlPath: run.aiActYamlPath,
      executor: run.executorResult,
    });
  }
  throw new Error(`不支持的命令：${domain} ${command}`);
}

export async function main(argv = process.argv.slice(2)): Promise<void> {
  if (argv.includes('--help') || argv.includes('-h')) {
    process.stdout.write(helpText);
    return;
  }
  const originalLog = console.log;
  const originalWarn = console.warn;
  console.log = (...args: unknown[]) => console.error(...args);
  console.warn = (...args: unknown[]) => console.error(...args);
  try {
    const output = await runCliCommand(argv);
    process.stdout.write(output);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = error instanceof CliUsageError ? error.exitCode : 1;
  } finally {
    console.log = originalLog;
    console.warn = originalWarn;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
