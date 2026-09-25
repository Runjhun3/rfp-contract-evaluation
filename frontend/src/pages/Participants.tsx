import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { post } from "../api";
import BidUploads from "../components/BidUploads";
import FirmPicker from "../components/FirmPicker";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { ErrorText, Loading } from "../components/Status";
import { plural } from "../format";
import type { ParticipantsPage } from "../types";
import { useApi } from "../useApi";

export default function Participants() {
  const { tenderId } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const search = params.get("q") ?? "";
  const base = `/api/v1/projects/${tenderId}`;
  const { data, error, reload } = useApi<ParticipantsPage>(`${base}/participants?q=${encodeURIComponent(search)}`);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `Participants · ${data.project.name}`);
  if (!data) return <Loading error={error} />;

  // Every write on this screen: show its error, or reload the lists after it.
  async function act(path: string, body: unknown, after: (reply: unknown) => void = reload) {
    setBusy(true);
    setActionError(null);
    try {
      after(await post<unknown>(path, body));
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const evaluate = () =>
    act(`${base}/runs`, undefined, (reply) => navigate(`/runs/${(reply as { run_id: string }).run_id}`));
  const { submissions, ready, approved } = data;

  return (
    <>
      <main className="page">
        <ProjectHead project={data.project} steps={data.steps} />
        <ErrorText error={actionError} />
        <div className="two">
          <FirmPicker data={data} search={search} busy={busy}
            onSave={(ids) => act(`${base}/participants`, { bidder_ids: ids })}
            onAdd={(firm) => act(`${base}/firms`, firm)} />
          <BidUploads submissions={submissions} busy={busy}
            onUpload={(id, form) => act(`/api/v1/submissions/${id}/file`, form)} />
        </div>
      </main>
      <div className="actions">
        <Link to={`/projects/${tenderId}/criteria`}>Back to criteria</Link>
        <div className="row">
          {!approved ? <span className="small muted">Criteria must be approved first.</span>
            : !ready ? <span className="small muted">Upload at least one bid.</span>
            : ready < submissions.length ? <span className="small muted">Participants without a bid are left out of this run.</span>
            : null}
          <button className="btn primary" type="button" onClick={evaluate} disabled={!approved || !ready || busy}>
            Evaluate {plural(ready, "participant")}
          </button>
        </div>
      </div>
    </>
  );
}
