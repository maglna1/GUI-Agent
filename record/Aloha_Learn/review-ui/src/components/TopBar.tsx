interface Props {
  totalIcons: number;
  accepted: number;
  edited: number;
  skipped: number;
  manualMode: boolean;
  onToggleManual: (next: boolean) => void;
  onAcceptAll: () => void;
  onSubmit: () => void;
}

export function TopBar({
  totalIcons, accepted, edited, skipped,
  manualMode, onToggleManual, onAcceptAll, onSubmit,
}: Props) {
  return (
    <header className="topbar">
      <h1>Record Icon Review</h1>
      <div className="topbar-counts">
        共 {totalIcons} 张 · {accepted} accept · {edited} edit · {skipped} skip
      </div>
      <div className="topbar-actions">
        <label className="manual-toggle">
          <input
            type="checkbox"
            checked={manualMode}
            onChange={(e) => onToggleManual(e.target.checked)}
            aria-label="全手动"
          />
          全手动
        </label>
        <button onClick={onAcceptAll} className="btn btn-secondary">全部接受</button>
        <button onClick={onSubmit} className="btn btn-primary">提交</button>
      </div>
    </header>
  );
}