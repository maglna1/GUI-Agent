import type { StepState } from "../types";
import { PipelineLogPanel } from "./PipelineLogPanel";

interface Props {
  state: StepState;
}

/** Step 2: Trace 生成（parser.py step 3）— 只读日志 + 进度。 */
export function PipelineStep2Trace({ state }: Props) {
  const pct =
    state.progress_total > 0
      ? Math.round((state.progress_current / state.progress_total) * 100)
      : 0;

  return (
    <div className="pipeline-step pipeline-step--2" data-testid="pipeline-step-2">
      <h2>Step 2 · Trace 生成</h2>
      <p className="pipeline-step-help">
        parser.py 在跑 step 3：每条点击调一次 LLM 拿 prompt + Operation。
        9 个 step 一般需要 30 秒 ~ 数分钟（依赖 provider）。
        状态：{state.status}。
      </p>

      {state.progress_total > 0 && (
        <div className="pipeline-progress-row">
          <div className="pipeline-progress-text">
            进度 {state.progress_current} / {state.progress_total} ({pct}%)
          </div>
          <div
            className="pipeline-progress"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="pipeline-progress-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {state.error && <div className="error-banner">{state.error}</div>}

      <PipelineLogPanel
        lines={state.log_lines}
        emptyText="等待 parser.py 输出..."
      />
    </div>
  );
}
