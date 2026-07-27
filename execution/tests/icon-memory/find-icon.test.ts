import assert from 'node:assert/strict';
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { findIconByLabel } from '../../cua/icon-memory/find-icon.js';

/** 在 tmp 下造一个 project 的 components/ 目录并写入空 PNG。 */
async function makeProjectIcon(libraryRoot: string, projectName: string, label: string): Promise<string> {
  const dir = path.join(
    libraryRoot,
    projectName,
    'components_review_ui_mutimodal_memory_manual',
    'components',
  );
  await mkdir(dir, { recursive: true });
  const iconPath = path.join(dir, `${label}.png`);
  // 1x1 透明 PNG 的字节数据，足够 stat.isFile() 通过。
  const PNG_BYTES = Buffer.from([
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
  ]);
  await writeFile(iconPath, PNG_BYTES);
  return iconPath;
}

test('findIconByLabel 命中单个 project 下的 label 图标', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'icon-mem-'));
  const expected = await makeProjectIcon(root, 'projA', 'minimax_code');
  const got = await findIconByLabel('minimax_code', [root]);
  assert.equal(got, expected);
});

test('findIconByLabel 多个 project 同名时按 project 名字母序取第一个', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'icon-mem-'));
  await makeProjectIcon(root, 'projB', 'chrome');
  const expected = await makeProjectIcon(root, 'projA', 'chrome');
  const got = await findIconByLabel('chrome', [root]);
  assert.equal(got, expected);
});

test('findIconByLabel 多个 library root 时跨 root 查找', async () => {
  const root1 = await mkdtemp(path.join(os.tmpdir(), 'icon-mem-1-'));
  const root2 = await mkdtemp(path.join(os.tmpdir(), 'icon-mem-2-'));
  await makeProjectIcon(root1, 'projA', 'edge');
  const expected2 = await makeProjectIcon(root2, 'projB', 'edge');
  // root1/projA 字母序早于 root2/projB，应返回 root1 的
  const got = await findIconByLabel('edge', [root1, root2]);
  assert.ok(got);
  assert.notEqual(got, expected2);
});

test('findIconByLabel 找不到时返回 undefined', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'icon-mem-'));
  await makeProjectIcon(root, 'projA', 'exists');
  const got = await findIconByLabel('missing', [root]);
  assert.equal(got, undefined);
});

test('findIconByLabel 跳过不存在 components/ 目录的 project', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'icon-mem-'));
  // 一个 project 有图标，另一个没有
  await mkdir(path.join(root, 'emptyProj'), { recursive: true });
  const expected = await makeProjectIcon(root, 'projA', 'ssrun');
  const got = await findIconByLabel('ssrun', [root]);
  assert.equal(got, expected);
});

test('findIconByLabel label 为空抛错', async () => {
  await assert.rejects(() => findIconByLabel('', ['/tmp']), /label 不能为空/);
});

test('findIconByLabel roots 为空抛错', async () => {
  await assert.rejects(() => findIconByLabel('x', []), /roots 不能为空/);
});

test('findIconByLabel library root 不存在时返回 undefined 不抛错', async () => {
  const got = await findIconByLabel('x', [path.join(os.tmpdir(), 'nonexistent-icon-mem')]);
  assert.equal(got, undefined);
});
