import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { requireDataPaths, resolveRuntimeLayout } from '../../cua/task/data-paths.js';

test('数据根遵循显式、进程、env.local、env 优先级', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-data-paths-'));
  const skill = path.join(root, 'skill');
  const builtin = path.join(skill, 'projects');
  const fromEnv = path.join(root, 'from-env');
  const fromLocal = path.join(root, 'from-local');
  const fromProcess = path.join(root, 'from-process');
  const explicit = path.join(root, 'explicit');
  await import('node:fs/promises').then(({ mkdir }) => mkdir(builtin, { recursive: true }));
  await writeFile(path.join(skill, '.env'), `CUA_DATA_ROOT=${fromEnv}\n`, 'utf8');
  await writeFile(path.join(skill, '.env.local'), `CUA_DATA_ROOT=${fromLocal}\n`, 'utf8');
  const previous = process.env.CUA_DATA_ROOT;
  delete process.env.CUA_DATA_ROOT;
  try {
    assert.equal((await resolveRuntimeLayout(undefined, { executionRoot: skill })).data?.root, fromLocal);
    process.env.CUA_DATA_ROOT = fromProcess;
    assert.equal((await resolveRuntimeLayout(undefined, { executionRoot: skill })).data?.root, fromProcess);
    const layout = await resolveRuntimeLayout(explicit, { executionRoot: skill });
    assert.equal(layout.data?.root, explicit);
    assert.equal(layout.data?.projectsRoot, path.join(explicit, 'projects'));
  } finally {
    if (previous === undefined) delete process.env.CUA_DATA_ROOT;
    else process.env.CUA_DATA_ROOT = previous;
  }
});

test('数据根拒绝缺失、相对路径和 Skill 内路径', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-data-invalid-'));
  const skill = path.join(root, 'skill');
  await import('node:fs/promises').then(({ mkdir }) => mkdir(path.join(skill, 'projects'), { recursive: true }));
  const previous = process.env.CUA_DATA_ROOT;
  delete process.env.CUA_DATA_ROOT;
  try {
    await assert.rejects(requireDataPaths(await resolveRuntimeLayout(undefined, { executionRoot: skill })), /CUA_DATA_ROOT|--data-root/);
    await assert.rejects(resolveRuntimeLayout('relative', { executionRoot: skill }), /绝对路径/);
    await assert.rejects(resolveRuntimeLayout(path.join(skill, 'data'), { executionRoot: skill }), /Skill/);
  } finally {
    if (previous === undefined) delete process.env.CUA_DATA_ROOT;
    else process.env.CUA_DATA_ROOT = previous;
  }
});
