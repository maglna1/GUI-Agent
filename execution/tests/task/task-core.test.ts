import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { loadRuntimeInputs } from '../../cua/task/inputs.js';
import { describeTask, listScenes, listTasks, resolveTask } from '../../cua/task/tasks.js';
import { createTaskFixture } from '../helpers/task-fixture.js';

test('resolver 使用默认值并替换所有显式占位符', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-task-resolve-'));
  const builtin = path.join(root, 'builtin');
  const user = path.join(root, 'user');
  await import('node:fs/promises').then(({ mkdir }) => mkdir(builtin, { recursive: true }));
  const taskRoot = await createTaskFixture(user);
  const catalog = { builtinProjectsRoot: builtin, userProjectsRoot: user };
  const defaults = await resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog });
  assert.deepEqual(defaults.inputs, { 'step-001-input': '默认关键词' });

  const resolved = await resolveTask({
    scene: 'browser-demo',
    task: 'search-demo',
    catalog,
    inputs: { 'step-001-input': 'GUI agent' },
  });
  const tasks = resolved.document.tasks as Array<Record<string, unknown>>;
  assert.equal(((tasks[0].flow as Array<Record<string, any>>)[0].KeyboardTypeText as any).value, 'GUI agent');
  assert.equal((tasks[1].flow as Array<Record<string, string>>)[0].aiTap, '点击与 GUI agent 对应的候选项');
  assert.match(await readFile(path.join(taskRoot, 'task.yaml'), 'utf8'), /\{\{step-001-input\}\}/);
});

test('resolver 拒绝未知、未声明、未使用和非法占位符', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-task-invalid-'));
  const builtin = path.join(root, 'builtin');
  const user = path.join(root, 'user');
  await import('node:fs/promises').then(({ mkdir }) => mkdir(builtin, { recursive: true }));
  const taskRoot = await createTaskFixture(user);
  const catalog = { builtinProjectsRoot: builtin, userProjectsRoot: user };
  await assert.rejects(resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog, inputs: { unknown: 'value' } }), /未知输入参数：unknown/);
  const yamlPath = path.join(taskRoot, 'task.yaml');
  const original = await readFile(yamlPath, 'utf8');
  await writeFile(yamlPath, original.replaceAll('{{step-001-input}}', '{{missing}}'), 'utf8');
  await assert.rejects(resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog }), /未声明输入占位符：missing/);
  await writeFile(yamlPath, original.replaceAll('{{step-001-input}}', 'fixed'), 'utf8');
  await assert.rejects(resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog }), /任务清单输入未在 YAML 中使用/);
  await writeFile(yamlPath, original.replaceAll('{{step-001-input}}', '{{StepInput}}'), 'utf8');
  await assert.rejects(resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog }), /非法输入占位符/);
});

test('稳定步骤身份和 continueOnError 被严格检查', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-step-contract-'));
  const builtin = path.join(root, 'builtin');
  const user = path.join(root, 'user');
  await import('node:fs/promises').then(({ mkdir }) => mkdir(builtin, { recursive: true }));
  const taskRoot = await createTaskFixture(user);
  const catalog = { builtinProjectsRoot: builtin, userProjectsRoot: user };
  const yamlPath = path.join(taskRoot, 'task.yaml');
  const original = await readFile(yamlPath, 'utf8');
  await writeFile(yamlPath, original.replace('step-002 | click', 'step-001 | click'), 'utf8');
  await assert.rejects(resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog }), /唯一且严格递增/);
  await writeFile(
    yamlPath,
    original.replace('\n    flow:\n', '\n    continueOnError: true\n    flow:\n'),
    'utf8',
  );
  await assert.rejects(resolveTask({ scene: 'browser-demo', task: 'search-demo', catalog }), /不允许启用 continueOnError/);
});

test('catalog 合并场景并拒绝重复任务标识', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-catalog-'));
  const builtin = path.join(root, 'builtin');
  const user = path.join(root, 'user');
  await createTaskFixture(builtin);
  const catalog = { builtinProjectsRoot: builtin, userProjectsRoot: user };
  assert.deepEqual((await listScenes(catalog))[0].origins, ['builtin']);
  const tasks = await listTasks('browser-demo', catalog);
  assert.equal(tasks[0].task, 'search-demo');
  assert.equal(tasks[0].taskCount, 2);
  assert.equal((await describeTask('browser-demo', 'search-demo', catalog)).writable, false);
  await createTaskFixture(user);
  assert.deepEqual((await listScenes(catalog))[0].origins, ['builtin', 'user']);
  await assert.rejects(listTasks('browser-demo', catalog), /同时存在于内置与用户 catalog/);
});

test('本次输入拒绝重复值和非字符串', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-inputs-'));
  const inputsPath = path.join(root, 'inputs.json');
  await writeFile(inputsPath, JSON.stringify({ from: 'SIN' }), 'utf8');
  assert.deepEqual(await loadRuntimeInputs(inputsPath, ['to=LAX']), { from: 'SIN', to: 'LAX' });
  await assert.rejects(loadRuntimeInputs(inputsPath, ['from=SHA']), /输入 from 被重复提供/);
  await writeFile(inputsPath, JSON.stringify({ count: 1 }), 'utf8');
  await assert.rejects(loadRuntimeInputs(inputsPath), /必须是字符串/);
});
