import type { ClickList, LabelsList, IconLookup, Decision, FinishResult, PipelineState } from "../types";

async function asJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`HTTP ${r.status}: ${text || r.statusText}`);
  }
  return r.json() as Promise<T>;
}

export async function getClicks(): Promise<ClickList> {
  return asJson<ClickList>(await fetch("/api/clicks", { method: "GET" }));
}

export async function getLabels(): Promise<LabelsList> {
  return asJson<LabelsList>(await fetch("/api/labels", { method: "GET" }));
}

export async function getIcon(label: string): Promise<IconLookup> {
  return asJson<IconLookup>(
    await fetch(`/api/icon/${encodeURIComponent(label)}`, { method: "GET" })
  );
}

/** Send decisions to the server. server keys decisions by step_idx string. */
export async function postDecisions(
  decisions: Record<string, Decision>
): Promise<{ ok: true; count: number }> {
  return asJson<{ ok: true; count: number }>(
    await fetch("/api/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decisions }),
    })
  );
}

export async function postFinish(): Promise<FinishResult> {
  return asJson<FinishResult>(await fetch("/api/finish", { method: "POST" }));
}

// -- Pipeline endpoints -----------------------------------------------------

export async function getPipelineState(): Promise<PipelineState> {
  return asJson<PipelineState>(
    await fetch("/api/pipeline/state", { method: "GET" })
  );
}

export async function postPipelineStart(goal: string): Promise<{ ok: true; snapshot: PipelineState }> {
  return asJson<{ ok: true; snapshot: PipelineState }>(
    await fetch("/api/pipeline/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal }),
    })
  );
}

/** List local record projects (for the start-screen dropdown). */
export async function getPipelineProjects(): Promise<{ projects: string[] }> {
  return asJson<{ projects: string[] }>(
    await fetch("/api/pipeline/projects", { method: "GET" })
  );
}

/** List existing scenes (for the start-screen combobox suggestions). */
export async function getPipelineScenes(): Promise<{ scenes: string[] }> {
  return asJson<{ scenes: string[] }>(
    await fetch("/api/pipeline/scenes", { method: "GET" })
  );
}

/** Set project/scene/task/goal on the orchestrator before starting. */
export async function postPipelineConfigure(payload: {
  project: string;
  scene: string;
  task: string;
  goal: string;
}): Promise<{ ok: true; snapshot: PipelineState }> {
  return asJson<{ ok: true; snapshot: PipelineState }>(
    await fetch("/api/pipeline/configure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  );
}

export async function postPipelineCancel(): Promise<{ ok: true }> {
  return asJson<{ ok: true }>(
    await fetch("/api/pipeline/cancel", { method: "POST" })
  );
}

export async function postPipelineLabels(
  labels: Record<string, string>
): Promise<{ ok: true; count: number }> {
  return asJson<{ ok: true; count: number }>(
    await fetch("/api/pipeline/labels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ labels }),
    })
  );
}

export async function postPipelineRunActualTask(): Promise<{ ok: true; started: boolean }> {
  return asJson<{ ok: true; started: boolean }>(
    await fetch("/api/pipeline/run-actual-task", { method: "POST" })
  );
}

/** Subscribe to orchestrator SSE events. Caller must close the EventSource. */
export function openPipelineEventStream(): EventSource {
  return new EventSource("/api/pipeline/events");
}

// -- Step 3 inline (main-UI) icon-click confirmation ----------------------
// These mirror the legacy icon_review endpoints but are served by
// pipeline_server so Step 3 can render ClickList inline without a popup.

export async function getPipelineClicks(): Promise<{ clicks: import("../types").Click[]; total: number }> {
  return asJson<{ clicks: import("../types").Click[]; total: number }>(
    await fetch("/api/pipeline/clicks", { method: "GET" })
  );
}

export async function getLibraryLabels(): Promise<{ labels: string[] }> {
  return asJson<{ labels: string[] }>(await fetch("/api/labels", { method: "GET" }));
}

export async function postPipelineDecisions(
  decisions: Record<string, Decision>
): Promise<{ ok: true; count: number }> {
  return asJson<{ ok: true; count: number }>(
    await fetch("/api/pipeline/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decisions }),
    })
  );
}
