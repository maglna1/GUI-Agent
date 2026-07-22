import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { executeMidsceneYaml } from '../../executors/midscene-yaml.js';

async function yamlFixture(content: string) {
  const runDirectory = await mkdtemp(path.join(os.tmpdir(), 'cua-yaml-runner-'));
  const yamlPath = path.join(runDirectory, 'task.yaml');
  const resultPath = path.join(runDirectory, 'execution-result.json');
  await writeFile(yamlPath, content, 'utf8');
  return { runDirectory, yamlPath, resultPath };
}

test('dry-run 解析 YAML 且不创建 Agent', async () => {
  const fixture = await yamlFixture(`
computer: {}
tasks:
  - name: 键盘输入示例
    flow:
      - KeyboardTypeText:
          locate: Chrome 地址栏
          value: QATAR AIRWAYS
          mode: replace
      - KeyboardPress:
          keyName: Enter
`);
  let factoryCalled = false;
  const result = await executeMidsceneYaml({
    ...fixture,
    dryRun: true,
    agentFactory: async () => {
      factoryCalled = true;
      throw new Error('dry-run 不应创建 Agent');
    },
  });
  assert.equal(factoryCalled, false);
  assert.equal(result.status, 'succeeded');
  assert.equal(result.taskCount, 1);
  assert.deepEqual(JSON.parse(await readFile(fixture.resultPath, 'utf8')), result);
});

test('非法 YAML 写入失败结果并保留原始错误', async () => {
  const fixture = await yamlFixture('computer: {}\ntasks: []\n');
  await assert.rejects(executeMidsceneYaml({ ...fixture, dryRun: true }), /tasks 必须是非空数组/);
  const result = JSON.parse(await readFile(fixture.resultPath, 'utf8'));
  assert.equal(result.status, 'failed');
  assert.match(result.error, /tasks 必须是非空数组/);
});

test('实际执行设置本次报告目录并在成功后销毁 Agent 和恢复环境', async () => {
  const fixture = await yamlFixture('tasks:\n  - name: test\n    flow:\n      - sleep: 1\n');
  const previousRequired = Object.fromEntries(
    ['MIDSCENE_MODEL_BASE_URL', 'MIDSCENE_MODEL_NAME', 'MIDSCENE_MODEL_API_KEY', 'MIDSCENE_MODEL_FAMILY'].map(
      (key) => [key, process.env[key]],
    ),
  );
  const previousRunDirectory = process.env.MIDSCENE_RUN_DIR;
  for (const key of Object.keys(previousRequired)) process.env[key] = 'test';
  process.env.MIDSCENE_RUN_DIR = 'previous-directory';
  let destroyed = false;
  try {
    const result = await executeMidsceneYaml({
      ...fixture,
      dryRun: false,
      agentFactory: async () => {
        assert.equal(process.env.MIDSCENE_RUN_DIR, path.join(fixture.runDirectory, 'midscene'));
        return {
          runYaml: async () => ({ result: { ok: true } }),
          destroy: async () => {
            destroyed = true;
          },
        };
      },
    });
    assert.equal(result.status, 'succeeded');
    assert.deepEqual(result.midsceneResult, { ok: true });
    assert.equal(destroyed, true);
    assert.equal(process.env.MIDSCENE_RUN_DIR, 'previous-directory');
  } finally {
    for (const [key, value] of Object.entries(previousRequired)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    if (previousRunDirectory === undefined) delete process.env.MIDSCENE_RUN_DIR;
    else process.env.MIDSCENE_RUN_DIR = previousRunDirectory;
  }
});

test('Agent 执行失败仍会销毁并恢复环境', async () => {
  const fixture = await yamlFixture('tasks:\n  - name: test\n    flow:\n      - sleep: 1\n');
  const required = ['MIDSCENE_MODEL_BASE_URL', 'MIDSCENE_MODEL_NAME', 'MIDSCENE_MODEL_API_KEY', 'MIDSCENE_MODEL_FAMILY'];
  const previous = Object.fromEntries(required.map((key) => [key, process.env[key]]));
  const previousRunDirectory = process.env.MIDSCENE_RUN_DIR;
  for (const key of required) process.env[key] = 'test';
  let destroyed = false;
  try {
    await assert.rejects(
      executeMidsceneYaml({
        ...fixture,
        dryRun: false,
        agentFactory: async () => ({
          runYaml: async () => {
            throw new Error('KeyboardTypeText 不支持字符');
          },
          destroy: async () => {
            destroyed = true;
          },
        }),
      }),
      /KeyboardTypeText 不支持字符/,
    );
    assert.equal(destroyed, true);
    assert.equal(process.env.MIDSCENE_RUN_DIR, previousRunDirectory);
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    if (previousRunDirectory === undefined) delete process.env.MIDSCENE_RUN_DIR;
    else process.env.MIDSCENE_RUN_DIR = previousRunDirectory;
  }
});
