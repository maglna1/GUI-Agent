import { useEffect, useMemo, useRef, useState } from "react";
import {
  getPipelineState,
  openPipelineEventStream,
  postPipelineStart,
  getPipelineProjects,
  getPipelineScenes,
  postPipelineConfigure,
} from "./api/client";
import type { PipelineState } from "./types";
import { PipelineStepper } from "./components/PipelineStepper";
import { PipelineStep1Icons, type IconDecision } from "./components/PipelineStep1Icons";
import { PipelineStep2Trace } from "./components/PipelineStep2Trace";
import { PipelineStep3Icons } from "./components/PipelineStep3Icons";
import { PipelineStep4Sync } from "./components/PipelineStep4Sync";

const DEFAULT_GOAL = "通过统一 pipeline 窗口运行 record 项目";

export default function App() {
  // All hooks must be called in the same order every render — no early
  // returns above here.
  const [state, setState] = useState<PipelineState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [goal, setGoal] = useState<string>(DEFAULT_GOAL);
  const [submitting, setSubmitting] = useState(false);
  const [step1Draft, setStep1Draft] = useState<Record<string, IconDecision>>({});
  const labelsSeededRef = useRef<string | null>(null);
  const sseSourceRef = useRef<EventSource | null>(null);
  // Start-screen config: project (dropdown), scene/task (input). Populated
  // from the server + the orchestrator's pre-fill (if launched with args).
  const [projects, setProjects] = useState<string[]>([]);
  const [scenes, setScenes] = useState<string[]>([]);
  const [project, setProject] = useState<string>("");
  const [scene, setScene] = useState<string>("");
  const [task, setTask] = useState<string>("");
  // Which step the user is currently viewing. Auto-follows the pipeline's
  // current_step, but the user can click a past step in the stepper to
  // review it (read-only).
  const [viewStep, setViewStep] = useState<number>(0);

  // Initial state load + SSE subscription.
  useEffect(() => {
    let cancelled = false;
    getPipelineState()
      .then((s) => {
        if (!cancelled) {
          setState(s);
          // Pre-fill start screen from orchestrator state (if launched
          // with args or already configured).
          if (s.project) {
            const projectName = s.project.split(/[\\/]/).pop() ?? s.project;
            setProject(projectName);
          }
          if (s.scene) setScene(s.scene);
          if (s.task) setTask(s.task);
          if (s.goal) setGoal(s.goal);
        }
      })
      .catch((e) => setError(`Failed to load pipeline state: ${e}`));
    // Load project + scene lists for the dropdowns.
    getPipelineProjects().then((r) => !cancelled && setProjects(r.projects)).catch(() => {});
    getPipelineScenes().then((r) => !cancelled && setScenes(r.scenes)).catch(() => {});
    const es = openPipelineEventStream();
    sseSourceRef.current = es;
    es.addEventListener("state", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as {
        snapshot: PipelineState;
      };
      if (!cancelled) setState(data.snapshot);
    });
    es.addEventListener("log", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as {
        step: number;
        line: string;
      };
      if (!cancelled) {
        // Append the line to the step's log_lines in local state so the
        // log panel updates in real time without waiting for a full snapshot.
        setState((prev) => {
          if (!prev) return prev;
          const stepKey = String(data.step);
          const prevStep = prev.steps[stepKey];
          if (!prevStep) return prev;
          return {
            ...prev,
            steps: {
              ...prev.steps,
              [stepKey]: {
                ...prevStep,
                log_lines: [...prevStep.log_lines, data.line].slice(-200),
              },
            },
          };
        });
      }
    });
    es.addEventListener("step1_complete_llm", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as {
        labels: Record<string, string>;
        snapshot: PipelineState;
      };
      if (!cancelled) {
        setState(data.snapshot);
        // Seed local draft: accept everything by default, keep LLM labels.
        const seeded: Record<string, IconDecision> = {};
        for (const [k, v] of Object.entries(data.labels)) {
          seeded[k] = { is_icon: true, label: v };
        }
        setStep1Draft(seeded);
        labelsSeededRef.current = data.snapshot.run_id;
      }
    });
    es.addEventListener("step1_complete", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as { snapshot: PipelineState };
      if (!cancelled) setState(data.snapshot);
    });
    es.addEventListener("step3_complete", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as { snapshot: PipelineState };
      if (!cancelled) setState(data.snapshot);
    });
    es.addEventListener("step4_substep", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as { snapshot: PipelineState };
      if (!cancelled) setState(data.snapshot);
    });
    es.addEventListener("actual_task_finished", () => {
      if (!cancelled) {
        getPipelineState().then(setState).catch(() => {});
      }
    });
    return () => {
      cancelled = true;
      es.close();
      sseSourceRef.current = null;
    };
  }, []);

  // Seed step1 labels once orchestrator emits them.
  useEffect(() => {
    if (
      state &&
      Object.keys(state.step1_llm_labels).length > 0 &&
      labelsSeededRef.current !== state.run_id
    ) {
      const seeded: Record<string, IconDecision> = {};
      for (const [k, v] of Object.entries(state.step1_llm_labels)) {
        seeded[k] = { is_icon: true, label: v };
      }
      setStep1Draft(seeded);
      labelsSeededRef.current = state.run_id;
    }
  }, [state]);

  // Derived values must be computed regardless of state (hooks count must
  // be stable across renders).
  const currentStep = state?.current_step ?? 0;
  const stepStates = useMemo(() => state?.steps ?? {}, [state]);
  const finishedAt = state?.finished_at ?? "";
  const stepDefs = state?.step_defs ?? [];

  // Auto-follow the pipeline's current step: whenever it advances, jump the
  // view to it (so the user sees live progress). The user can still click
  // back to a past step afterwards.
  useEffect(() => {
    if (currentStep > 0) setViewStep(currentStep);
  }, [currentStep]);

  // Read-only Step 1 decisions (for history view): build from the persisted
  // step1_labels, treating every label as accepted.
  const step1ReadOnlyDecisions = useMemo<Record<string, IconDecision>>(() => {
    const out: Record<string, IconDecision> = {};
    if (state) {
      for (const [k, v] of Object.entries(state.step1_labels)) {
        out[k] = { is_icon: true, label: v };
      }
    }
    return out;
  }, [state]);

  // The step currently being viewed (falls back to currentStep).
  const activeView = viewStep || currentStep;
  const isReviewing = activeView !== currentStep;

  async function handleStart() {
    setSubmitting(true);
    setError(null);
    try {
      // Validate config locally first.
      if (!project || !scene || !task) {
        setError("请选择 project 并填写 scene / task");
        setSubmitting(false);
        return;
      }
      // Configure project/scene/task/goal on the orchestrator, then start.
      await postPipelineConfigure({ project, scene, task, goal });
      const res = await postPipelineStart(goal);
      setState(res.snapshot);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  // ---- Render (no hooks below this line) ---------------------------

  if (error && !state) {
    return <div className="error-banner">{error}</div>;
  }

  if (!state) {
    return <div className="pipeline-loading">加载状态中...</div>;
  }

  return (
    <div className="pipeline-app">
      <PipelineStepper
        steps={stepDefs}
        currentStep={currentStep}
        stepStates={stepStates}
        viewStep={activeView}
        onJump={(id) => {
          if (id <= Math.max(currentStep, 0)) setViewStep(id);
        }}
      />

      {error && <div className="error-banner">{error}</div>}

      {isReviewing && (
        <div className="review-banner">
          回顾 Step {activeView}（只读）
          <button className="btn" onClick={() => setViewStep(currentStep)}>
            返回当前 Step {currentStep}
          </button>
        </div>
      )}

      {activeView === 0 && (
        <div className="pipeline-step pipeline-step--start" data-testid="pipeline-start">
          <h2>开始</h2>
          <p className="pipeline-step-help">
            4 步流程：(1) LLM 给每个图标起名 -&gt; 人工可改；(2) parser.py
            生成 trace.json；(3) 在主界面标记哪些 click 是图标点击；
            (4) sync + 转换 + 验证，可选真实桌面接管。
          </p>
          <div className="start-config-grid">
            <label className="start-config-field">
              <span>Project（下拉选）</span>
              <select
                value={project}
                onChange={(e) => {
                  const v = e.target.value;
                  setProject(v);
                  // Auto-fill task = project name if task is empty or matched
                  // the previous project name.
                  if (!task || task === project) setTask(v);
                }}
                data-testid="start-project"
              >
                <option value="">- 选择 project -</option>
                {projects.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>
            <label className="start-config-field">
              <span>Scene（可输新名 / 选已有）</span>
              <input
                type="text"
                list="scene-suggestions"
                value={scene}
                onChange={(e) => setScene(e.target.value)}
                placeholder="如 record-icon-demo"
                spellCheck={false}
                data-testid="start-scene"
              />
              <datalist id="scene-suggestions">
                {scenes.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
            </label>
            <label className="start-config-field">
              <span>Task（默认=project 名，可改）</span>
              <input
                type="text"
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="如 record_icon_click"
                spellCheck={false}
                data-testid="start-task"
              />
            </label>
          </div>
          <label className="pipeline-goal-row">
            <span>目标 / Goal</span>
            <textarea
              rows={2}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              spellCheck={false}
              data-testid="pipeline-goal"
            />
          </label>
          <div className="pipeline-step-actions">
            <button
              className="btn btn-primary"
              disabled={submitting || !project || !scene || !task}
              onClick={handleStart}
              data-testid="pipeline-start-btn"
            >
              {submitting ? "启动中..." : "开始 pipeline"}
            </button>
          </div>
        </div>
      )}

      {activeView === 1 && (
        <PipelineStep1Icons
          state={state}
          decisions={isReviewing ? step1ReadOnlyDecisions : step1Draft}
          llmLabels={state.step1_llm_labels}
          onChange={isReviewing ? undefined : setStep1Draft}
          onSubmitted={isReviewing ? undefined : () => {/* SSE will advance state */}}
          readOnly={isReviewing}
        />
      )}

      {activeView === 2 && (
        <PipelineStep2Trace state={stepStates[String(2)] ?? emptyStepState()} />
      )}

      {activeView === 3 && (
        <PipelineStep3Icons
          stepState={stepStates[String(3)] ?? emptyStepState()}
          readOnly={isReviewing}
          savedDecisions={isReviewing ? state.step3_decisions : undefined}
        />
      )}

      {activeView === 4 && (
        <PipelineStep4Sync
          state={state}
          stepState={stepStates[String(4)] ?? emptyStepState()}
          onActualTaskTriggered={() => {/* SSE will refresh */}}
        />
      )}

      {currentStep < 0 && (
        <div className="pipeline-step pipeline-step--error">
          <h2>pipeline 异常退出</h2>
          {Object.entries(stepStates).map(([k, s]) =>
            s.error ? (
              <div key={k} className="error-banner">Step {k}: {s.error}</div>
            ) : null
          )}
        </div>
      )}

      {finishedAt && currentStep > 0 && (
        <div className="pipeline-done-banner" data-testid="pipeline-done">
          pipeline 已结束于 {finishedAt}
        </div>
      )}
    </div>
  );
}

function emptyStepState(): {
  status: "pending";
  progress_current: number;
  progress_total: number;
  log_lines: string[];
  error: string | null;
} {
  return {
    status: "pending",
    progress_current: 0,
    progress_total: 0,
    log_lines: [],
    error: null,
  };
}
