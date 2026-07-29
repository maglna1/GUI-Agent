import type { Click, Decision } from "../types";

export interface State {
  clicks: Click[];
  labels: string[];
  decisions: Record<string, Decision>;
  submitting: boolean;
  loadError: string | null;
}

export type Action =
  | { type: "SET_LOAD_ERROR"; error: string }
  | { type: "SET_QUEUE"; clicks: Click[]; labels: string[] }
  | { type: "SET_DECISION"; step_idx: number; decision: Decision }
  | { type: "CLEAR_DECISION"; step_idx: number }
  | { type: "SET_SUBMITTING"; submitting: boolean };

export const initialState: State = {
  clicks: [],
  labels: [],
  decisions: {},
  submitting: false,
  loadError: null,
};

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_LOAD_ERROR":
      return { ...state, loadError: action.error };
    case "SET_QUEUE": {
      // Seed every click as not-an-icon (default = no injection).
      const decisions: Record<string, Decision> = {};
      for (const click of action.clicks) {
        decisions[String(click.step_idx)] = { is_icon: false, label: "" };
      }
      return {
        ...state,
        clicks: action.clicks,
        labels: action.labels,
        decisions,
      };
    }
    case "SET_DECISION":
      return {
        ...state,
        decisions: {
          ...state.decisions,
          [String(action.step_idx)]: action.decision,
        },
      };
    case "CLEAR_DECISION":
      return {
        ...state,
        decisions: {
          ...state.decisions,
          [String(action.step_idx)]: { is_icon: false, label: "" },
        },
      };
    case "SET_SUBMITTING":
      return { ...state, submitting: action.submitting };
    default:
      return state;
  }
}
