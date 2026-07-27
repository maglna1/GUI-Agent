interface Props {
  totalIcons: number;
  accepted: number;
  edited: number;
  skipped: number;
  reviewed: number;
  manualMode: boolean;
  onToggleManual: (next: boolean) => void;
  onAcceptAll: () => void;
  onSubmit: () => void;
}

export function TopBar({
  totalIcons, accepted, edited, skipped, reviewed,
  manualMode, onToggleManual, onAcceptAll, onSubmit,
}: Props) {
  const progressPct = totalIcons === 0 ? 0 : Math.min(100, Math.round((reviewed / totalIcons) * 100));

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-brand-mark" aria-hidden="true">R</span>
        <span>Record Icon Review</span>
      </div>

      <div className="topbar-counts">
        <span className="topbar-pill accept">✓ {accepted}</span>
        <span className="topbar-pill edit">✎ {edited}</span>
        <span className={`topbar-pill skip${skipped > 0 ? " active" : ""}`}>⨯ {skipped}</span>
        <span style={{ color: "var(--color-text-subtle)", marginLeft: "var(--space-1)" }}>
          / {totalIcons}
        </span>
      </div>

      <div
        className="topbar-progress"
        role="progressbar"
        aria-valuenow={reviewed}
        aria-valuemin={0}
        aria-valuemax={totalIcons}
      >
        <div className="topbar-progress-bar" style={{ width: `${progressPct}%` }} />
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
        <button onClick={onAcceptAll} className="btn">全部接受</button>
        <button onClick={onSubmit} className="btn btn-primary">提交</button>
      </div>
    </header>
  );
}