import type { ClickList, LabelsList, IconLookup, Decision, FinishResult } from "../types";

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
