import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelineStepper } from "./PipelineStepper";
import type { StepDef, StepState } from "../types";

const STEPS: StepDef[] = [
  { id: 1, key: "label", label: "图标命名" },
  { id: 2, key: "trace", label: "Trace 生成" },
  { id: 3, key: "icons", label: "图标点击确认" },
  { id: 4, key: "exec",  label: "Sync + 转换 + 验证" },
];

function pendingStep(_id: number): StepState {
  return {
    status: "pending",
    progress_current: 0,
    progress_total: 0,
    log_lines: [],
    error: null,
  };
}

function runningStep(total: number, cur: number): StepState {
  return {
    status: "running",
    progress_current: cur,
    progress_total: total,
    log_lines: [],
    error: null,
  };
}

describe("PipelineStepper", () => {
  it("renders all 4 step labels", () => {
    const states: Record<string, StepState> = {};
    STEPS.forEach((s) => (states[String(s.id)] = pendingStep(s.id)));
    render(
      <PipelineStepper
        steps={STEPS}
        currentStep={0}
        stepStates={states}
      />
    );
    expect(screen.getByText("图标命名")).toBeInTheDocument();
    expect(screen.getByText("Trace 生成")).toBeInTheDocument();
    expect(screen.getByText("图标点击确认")).toBeInTheDocument();
    expect(screen.getByText("Sync + 转换 + 验证")).toBeInTheDocument();
  });

  it("marks the active step with aria-current=step", () => {
    const states: Record<string, StepState> = {};
    STEPS.forEach((s) => (states[String(s.id)] = pendingStep(s.id)));
    render(
      <PipelineStepper
        steps={STEPS}
        currentStep={2}
        stepStates={states}
      />
    );
    // Markup is a div; we set aria-current="step" on the active one.
    const activeByAttr = document.querySelectorAll("[aria-current='step']");
    expect(activeByAttr).toHaveLength(1);
  });

  it("shows progress bar with percent fill when progress_total > 0", () => {
    const states: Record<string, StepState> = {};
    states["2"] = runningStep(10, 4);
    render(
      <PipelineStepper
        steps={STEPS}
        currentStep={2}
        stepStates={states}
      />
    );
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    const fill = bar.querySelector(".stepper-step-bar-fill") as HTMLElement;
    expect(fill.style.width).toBe("40%");
  });

  it("supports step jump when onJump is provided and step succeeded", () => {
    const states: Record<string, StepState> = {};
    states["1"] = { status: "succeeded", progress_current: 0, progress_total: 0, log_lines: [], error: null };
    states["2"] = pendingStep(2);
    const onJump = vi.fn();
    render(
      <PipelineStepper
        steps={STEPS}
        currentStep={2}
        stepStates={states}
        onJump={onJump}
      />
    );
    const step1 = screen.getByText("图标命名").closest("[role='button']");
    expect(step1).toBeTruthy();
    step1?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onJump).toHaveBeenCalledWith(1);
  });
});
