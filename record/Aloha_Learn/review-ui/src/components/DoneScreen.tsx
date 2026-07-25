import type { AppliedCounts } from "../types";

interface Props {
  applied: AppliedCounts;
  keysAdded: string[];
  keysUpdated: string[];
}

export function DoneScreen({ applied, keysAdded, keysUpdated }: Props) {
  return (
    <div className="done-screen">
      <h1>已完成</h1>
      <ul>
        <li>accept: {applied.accepted}</li>
        <li>edit: {applied.edited}</li>
        <li>skip: {applied.skipped}</li>
        <li>sanitize_fallback: {applied.sanitize_fallback}</li>
      </ul>
      <p data-testid="keys-added">{"keys_added: " + keysAdded.join(", ")}</p>
      <p data-testid="keys-updated">{"keys_updated: " + keysUpdated.join(", ")}</p>
    </div>
  );
}