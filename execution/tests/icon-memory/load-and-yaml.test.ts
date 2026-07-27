import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { loadIconAsDataUrl } from '../../cua/icon-memory/load-icon.js';
import { buildTapIconYaml } from '../../cua/icon-memory/tap-icon-yaml.js';

const PNG_BYTES = Buffer.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00,
]);

test('loadIconAsDataUrl 返回 data:image/png;base64, 前缀', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'icon-load-'));
  const iconPath = path.join(dir, 'x.png');
  await writeFile(iconPath, PNG_BYTES);
  const url = await loadIconAsDataUrl(iconPath);
  assert.ok(url.startsWith('data:image/png;base64,'));
  // base64 部分应能解码回原字节
  const b64 = url.slice('data:image/png;base64,'.length);
  assert.equal(Buffer.from(b64, 'base64').toString('hex'), PNG_BYTES.toString('hex'));
});

test('buildTapIconYaml 产出含 aiTap + locate.images 的 YAML', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'icon-yaml-'));
  const iconPath = path.join(dir, 'minimax_code.png');
  await writeFile(iconPath, PNG_BYTES);
  const yaml = await buildTapIconYaml('minimax_code', iconPath);
  // 关键结构
  assert.match(yaml, /tasks:/);
  assert.match(yaml, /- name: tap-icon/);
  assert.match(yaml, /- aiTap:/);
  assert.match(yaml, /prompt: '点击屏幕上的 minimax_code 图标'/);
  assert.match(yaml, /locate:/);
  assert.match(yaml, /images:/);
  assert.match(yaml, /- name: 'minimax_code'/);
  assert.match(yaml, /url: 'data:image\/png;base64,/);
});

test('buildTapIconYaml label 为空抛错', async () => {
  await assert.rejects(() => buildTapIconYaml('', '/tmp/x.png'), /label 不能为空/);
});

test('buildTapIconYaml label 含单引号时正确转义', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'icon-yaml-'));
  const iconPath = path.join(dir, "foo'bar.png");
  await writeFile(iconPath, PNG_BYTES);
  const yaml = await buildTapIconYaml("foo'bar", iconPath);
  // YAML 单引号字符串中单引号转义为 ''
  assert.match(yaml, /name: 'foo''bar'/);
});
