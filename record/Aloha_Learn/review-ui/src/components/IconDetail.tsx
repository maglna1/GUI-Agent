import { useState } from "react";
import type { Icon } from "../types";
import { sanitize, isValidLabel } from "../lib/sanitize";

interface Props {
  icon: Icon;
  initialLabel: string;
  onSave: (label: string) => void;
  onSkip: () => void;
  onCancel: () => void;
}

export function IconDetail({ icon, initialLabel, onSave, onSkip, onCancel }: Props) {
  const [raw, setRaw] = useState(initialLabel);

  let sanitized = "";
  try {
    sanitized = sanitize(raw);
  } catch {
    sanitized = "";
  }

  const canSave = isValidLabel(sanitized);

  return (
    <div className="modal-backdrop" role="dialog" aria-label="Edit icon">
      <div className="modal">
        <img src={icon.icon_url} alt={icon.llm_label} className="modal-img" />
        <div className="modal-body">
          <label className="modal-label">Label</label>
          <input
            className="modal-input"
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
          />
          <div className="modal-sanitized">
            sanitized: <code>{sanitized || "(empty)"}</code>
          </div>
          <div className="modal-actions">
            <button onClick={onCancel} className="btn">取消</button>
            <button onClick={onSkip} className="btn">跳过</button>
            <button
              onClick={() => onSave(sanitized)}
              disabled={!canSave}
              className="btn btn-primary"
            >保存</button>
          </div>
        </div>
      </div>
    </div>
  );
}