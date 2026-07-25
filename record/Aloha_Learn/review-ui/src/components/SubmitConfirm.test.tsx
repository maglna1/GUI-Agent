import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SubmitConfirm } from "./SubmitConfirm";

describe("SubmitConfirm", () => {
  it("shows counts and triggers callbacks", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <SubmitConfirm
        accepted={3}
        edited={2}
        skipped={1}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );
    expect(screen.getByText(/accept: 3/)).toBeInTheDocument();
    expect(screen.getByText(/edit: 2/)).toBeInTheDocument();
    expect(screen.getByText(/skip: 1/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认提交" }));
    expect(onConfirm).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "再看看" }));
    expect(onCancel).toHaveBeenCalled();
  });
});