interface Props {
  iconCount: number;
  normalCount: number;
  onCancel: () => void;
  onConfirm: () => void;
}

export function SubmitConfirm({ iconCount, normalCount, onCancel, onConfirm }: Props) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <h2>确认提交</h2>
        <ul>
          <li>是图标点击：{iconCount} 个（会注入 icon 参考图到对应操作）</li>
          <li>普通点击：{normalCount} 个（不注入，保持 LLM 描述）</li>
        </ul>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
          提交后窗口关闭，回放到 trace 生成会继续。
        </p>
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>取消</button>
          <button className="btn btn-primary" onClick={onConfirm}>确认</button>
        </div>
      </div>
    </div>
  );
}
