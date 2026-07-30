export interface Click {
  /** Stable identifier in the original log (e.g. 0-indexed event number). */
  step_idx: number;
  /** Seconds since the recording started. */
  timestamp: number;
  /** [x, y] of the click in screen coordinates, when known. */
  coords: [number | null, number | null];
  /** Window title the recorder saw at the time of the click. */
  current_software: string;
  /** LLM-written prompt for this click (or empty if not yet generated). */
  prompt: string;
  /** URL for the cropped screenshot the recorder captured. */
  screenshot_url: string;
}

/**
 * Decision shape: the user either confirms a click was an icon click
 * (is_icon=true, label=icon name) or marks it as a normal click
 * (is_icon=false). is_icon=true with label="" is treated as no-op.
 */
export type Decision = { is_icon: boolean; label: string };

export interface ClickList {
  clicks: Click[];
  total: number;
}

export interface LabelsList {
  labels: string[];
}

export interface IconLookup {
  label: string;
  url: string;
}

export interface FinishResult {
  ok: true;
  decided: number;
  total: number;
}

// -- Pipeline (unified 4-step orchestrator) -------------------------------

export type StepStatus =
  | 'pending'
  | 'running'
  | 'waiting'
  | 'succeeded'
  | 'failed'
  | 'skipped';

export interface StepState {
  status: StepStatus;
  progress_current: number;
  progress_total: number;
  log_lines: string[];
  error: string | null;
}

export interface StepDef {
  id: number;
  key: string;
  label: string;
}

export interface PipelineState {
  run_id: string;
  project: string;
  scene: string;
  task: string;
  goal: string;
  library_roots: string[];
  data_root: string | null;
  current_step: number; // 0 = idle, 1-4 = step, -1 = errored
  started_at: string;
  finished_at: string;
  steps: Record<string, StepState>;
  step1_labels: Record<string, string>;
  step1_llm_labels: Record<string, string>;
  step3_decisions: Record<string, Decision>;
  step4_results: Record<string, {
    status: string;
    exit_code: number;
    stdout_tail: string;
  }>;
  step_defs: StepDef[];
}

export interface PipelineEvent {
  type:
    | 'state'
    | 'log'
    | 'progress'
    | 'step1_complete_llm'
    | 'step1_complete'
    | 'step3_complete'
    | 'step4_substep'
    | 'actual_task_started'
    | 'actual_task_finished'
    | 'actual_task_error'
    | 'keepalive';
  [key: string]: unknown;
}
