import { describe, expect, it } from "vitest";
import { initialState, reducer } from "./reducer";
import type { Click } from "../types";

const SAMPLE: Click[] = [
  {
    step_idx: 1,
    timestamp: 10.5,
    coords: [320, 788],
    current_software: "ssrun",
    prompt: "点击 ssrun 图标",
    screenshot_url: "/api/screenshot/10.4s.jpg",
  },
  {
    step_idx: 5,
    timestamp: 22.3,
    coords: [100, 200],
    current_software: "vscode",
    prompt: "点击编辑器",
    screenshot_url: "/api/screenshot/22.2s.jpg",
  },
];

describe("icon-review reducer", () => {
  it("seeds every click as not-icon on SET_QUEUE", () => {
    const state = reducer(initialState, {
      type: "SET_QUEUE",
      clicks: SAMPLE,
      labels: ["ssrun", "chrome"],
    });
    expect(Object.keys(state.decisions)).toHaveLength(2);
    expect(state.decisions["1"]).toEqual({ is_icon: false, label: "" });
    expect(state.decisions["5"]).toEqual({ is_icon: false, label: "" });
    expect(state.labels).toEqual(["ssrun", "chrome"]);
  });

  it("SET_DECISION persists label per click", () => {
    const state1 = reducer(initialState, {
      type: "SET_QUEUE",
      clicks: SAMPLE,
      labels: ["ssrun"],
    });
    const state2 = reducer(state1, {
      type: "SET_DECISION",
      step_idx: 1,
      decision: { is_icon: true, label: "ssrun" },
    });
    expect(state2.decisions["1"]).toEqual({ is_icon: true, label: "ssrun" });
    expect(state2.decisions["5"]).toEqual({ is_icon: false, label: "" });
  });

  it("CLEAR_DECISION resets the click", () => {
    const state1 = reducer(initialState, {
      type: "SET_QUEUE",
      clicks: SAMPLE,
      labels: ["ssrun"],
    });
    const state2 = reducer(state1, {
      type: "SET_DECISION",
      step_idx: 1,
      decision: { is_icon: true, label: "ssrun" },
    });
    const state3 = reducer(state2, { type: "CLEAR_DECISION", step_idx: 1 });
    expect(state3.decisions["1"]).toEqual({ is_icon: false, label: "" });
  });

  it("SET_SUBMITTING only toggles submitting flag", () => {
    const state1 = reducer(initialState, {
      type: "SET_SUBMITTING",
      submitting: true,
    });
    expect(state1.submitting).toBe(true);
  });

  it("SET_LOAD_ERROR surfaces an error without losing decisions", () => {
    const state1 = reducer(initialState, {
      type: "SET_QUEUE",
      clicks: SAMPLE,
      labels: [],
    });
    const state2 = reducer(state1, {
      type: "SET_LOAD_ERROR",
      error: "boom",
    });
    expect(state2.loadError).toBe("boom");
    expect(Object.keys(state2.decisions)).toHaveLength(2);
  });
});
