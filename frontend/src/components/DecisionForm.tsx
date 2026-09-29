import { useState, type FormEvent } from "react";
import { post } from "../api";
import { marks } from "../format";
import type { Score, Verdict } from "../types";
import { ErrorText } from "./Status";

type Props = { score: Score; item: Verdict | null; onSaved: () => void };

// The committee's decision on one item (project or CV), or on the whole criterion
// when it has no items. Accepting keeps the AI's marks and needs no reason; overriding
// needs one. Decisions are appended to the record (never edited); the API checks them
// again and recomputes the criterion's final marks.
export default function DecisionForm({ score, item, onSaved }: Props) {
  const last = item?.decision ?? null;
  const [action, setAction] = useState<"ACCEPT" | "OVERRIDE">(last?.action === "OVERRIDE" ? "OVERRIDE" : "ACCEPT");
  const [override, setOverride] = useState(last?.action === "OVERRIDE" ? String(last.final_marks) : "");
  // The reason last recorded stays in the box until the committee changes it.
  const [reason, setReason] = useState(last?.reason ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const suggested = item ? item.ai_marks : score.checked_marks;
  const limit = item ? item.item_limit : score.max_marks;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await post(`/api/v1/scores/${score.score_id}/decision`,
        { item_id: item?.item_id ?? null, action, marks: override, reason });
      setSaved(true);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <ErrorText error={error} />
      <fieldset className="row">
        <legend>
          <strong>Committee decision for {item ? "this item" : score.code}</strong>
          {last && <span className="small muted"> · {last.action === "OVERRIDE" ? "overridden" : "accepted"}: {marks(last.final_marks)}</span>}
        </legend>
        <label className="check">
          <input type="radio" name="action" checked={action === "ACCEPT"} onChange={() => setAction("ACCEPT")} /> Accept {marks(suggested)}
        </label>
        <label className="check">
          <input type="radio" name="action" checked={action === "OVERRIDE"} onChange={() => setAction("OVERRIDE")} /> Override with
        </label>
        <label className="sr-only" htmlFor="override-marks">Overriding marks</label>
        <input id="override-marks" className="narrow" type="text" inputMode="decimal" value={override}
          onChange={(e) => setOverride(e.target.value)} disabled={action !== "OVERRIDE"} required={action === "OVERRIDE"}
          aria-describedby="override-range" />
        <span id="override-range" className="small muted">
          (0–{marks(limit)}){item?.count_based && " · 1 = the item counts, 0 = it does not"}
        </span>
      </fieldset>
      <label className="field">
        Reason (goes on the record){action === "ACCEPT" ? " · optional when accepting" : " · needed to override"}
        <textarea rows={3} minLength={action === "OVERRIDE" ? 10 : undefined} required={action === "OVERRIDE"}
          value={reason} onChange={(e) => setReason(e.target.value)} />
      </label>
      <div className="row">
        <button className="btn primary" type="submit" disabled={busy}>Record decision</button>
        {saved && <span className="small muted" role="status">Saved. The criterion's final marks are updated.</span>}
      </div>
    </form>
  );
}
