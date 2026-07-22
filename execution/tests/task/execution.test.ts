import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import type { ExecutorResult } from '../../cua/contracts/types.js';
import {
  buildRecordedTaskAiActPrompt,
  runPrompt,
  runRecordedTaskAiAct,
  runTask,
} from '../../cua/task/execution.js';
import { readYamlDocument } from '../../cua/task/yaml-task.js';
import type { MidsceneYamlExecutionOptions } from '../../executors/midscene-yaml.js';

const executionRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const catalog = { builtinProjectsRoot: path.join(executionRoot, 'projects') };

async function fakeExecutor(options: MidsceneYamlExecutionOptions): Promise<ExecutorResult> {
  const document = await readYamlDocument(options.yamlPath);
  return {
    schemaVersion: '0.2',
    status: 'succeeded',
    sourceYamlPath: path.resolve(options.yamlPath),
    dryRun: options.dryRun,
    taskCount: (document.tasks as unknown[]).length,
    finishedAt: new Date().toISOString(),
  };
}

test('整体 aiAct prompt 保留步骤和动作并忽略 sleep', () => {
  const document = {
    tasks: [
      { name: 'step-001 | click', flow: [{ sleep: 500 }, { aiTap: '点击 Chrome 顶部地址栏' }] },
      { name: 'step-002 | input', flow: [{ KeyboardTypeText: { locate: 'Chrome 顶部地址栏', value: 'GUI agent', mode: 'replace' } }] },
      { name: 'step-003 | keyboard', flow: [{ KeyboardPress: { keyName: 'Enter' } }] },
      { name: 'step-004 | wait', flow: [{ aiWaitFor: '等待搜索结果页出现', timeout: 15_000 }] },
      { name: 'step-005 | doubleClick', flow: [{ aiDoubleClick: 'report.xlsx 文件行' }] },
    ],
  };
  const prompt = buildRecordedTaskAiActPrompt(document);
  assert.match(prompt, /^请严格按以下步骤顺序完成电脑操作：/);
  assert.ok(prompt.indexOf('step-001') < prompt.indexOf('step-002'));
  assert.match(prompt, /使用 KeyboardTypeText 在 "Chrome 顶部地址栏" 中替换输入 "GUI agent"/);
  assert.match(prompt, /按下 "Enter" 键/);
  assert.match(prompt, /双击以下描述对应的目标："report.xlsx 文件行"/);
  assert.doesNotMatch(prompt, /500|timeout/);
});

test('逐 task 执行与 inspect 使用相同 resolved YAML', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-run-task-'));
  const run = await runTask({
    scene: 'browser-demo',
    task: 'air-tickets-demo',
    catalog,
    runsRoot: root,
    inputs: { 'step-002-input': 'GOOGLE' },
    dryRun: true,
    executor: fakeExecutor,
  });
  const document = await readYamlDocument(run.resolvedTaskPath);
  assert.deepEqual(document, run.resolved.document);
  assert.equal(((document.tasks as Array<Record<string, any>>)[1].flow[1].KeyboardTypeText as any).value, 'GOOGLE');
  assert.equal(run.executorResult.taskCount, 16);
});

test('录制任务整体 aiAct 复用 resolved 输入并保存临时投影', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-run-act-'));
  const run = await runRecordedTaskAiAct({
    scene: 'browser-demo',
    task: 'air-tickets-demo',
    catalog,
    runsRoot: root,
    inputs: { 'step-002-input': 'GOOGLE' },
    dryRun: true,
    executor: fakeExecutor,
  });
  const prompt = await readFile(run.promptPath, 'utf8');
  const aiAct = await readYamlDocument(run.aiActYamlPath);
  assert.equal(prompt.match(/step-/g)?.length, 16);
  assert.match(prompt, /替换输入 "GOOGLE"/);
  assert.doesNotMatch(prompt, /sleep/);
  assert.equal((aiAct.tasks as Array<Record<string, any>>)[0].flow[0].ai, prompt);
  assert.equal(run.executorResult.taskCount, 1);
});

test('自然语言 prompt 生成单 ai action 且拒绝空文本', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'cua-run-prompt-'));
  const run = await runPrompt({ prompt: '打开 Chrome 并搜索 GUI agent', runsRoot: root, dryRun: true, executor: fakeExecutor });
  const document = await readYamlDocument(run.yamlPath);
  assert.deepEqual((document.tasks as Array<Record<string, unknown>>)[0].flow, [{ ai: '打开 Chrome 并搜索 GUI agent' }]);
  assert.match(String((document.agent as Record<string, unknown>).aiActContext), /KeyboardTypeText/);
  await assert.rejects(runPrompt({ prompt: '   ', runsRoot: root, executor: fakeExecutor }), /prompt 不能为空/);
});

test('未知 aiAct action 在创建 run directory 前失败', async () => {
  assert.throws(
    () => buildRecordedTaskAiActPrompt({ tasks: [{ name: 'step-001 | click', flow: [{ aiHover: '目标' }] }] }),
    /必须且只能包含一个受支持动作/,
  );
});
