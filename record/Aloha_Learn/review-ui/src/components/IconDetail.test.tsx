import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IconDetail } from "./IconDetail";
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

describe("IconDetail", () => {
  it("shows the big image and an editable label", () => {
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={() => {}}
        onSkip={() => {}}
        onCancel={() => {}}
      />
    );
    expect(screen.getByAltText("start_button")).toHaveAttribute("src", "/icons/a.png");
    expect(screen.getByDisplayValue("start_button")).toBeInTheDocument();
  });

  it("disables save when sanitize yields empty", () => {
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={() => {}}
        onSkip={() => {}}
        onCancel={() => {}}
      />
    );
    const input = screen.getByDisplayValue("start_button");
    fireEvent.change(input, { target: { value: "///??**" } });
    expect(screen.getByText("保存")).toBeDisabled();
  });

  it("calls onSave with sanitized label on save click", () => {
    const onSave = vi.fn();
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={onSave}
        onSkip={() => {}}
        onCancel={() => {}}
      />
    );
    const input = screen.getByDisplayValue("start_button");
    fireEvent.change(input, { target: { value: "Search Box" } });
    fireEvent.click(screen.getByText("保存"));
    expect(onSave).toHaveBeenCalledWith("search_box");
  });

  it("calls onSkip and onCancel", () => {
    const onSkip = vi.fn();
    const onCancel = vi.fn();
    render(
      <IconDetail
        icon={icon}
        initialLabel="start_button"
        onSave={() => {}}
        onSkip={onSkip}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByText("跳过"));
    expect(onSkip).toHaveBeenCalled();
    fireEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalled();
  });
});