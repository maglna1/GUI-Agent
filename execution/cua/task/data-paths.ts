import { access, mkdir, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import dotenv from 'dotenv';
import type { DataPaths, RuntimeLayout } from '../contracts/types.js';
import { packageRoot } from '../package-root.js';

export const executionRoot = packageRoot;
export const builtinProjectsRoot = path.join(executionRoot, 'projects');
export const dataRootEnv = 'CUA_DATA_ROOT';

function isInside(parent: string, target: string): boolean {
  const relative = path.relative(parent, target);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

async function configuredDataRoot(
  explicit?: string,
  root = executionRoot,
): Promise<{ value?: string; source?: string }> {
  if (explicit !== undefined) return { value: explicit, source: '--data-root' };
  const processValue = process.env[dataRootEnv]?.trim();
  if (processValue) return { value: processValue, source: dataRootEnv };

  for (const filename of ['.env.local', '.env']) {
    const envPath = path.join(root, filename);
    try {
      const parsed = dotenv.parse(await readFile(envPath));
      const value = parsed[dataRootEnv]?.trim();
      if (value) return { value, source: envPath };
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    }
  }
  return {};
}

export function dataPaths(root: string): DataPaths {
  return {
    root,
    projectsRoot: path.join(root, 'projects'),
    runsRoot: path.join(root, 'runs'),
    cacheRoot: path.join(root, 'cache'),
  };
}

export async function resolveRuntimeLayout(
  explicit?: string,
  options: { executionRoot?: string; builtinProjectsRoot?: string } = {},
): Promise<RuntimeLayout> {
  const root = path.resolve(options.executionRoot ?? executionRoot);
  const configured = await configuredDataRoot(explicit, root);
  let data: DataPaths | undefined;
  if (configured.value !== undefined) {
    if (!path.isAbsolute(configured.value)) {
      throw new Error(`${configured.source} 必须配置绝对路径：${configured.value}`);
    }
    const normalized = path.resolve(configured.value);
    if (isInside(root, normalized)) {
      throw new Error(`${configured.source} 不得位于 Skill 根目录内：${normalized}`);
    }
    data = dataPaths(normalized);
  }
  return {
    catalog: {
      builtinProjectsRoot: path.resolve(options.builtinProjectsRoot ?? path.join(root, 'projects')),
      ...(data ? { userProjectsRoot: data.projectsRoot } : {}),
    },
    ...(data ? { data } : {}),
  };
}

export async function requireDataPaths(layout: RuntimeLayout): Promise<DataPaths> {
  if (!layout.data) {
    throw new Error('该命令需要可写数据目录，请提供 --data-root 或配置 CUA_DATA_ROOT');
  }
  try {
    for (const directory of Object.values(layout.data)) {
      await mkdir(directory, { recursive: true });
      await access(directory, constants.W_OK);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`CUA 数据目录不可写：${layout.data.root}\n${message}`);
  }
  return layout.data;
}
