import type { Icon, Decision } from "../types";

interface Props {
  icon: Icon;
  decision: Decision | null;
  existingLabels: string[];
  isFocused?: boolean;
  onMouseEnter?: () => void;
  onAccept: (filename: string) => void;
  onEdit: (filename: string) => void;
  onSkip: (filename: string) => void;
}

export function IconCard({
  icon, decision, existingLabels, isFocused, onMouseEnter,
  onAccept, onEdit, onSkip,
}: Props) {
  const isExisting = existingLabels.includes(icon.llm_label);
  const action = decision?.action;
  const stateClass = action ? ` ${action}` : "";
  return (
    <div
      className={`icon-card${stateClass}`}
      data-filename={icon.filename}
      tabIndex={isFocused ? 0 : -1}
      onMouseEnter={onMouseEnter}
    >
      <div className="icon-card-thumb" onClick={() => onEdit(icon.filename)} role="button">
        <img src={icon.icon_url} alt={icon.llm_label} className="icon-card-img" />
      </div>
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
          className={`icon-card-btn accept${action === "accept" ? " active" : ""}`}
          onClick={() => onAccept(icon.filename)}
          aria-label="accept"
        >✓</button>
        <button
          className={`icon-card-btn edit${action === "edit" ? " active" : ""}`}
          onClick={() => onEdit(icon.filename)}
          aria-label="edit"
        >✎</button>
        <button
          className={`icon-card-btn skip${action === "skip" ? " active" : ""}`}
          onClick={() => onSkip(icon.filename)}
          aria-label="skip"
        >⨯</button>
      </div>
    </div>
  );
}