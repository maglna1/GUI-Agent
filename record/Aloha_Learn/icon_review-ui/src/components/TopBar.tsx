interface Props {
  totalClicks: number;
  iconCount: number;
  submitted: boolean;
  onSubmit: () => void;
}

export function TopBar({ totalClicks, iconCount, submitted, onSubmit }: Props) {
  const reviewed = iconCount;
  const progressPct = totalClicks === 0 ? 0 : Math.min(100, Math.round((reviewed / totalClicks) * 100));
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="topbar-brand-mark" aria-hidden="true">I</span>
        <span>Record Icon Click Review</span>
      </div>

      <div className="topbar-counts">
        <span className="topbar-pill icon">是图标 {iconCount}</span>
        <span className="topbar-pill normal">普通 {totalClicks - iconCount}</span>
        <span style={{ color: "var(--color-text-subtle)", marginLeft: "var(--space-1)" }}>
          / {totalClicks}
        </span>
      </div>

      <div
        className="topbar-progress"
        role="progressbar"
        aria-valuenow={reviewed}
        aria-valuemin={0}
        aria-valuemax={totalClicks}
      >
        <div className="topbar-progress-bar" style={{ width: `${progressPct}%` }} />
      </div>

      <div className="topbar-actions">
        <button
          onClick={onSubmit}
          className="btn btn-primary"
          disabled={submitted || totalClicks === 0}
        >
          {submitted ? "已提交" : "提交并关闭"}
        </button>
      </div>
    </header>
  );
}
