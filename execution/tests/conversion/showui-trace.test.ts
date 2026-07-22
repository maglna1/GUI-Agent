import assert from 'node:assert/strict';
import { cp, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import {
  clampRecordedWaitMs,
  convertTrace,
  type ConvertOptions,
} from '../../cua/conversion/showui-trace.js';
import { readTaskManifest } from '../../cua/contracts/validation.js';
import { readYamlDocument } from '../../cua/task/yaml-task.js';

const executionRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const airTask = path.join(executionRoot, 'projects', 'browser-demo', 'air-tickets-demo');
const goal = '将 Qatar Airways 订票页面设置为 Singapore 到 Los Angeles 的单程航班搜索';

async function prepare(task: string): Promise<{ root: string; taskRoot: string; options: ConvertOptions }> {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-conversion-'));
  const user = path.join(root, 'user');
  const builtin = path.join(root, 'builtin');
  const taskRoot = path.join(user, 'browser-demo', task);
  await cp(path.join(airTask, 'source'), path.join(taskRoot, 'source'), { recursive: true });
  return {
    root,
    taskRoot,
    options: {
      scene: 'browser-demo',
      task,
      goal,
      catalog: { builtinProjectsRoot: builtin, userProjectsRoot: user },
      conversionCommand: `npm run cua -- task init-from-trace --scene browser-demo --task ${task}`,
    },
  };
}

test('录制等待按 200ms 到 30s 边界裁剪', () => {
  assert.equal(clampRecordedWaitMs(199), 0);
  assert.equal(clampRecordedWaitMs(200), 200);
  assert.equal(clampRecordedWaitMs(30_001), 30_000);
});

test('转换器生成与录制 operation 对应的 Midscene YAML 和输入契约', async () => {
  const fixture = await prepare('new-task');
  const output = await convertTrace(fixture.options);
  const document = await readYamlDocument(output);
  const golden = await readYamlDocument(path.join(airTask, 'task.yaml'));
  const manifest = await readTaskManifest(path.join(fixture.taskRoot, 'task.json'));
  const tasks = document.tasks as Array<Record<string, any>>;

  assert.equal(tasks.length, 16);
  assert.deepEqual(document.tasks, golden.tasks);
  assert.deepEqual(tasks[0], {
    name: 'step-001 | click',
    flow: [{ aiTap: '点击 Chrome 浏览器顶部的地址栏/搜索栏区域以聚焦输入框' }],
  });
  assert.equal(tasks[1].flow[0].sleep, 4101);
  assert.equal(tasks[1].flow[1].KeyboardTypeText.value, '{{step-002-input}}');
  assert.deepEqual(Object.keys(manifest.inputs), ['step-002-input', 'step-008-input', 'step-010-input']);
  assert.equal(manifest.inputs['step-002-input'].default, 'QATAR AIRWAYS');
  assert.match(await readFile(path.join(fixture.taskRoot, 'SKILL.md'), 'utf8'), /npm run cua -- task describe/);
});

test('双击 operation 映射为 aiDoubleClick', async () => {
  const fixture = await prepare('double-click-task');
  const tracePath = path.join(fixture.taskRoot, 'source', 'showui-trace.json');
  const trace = JSON.parse(await readFile(tracePath, 'utf8'));
  trace.trajectory[0].caption.operation = {
    type: 'doubleClick',
    prompt: '双击页面中部文件列表里的 report.xlsx 文件行以打开文件',
  };
  await writeFile(tracePath, JSON.stringify(trace), 'utf8');
  const document = await readYamlDocument(await convertTrace(fixture.options));
  assert.deepEqual((document.tasks as unknown[])[0], {
    name: 'step-001 | doubleClick',
    flow: [{ aiDoubleClick: '双击页面中部文件列表里的 report.xlsx 文件行以打开文件' }],
  });
});

test('转换器只消费 operation，不根据其他自然语言字段猜测动作', async () => {
  const fixture = await prepare('structured-only');
  const tracePath = path.join(fixture.taskRoot, 'source', 'showui-trace.json');
  const trace = JSON.parse(await readFile(tracePath, 'utf8'));
  trace.trajectory[0].caption.action = '按下 Enter 键';
  trace.trajectory[0].caption.think = '这是键盘动作';
  const originalOperation = trace.trajectory[0].caption.operation;
  await writeFile(tracePath, JSON.stringify(trace), 'utf8');
  const document = await readYamlDocument(await convertTrace(fixture.options));
  assert.equal((document.tasks as Array<Record<string, any>>)[0].flow[0].aiTap, originalOperation.prompt);
});

test('缺失 operation、定位提示和非法步骤不会写出半成品', async () => {
  for (const [task, mutate, message] of [
    ['missing-operation', (trace: any) => delete trace.trajectory[0].caption.operation, /operation/],
    ['missing-locate', (trace: any) => delete trace.trajectory[1].caption.operation.locatePrompt, /operation\.locatePrompt 不能为空/],
    ['duplicate-step', (trace: any) => (trace.trajectory[1].step_idx = 1), /唯一且按轨迹顺序严格递增/],
  ] as const) {
    const fixture = await prepare(task);
    const tracePath = path.join(fixture.taskRoot, 'source', 'showui-trace.json');
    const trace = JSON.parse(await readFile(tracePath, 'utf8'));
    mutate(trace);
    await writeFile(tracePath, JSON.stringify(trace), 'utf8');
    await assert.rejects(convertTrace(fixture.options), message);
    await assert.rejects(readFile(path.join(fixture.taskRoot, 'task.yaml')), /ENOENT/);
    await assert.rejects(readFile(path.join(fixture.taskRoot, 'task.json')), /ENOENT/);
  }
});

test('已有任务资产和内置任务均拒绝覆盖', async () => {
  const existing = await prepare('existing-task');
  await writeFile(path.join(existing.taskRoot, 'task.yaml'), 'preserve: true\n', 'utf8');
  await assert.rejects(convertTrace(existing.options), /任务资产已存在，拒绝覆盖/);
  assert.equal(await readFile(path.join(existing.taskRoot, 'task.yaml'), 'utf8'), 'preserve: true\n');

  const builtin = await prepare('builtin-task');
  await cp(airTask, path.join(builtin.options.catalog.builtinProjectsRoot, 'browser-demo', 'builtin-task'), {
    recursive: true,
  });
  await assert.rejects(convertTrace(builtin.options), /内置任务不可覆盖/);
});
