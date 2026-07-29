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
