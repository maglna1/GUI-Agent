import { useEffect, useRef, useState } from "react";

interface Props {
  labels: string[];
  value: string;
  disabled?: boolean;
  onChange: (label: string) => void;
  /** aria-label for the trigger button. */
  ariaLabel?: string;
}

/** Label dropdown that shows icon thumbnails (not just names) so the user
 * can visually match the click target to a library icon. Replaces the old
 * bare <select> in ClickRow. */
export function LabelPicker({ labels, value, disabled, onChange, ariaLabel }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const filtered = labels.filter((l) =>
    query.trim() ? l.toLowerCase().includes(query.trim().toLowerCase()) : true
  );

  const trigger = value || (labels.length === 0 ? "(库为空)" : "- 选择 -");

  return (
    <div className="label-picker" ref={ref}>
      <button
        type="button"
        className="label-picker-trigger"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        aria-label={ariaLabel}
        data-testid="label-picker-trigger"
      >
        {value && (
          <img
            src={`/api/icon/${encodeURIComponent(value)}`}
            alt=""
            className="label-picker-trigger-icon"
          />
        )}
        <span className="label-picker-trigger-text">{trigger}</span>
        <span className="label-picker-caret">▾</span>
      </button>
      {open && !disabled && (
        <div className="label-picker-dropdown" data-testid="label-picker-dropdown">
          <input
            type="text"
            className="label-picker-search"
            placeholder="搜索标签..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            spellCheck={false}
          />
          <div className="label-picker-list">
            {filtered.length === 0 && (
              <div className="label-picker-empty">无匹配标签</div>
            )}
            {filtered.map((label) => (
              <button
                key={label}
                type="button"
                className={`label-picker-option${label === value ? " selected" : ""}`}
                onClick={() => {
                  onChange(label);
                  setOpen(false);
                  setQuery("");
                }}
                title={label}
              >
                <img
                  src={`/api/icon/${encodeURIComponent(label)}`}
                  alt={label}
                  className="label-picker-option-icon"
                />
                <span className="label-picker-option-name">{label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
