import type { Decision, Icon } from "../types";

export interface State {
  icons: Icon[];
  existingLabels: string[];
  dest: string;
  manualMode: boolean;
  submitting: boolean;
  decisions: Record<string, Decision | null>;
}

export type Action =
  | { type: "SET_QUEUE"; icons: Icon[]; existing_labels: string[]; dest?: string; manual_mode_default?: boolean }
  | { type: "SET_DECISION"; filename: string; decision: Decision }
  | { type: "SET_MANUAL_MODE"; manualMode: boolean }
  | { type: "SET_SUBMITTING"; submitting: boolean }
  | { type: "APPLY_BULK_ACCEPT" }
  | { type: "APPLY_BULK_SKIP" }
  | { type: "RESET" };

export const initialState: State = {
  icons: [],
  existingLabels: [],
  dest: "",
  manualMode: false,
  submitting: false,
  decisions: {},
};

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_QUEUE": {
      const decisions: Record<string, Decision | null> = {};
      for (const icon of action.icons) decisions[icon.filename] = null;
      return {
        ...state,
        icons: action.icons,
        existingLabels: action.existing_labels,
        dest: action.dest ?? state.dest,
        manualMode: action.manual_mode_default ?? state.manualMode,
        decisions,
      };
    }
    case "SET_DECISION": {
      return {
        ...state,
        decisions: { ...state.decisions, [action.filename]: action.decision },
      };
    }
    case "SET_MANUAL_MODE":
      return { ...state, manualMode: action.manualMode };
    case "SET_SUBMITTING":
      return { ...state, submitting: action.submitting };
    case "APPLY_BULK_ACCEPT": {
      const decisions: Record<string, Decision | null> = {};
      for (const k of Object.keys(state.decisions)) decisions[k] = { action: "accept" };
      return { ...state, decisions };
    }
    case "APPLY_BULK_SKIP": {
      const decisions: Record<string, Decision | null> = {};
      for (const k of Object.keys(state.decisions)) decisions[k] = { action: "skip" };
      return { ...state, decisions };
    }
    case "RESET":
      return initialState;
    default:
      return state;
  }
}