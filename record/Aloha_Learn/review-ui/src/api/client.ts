import type { Queue, FinishResult, Decision } from "../types";

async function asJson<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`HTTP ${r.status}: ${text || r.statusText}`);
  }
  return r.json() as Promise<T>;
}

export async function getQueue(): Promise<Queue> {
  return asJson<Queue>(await fetch("/api/queue", { method: "GET" }));
}

export async function postDecisions(payload: {
  decisions: Record<string, Decision | null>;
  manual_mode: boolean;
}): Promise<void> {
  const r = await fetch("/api/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await asJson<{ ok: true }>(r);
}

export async function postFinish(): Promise<FinishResult> {
  return asJson<FinishResult>(await fetch("/api/finish", { method: "POST" }));
}