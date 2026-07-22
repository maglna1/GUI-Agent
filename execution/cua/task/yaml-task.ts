import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { parseYamlScript } from '@midscene/core/yaml';
import { parse, stringify } from 'yaml';
import type { JsonObject, TaskManifest } from '../contracts/types.js';

const placeholderPattern = /\{\{([a-z][a-z0-9-]*)\}\}/g;
const recordedTaskNamePattern = /^(step-(\d{3,})) \| (click|doubleClick|input|keyboard|wait)$/;
const recordedInputIdPattern = /^(step-(\d{3,}))-input$/;

function isRecord(value: unknown): value is JsonObject {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function validateYamlDocument(document: JsonObject, source: string): void {
  const tasks = document.tasks;
  if (!Array.isArray(tasks) || tasks.length === 0) {
    throw new Error(`Midscene YAML tasks 必须是非空数组：${source}`);
  }
  tasks.forEach((task, taskIndex) => {
    if (!isRecord(task)) throw new Error(`Midscene YAML tasks[${taskIndex + 1}] 必须是对象：${source}`);
    if (typeof task.name !== 'string' || !task.name.trim()) {
      throw new Error(`Midscene YAML tasks[${taskIndex + 1}].name 不能为空：${source}`);
    }
    if (!Array.isArray(task.flow) || task.flow.length === 0) {
      throw new Error(`Midscene YAML tasks[${taskIndex + 1}].flow 必须是非空数组：${source}`);
    }
    task.flow.forEach((action, actionIndex) => {
      if (!isRecord(action) || Object.keys(action).length === 0) {
        throw new Error(
          `Midscene YAML tasks[${taskIndex + 1}].flow[${actionIndex + 1}] 必须是非空对象：${source}`,
        );
      }
    });
  });
}

export async function readYamlDocument(sourcePath: string): Promise<JsonObject> {
  const absolutePath = path.resolve(sourcePath);
  let document: unknown;
  try {
    document = parse(await readFile(absolutePath, 'utf8'));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`读取并解析 Midscene YAML 失败：${absolutePath}\n${message}`);
  }
  if (!isRecord(document)) throw new Error(`Midscene YAML 根节点必须是对象：${absolutePath}`);
  validateYamlDocument(document, absolutePath);
  return document;
}

export function dumpYamlDocument(document: JsonObject): string {
  validateYamlDocument(document, 'YAML output');
  return stringify(document, { lineWidth: 120 });
}

export async function writeYamlDocument(sourcePath: string, document: JsonObject): Promise<void> {
  const absolutePath = path.resolve(sourcePath);
  await mkdir(path.dirname(absolutePath), { recursive: true });
  await writeFile(absolutePath, dumpYamlDocument(document), 'utf8');
}

export function validateRecordedTaskDocument(
  document: JsonObject,
  manifest: TaskManifest,
  source: string,
): void {
  if (!isRecord(document.agent)) throw new Error(`录制任务 YAML agent 必须是对象：${source}`);
  if (document.agent.groupName !== manifest.task) {
    throw new Error(`录制任务 YAML agent.groupName 必须等于 task.json 的 task：${source}`);
  }
  if (document.agent.groupDescription !== manifest.goal) {
    throw new Error(`录制任务 YAML agent.groupDescription 必须等于 task.json 的 goal：${source}`);
  }

  let previous = 0;
  const operationByStep = new Map<string, string>();
  (document.tasks as JsonObject[]).forEach((task, index) => {
    const match = recordedTaskNamePattern.exec(String(task.name));
    if (!match) {
      throw new Error(`录制任务 YAML tasks[${index + 1}].name 必须符合 step-NNN | <operation-type>：${source}`);
    }
    const [, stepId, numberText, operationType] = match;
    const number = Number(numberText);
    if (number <= 0 || stepId !== `step-${String(number).padStart(3, '0')}`) {
      throw new Error(`录制任务 YAML tasks[${index + 1}] 的 step ID 非法：${source}`);
    }
    if (number <= previous) throw new Error(`录制任务 YAML step ID 必须唯一且严格递增：${source}`);
    if (task.continueOnError === true) throw new Error(`录制任务 YAML 不允许启用 continueOnError：${source}`);
    operationByStep.set(stepId, operationType);
    previous = number;
  });

  for (const inputId of Object.keys(manifest.inputs)) {
    const match = recordedInputIdPattern.exec(inputId);
    if (!match) throw new Error(`录制任务输入 ID 必须符合 step-NNN-input：${inputId}`);
    const [, stepId, numberText] = match;
    const number = Number(numberText);
    if (number <= 0 || stepId !== `step-${String(number).padStart(3, '0')}`) {
      throw new Error(`录制任务输入 ID 非法：${inputId}`);
    }
    if (operationByStep.get(stepId) !== 'input') {
      throw new Error(`录制任务输入 ${inputId} 未对应 input 类型步骤`);
    }
  }
}

function collectPlaceholders(value: unknown): Set<string> {
  if (typeof value === 'string') {
    const matches = new Set([...value.matchAll(placeholderPattern)].map((match) => match[1]));
    const residue = value.replace(placeholderPattern, '');
    if (residue.includes('{{') || residue.includes('}}')) throw new Error(`非法输入占位符：${value}`);
    return matches;
  }
  if (Array.isArray(value)) {
    return new Set(value.flatMap((item) => [...collectPlaceholders(item)]));
  }
  if (isRecord(value)) {
    const result = new Set<string>();
    for (const [key, item] of Object.entries(value)) {
      for (const match of collectPlaceholders(key)) result.add(match);
      for (const match of collectPlaceholders(item)) result.add(match);
    }
    return result;
  }
  return new Set();
}

export function resolveYamlInputs(
  document: JsonObject,
  manifest: TaskManifest,
  provided: Record<string, string> = {},
): { document: JsonObject; inputs: Record<string, string> } {
  const unknown = Object.keys(provided).filter((key) => !Object.hasOwn(manifest.inputs, key)).sort();
  if (unknown.length) throw new Error(`未知输入参数：${unknown.join(', ')}`);
  const placeholders = collectPlaceholders(document);
  const undeclared = [...placeholders].filter((key) => !Object.hasOwn(manifest.inputs, key)).sort();
  if (undeclared.length) throw new Error(`YAML 包含未声明输入占位符：${undeclared.join(', ')}`);
  const unused = Object.keys(manifest.inputs).filter((key) => !placeholders.has(key)).sort();
  if (unused.length) throw new Error(`任务清单输入未在 YAML 中使用：${unused.join(', ')}`);

  const inputs = Object.fromEntries(
    Object.entries(manifest.inputs).map(([inputId, definition]) => [inputId, definition.default]),
  );
  Object.assign(inputs, provided);
  const resolve = (value: unknown): unknown => {
    if (typeof value === 'string') {
      return value.replace(placeholderPattern, (_, inputId: string) => inputs[inputId]);
    }
    if (Array.isArray(value)) return value.map(resolve);
    if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [resolve(key), resolve(item)]));
    return value;
  };
  const resolved = resolve(document);
  if (!isRecord(resolved)) throw new Error('resolved task 根节点不是对象');
  validateYamlDocument(resolved, 'resolved task');
  if (collectPlaceholders(resolved).size) throw new Error('resolved task 仍包含未解析输入占位符');
  parseYamlScript(dumpYamlDocument(resolved));
  return { document: resolved, inputs };
}
