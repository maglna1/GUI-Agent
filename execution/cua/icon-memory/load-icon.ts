import { readFile } from 'node:fs/promises';

/**
 * 读取 PNG 文件并转为 data URL（base64）。
 *
 * Midscene aiTap 的 `locate.images[].url` 接受 data URL 形式的参考图片。
 * 用 data URL 而非 http URL，避免再起一个静态文件服务器；图标本身很小
 *（30×30 PNG 通常 < 2KB），base64 内联进 YAML 完全可接受。
 *
 * @param iconPath PNG 绝对路径。
 * @returns 形如 `data:image/png;base64,<base64>` 的字符串。
 */
export async function loadIconAsDataUrl(iconPath: string): Promise<string> {
  const bytes = await readFile(iconPath);
  return `data:image/png;base64,${bytes.toString('base64')}`;
}
