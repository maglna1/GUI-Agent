import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DoneScreen } from "./DoneScreen";

describe("DoneScreen", () => {
  it("renders applied counts and key lists", () => {
    render(
      <DoneScreen
        applied={{ accepted: 2, edited: 1, skipped: 1, sanitize_fallback: 0 }}
        keysAdded={["a", "b"]}
        keysUpdated={["c"]}
      />
    );
    expect(screen.getByText(/已完成/)).toBeInTheDocument();
    expect(screen.getByTestId("keys-added")).toHaveTextContent(/a, b/);
    expect(screen.getByTestId("keys-updated")).toHaveTextContent(/c/);
  });
});