import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PipelineStep1Icons, type IconDecision } from "./PipelineStep1Icons";
import type { PipelineState } from "../types";

vi.mock("../api/client", () => ({
  postPipelineLabels: vi.fn().mockResolvedValue({ ok: true, count: 2 }),
}));

const STATE: PipelineState = {
  run_id: "x", project: "/p", scene: "s", task: "t", goal: "",
  library_roots: [], data_root: null,
  current_step: 1, started_at: "", finished_at: "",
  steps: { "1": { status: "waiting", progress_current: 0, progress_total: 0, log_lines: [], error: null } },
  step1_labels: { "a.png": "minimax_code", "b.png": "youdao_dictionary" },
  step1_llm_labels: { "a.png": "minimax_code", "b.png": "youdao_dictionary" },
  step3_decisions: {}, step4_results: {}, step_defs: [],
};

function decisionsWithLlm(): Record<string, IconDecision> {
  return {
    "a.png": { is_icon: true, label: "minimax_code" },
    "b.png": { is_icon: true, label: "youdao_dictionary" },
  };
}

describe("PipelineStep1Icons", () => {
  it("renders thumbnails with /api/pipeline/icon/ URLs", () => {
    render(
      <PipelineStep1Icons
        state={STATE}
        decisions={decisionsWithLlm()}
        llmLabels={STATE.step1_llm_labels}
        onChange={() => {}}
        onSubmitted={() => {}}
      />
    );
    const img = screen.getByAltText("a.png") as HTMLImageElement;
    // jsdom resolves the relative URL against the test origin (http://localhost:3000).
    expect(img.getAttribute("src")).toBe("/api/pipeline/icon/a.png");
  });

  it("accept-all switches all to is_icon=true", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PipelineStep1Icons
        state={STATE}
        decisions={{ "a.png": { is_icon: false, label: "minimax_code" }, "b.png": { is_icon: false, label: "youdao_dictionary" } }}
        llmLabels={STATE.step1_llm_labels}
        onChange={onChange}
        onSubmitted={() => {}}
      />
    );
    await user.click(screen.getByTestId("step1-accept-all"));
    expect(onChange).toHaveBeenCalledTimes(1);
    const newDecisions = onChange.mock.calls[0][0];
    expect(newDecisions["a.png"].is_icon).toBe(true);
    expect(newDecisions["b.png"].is_icon).toBe(true);
  });

  it("skip-all switches all to is_icon=false", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PipelineStep1Icons
        state={STATE}
        decisions={decisionsWithLlm()}
        llmLabels={STATE.step1_llm_labels}
        onChange={onChange}
        onSubmitted={() => {}}
      />
    );
    await user.click(screen.getByTestId("step1-skip-all"));
    const newDecisions = onChange.mock.calls[0][0];
    expect(newDecisions["a.png"].is_icon).toBe(false);
    expect(newDecisions["b.png"].is_icon).toBe(false);
  });

  it("per-row skip moves is_icon=false on that row only", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <PipelineStep1Icons
        state={STATE}
        decisions={decisionsWithLlm()}
        llmLabels={STATE.step1_llm_labels}
        onChange={onChange}
        onSubmitted={() => {}}
      />
    );
    await user.click(screen.getByTestId("step1-skip-a.png"));
    const newDecisions = onChange.mock.calls[0][0];
    expect(newDecisions["a.png"].is_icon).toBe(false);
    expect(newDecisions["b.png"].is_icon).toBe(true);
  });

  it("shows correct pill counts", () => {
    render(
      <PipelineStep1Icons
        state={STATE}
        decisions={{
          "a.png": { is_icon: true, label: "minimax_code" },
          "b.png": { is_icon: false, label: "" },
        }}
        llmLabels={STATE.step1_llm_labels}
        onChange={() => {}}
        onSubmitted={() => {}}
      />
    );
    expect(screen.getByText(/1 接受/)).toBeInTheDocument();
    expect(screen.getByText(/1 跳过/)).toBeInTheDocument();
  });

  it("submit calls postPipelineLabels with only accepted+labeled", async () => {
    const { postPipelineLabels } = await import("../api/client");
    const user = userEvent.setup();
    const onSubmitted = vi.fn();
    render(
      <PipelineStep1Icons
        state={STATE}
        decisions={{
          "a.png": { is_icon: true,  label: "minimax_code" },
          "b.png": { is_icon: false, label: "youdao_dictionary" },
        }}
        llmLabels={STATE.step1_llm_labels}
        onChange={() => {}}
        onSubmitted={onSubmitted}
      />
    );
    await user.click(screen.getByTestId("step1-submit"));
    expect(postPipelineLabels).toHaveBeenCalled();
    const call = (postPipelineLabels as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(call).toEqual({ "a.png": "minimax_code" });
    expect(onSubmitted).toHaveBeenCalled();
  });
});
