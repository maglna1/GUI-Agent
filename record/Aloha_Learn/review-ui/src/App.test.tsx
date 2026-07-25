import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";
import type { Queue, FinishResult } from "./types";

vi.mock("./api/client", () => ({
  getQueue: vi.fn(),
  postDecisions: vi.fn(),
  postFinish: vi.fn(),
}));

import { getQueue, postDecisions, postFinish } from "./api/client";

const queue: Queue = {
  icons: [
    { filename: "a.png", icon_url: "/icons/a.png", llm_label: "start_button", is_timestamp_fallback: false, action: "LClick at", coords: [1, 2], current_software: "Chrome", base: "10.0s" },
    { filename: "b.png", icon_url: "/icons/b.png", llm_label: "search", is_timestamp_fallback: false, action: "LClick at", coords: [3, 4], current_software: "Chrome", base: "11.0s" },
  ], existing_labels: [], dest: "D:", manual_mode_default: false,
};
const finishResult: FinishResult = { applied: { accepted: 1, edited: 0, skipped: 1, sanitize_fallback: 0 }, keys_added: ["start_button"], keys_updated: [] };

describe("App", () => {
  beforeEach(() => {
    vi.mocked(getQueue).mockResolvedValue(queue);
    vi.mocked(postDecisions).mockResolvedValue();
    vi.mocked(postFinish).mockResolvedValue(finishResult);
  });
  afterEach(() => { vi.clearAllMocks(); });

  it("fetches queue, renders cards, and submits on confirm", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("start_button")).toBeInTheDocument());
    fireEvent.click(screen.getAllByText("⨯")[1]);
    fireEvent.click(screen.getAllByText("⨯")[0]);
    fireEvent.click(screen.getByText("提交"));
    fireEvent.click(screen.getAllByText("确认提交")[1]);
    await waitFor(() => expect(postFinish).toHaveBeenCalled());
    expect(await screen.findByText("已完成")).toBeInTheDocument();
  });

  it("debounces postDecisions on decision change", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("start_button")).toBeInTheDocument());
    fireEvent.click(screen.getAllByText("✓")[0]);
    await waitFor(() => expect(postDecisions).toHaveBeenCalled(), { timeout: 1000 });
  });

  it("blocks submit when there are missing decisions", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("start_button")).toBeInTheDocument());
    fireEvent.click(screen.getByText("提交"));
    expect(screen.queryByText("确认提交")).not.toBeInTheDocument();
    expect(postFinish).not.toHaveBeenCalled();
  });
});
