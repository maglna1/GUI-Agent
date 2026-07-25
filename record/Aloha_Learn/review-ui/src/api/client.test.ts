import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { getQueue, postDecisions, postFinish } from "./client";
import type { Queue, FinishResult } from "../types";

describe("api/client", () => {
  const origFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = origFetch;
  });

  it("getQueue fetches /api/queue and parses JSON", async () => {
    const queue: Queue = {
      icons: [], existing_labels: [], dest: "D:", manual_mode_default: false,
    };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true, status: 200, json: async () => queue,
    });
    const got = await getQueue();
    expect(got).toEqual(queue);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/queue", expect.objectContaining({ method: "GET" }));
  });

  it("getQueue throws on non-2xx", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: false, status: 500, text: async () => "boom" });
    await expect(getQueue()).rejects.toThrow(/500/);
  });

  it("postDecisions sends POST with body", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ok: true }) });
    await postDecisions({ decisions: { a: { action: "accept" } }, manual_mode: false });
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/decisions", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ decisions: { a: { action: "accept" } }, manual_mode: false }),
    }));
  });

  it("postFinish returns FinishResult", async () => {
    const result: FinishResult = {
      applied: { accepted: 1, edited: 0, skipped: 0, sanitize_fallback: 0 },
      keys_added: ["x"], keys_updated: [],
    };
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: true, status: 200, json: async () => result });
    const got = await postFinish();
    expect(got).toEqual(result);
  });
});