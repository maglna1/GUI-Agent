import { useState } from "react";
import { postPipelineRunActualTask } from "../api/client";
import type { PipelineState } from "../types";
import { PipelineLogPanel } from "./PipelineLogPanel";

interface Props {
  state: PipelineState;
  stepState: { status: string; progress_current: number; progress_total: number; log_lines: string[]; error: string | null };
  onActualTaskTriggered: () => void;
}

/** Step 4: Sync + init + validate 自动跑完，task run 单独按钮触发真实桌面回放。 */
export function PipelineStep4Sync({ state, stepState, onActualTaskTriggered }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function triggerActualTask() {
    setError(null);
    try {
      await postPipelineRunActualTask();
      setConfirming(false);
      onActualTaskTriggered();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const subs = [
    { key: "sync",           label: "sync_to_execution.py     — 复制 trace.json / sc.json" },
    { key: "init_from_trace", label: "task init-from-trace  — 生成 task.yaml" },
    { key: "validate",        label: "task validate         — 校验 YAML + 输入契约" },
  ];

  const allOk = subs.every((s) => state.step4_results[s.key]?.status === "succeeded");

  return (
    <div className="pipeline-step pipeline-step--4" data-testid="pipeline-step-4">
      <h2>Step 4 · Sync + 转换 + 验证</h2>
      <p className="pipeline-step-help">
        自动按顺序跑了 3 步。点下面按钮可以再跑一次真实的
        <code>task run</code>（桌面接管，会真点击屏幕 — 谨慎）。
      </p>

      <table className="step4-table">
        <thead>
          <tr>
            <th>子步骤</th>
            <th>状态</th>
            <th>退出码</th>
          </tr>
        </thead>
        <tbody>
          {subs.map((s) => {
            const r = state.step4_results[s.key];
            const status = r?.status ?? (
              stepState.status === "running"
                ? "running..."
                : stepState.status === "succeeded"
                ? "succeeded"
                : stepState.status
            );
            return (
              <tr key={s.key}>
                <td>{s.label}</td>
                <td>
                  <span
                    className={`step4-status step4-status--${
                      status === "succeeded"
                        ? "ok"
                        : status === "failed"
                        ? "fail"
                        : "pending"
                    }`}
                  >
                    {status}
                  </span>
                </td>
                <td>{r?.exit_code ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {stepState.error && <div className="error-banner">{stepState.error}</div>}
      {error && <div className="error-banner">{error}</div>}

      <PipelineLogPanel lines={stepState.log_lines} emptyText="暂无日志" />

      {allOk && !confirming && (
        <div className="pipeline-step-actions">
          <button
            className="btn btn-primary"
            onClick={() => setConfirming(true)}
            data-testid="step4-run-actual"
          >
            真实跑 task run（接管桌面）
          </button>
        </div>
      )}

      {confirming && (
        <div className="confirm-box" role="alertdialog" aria-modal="true">
          <div className="confirm-content">
            <h3>真的要跑 <code>task run</code> 吗？</h3>
            <p>
              这会把 Midscene Computer Agent 启动到你的桌面上，
              它会真的点击任务栏上的应用图标。需要你保证：
            </p>
            <ul>
              <li>任务栏图标可见</li>
              <li>没有别的窗口挡在前面</li>
              <li>手动停止方案就绪（Ctrl+C 关终端）</li>
            </ul>
            <div className="modal-actions">
              <button className="btn" onClick={() => setConfirming(false)}>取消</button>
              <button
                className="btn btn-primary"
                onClick={triggerActualTask}
                data-testid="step4-run-actual-confirm"
              >
                确认接管桌面
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
