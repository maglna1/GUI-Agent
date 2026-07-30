import { describe, expect, it, vi } from "vitest";
import {
  getClicks,
  getLabels,
  getIcon,
  postDecisions,
  postFinish,
  getPipelineState,
  postPipelineStart,
  postPipelineLabels,
  postPipelineRunActualTask,
  openPipelineEventStream,
} from "./client";

describe("icon-review api", () => {
  it("getClicks hits /api/clicks", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ clicks: [], total: 0 }),
    });
    vi.stubGlobal("fetch", mock);

    await getClicks();
    expect(mock).toHaveBeenCalledWith("/api/clicks", { method: "GET" });
    vi.unstubAllGlobals();
  });

  it("getLabels hits /api/labels", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ labels: ["ssrun"] }),
    });
    vi.stubGlobal("fetch", mock);

    await getLabels();
    expect(mock).toHaveBeenCalledWith("/api/labels", { method: "GET" });
    vi.unstubAllGlobals();
  });

  it("getIcon encodes the label", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ label: "minimax code", url: "data:image/png;base64,AAA" }),
    });
    vi.stubGlobal("fetch", mock);

    await getIcon("minimax code");
    expect(mock).toHaveBeenCalledWith(
      "/api/icon/minimax%20code",
      { method: "GET" }
    );
    vi.unstubAllGlobals();
  });

  it("postDecisions posts decisions with Content-Type", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, count: 3 }),
    });
    vi.stubGlobal("fetch", mock);

    const r = await postDecisions({ "1": { is_icon: true, label: "ssrun" } });
    expect(r.count).toBe(3);
    expect(mock).toHaveBeenCalledWith(
      "/api/decisions",
      expect.objectContaining({ method: "POST" })
    );
    const body = JSON.parse(mock.mock.calls[0][1].body as string);
    expect(body.decisions["1"]).toEqual({ is_icon: true, label: "ssrun" });
    vi.unstubAllGlobals();
  });

  it("postFinish hits /api/finish", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, decided: 2, total: 5 }),
    });
    vi.stubGlobal("fetch", mock);

    const r = await postFinish();
    expect(r).toEqual({ ok: true, decided: 2, total: 5 });
    expect(mock).toHaveBeenCalledWith("/api/finish", { method: "POST" });
    vi.unstubAllGlobals();
  });
});

describe("icon-review pipeline api", () => {
  it("getPipelineState hits /api/pipeline/state", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        run_id: "x",
        project: "/p", scene: "s", task: "t", goal: "",
        library_roots: [], data_root: null,
        current_step: 0, started_at: "", finished_at: "",
        steps: {}, step1_labels: {}, step1_llm_labels: {},
        step3_decisions: {}, step4_results: {}, step_defs: [],
      }),
    });
    vi.stubGlobal("fetch", mock);
    await getPipelineState();
    expect(mock).toHaveBeenCalledWith("/api/pipeline/state", { method: "GET" });
    vi.unstubAllGlobals();
  });

  it("postPipelineStart posts goal to /api/pipeline/start", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ok: true,
        snapshot: {
          run_id: "x", project: "/p", scene: "s", task: "t", goal: "go",
          library_roots: [], data_root: null, current_step: 1,
          started_at: "", finished_at: "",
          steps: {}, step1_labels: {}, step1_llm_labels: {},
          step3_decisions: {}, step4_results: {}, step_defs: [],
        },
      }),
    });
    vi.stubGlobal("fetch", mock);
    await postPipelineStart("go");
    const [url, init] = mock.mock.calls[0];
    expect(url).toBe("/api/pipeline/start");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body).goal).toBe("go");
    vi.unstubAllGlobals();
  });

  it("postPipelineLabels posts cleaned labels", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, count: 2 }),
    });
    vi.stubGlobal("fetch", mock);
    await postPipelineLabels({ "icon_a.png": "minimax_code", "icon_b.png": "ssrun" });
    const [, init] = mock.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(body.labels["icon_a.png"]).toBe("minimax_code");
    expect(body.labels["icon_b.png"]).toBe("ssrun");
    expect(mock.mock.calls[0][0]).toBe("/api/pipeline/labels");
    vi.unstubAllGlobals();
  });

  it("postPipelineRunActualTask hits /api/pipeline/run-actual-task", async () => {
    const mock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, started: true }),
    });
    vi.stubGlobal("fetch", mock);
    const r = await postPipelineRunActualTask();
    expect(r).toEqual({ ok: true, started: true });
    expect(mock.mock.calls[0][0]).toBe("/api/pipeline/run-actual-task");
    vi.unstubAllGlobals();
  });

  it("openPipelineEventStream returns EventSource pointing at /api/pipeline/events", () => {
    const ctor = vi.fn();
    vi.stubGlobal("EventSource", ctor as unknown as typeof EventSource);
    openPipelineEventStream();
    expect(ctor).toHaveBeenCalledWith("/api/pipeline/events");
    vi.unstubAllGlobals();
  });
});
