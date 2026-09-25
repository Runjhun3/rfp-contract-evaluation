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

export default function Results() {
  const { runId } = useParams();
  const { data, error, reload } = useApi<ResultsPage>(`/api/v1/runs/${runId}/results`);
  const [presentation, setPresentation] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `Results · ${data.project.name}`);

  useEffect(() => {
    if (data) setPresentation(Object.fromEntries(data.rows.map((r) => [r.submission_id, r.presentation ?? ""])));
  }, [data]);

  if (!data) return <Loading error={error} />;

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaveError(null);
    try {
      await post(`/api/v1/runs/${runId}/presentation`, { marks: presentation });
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
        {data.open_reviews > 0 && (
          <div className="notice">
            <strong>{plural(data.open_reviews, "mark")} need{data.open_reviews === 1 ? "s" : ""} a committee decision</strong>{" "}
            before the sheet can be signed. Click an amber mark to see the evidence.
          </div>
        )}
        <ErrorText error={saveError} />
        <form onSubmit={save}>
          <ResultsTable data={data} presentation={presentation} onPresentation={setPresentation} />
          {data.presentation && (
            <p><button className="btn small" type="submit" disabled={busy}>Save presentation marks</button></p>
          )}
        </form>
        <p className="small muted">
          Amber = needs a committee decision · dotted underline = decided by the committee · document
          marks are recommendations until accepted or overridden.
        </p>
      </main>
      <div className="actions">
        <Link to={`/projects/${data.project.tender_id}/participants`}>Participants</Link>
        <div className="row">
          {data.open_reviews > 0 && <span className="small muted">Export is available once all decisions are recorded.</span>}
          <button className="btn primary" type="button" disabled>Export Annexure III sheet</button>
        </div>
      </div>
    </>
  );
}
