import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TopBar } from "./TopBar";

describe("TopBar", () => {
  it("renders brand, count pills, progress bar, and the manual-mode toggle", () => {
    render(
      <TopBar
        totalIcons={10}
        accepted={3}
        edited={2}
        skipped={1}
        reviewed={6}
        manualMode={false}
        onToggleManual={() => {}}
        onAcceptAll={() => {}}
        onSubmit={() => {}}
      />
    );
    expect(screen.getByText("Record Icon Review")).toBeInTheDocument();
    // Count pills are spans with text "✓ 3", "✎ 2", "⨯ 1" etc.
    expect(screen.getByText(/✓/)).toBeInTheDocument();
    expect(screen.getByText(/✎/)).toBeInTheDocument();
    expect(screen.getByText(/⨯/)).toBeInTheDocument();
    expect(screen.getByText(/\/\s*10/)).toBeInTheDocument(); // "/ 10" total indicator
    // Progress bar reflects reviewed/total
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "6");
    expect(bar).toHaveAttribute("aria-valuemax", "10");
    expect(screen.getByLabelText(/全手动/)).toBeInTheDocument();
  });

  it("calls callbacks on user actions", () => {
    const onToggle = vi.fn();
    const onAcceptAll = vi.fn();
    const onSubmit = vi.fn();
    render(
      <TopBar
        totalIcons={5}
        accepted={0}
        edited={0}
        skipped={0}
        reviewed={0}
        manualMode={false}
        onToggleManual={onToggle}
        onAcceptAll={onAcceptAll}
        onSubmit={onSubmit}
      />
    );
    fireEvent.click(screen.getByLabelText(/全手动/));
    expect(onToggle).toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByText("全部接受"));
    expect(onAcceptAll).toHaveBeenCalled();
    fireEvent.click(screen.getByText("提交"));
    expect(onSubmit).toHaveBeenCalled();
  });
});