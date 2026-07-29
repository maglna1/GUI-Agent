import { useEffect, useReducer, useRef, useState } from "react";
import { reducer, initialState } from "./store/reducer";
import { getClicks, getLabels, postDecisions, postFinish } from "./api/client";
import type { FinishResult } from "./types";
import { TopBar } from "./components/TopBar";
import { ClickList } from "./components/ClickList";
import { SubmitConfirm } from "./components/SubmitConfirm";
import { DoneScreen } from "./components/DoneScreen";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [confirming, setConfirming] = useState(false);
  const [doneResult, setDoneResult] = useState<FinishResult | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getClicks(), getLabels()])
      .then(([clicksRes, labelsRes]) => {
        if (cancelled) return;
        dispatch({
          type: "SET_QUEUE",
          clicks: clicksRes.clicks,
          labels: labelsRes.labels,
        });
      })
      .catch((e) =>
        dispatch({ type: "SET_LOAD_ERROR", error: `Failed to load: ${e}` })
      );
    return () => {
      cancelled = true;
    };
  }, []);

  // Debounced auto-save so per-row checkbox flips don't trigger a flood.
  useEffect(() => {
    if (state.clicks.length === 0) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      postDecisions(state.decisions).catch((e) =>
        console.error("postDecisions failed", e)
      );
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [state.decisions, state.clicks.length]);

  const iconCount = Object.values(state.decisions).filter(
    (d) => d.is_icon && d.label
  ).length;
  const totalClicks = state.clicks.length;

  async function handleConfirm() {
    setConfirming(false);
    dispatch({ type: "SET_SUBMITTING", submitting: true });
    try {
      // Final flush before close.
      await postDecisions(state.decisions);
      const result = await postFinish();
      setDoneResult(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      dispatch({ type: "SET_LOAD_ERROR", error: `Submit failed: ${msg}` });
      dispatch({ type: "SET_SUBMITTING", submitting: false });
    }
  }

  if (doneResult) {
    return <DoneScreen decided={doneResult.decided} total={doneResult.total} />;
  }

  if (state.loadError && state.clicks.length === 0) {
    return <div className="error-banner">{state.loadError}</div>;
  }

  return (
    <div className="app">
      <TopBar
        totalClicks={totalClicks}
        iconCount={iconCount}
        submitted={state.submitting}
        onSubmit={() => setConfirming(true)}
      />
      {state.loadError && <div className="error-banner">{state.loadError}</div>}
      <ClickList
        clicks={state.clicks}
        decisions={state.decisions}
        labels={state.labels}
        onDecision={(step_idx, decision) =>
          dispatch({ type: "SET_DECISION", step_idx, decision })
        }
      />
      {confirming && (
        <SubmitConfirm
          iconCount={iconCount}
          normalCount={totalClicks - iconCount}
          onCancel={() => setConfirming(false)}
          onConfirm={handleConfirm}
        />
      )}
    </div>
  );
}
