import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClickRow } from "./ClickRow";
import type { Click } from "../types";

vi.mock("../api/client", () => ({
  getIcon: vi.fn().mockResolvedValue({ label: "ssrun", url: "data:image/png;base64,AAA" }),
}));

const sample: Click = {
  step_idx: 7,
  timestamp: 12.5,
  coords: [321, 788],
  current_software: "ssrun",
  prompt: "点击 ssrun 启动器图标",
  screenshot_url: "/api/screenshot/12.4s.jpg",
};

// step_idx 7 + rowNumber 3 → both labels visible in the meta pill row, easy
// to assert against in aria attributes and DOM queries.
const ROW_NUMBER = 3;

describe("ClickRow", () => {
  it("toggles the is_icon checkbox and notifies onChange", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ClickRow
        rowNumber={ROW_NUMBER}
        click={sample}
        decision={{ is_icon: false, label: "" }}
        labels={["ssrun", "chrome"]}
        onChange={onChange}
      />
    );

    const box = screen.getByLabelText(`标记 Row ${ROW_NUMBER}（步骤 7）为图标点击`) as HTMLInputElement;
    expect(box.checked).toBe(false);

    await user.click(box);
    expect(onChange).toHaveBeenCalledWith({ is_icon: true, label: "" });
  });

  it("selecting a label while is_icon=true emits the full decision", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ClickRow
        rowNumber={ROW_NUMBER}
        click={sample}
        decision={{ is_icon: true, label: "ssrun" }}
        labels={["ssrun", "chrome"]}
        onChange={onChange}
      />
    );

    // LabelPicker trigger button (has the aria-label).
    const trigger = screen.getByLabelText(`选择 Row ${ROW_NUMBER}（步骤 7）的图标标签`) as HTMLButtonElement;
    expect(trigger.disabled).toBe(false);

    await user.click(trigger);
    // Dropdown opens; click the "chrome" option.
    const chromeOption = await screen.findByRole("button", { name: /chrome$/ });
    await user.click(chromeOption);
    expect(onChange).toHaveBeenCalledWith({ is_icon: true, label: "chrome" });
  });

  it("disables label picker when is_icon is false", () => {
    render(
      <ClickRow
        rowNumber={ROW_NUMBER}
        click={sample}
        decision={{ is_icon: false, label: "" }}
        labels={["ssrun", "chrome"]}
        onChange={() => {}}
      />
    );

    const trigger = screen.getByLabelText(`选择 Row ${ROW_NUMBER}（步骤 7）的图标标签`) as HTMLButtonElement;
    expect(trigger.disabled).toBe(true);
  });

  it("disables label picker when label library is empty", () => {
    render(
      <ClickRow
        rowNumber={ROW_NUMBER}
        click={sample}
        decision={{ is_icon: true, label: "" }}
        labels={[]}
        onChange={() => {}}
      />
    );

    const trigger = screen.getByLabelText(`选择 Row ${ROW_NUMBER}（步骤 7）的图标标签`) as HTMLButtonElement;
    expect(trigger.disabled).toBe(true);
  });

  it("renders screenshot, prompt, coords, and software", () => {
    render(
      <ClickRow
        rowNumber={ROW_NUMBER}
        click={sample}
        decision={{ is_icon: false, label: "" }}
        labels={["ssrun"]}
        onChange={() => {}}
      />
    );

    expect(screen.getByAltText(/screenshot for step 7/i)).toBeInTheDocument();
    expect(screen.getByText("点击 ssrun 启动器图标")).toBeInTheDocument();
    expect(screen.getAllByText("ssrun").length).toBeGreaterThan(0);
    expect(screen.getByText("12.50s")).toBeInTheDocument();
  });

  it("shows visual Row N pill alongside 步骤 #N", () => {
    render(
      <ClickRow
        rowNumber={ROW_NUMBER}
        click={sample}
        decision={{ is_icon: false, label: "" }}
        labels={["ssrun"]}
        onChange={() => {}}
      />
    );

    // Visual row number, top-down starting at 1.
    expect(screen.getByTestId("row-number")).toHaveTextContent(`Row ${ROW_NUMBER}`);
    // Step number (matches trace.step_idx) is shown alongside.
    expect(screen.getByText("步骤 #7")).toBeInTheDocument();
  });
});
