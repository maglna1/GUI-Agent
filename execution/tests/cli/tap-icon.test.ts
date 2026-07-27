import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { CliUsageError, runCliCommand } from '../../cua/cli/main.js';

const PNG_BYTES = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/** 造一个 library root，里面有 project/<components>/<label>.png。 */
async function makeLibraryWithIcon(label: string): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), 'tap-icon-lib-'));
  const dir = path.join(
    root, 'projA', 'components_review_ui_mutimodal_memory_manual', 'components',
  );
  await mkdir(dir, { recursive: true });
  await writeFile(path.join(dir, `${label}.png`), PNG_BYTES);
  return root;
}

/** 临时 CUA_DATA_ROOT，让 requireDataPaths 通过。 */
async function makeDataRoot(): Promise<string> {
  const root = await mkdtemp(path.join(os.tmpdir(), 'tap-icon-data-'));
  await mkdir(path.join(root, 'runs'), { recursive: true });
  return root;
}

test('act tap-icon --dry-run 找到图标并生成 YAML 不调模型', async () => {
  const library = await makeLibraryWithIcon('minimax_code');
  const dataRoot = await makeDataRoot();
  const out = JSON.parse(
    await runCliCommand([
      'act', 'tap-icon',
      '--label', 'minimax_code',
      '--icon-library', library,
      '--data-root', dataRoot,
      '--dry-run',
    ]),
  );
  assert.equal(out.mode, 'tap-icon');
  assert.equal(out.label, 'minimax_code');
  assert.match(out.iconPath, /minimax_code\.png$/);
  assert.equal(out.executor.dryRun, true);
  assert.equal(out.executor.status, 'succeeded');
});

test('act tap-icon 缺 --label 报 CliUsageError', async () => {
  const dataRoot = await makeDataRoot();
  await assert.rejects(
    runCliCommand(['act', 'tap-icon', '--data-root', dataRoot, '--dry-run']),
    (err: unknown) => err instanceof CliUsageError,
  );
});

test('act tap-icon 找不到 label 时抛错（dry-run 也会先找图标）', async () => {
  const library = await makeLibraryWithIcon('exists');
  const dataRoot = await makeDataRoot();
  await assert.rejects(
    runCliCommand([
      'act', 'tap-icon',
      '--label', 'missing_label',
      '--icon-library', library,
      '--data-root', dataRoot,
      '--dry-run',
    ]),
    /未找到 label="missing_label"/,
  );
});
