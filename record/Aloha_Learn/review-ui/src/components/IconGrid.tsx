import type { Icon, Decision } from "../types";
import { IconCard } from "./IconCard";

interface Props {
  icons: Icon[];
  decisions: Record<string, Decision | null>;
  existingLabels: string[];
  onAccept: (filename: string) => void;
  onEdit: (filename: string) => void;
  onSkip: (filename: string) => void;
}

export function IconGrid({ icons, decisions, existingLabels, onAccept, onEdit, onSkip }: Props) {
  return (
    <div className="icon-grid">
      {icons.map((icon) => (
        <IconCard
          key={icon.filename}
          icon={icon}
          decision={decisions[icon.filename] ?? null}
          existingLabels={existingLabels}
          onAccept={onAccept}
          onEdit={onEdit}
          onSkip={onSkip}
        />
      ))}
    </div>
  );
}