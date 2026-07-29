interface Props {
  decided: number;
  total: number;
}

export function DoneScreen({ decided, total }: Props) {
  return (
    <div className="done-screen">
      <h1>已提交</h1>
      <p>已为 {decided} 个 click 确认图标关联。</p>
      <div className="done-screen-summary">
        <div>
          <strong>{total}</strong>
          <div style={{ color: "var(--color-text-muted)" }}>click 总数</div>
        </div>
        <div>
          <strong>{decided}</strong>
          <div style={{ color: "var(--color-text-muted)" }}>标记为图标</div>
        </div>
      </div>
      <p>可以关闭此窗口；trace 生成会继续。</p>
    </div>
  );
}
