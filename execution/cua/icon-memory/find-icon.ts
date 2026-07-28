import { readdir, stat } from 'node:fs/promises';
import path from 'node:path';

/**
 * 图标记忆库扫描：在给定的 library roots 下找按 label 命名的图标 PNG。
 *
 * 每个 library root 下的目录结构约定：
 *   <libraryRoot>/<project>/components_review_ui_mutimodal_memory_manual/components/<label>.png
 *
 * 这是 record 流程 review UI 的产物：每个 project 跑完 review 后，图标按 LLM
 * 命名落到该目录。同名 label 在多个 project 下可能都存在，本函数按 project
 * 名字母序取第一个命中。
 *
 * @param label   图标 label，如 "minimax_code"。匹配 <label>.png（大小写敏感）。
 * @param roots   library root 路径数组（通常为 [record/Aloha_Learn/projects]）。
 * @returns       命中图标的绝对路径；找不到返回 undefined。
 */
export async function findIconByLabel(
  label: string,
  roots: string[],
): Promise<string | undefined> {
  if (!label) throw new Error('label 不能为空');
  if (roots.length === 0) throw new Error('roots 不能为空');

  const iconName = `${label}.png`;
  const candidates: string[] = [];

  for (const root of roots) {
    const projects = await listChildDirectories(root);
    for (const projectDir of projects) {
      const iconPath = path.join(
        projectDir,
        'components_review_ui_mutimodal_memory_manual',
        'components',
        iconName,
      );
      try {
        const s = await stat(iconPath);
        if (s.isFile()) candidates.push(iconPath);
      } catch {
        // 不存在或不可读，跳过。
      }
    }
  }

  if (candidates.length === 0) return undefined;
  // 按路径字母序取第一个，保证可复现。
  candidates.sort();
  return candidates[0];
}

/**
 * 列出 root 下的直接子目录（非递归）。root 不存在时返回空数组。
 */
async function listChildDirectories(root: string): Promise<string[]> {
  let entries: import('node:fs').Dirent[];
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }
  const dirs: string[] = [];
  for (const entry of entries) {
    if (entry.isDirectory()) dirs.push(path.join(root, entry.name));
  }
  return dirs;
}
