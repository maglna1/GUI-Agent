import { useEffect, useState } from "react";
import type { Click, Decision } from "../types";
import { getIcon } from "../api/client";

interface Props {
  /** 1-based visual row number (top-to-bottom). Shown alongside step_idx
   *  so users can count rows naturally without getting confused. */
  rowNumber: number;
  click: Click;
  decision: Decision;
  labels: string[];
  onChange: (next: Decision) => void;
}

function formatCoord(c: number | null): string {
  return c === null || Number.isNaN(c) ? "—" : String(c);
}

function formatTs(ts: number): string {
  return `${ts.toFixed(2)}s`;
}

function formatSoftware(s: string): string {
  return s || "(未记录)";
}

export function ClickRow({ rowNumber, click, decision, labels, onChange }: Props) {
  const [preview, setPreview] = useState<string | null>(null);

  // Fetch a tiny preview of the icon once a label is chosen. Cache-bust by
  // label so a re-pick immediately invalidates the prior image.
  useEffect(() => {
    let cancelled = false;
    setPreview(null);
    if (!decision.is_icon || !decision.label) return;
    getIcon(decision.label)
      .then((res) => {
        if (!cancelled) setPreview(res.url);
      })
      .catch(() => {
        if (!cancelled) setPreview(null);
      });
    return () => {
      cancelled = true;
    };
  }, [decision.is_icon, decision.label]);

  return (
    <div
      className={`click-row${decision.is_icon ? " is-icon" : ""}`}
      data-step-idx={click.step_idx}
    >
      <div className="click-row-thumb">
        <img src={click.screenshot_url} alt={`screenshot for step ${click.step_idx}`} />
      </div>
      <div className="click-row-body">
        <div className="click-row-meta">
          <span
            className="click-row-meta-pill click-row-meta-pill-row"
            data-testid="row-number"
          >
            Row {rowNumber}
          </span>
          <span className="click-row-meta-pill">步骤 #{click.step_idx}</span>
          <span className="click-row-meta-pill">{formatTs(click.timestamp)}</span>
          <span className="click-row-meta-pill">
            ({formatCoord(click.coords[0])}, {formatCoord(click.coords[1])})
          </span>
          <span className="click-row-meta-pill" title={click.current_software}>
            {formatSoftware(click.current_software)}
          </span>
        </div>
        <div className="click-row-prompt" title={click.prompt}>
          {click.prompt || "(无 LLM 描述)"}
        </div>
      </div>
      <div className="click-row-controls">
        <label className="click-row-toggle">
          <input
            type="checkbox"
            checked={decision.is_icon}
            onChange={(e) => {
              const isIcon = e.target.checked;
              onChange({
                is_icon: isIcon,
                label: isIcon ? decision.label : "",
              });
            }}
            aria-label={`标记 Row ${rowNumber}（步骤 ${click.step_idx}）为图标点击`}
          />
          是图标点击
        </label>
        <label className="click-row-label-picker">
          <span>对应图标库标签</span>
          <select
            disabled={!decision.is_icon || labels.length === 0}
            value={decision.label}
            onChange={(e) =>
              onChange({ is_icon: true, label: e.target.value })
            }
            aria-label={`选择 Row ${rowNumber}（步骤 ${click.step_idx}）的图标标签`}
          >
            <option value="">
              {labels.length === 0 ? "(图标库为空)" : "— 选择 —"}
            </option>
            {labels.map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>
          {decision.is_icon && decision.label && (
            <div className="click-row-label-picker-icon">
              {preview ? (
                <img src={preview} alt={decision.label} />
              ) : (
                <span className="click-row-thumb-fallback">…</span>
              )}
              <code>{decision.label}</code>
            </div>
          )}
        </label>
      </div>
    </div>
  );
}
