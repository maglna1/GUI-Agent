import type { StepDef, StepState } from "../types";

interface Props {
  steps: StepDef[];
  currentStep: number; // 0 idle, 1-4 active, -1 errored
  stepStates: Record<string, StepState>;
  /** Which step the user is currently viewing (for history review). */
  viewStep?: number;
  /** Click-to-jump handler for steps that have already started. */
  onJump?: (stepId: number) => void;
}

/** Top-of-window 4-step horizontal progress bar. */
export function PipelineStepper({ steps, currentStep, stepStates, viewStep, onJump }: Props) {
  const viewing = viewStep ?? currentStep;
  return (
    <header className="stepper" data-testid="pipeline-stepper">
      {steps.map((step) => {
        const state = stepStates[String(step.id)];
        const status = state?.status ?? "pending";
        const progressMax = state?.progress_total ?? 0;
        const progressCur = state?.progress_current ?? 0;
        const isActive = step.id === currentStep;
        const isViewing = step.id === viewing && !isActive;
        // A step is clickable if it has started (id <= currentStep) and has
        // produced any state (running/waiting/succeeded/failed).
        const hasStarted = step.id <= Math.max(currentStep, 0) && currentStep > 0;
        const isClickable = hasStarted && !!onJump;
        const cls = [
          "stepper-step",
          `stepper-step--${status}`,
          isActive ? "stepper-step--active" : "",
          isViewing ? "stepper-step--viewing" : "",
          hasStarted && !isActive ? "stepper-step--past" : "",
          isClickable ? "stepper-step--clickable" : "",
        ]
          .filter(Boolean)
          .join(" ");
        const pct =
          progressMax > 0 ? Math.min(100, Math.round((progressCur / progressMax) * 100)) : 0;
        return (
          <div
            key={step.id}
            className={cls}
            onClick={() => isClickable && onJump?.(step.id)}
            role={isClickable ? "button" : undefined}
            aria-current={isActive ? "step" : undefined}
            data-step-id={step.id}
            data-step-status={status}
          >
            <div className="stepper-step-num">{step.id}</div>
            <div className="stepper-step-body">
              <div className="stepper-step-label">{step.label}</div>
              <div className="stepper-step-status">
                {statusLabel(status)}
                {progressMax > 0 && (
                  <span className="stepper-step-progress">
                    {" "}
                    {progressCur}/{progressMax}
                  </span>
                )}
              </div>
              {progressMax > 0 && (
                <div
                  className="stepper-step-bar"
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div className="stepper-step-bar-fill" style={{ width: `${pct}%` }} />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </header>
  );
}

function statusLabel(s: string): string {
  switch (s) {
    case "pending":  return "等待中";
    case "running":  return "进行中";
    case "waiting":  return "等你确认";
    case "succeeded": return "完成";
    case "failed":   return "失败";
    case "skipped":  return "跳过";
    default: return s;
  }
}
