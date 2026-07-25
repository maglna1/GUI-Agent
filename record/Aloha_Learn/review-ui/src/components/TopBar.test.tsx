import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TopBar } from "./TopBar";

describe("TopBar", () => {
  it("renders counts and the manual-mode toggle", () => {
    render(
      <TopBar
        totalIcons={10}
        accepted={3}
        edited={2}
        skipped={1}
        manualMode={false}
        onToggleManual={() => {}}
        onAcceptAll={() => {}}
        onSubmit={() => {}}
      />
    );
    expect(screen.getByText(/共 10 张/)).toBeInTheDocument();
    expect(screen.getByText(/3 accept/)).toBeInTheDocument();
    expect(screen.getByText(/2 edit/)).toBeInTheDocument();
    expect(screen.getByText(/1 skip/)).toBeInTheDocument();
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