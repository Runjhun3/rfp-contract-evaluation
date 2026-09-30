import { useState, type FormEvent } from "react";
import { post } from "../api";
import { word } from "../eligibility";
import type { CheckDetail } from "../types";
import { ErrorText } from "./Status";

type Choice = "MET" | "NOT_MET";
type Props = { check: CheckDetail; onSaved: () => void };

// The committee's decision on one screening check: an eligibility criterion is met or
// not, a required document submitted or not. Confirming a clear AI result needs no
// reason; one is needed when the AI was unsure or the committee disagrees with it.
// Decisions are appended to the record; the API checks the rule again.
export default function CheckDecisionForm({ check, onSaved }: Props) {
  const last = check.decision;
  const start: Choice | "" = last?.decision ?? (check.result === "UNSURE" ? "" : check.result);
  const [choice, setChoice] = useState<Choice | "">(start);
  const [reason, setReason] = useState(last?.reason ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const needsReason = check.result === "UNSURE" || (choice !== "" && choice !== check.result);
  const isDocument = check.stage === "DOCUMENT";
  const options = isDocument ? { MET: "Submitted", NOT_MET: "Not submitted" }
    : { MET: "Meets the requirement", NOT_MET: "Does not meet it" };

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!choice) return setError(isDocument ? "Choose whether the document was submitted." : "Choose whether the bid meets the requirement.");
    setBusy(true);
    setError(null);
    try {
      await post(`/api/v1/eligibility/${check.check_id}/decision`, { decision: choice, reason });
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
          <strong>Committee decision for this check</strong>
          {last && <span className="small muted"> · decided {word(check.stage, last.decision)} by {last.by}, {last.decided}</span>}
        </legend>
        {(["MET", "NOT_MET"] as const).map((v) => (
          <label key={v} className="check">
            <input type="radio" name="decision" checked={choice === v} onChange={() => setChoice(v)} />
            {options[v]}
          </label>
        ))}
      </fieldset>
      <label className="field">
        Reason (goes on the record){needsReason
          ? (check.result === "UNSURE" ? " · needed, the AI was unsure" : " · needed, you disagree with the AI")
          : " · optional when confirming the AI"}
        <textarea rows={3} minLength={needsReason ? 10 : undefined} required={needsReason}
          value={reason} onChange={(e) => setReason(e.target.value)} />
      </label>
      <div className="row">
        <button className="btn primary" type="submit" disabled={busy}>Record decision</button>
      </div>
    </form>
  );
}
