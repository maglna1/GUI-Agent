import { useEffect, useState } from "react";
import type { Click, Decision } from "../types";
import { getIcon } from "../api/client";
import { LabelPicker } from "./LabelPicker";

interface Props {
  /** 1-based visual row number (top-to-bottom). Shown alongside step_idx
   *  so users can count rows naturally without getting confused. */
  rowNumber: number;
  click: Click;
  decision: Decision;
  labels: string[];
  onChange: (next: Decision) => void;
  /** Read-only mode (history view): hide all edit controls. */
  readOnly?: boolean;
}

function formatCoord(c: number | null): string {
  return c === null || Number.isNaN(c) ? "-" : String(c);
}

function formatTs(ts: number): string {
  return `${ts.toFixed(2)}s`;
}

function formatSoftware(s: string): string {
  return s || "(未记录)";
}

export function ClickRow({ rowNumber, click, decision, labels, onChange, readOnly }: Props) {
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
        {readOnly ? (
          <div className="click-row-readonly">
            {decision.is_icon ? (
              <>
                <span className="click-row-readonly-badge click-row-readonly-badge--icon">
                  ✓ 图标点击
                </span>
                {decision.label && (
                  <div className="click-row-label-picker-icon">
                    {preview ? (
                      <img src={preview} alt={decision.label} />
                    ) : (
                      <span className="click-row-thumb-fallback">…</span>
                    )}
                    <code>{decision.label}</code>
                  </div>
                )}
              </>
            ) : (
              <span className="click-row-readonly-badge click-row-readonly-badge--normal">
                普通点击
              </span>
            )}
          </div>
        ) : (
          <>
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
            <div className="click-row-label-picker">
              <span>对应图标库标签</span>
              <LabelPicker
                labels={labels}
                value={decision.label}
                disabled={!decision.is_icon || labels.length === 0}
                onChange={(label) => onChange({ is_icon: true, label })}
                ariaLabel={`选择 Row ${rowNumber}（步骤 ${click.step_idx}）的图标标签`}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
