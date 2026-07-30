import { useState } from "react";
import { postPipelineLabels } from "../api/client";
import type { PipelineState } from "../types";

export interface IconDecision {
  is_icon: boolean;
  label: string;
}

interface Props {
  state: PipelineState;
  /** Local override so we can edit before submitting. */
  decisions: Record<string, IconDecision>;
  llmLabels: Record<string, string>;
  onChange?: (next: Record<string, IconDecision>) => void;
  onSubmitted?: () => void;
  /** Read-only history view: hide all edit controls + submit. */
  readOnly?: boolean;
}

/** Step 1: 图标 grid。每张 icon 可勾/拒/编辑，类似原 review-ui 的样式。 */
export function PipelineStep1Icons({ decisions, llmLabels, onChange, onSubmitted, readOnly }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<string>("");

  const filenames = Object.keys(decisions).sort();
  const acceptedCount = filenames.filter((f) => decisions[f]?.is_icon).length;
  const skippedCount = filenames.length - acceptedCount;

  function acceptOne(filename: string) {
    const prev = decisions[filename];
    onChange?.({
      ...decisions,
      [filename]: {
        is_icon: true,
        label: prev?.label || llmLabels[filename] || "",
      },
    });
  }

  function skipOne(filename: string) {
    onChange?.({
      ...decisions,
      [filename]: { is_icon: false, label: "" },
    });
  }

  function acceptAll() {
    const next: Record<string, IconDecision> = {};
    for (const f of filenames) {
      next[f] = {
        is_icon: true,
        label: decisions[f]?.label || llmLabels[f] || "",
      };
    }
    onChange?.(next);
  }

  function skipAll() {
    const next: Record<string, IconDecision> = {};
    for (const f of filenames) {
      next[f] = { is_icon: false, label: "" };
    }
    onChange?.(next);
  }

  function startEditing(filename: string) {
    setEditing(filename);
    setEditDraft(decisions[filename]?.label || llmLabels[filename] || "");
  }

  function commitEditing() {
    if (!editing) return;
    const trimmed = editDraft.trim();
    onChange?.({
      ...decisions,
      [editing]: { is_icon: true, label: trimmed },
    });
    setEditing(null);
    setEditDraft("");
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const cleaned: Record<string, string> = {};
      for (const [k, v] of Object.entries(decisions)) {
        if (v.is_icon && v.label.trim()) cleaned[k] = v.label.trim();
      }
      const res = await postPipelineLabels(cleaned);
      if (!res.ok) {
        throw new Error("submit failed");
      }
      onSubmitted?.();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setSubmitting(false);
    }
  }

  if (filenames.length === 0) {
    return (
      <div className="pipeline-step pipeline-step--1">
        <h2>Step 1 · 图标命名</h2>
        <div className="pipeline-empty">还没有图标；先跑 parser.py step 1+2。</div>
      </div>
    );
  }

  return (
    <div className="pipeline-step pipeline-step--1" data-testid="pipeline-step-1">
      <h2>
        Step 1 · 图标命名（LLM 出名 + 人工确认）
        <span className="step1-counts">
          <span className="step1-pill step1-pill--ok">{acceptedCount} 接受</span>
          <span className="step1-pill step1-pill--skip">{skippedCount} 跳过</span>
          <span className="step1-pill step1-pill--total">/ {filenames.length}</span>
        </span>
      </h2>
      <p className="pipeline-step-help">
        LLM 给每个图标起了一个 snake_case 名。在下方逐张 接受 / 编辑 / 跳过：
        <strong>接受</strong> 会保留标签；<strong>编辑</strong> 可以改名；
        <strong>跳过</strong> 不写入图标库。
      </p>

      {!readOnly && (
        <div className="step1-bulk-actions">
          <button className="btn" onClick={acceptAll} data-testid="step1-accept-all">
            全量接受
          </button>
          <button className="btn" onClick={skipAll} data-testid="step1-skip-all">
            全量跳过
          </button>
          <span className="step1-bulk-meta">
            已 {acceptedCount} / {filenames.length} 接受
          </span>
        </div>
      )}

      <div className="step1-grid">
        {filenames.map((f) => {
          const d = decisions[f] ?? { is_icon: false, label: "" };
          const llmLabel = llmLabels[f] || "";
          const state = d.is_icon ? "accepted" : "skipped";
          return (
            <div
              key={f}
              className={`step1-card step1-card--${state}`}
              data-filename={f}
              data-state={state}
            >
              <div className="step1-card-thumb">
                <img
                  src={`/api/pipeline/icon/${encodeURIComponent(f)}`}
                  alt={f}
                  loading="lazy"
                />
                {!d.is_icon && (
                  <div className="step1-card-skipped-overlay">已跳过</div>
                )}
              </div>

              <div className="step1-card-body">
                <div className="step1-card-filename" title={f}>
                  {f}
                </div>

                {editing === f ? (
                  <div className="step1-card-edit">
                    <input
                      type="text"
                      value={editDraft}
                      onChange={(e) => setEditDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitEditing();
                        if (e.key === "Escape") {
                          setEditing(null);
                          setEditDraft("");
                        }
                      }}
                      autoFocus
                      spellCheck={false}
                      aria-label={`编辑 ${f} 标签`}
                    />
                    <div className="step1-card-edit-actions">
                      <button
                        className="btn btn-primary"
                        onClick={commitEditing}
                      >
                        保存
                      </button>
                      <button
                        className="btn"
                        onClick={() => {
                          setEditing(null);
                          setEditDraft("");
                        }}
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="step1-card-label">
                    {d.is_icon ? (
                      <code>{d.label || llmLabel || <em>（无名）</em>}</code>
                    ) : (
                      <em className="step1-card-label--muted">
                        {llmLabel || "未命名"}
                      </em>
                    )}
                    {!d.is_icon && llmLabel && (
                      <span className="step1-card-label-hint">
                        LLM 原本：<code>{llmLabel}</code>
                      </span>
                    )}
                  </div>
                )}

                {!readOnly && (
                  <div className="step1-card-actions">
                    <button
                      className={`btn ${d.is_icon ? "btn-active" : ""}`}
                      onClick={() => acceptOne(f)}
                      data-testid={`step1-accept-${f}`}
                      aria-pressed={d.is_icon}
                    >
                      ✓ 接受
                    </button>
                    <button
                      className="btn"
                      onClick={() => startEditing(f)}
                      disabled={!d.is_icon}
                      data-testid={`step1-edit-${f}`}
                    >
                      ✎ 编辑
                    </button>
                    <button
                      className={`btn ${!d.is_icon ? "btn-active-skip" : ""}`}
                      onClick={() => skipOne(f)}
                      data-testid={`step1-skip-${f}`}
                      aria-pressed={!d.is_icon}
                    >
                      ⨯ 跳过
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {editing !== null && (
        <div className="step1-edit-modal" role="dialog">
          <div className="step1-edit-modal-content">
            <h3>编辑标签</h3>
            <code className="step1-edit-filename">{editing}</code>
            <input
              type="text"
              value={editDraft}
              onChange={(e) => setEditDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitEditing();
                if (e.key === "Escape") {
                  setEditing(null);
                  setEditDraft("");
                }
              }}
              autoFocus
              spellCheck={false}
              data-testid="step1-edit-input"
              aria-label={`编辑 ${editing} 标签`}
            />
            <div className="modal-actions">
              <button
                className="btn"
                onClick={() => {
                  setEditing(null);
                  setEditDraft("");
                }}
              >
                取消
              </button>
              <button
                className="btn btn-primary"
                onClick={commitEditing}
                data-testid="step1-edit-save"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      {!readOnly && (
        <div className="pipeline-step-actions">
          <button
            className="btn btn-primary"
            disabled={submitting || filenames.length === 0}
            onClick={handleSubmit}
            data-testid="step1-submit"
          >
            {submitting ? "提交中..." : "确认并进入 Step 2"}
        </button>
        </div>
      )}
    </div>
  );
}
