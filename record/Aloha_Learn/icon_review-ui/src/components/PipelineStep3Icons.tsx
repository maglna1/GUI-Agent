import { useEffect, useState } from "react";
import {
  getPipelineClicks,
  getLibraryLabels,
  postPipelineDecisions,
} from "../api/client";
import type { Click, Decision, StepState } from "../types";
import { ClickList } from "./ClickList";
import { PipelineLogPanel } from "./PipelineLogPanel";

interface Props {
  stepState: StepState;
  /** Read-only history view: show saved decisions without edit controls. */
  readOnly?: boolean;
  /** Saved decisions (from orchestrator state) for read-only view. */
  savedDecisions?: Record<string, Decision>;
}

/** Step 3: 图标点击确认 - 主界面内嵌，不弹独立窗口。
 * 加载 clicks + 图标库 labels，渲染 ClickList，用户勾选 + 选 label 后提交，
 * orchestrator 接收后 apply_icon_decisions 注入 images 到 trace.json。 */
export function PipelineStep3Icons({ stepState, readOnly, savedDecisions }: Props) {
  const [clicks, setClicks] = useState<Click[]>([]);
  const [labels, setLabels] = useState<string[]>([]);
  const [localDecisions, setLocalDecisions] = useState<Record<string, Decision>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const decisions = readOnly ? (savedDecisions ?? {}) : localDecisions;

  useEffect(() => {
    let cancelled = false;
    Promise.all([getPipelineClicks(), getLibraryLabels()])
      .then(([c, l]) => {
        if (cancelled) return;
        setClicks(c.clicks);
        setLabels(l.labels);
        if (!readOnly) {
          const seed: Record<string, Decision> = {};
          for (const click of c.clicks) {
            seed[String(click.step_idx)] = { is_icon: false, label: "" };
          }
          setLocalDecisions(seed);
        }
      })
      .catch((e) => setLoadError(`加载 clicks/labels 失败: ${e}`));
    return () => {
      cancelled = true;
    };
  }, [readOnly]);

  const iconCount = Object.values(decisions).filter(
    (d) => d.is_icon && d.label
  ).length;

  async function handleSubmit() {
    setSubmitting(true);
    setLoadError(null);
    try {
      await postPipelineDecisions(localDecisions);
      setSubmitted(true);
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : String(e));
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="pipeline-step pipeline-step--3" data-testid="pipeline-step-3">
        <h2>Step 3 · 图标点击确认（已提交）</h2>
        <p className="pipeline-step-help">
          已提交 <strong>{iconCount}</strong> 个图标点击。orchestrator 正在把
          images 注入 trace.json，完成后自动进入 Step 4。
        </p>
        {stepState.error && <div className="error-banner">{stepState.error}</div>}
        <PipelineLogPanel lines={stepState.log_lines} emptyText="等待注入日志..." />
      </div>
    );
  }

  return (
    <div className="pipeline-step pipeline-step--3" data-testid="pipeline-step-3">
      <h2>
        Step 3 · 图标点击确认
        {readOnly && <span className="step-readonly-tag">（回顾）</span>}
        <span className="step1-counts">
          <span className="step1-pill step1-pill--ok">{iconCount} 图标</span>
          <span className="step1-pill step1-pill--total">/ {clicks.length}</span>
        </span>
      </h2>
      <p className="pipeline-step-help">
        {readOnly
          ? "只读回顾：查看已确认的图标点击决策。"
          : "勾选哪些 click 是图标点击，并从图标库选对应 label。提交后 orchestrator 自动注入 images 到 trace.json。"}
      </p>
      {loadError && <div className="error-banner">{loadError}</div>}
      {stepState.error && <div className="error-banner">{stepState.error}</div>}
      {!readOnly && labels.length === 0 && clicks.length > 0 && (
        <div className="error-banner">
          图标库为空（本 project 下无图标）。Step 3 仍可提交，但不会注入 images。
        </div>
      )}
      <ClickList
        clicks={clicks}
        decisions={decisions}
        labels={labels}
        onDecision={readOnly ? undefined : (idx, d) =>
          setLocalDecisions({ ...localDecisions, [String(idx)]: d })
        }
        readOnly={readOnly}
      />
      {!readOnly && (
        <div className="pipeline-step-actions">
          <button
            className="btn btn-primary"
            disabled={submitting || clicks.length === 0}
            onClick={handleSubmit}
            data-testid="step3-submit"
          >
            {submitting ? "提交中..." : "确认并进入 Step 4"}
          </button>
        </div>
      )}
      <PipelineLogPanel lines={stepState.log_lines} emptyText={readOnly ? "无日志" : "提交后显示注入日志"} />
    </div>
  );
}
