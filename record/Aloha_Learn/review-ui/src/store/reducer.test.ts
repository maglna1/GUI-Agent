import { describe, it, expect } from "vitest";
import { reducer, initialState } from "./reducer";
import type { Icon } from "../types";

const mkIcon = (filename: string, llm_label = "x"): Icon => ({
  filename,
  icon_url: `/icons/${filename}`,
  llm_label,
  is_timestamp_fallback: false,
  action: "LClick at",
  coords: [1, 2],
  current_software: "Chrome",
  base: "10.0s",
});

describe("reducer", () => {
  it("SET_QUEUE populates icons and zeros decisions", () => {
    const icons = [mkIcon("a.png"), mkIcon("b.png")];
    const s = reducer(initialState, { type: "SET_QUEUE", icons, existing_labels: ["y"] });
    expect(s.icons).toEqual(icons);
    expect(s.existingLabels).toEqual(["y"]);
    expect(Object.keys(s.decisions)).toEqual(["a.png", "b.png"]);
    expect(s.decisions["a.png"]).toBeNull();
  });

  it("SET_DECISION stores accept/edit/skip", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png")], existing_labels: [],
    });
    const s1 = reducer(base, { type: "SET_DECISION", filename: "a.png", decision: { action: "accept" } });
    expect(s1.decisions["a.png"]).toEqual({ action: "accept" });
    const s2 = reducer(s1, { type: "SET_DECISION", filename: "a.png", decision: { action: "edit", label: "btn" } });
    expect(s2.decisions["a.png"]).toEqual({ action: "edit", label: "btn" });
    const s3 = reducer(s2, { type: "SET_DECISION", filename: "a.png", decision: { action: "skip" } });
    expect(s3.decisions["a.png"]).toEqual({ action: "skip" });
  });

  it("SET_MANUAL_MODE toggles manualMode", () => {
    const s = reducer(initialState, { type: "SET_MANUAL_MODE", manualMode: true });
    expect(s.manualMode).toBe(true);
  });

  it("SET_SUBMITTING toggles submitting", () => {
    const s = reducer(initialState, { type: "SET_SUBMITTING", submitting: true });
    expect(s.submitting).toBe(true);
  });

  it("APPLY_BULK_ACCEPT sets all to accept", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png"), mkIcon("b.png")], existing_labels: [],
    });
    const s = reducer(base, { type: "APPLY_BULK_ACCEPT" });
    expect(s.decisions["a.png"]).toEqual({ action: "accept" });
    expect(s.decisions["b.png"]).toEqual({ action: "accept" });
  });

  it("APPLY_BULK_SKIP sets all to skip", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png"), mkIcon("b.png")], existing_labels: [],
    });
    const s = reducer(base, { type: "APPLY_BULK_SKIP" });
    expect(s.decisions["a.png"]).toEqual({ action: "skip" });
    expect(s.decisions["b.png"]).toEqual({ action: "skip" });
  });

  it("SET_QUEUE resets decisions", () => {
    const base = reducer(initialState, {
      type: "SET_QUEUE", icons: [mkIcon("a.png")], existing_labels: [],
    });
    const filled = reducer(base, { type: "SET_DECISION", filename: "a.png", decision: { action: "accept" } });
    const reset = reducer(filled, { type: "SET_QUEUE", icons: [mkIcon("a.png"), mkIcon("b.png")], existing_labels: [] });
    expect(reset.decisions["a.png"]).toBeNull();
    expect(reset.decisions["b.png"]).toBeNull();
  });
});