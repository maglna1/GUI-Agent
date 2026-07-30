import { useEffect, useRef } from "react";

interface Props {
  lines: string[];
  emptyText?: string;
}

/** Auto-scrolling log panel used by step 2 and step 4. */
export function PipelineLogPanel({ lines, emptyText }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines]);

  if (lines.length === 0) {
    return (
      <div className="pipeline-log pipeline-log--empty">
        {emptyText ?? "暂无日志"}
      </div>
    );
  }

  return (
    <div className="pipeline-log" ref={ref} data-testid="pipeline-log">
      {lines.map((line, idx) => (
        <div key={idx} className="pipeline-log-line">
          {line}
        </div>
      ))}
    </div>
  );
}
