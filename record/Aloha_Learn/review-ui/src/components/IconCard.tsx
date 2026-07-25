import type { Icon, Decision } from "../types";

interface Props {
  icon: Icon;
  decision: Decision | null;
  existingLabels: string[];
  onAccept: (filename: string) => void;
  onEdit: (filename: string) => void;
  onSkip: (filename: string) => void;
}

export function IconCard({ icon, decision, existingLabels, onAccept, onEdit, onSkip }: Props) {
  const isExisting = existingLabels.includes(icon.llm_label);
  return (
    <div className="icon-card" data-filename={icon.filename}>
      <img src={icon.icon_url} alt={icon.llm_label} className="icon-card-img" />
      <div className="icon-card-label">
        <span className="icon-card-label-text">{icon.llm_label}</span>
        {icon.is_timestamp_fallback && (
          <span className="icon-card-badge fallback">⏱ LLM 未命名</span>
        )}
        {isExisting && !icon.is_timestamp_fallback && (
          <span className="icon-card-badge conflict">已存在（将 upsert）</span>
        )}
      </div>
      <div className="icon-card-actions">
        <button
          className={`icon-card-btn accept ${decision?.action === "accept" ? "active" : ""}`}
          onClick={() => onAccept(icon.filename)}
          aria-label="accept"
        >✓</button>
        <button
          className={`icon-card-btn edit ${decision?.action === "edit" ? "active" : ""}`}
          onClick={() => onEdit(icon.filename)}
          aria-label="edit"
        >✎</button>
        <button
          className={`icon-card-btn skip ${decision?.action === "skip" ? "active" : ""}`}
          onClick={() => onSkip(icon.filename)}
          aria-label="skip"
        >⨯</button>
      </div>
    </div>
  );
}