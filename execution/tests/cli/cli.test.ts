import assert from 'node:assert/strict';
import { mkdtemp } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { CliUsageError, helpText, runCliCommand } from '../../cua/cli/main.js';

test('scene/task 查询保持机器可读输出契约', async () => {
  const scenes = JSON.parse(await runCliCommand(['scene', 'list', '--json']));
  assert.equal(scenes.scenes[0].scene, 'browser-demo');
  const tasks = JSON.parse(await runCliCommand(['task', 'list', '--scene', 'browser-demo', '--json']));
  assert.equal(tasks.tasks[0].task, 'air-tickets-demo');
  assert.deepEqual(Object.keys(tasks.tasks[0].inputs), [
    'step-002-input',
    'step-008-input',
    'step-010-input',
  ]);
  assert.match(tasks.tasks[0].taskYamlPath, /task\.yaml$/);
  const described = JSON.parse(
    await runCliCommand(['task', 'describe', '--scene', 'browser-demo', '--task', 'air-tickets-demo', '--json']),
  );
  assert.equal(described.taskCount, 16);
});

test('task inspect 只覆盖本次明确输入', async () => {
  const inspected = JSON.parse(
    await runCliCommand([
      'task', 'inspect', '--scene', 'browser-demo', '--task', 'air-tickets-demo',
      '--input', 'step-002-input=GOOGLE', '--json',
    ]),
  );
  assert.equal(inspected.inputs['step-002-input'], 'GOOGLE');
  assert.equal(inspected.inputs['step-008-input'], 'SINGAPORE');
  assert.equal(inspected.yaml.tasks[1].flow[1].KeyboardTypeText.value, 'GOOGLE');
});

test('CLI 拒绝重复、旧命令和非法 aiAct 来源', async () => {
  const cases: Array<[string[], RegExp]> = [
    [['task', 'inspect', '--scene', 'first', '--scene', 'second', '--task', 'demo'], /不能重复提供/],
    [['flow', 'inspect'], /不支持的命令/],
    [['calibration', 'apply'], /不支持的命令/],
    [['act', 'run'], /必须提供 --prompt/],
    [['act', 'run', '--scene', 'browser-demo'], /同时提供 --scene 和 --task/],
    [['act', 'run', '--prompt', '打开 Chrome', '--input', 'query=value'], /不能与任务参数混用/],
  ];
  for (const [argv, expected] of cases) {
    await assert.rejects(runCliCommand(argv), (error: Error) => {
      assert.ok(error instanceof CliUsageError);
      assert.match(error.message, expected);
      return true;
    });
  }
});

test('task validate、task run dry-run 与两种 aiAct dry-run 生成外部运行资产', async () => {
  const dataRoot = await mkdtemp(path.join(os.tmpdir(), 'cua-cli-runs-'));
  const common = ['--data-root', dataRoot];
  const validated = JSON.parse(
    await runCliCommand(['task', 'validate', '--scene', 'browser-demo', '--task', 'air-tickets-demo', ...common]),
  );
  assert.equal(validated.valid, true);
  assert.equal(validated.executor.dryRun, true);
  const taskRun = JSON.parse(
    await runCliCommand(['task', 'run', '--scene', 'browser-demo', '--task', 'air-tickets-demo', '--dry-run', ...common]),
  );
  assert.equal(taskRun.executor.taskCount, 16);
  const recordedAct = JSON.parse(
    await runCliCommand(['act', 'run', '--scene', 'browser-demo', '--task', 'air-tickets-demo', '--dry-run', ...common]),
  );
  assert.equal(recordedAct.mode, 'recorded-task');
  assert.match(recordedAct.promptPath, /ai-act-prompt\.txt$/);
  const promptAct = JSON.parse(
    await runCliCommand(['act', 'run', '--prompt', '打开 Chrome 并搜索 GUI agent', '--dry-run', ...common]),
  );
  assert.equal(promptAct.mode, 'prompt');
  for (const result of [validated, taskRun, recordedAct, promptAct]) {
    assert.ok(path.resolve(result.runDir).startsWith(path.join(dataRoot, 'runs')));
  }
});

test('CLI 使用中文帮助', () => {
  assert.match(helpText, /CUA 场景、任务与 Midscene YAML 执行工具/);
  assert.match(helpText, /npm|cua/);
});
