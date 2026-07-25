export interface Icon {
  filename: string;
  icon_url: string;
  llm_label: string;
  is_timestamp_fallback: boolean;
  action: string;
  coords: [number, number];
  current_software: string;
  base: string;
}

export type Decision =
  | { action: "accept" }
  | { action: "edit"; label: string }
  | { action: "skip" };

export interface Queue {
  icons: Icon[];
  existing_labels: string[];
  dest: string;
  manual_mode_default: boolean;
}

export interface AppliedCounts {
  accepted: number;
  edited: number;
  skipped: number;
  sanitize_fallback: number;
}

export interface FinishResult {
  applied: AppliedCounts;
  keys_added: string[];
  keys_updated: string[];
}