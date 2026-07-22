import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { parseYamlScript } from '@midscene/core/yaml';
import type { ExecutorResult } from '../cua/contracts/types.js';
import {
  createKeyboardEnabledComputerAgent,
  type ComputerAgentOptions,
} from './computer-agent.js';
import { checkRequiredModelEnv, warnIfNodeVersionIsOld } from './env.js';

interface AgentLike {
  runYaml(content: string): Promise<{ result: Record<string, unknown> }>;
  destroy(): Promise<void>;
}

export interface MidsceneYamlExecutionOptions {
  yamlPath: string;
  resultPath: string;
  runDirectory: string;
  dryRun: boolean;
  agentFactory?: (options: ComputerAgentOptions) => Promise<AgentLike>;
}

async function writeResult(resultPath: string, result: ExecutorResult): Promise<void> {
  await mkdir(path.dirname(resultPath), { recursive: true });
  await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
}

export async function executeMidsceneYaml(
  options: MidsceneYamlExecutionOptions,
): Promise<ExecutorResult> {
  const yamlPath = path.resolve(options.yamlPath);
  const resultPath = path.resolve(options.resultPath);
  let taskCount: number | undefined;
  try {
    let content: string;
    try {
      content = await readFile(yamlPath, 'utf8');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`读取 Midscene YAML 失败：${yamlPath}\n${message}`);
    }
    const script = parseYamlScript(content, yamlPath);
    if (!Array.isArray(script.tasks) || script.tasks.length === 0) {
      throw new Error('Midscene YAML tasks 必须是非空数组');
    }
    taskCount = script.tasks.length;
    let midsceneResult: Record<string, unknown> | undefined;

    if (!options.dryRun) {
      warnIfNodeVersionIsOld();
      checkRequiredModelEnv();
      const previousRunDirectory = process.env.MIDSCENE_RUN_DIR;
      let agent: AgentLike | undefined;
      try {
        process.env.MIDSCENE_RUN_DIR = path.join(path.resolve(options.runDirectory), 'midscene');
        const agentOptions: ComputerAgentOptions = {
          ...(script.agent ?? {}),
          ...(script.computer?.displayId ? { displayId: script.computer.displayId } : {}),
          generateReport: script.agent?.generateReport ?? true,
          groupName: script.agent?.groupName ?? 'midscene-yaml-task',
          groupDescription: script.agent?.groupDescription ?? '执行 Midscene YAML 电脑操作任务',
        };
        agent = await (options.agentFactory ?? createKeyboardEnabledComputerAgent)(agentOptions);
        midsceneResult = (await agent.runYaml(content)).result;
      } finally {
        try {
          if (agent) await agent.destroy();
        } finally {
          if (previousRunDirectory === undefined) delete process.env.MIDSCENE_RUN_DIR;
          else process.env.MIDSCENE_RUN_DIR = previousRunDirectory;
        }
      }
    }

    const result: ExecutorResult = {
      schemaVersion: '0.2',
      status: 'succeeded',
      sourceYamlPath: yamlPath,
      dryRun: options.dryRun,
      taskCount,
      ...(midsceneResult === undefined ? {} : { midsceneResult }),
      finishedAt: new Date().toISOString(),
    };
    await writeResult(resultPath, result);
    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await writeResult(resultPath, {
      schemaVersion: '0.2',
      status: 'failed',
      sourceYamlPath: yamlPath,
      dryRun: options.dryRun,
      ...(taskCount === undefined ? {} : { taskCount }),
      finishedAt: new Date().toISOString(),
      error: message,
    });
    throw error;
  }
}
