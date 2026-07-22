import { readFile } from 'node:fs/promises';
import path from 'node:path';

export function parseInputAssignment(assignment: string): [string, string] {
  const separator = assignment.indexOf('=');
  if (separator <= 0) throw new Error(`输入参数必须使用 key=value 格式：${assignment}`);
  return [assignment.slice(0, separator), assignment.slice(separator + 1)];
}

export async function loadRuntimeInputs(
  inputsFile?: string,
  assignments: string[] = [],
): Promise<Record<string, string>> {
  const inputs: Record<string, string> = {};
  const add = (key: string, value: unknown, source: string) => {
    if (typeof value !== 'string') throw new Error(`输入 ${key} 在 ${source} 中必须是字符串`);
    if (Object.hasOwn(inputs, key)) throw new Error(`输入 ${key} 被重复提供`);
    inputs[key] = value;
  };

  if (inputsFile) {
    const absolutePath = path.resolve(inputsFile);
    let parsed: unknown;
    try {
      parsed = JSON.parse(await readFile(absolutePath, 'utf8'));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`读取输入文件失败：${absolutePath}\n${message}`);
    }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(`输入文件必须是 JSON 对象：${absolutePath}`);
    }
    for (const [key, value] of Object.entries(parsed)) add(key, value, absolutePath);
  }
  for (const assignment of assignments) {
    const [key, value] = parseInputAssignment(assignment);
    add(key, value, '--input');
  }
  return inputs;
}
