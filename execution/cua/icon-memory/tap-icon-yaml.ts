import { loadIconAsDataUrl } from './load-icon.js';

/**
 * 构造一个"按 label 点击屏幕图标"的 Midscene YAML 文档。
 *
 * YAML 形态：
 * ```
 * tasks:
 *   - name: tap-icon
 *     flow:
 *       - aiTap:
 *           prompt: 点击屏幕上的 <label> 图标
 *           locate:
 *             images:
 *               - name: <label>
 *                 url: data:image/png;base64,...
 * ```
 *
 * aiTap 的 `locate.images` 让 Midscene 的 VLM 同时看到参考图标和当前屏幕
 * 截图，返回图标在屏幕上的坐标并点击。这是多模态定位，不是 cv2 模板匹配。
 *
 * @param label    图标 label（如 "minimax_code"），用于 prompt 和 image.name。
 * @param iconPath 图标 PNG 绝对路径，会被读取转成 data URL 内联进 YAML。
 * @returns        可直接喂给 executeMidsceneYaml 的 YAML 字符串。
 */
export async function buildTapIconYaml(label: string, iconPath: string): Promise<string> {
  if (!label) throw new Error('label 不能为空');
  const dataUrl = await loadIconAsDataUrl(iconPath);
  // prompt 用中文，与项目语言一致（AGENT.md #1）。
  const prompt = `点击屏幕上的 ${label} 图标`;
  // YAML 手写而非用 js-yaml dump，确保 aiTap 的对象形态与 Midscene 期望一致，
  // 且 data URL（含 base64 的 +/=）不会被错误转义。data URL 里没有 YAML 特殊
  // 字符（冒号后跟 base64 是合法的），但为保险用单引号包裹。
  return `tasks:
  - name: tap-icon
    flow:
      - aiTap:
          prompt: ${yamlString(prompt)}
          locate:
            images:
              - name: ${yamlString(label)}
                url: ${yamlString(dataUrl)}
`;
}

/**
 * 把字符串包成 YAML 单引号字符串。YAML 单引号字符串里唯一的转义是单引号
 * 本身（'' 表示一个 '）。data URL 和中文 label 都不含单引号，但这里仍按
 * 规范处理以防 label 含特殊字符。
 */
function yamlString(s: string): string {
  return `'${s.replaceAll(/'/g, "''")}'`;
}
