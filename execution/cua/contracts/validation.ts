import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { Ajv, type ErrorObject, type ValidateFunction } from 'ajv';
import type {
  ExecutorResult,
  ProcessedLogStep,
  SceneManifest,
  ShowuiTrace,
  TaskManifest,
} from './types.js';
import { packageRoot } from '../package-root.js';

const schemaDirectory = path.join(packageRoot, 'schemas');
const require = createRequire(import.meta.url);
const addFormats = require('ajv-formats') as (instance: Ajv) => void;
const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);

const validators = new Map<string, ValidateFunction>();

async function validatorFor(schemaFilename: string): Promise<ValidateFunction> {
  const existing = validators.get(schemaFilename);
  if (existing) return existing;
  const schemaPath = path.join(schemaDirectory, schemaFilename);
  const schema = JSON.parse(await readFile(schemaPath, 'utf8')) as object;
  const validator = ajv.compile(schema);
  validators.set(schemaFilename, validator);
  return validator;
}

function formatErrors(errors: ErrorObject[] | null | undefined): string {
  return (errors ?? [])
    .map((error) => {
      const field = error.instancePath || '/';
      const detail = error.message ?? error.keyword;
      return `${field}: ${detail}`;
    })
    .join('; ');
}

export async function validateContract<T>(
  value: unknown,
  schemaFilename: string,
  source: string,
): Promise<T> {
  const validator = await validatorFor(schemaFilename);
  if (!validator(value)) {
    throw new Error(`契约校验失败：${source}\n${formatErrors(validator.errors)}`);
  }
  return value as T;
}

export async function readJsonContract<T>(
  sourcePath: string,
  schemaFilename: string,
  label: string,
): Promise<T> {
  const absolutePath = path.resolve(sourcePath);
  let value: unknown;
  try {
    value = JSON.parse(await readFile(absolutePath, 'utf8'));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`读取并解析${label}失败：${absolutePath}\n${message}`);
  }
  return validateContract<T>(value, schemaFilename, absolutePath);
}

export const readSceneManifest = (sourcePath: string) =>
  readJsonContract<SceneManifest>(sourcePath, 'scene.schema.json', '场景清单');

export const readTaskManifest = (sourcePath: string) =>
  readJsonContract<TaskManifest>(sourcePath, 'task.schema.json', '任务清单');

export const readExecutorResult = (sourcePath: string) =>
  readJsonContract<ExecutorResult>(sourcePath, 'execution-result.schema.json', '执行结果');

export const readShowuiTrace = (sourcePath: string) =>
  readJsonContract<ShowuiTrace>(sourcePath, 'showui-trace.schema.json', 'ShowUI trace');

export const readProcessedLog = (sourcePath: string) =>
  readJsonContract<ProcessedLogStep[]>(sourcePath, 'processed-log.schema.json', 'processed log');

export async function writeJsonFile(sourcePath: string, value: unknown): Promise<void> {
  await writeFile(sourcePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}
