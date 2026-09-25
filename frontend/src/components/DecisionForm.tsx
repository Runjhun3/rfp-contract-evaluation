import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { post } from "../api";
import { marks } from "../format";
import type { Score } from "../types";
import { ErrorText } from "./Status";

type Props = { score: Score };

// Accept the checked marks or override them. Every decision needs a reason and is
// appended to the record (never edited); the API checks marks and reason again.
export default function DecisionForm({ score }: Props) {
  const navigate = useNavigate();
  const [action, setAction] = useState<"ACCEPT" | "OVERRIDE">("ACCEPT");
  const [override, setOverride] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post(`/api/v1/scores/${score.score_id}/decision`, { action, marks: override, reason });
      navigate(`/runs/${score.run_id}/results`);
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
        <legend><strong>Committee decision for {score.code}</strong></legend>
        <label className="check">
          <input type="radio" name="action" checked={action === "ACCEPT"} onChange={() => setAction("ACCEPT")} /> Accept {marks(score.checked_marks)}
        </label>
        <label className="check">
          <input type="radio" name="action" checked={action === "OVERRIDE"} onChange={() => setAction("OVERRIDE")} /> Override with
        </label>
        <label className="sr-only" htmlFor="override-marks">Overriding marks</label>
        <input id="override-marks" className="narrow" type="text" inputMode="decimal" value={override}
          onChange={(e) => setOverride(e.target.value)} disabled={action !== "OVERRIDE"} required={action === "OVERRIDE"} />
      </fieldset>
      <label className="field">Reason (goes on the record)
        <textarea rows={3} minLength={10} required value={reason} onChange={(e) => setReason(e.target.value)} />
      </label>
      <div><button className="btn primary" type="submit" disabled={busy}>Record decision</button></div>
    </form>
  );
}
