import { useEffect, useReducer, useRef, useState } from "react";
import { reducer, initialState } from "./store/reducer";
import { getQueue, postDecisions, postFinish } from "./api/client";
import { TopBar } from "./components/TopBar";
import { IconGrid } from "./components/IconGrid";
import { IconDetail } from "./components/IconDetail";
import { SubmitConfirm } from "./components/SubmitConfirm";
import { DoneScreen } from "./components/DoneScreen";
import type { FinishResult, Icon } from "./types";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [editing, setEditing] = useState<Icon | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [doneResult, setDoneResult] = useState<FinishResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getQueue()
      .then((q) => dispatch({ type: "SET_QUEUE", icons: q.icons, existing_labels: q.existing_labels, dest: q.dest, manual_mode_default: q.manual_mode_default }))
      .catch((e) => setError(`Failed to load queue: ${e}`));
  }, []);

  useEffect(() => {
    if (state.icons.length === 0) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      postDecisions({ decisions: state.decisions, manual_mode: state.manualMode }).catch((e) => console.error("postDecisions failed", e));
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [state.decisions, state.manualMode, state.icons.length]);

  const counts = countDecisions(state);

  function handleSubmit() {
    setError(null);
    const missing = state.icons.filter((icon) => state.decisions[icon.filename] === null);
    if (missing.length > 0) { setError(`还有 ${missing.length} 张未决定`); return; }
    setConfirming(true);
  }

  async function handleConfirm() {
    setConfirming(false);
    dispatch({ type: "SET_SUBMITTING", submitting: true });
    try { setDoneResult(await postFinish()); }
    catch (e: any) { setError(`Submit failed: ${e.message ?? e}`); dispatch({ type: "SET_SUBMITTING", submitting: false }); }
  }

  if (doneResult) return <DoneScreen applied={doneResult.applied} keysAdded={doneResult.keys_added} keysUpdated={doneResult.keys_updated} />;
  if (error && state.icons.length === 0) return <div className="error-banner">{error}</div>;

  return (
    <div className="app">
      <TopBar totalIcons={state.icons.length} accepted={counts.accepted} edited={counts.edited} skipped={counts.skipped} manualMode={state.manualMode} onToggleManual={(next) => dispatch({ type: "SET_MANUAL_MODE", manualMode: next })} onAcceptAll={() => dispatch({ type: "APPLY_BULK_ACCEPT" })} onSubmit={handleSubmit} />
      {error && <div className="error-banner">{error}</div>}
      <IconGrid icons={state.icons} decisions={state.decisions} existingLabels={state.existingLabels}
        onAccept={(filename) => dispatch({ type: "SET_DECISION", filename, decision: { action: "accept" } })}
        onEdit={(filename) => { const icon = state.icons.find((item) => item.filename === filename); if (icon) setEditing(icon); }}
        onSkip={(filename) => dispatch({ type: "SET_DECISION", filename, decision: { action: "skip" } })} />
      {editing && <IconDetail icon={editing} initialLabel={editing.llm_label} onCancel={() => setEditing(null)}
        onSkip={() => { dispatch({ type: "SET_DECISION", filename: editing.filename, decision: { action: "skip" } }); setEditing(null); }}
        onSave={(label) => { dispatch({ type: "SET_DECISION", filename: editing.filename, decision: { action: "edit", label } }); setEditing(null); }} />}
      {confirming && <SubmitConfirm accepted={counts.accepted} edited={counts.edited} skipped={counts.skipped} onCancel={() => setConfirming(false)} onConfirm={handleConfirm} />}
    </div>
  );
}

function countDecisions(state: ReturnType<typeof reducer>) {
  let accepted = 0, edited = 0, skipped = 0;
  for (const decision of Object.values(state.decisions)) {
    if (!decision) continue;
    if (decision.action === "accept") accepted++;
    else if (decision.action === "edit") edited++;
    else if (decision.action === "skip") skipped++;
  }
  return { accepted, edited, skipped };
}
