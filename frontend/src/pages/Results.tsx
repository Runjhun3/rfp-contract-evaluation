import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { post } from "../api";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import ResultsTable from "../components/ResultsTable";
import { ErrorText, Loading } from "../components/Status";
import { plural } from "../format";
import type { ResultsPage } from "../types";
import { useApi } from "../useApi";

// While any participant is being evaluated, check again every 10 s so its row fills in
// (or refreshes, when it is evaluated again) as soon as it finishes.
const whileRunning = (d: ResultsPage) => (d.evaluating > 0 ? 10000 : null);

// The project's results: each participant's latest evaluation, whichever run it came from.
export default function Results() {
  const { tenderId } = useParams();
  const { data, error, reload } = useApi<ResultsPage>(`/api/v1/projects/${tenderId}/results`, whileRunning);
  // Committee marks being typed, keyed "criterion id/submission id".
  const [entered, setEntered] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `Results · ${data.project.name}`);

  // Saved marks fill the inputs; what the user has typed but not saved is kept when a
  // refresh brings in another participant's results.
  useEffect(() => {
    if (!data) return;
    const saved = Object.fromEntries(data.rows.flatMap((r) =>
      data.committee.map((c) => [`${c.criterion_id}/${r.submission_id}`, r.manual[c.criterion_id] ?? ""])));
    setEntered((typed) => ({ ...saved, ...typed }));
  }, [data]);

  if (!data) return <Loading error={error} />;
  // A saved mark typed over with another value: the change needs a reason on the record.
  const changing = data.rows.some((r) => data.committee.some((c) => {
    const saved = r.manual[c.criterion_id];
    const typed = (entered[`${c.criterion_id}/${r.submission_id}`] ?? "").trim();
    return saved != null && typed !== "" && Number(typed) !== Number(saved);
  }));

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaveError(null);
    try {
      const marks: Record<string, Record<string, string>> = {};
      for (const [key, value] of Object.entries(entered)) {
        const [criterionId, submissionId] = key.split("/");
        (marks[criterionId] ??= {})[submissionId] = value;
      }
      await post(`/api/v1/projects/${tenderId}/committee-marks`, { marks, reason });
      setReason("");
      reload();
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <main className="page">
        <ProjectHead project={data.project} steps={data.steps} />
        {data.evaluating > 0 && (
          <div className="notice info" role="status">
            <strong>{plural(data.evaluating, "participant")} being evaluated.</strong>{" "}
            Their marks appear when each one finishes; ranks cover finished participants only.
          </div>
        )}
        {data.open_reviews > 0 && (
          <div className="notice">
            <strong>{plural(data.open_reviews, "mark")} awaiting committee approval.</strong>
          </div>
        )}
        <ErrorText error={saveError} />
        <form onSubmit={save}>
          <ResultsTable data={data} entered={entered} onEnter={setEntered} />
          {changing && (
            <label className="field reason">
              Reason for changing saved marks (goes on the record)
              <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
          )}
          {data.committee.length > 0 && (
            <p><button className="btn small" type="submit" disabled={busy}>Save committee marks</button></p>
          )}
        </form>
        <p className="small muted">
          Highlighted = not approved by the committee yet (● = flagged by the checks) · dotted underline =
          approved by the committee · document marks are recommendations until accepted or
          overridden · hover a committee mark to see who entered it.
        </p>
      </main>
      <div className="actions">
        <Link to={`/projects/${data.project.tender_id}/participants`}>Participants</Link>
        <div className="row">
          {data.export_blockers.length > 0 ? (
            // Why it is disabled stays one hover away, not on the page.
            <button className="btn primary" type="button" disabled title={data.export_blockers.join(" ")}>
              Export evaluation sheet
            </button>
          ) : (
            // A file download, not an API call: the browser saves the Excel sheet.
            <a className="btn primary" href={`/api/v1/projects/${tenderId}/export.xlsx`} download>Export evaluation sheet</a>
          )}
        </div>
      </div>
    </>
  );
}
