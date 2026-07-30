import type { Click, Decision } from "../types";
import { ClickRow } from "./ClickRow";

interface Props {
  clicks: Click[];
  decisions: Record<string, Decision>;
  labels: string[];
  onDecision?: (step_idx: number, decision: Decision) => void;
  readOnly?: boolean;
}

export function ClickList({ clicks, decisions, labels, onDecision, readOnly }: Props) {
  if (clicks.length === 0) {
    return <div className="empty-state">没有需要确认的 click。</div>;
  }
  return (
    <div className="click-list">
      {clicks.map((click, idx) => (
        <ClickRow
          key={click.step_idx}
          rowNumber={idx + 1}
          click={click}
          decision={decisions[String(click.step_idx)] ?? { is_icon: false, label: "" }}
          labels={labels}
          onChange={(d) => onDecision?.(click.step_idx, d)}
          readOnly={readOnly}
        />
      ))}
    </div>
  );
}
