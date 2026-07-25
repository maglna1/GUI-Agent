import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IconCard } from "./IconCard";
import type { Icon } from "../types";

const icon: Icon = {
  filename: "a.png",
  icon_url: "/icons/a.png",
  llm_label: "start_button",
  is_timestamp_fallback: false,
  action: "LClick at",
  coords: [1, 2],
  current_software: "Chrome",
  base: "10.0s",
};

describe("IconCard", () => {
  it("renders label, image, and three action buttons", () => {
    render(
      <IconCard
        icon={icon}
        decision={null}
        existingLabels={[]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    expect(screen.getByAltText("start_button")).toHaveAttribute("src", "/icons/a.png");
    expect(screen.getByText("start_button")).toBeInTheDocument();
    expect(screen.getByText("✓")).toBeInTheDocument();
    expect(screen.getByText("✎")).toBeInTheDocument();
    expect(screen.getByText("⨯")).toBeInTheDocument();
  });

  it("shows existing-label warning", () => {
    render(
      <IconCard
        icon={icon}
        decision={null}
        existingLabels={["start_button"]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    expect(screen.getByText(/已存在/)).toBeInTheDocument();
  });

  it("shows fallback indicator", () => {
    const fb: Icon = { ...icon, llm_label: "record_memory_icon_10_0s_crop", is_timestamp_fallback: true };
    render(
      <IconCard
        icon={fb}
        decision={null}
        existingLabels={[]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    expect(screen.getByText(/LLM 未命名/)).toBeInTheDocument();
  });

  it("calls onAccept/onEdit/onSkip on button clicks", () => {
    const onAccept = vi.fn();
    const onEdit = vi.fn();
    const onSkip = vi.fn();
    render(
      <IconCard
        icon={icon}
        decision={null}
        existingLabels={[]}
        onAccept={onAccept}
        onEdit={onEdit}
        onSkip={onSkip}
      />
    );
    fireEvent.click(screen.getByText("✓"));
    expect(onAccept).toHaveBeenCalledWith("a.png");
    fireEvent.click(screen.getByText("✎"));
    expect(onEdit).toHaveBeenCalledWith("a.png");
    fireEvent.click(screen.getByText("⨯"));
    expect(onSkip).toHaveBeenCalledWith("a.png");
  });

  it("reflects the current decision in button styling", () => {
    render(
      <IconCard
        icon={icon}
        decision={{ action: "skip" }}
        existingLabels={[]}
        onAccept={() => {}}
        onEdit={() => {}}
        onSkip={() => {}}
      />
    );
    const skipBtn = screen.getByText("⨯");
    expect(skipBtn.className).toMatch(/active/);
  });
});