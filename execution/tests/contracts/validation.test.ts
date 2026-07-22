import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import {
  readExecutorResult,
  readSceneManifest,
  readShowuiTrace,
  readTaskManifest,
} from '../../cua/contracts/validation.js';

const executionRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const fixtures = path.join(executionRoot, 'tests', 'fixtures', 'contracts');

test('现有场景、任务和 trace 通过边界契约', async () => {
  const sceneRoot = path.join(executionRoot, 'projects', 'browser-demo');
  const taskRoot = path.join(sceneRoot, 'air-tickets-demo');
  const scene = await readSceneManifest(path.join(sceneRoot, 'scene.json'));
  const task = await readTaskManifest(path.join(taskRoot, 'task.json'));
  const trace = await readShowuiTrace(path.join(taskRoot, 'source', 'showui-trace.json'));

  assert.equal(scene.scene, 'browser-demo');
  assert.equal(task.task, 'air-tickets-demo');
  assert.equal(trace.trajectory.length, 16);
});

test('任务清单未知字段会暴露文件和字段路径', async () => {
  const source = path.join(fixtures, 'invalid-task-unknown-field.json');
  await assert.rejects(readTaskManifest(source), (error: Error) => {
    assert.match(error.message, /invalid-task-unknown-field\.json/);
    assert.match(error.message, /additional properties/);
    return true;
  });
});

test('执行结果错误类型和时间格式被拒绝', async () => {
  const source = path.join(fixtures, 'invalid-execution-result.json');
  await assert.rejects(readExecutorResult(source), /\/dryRun.*must be boolean|\/finishedAt/);
});

test('trace 缺少结构化 operation 时直接失败', async () => {
  const source = path.join(fixtures, 'invalid-showui-trace.json');
  await assert.rejects(readShowuiTrace(source), /operation/);
});
