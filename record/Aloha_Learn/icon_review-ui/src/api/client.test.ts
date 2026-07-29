import { describe, expect, it, vi } from "vitest";
import { getClicks, getLabels, getIcon, postDecisions, postFinish } from "./client";

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
