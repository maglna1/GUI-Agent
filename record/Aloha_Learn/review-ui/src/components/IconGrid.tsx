import type { Icon, Decision } from "../types";
import { IconCard } from "./IconCard";

interface Props {
  icons: Icon[];
  decisions: Record<string, Decision | null>;
  existingLabels: string[];
  focusIndex: number;
  onFocus: (index: number) => void;
  onAccept: (filename: string) => void;
  onEdit: (filename: string) => void;
  onSkip: (filename: string) => void;
}

export function IconGrid({
  icons, decisions, existingLabels, focusIndex, onFocus,
  onAccept, onEdit, onSkip,
}: Props) {
  return (
    <div className="icon-grid" role="list">
      {icons.map((icon, index) => (
        <IconCard
          key={icon.filename}
          icon={icon}
          decision={decisions[icon.filename] ?? null}
          existingLabels={existingLabels}
          isFocused={index === focusIndex}
          onMouseEnter={() => onFocus(index)}
          onAccept={onAccept}
          onEdit={onEdit}
          onSkip={onSkip}
        />
      ))}
    </div>
  );
}