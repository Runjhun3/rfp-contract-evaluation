import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { del, post } from "../api";
import BidUploads from "../components/BidUploads";
import FirmPicker from "../components/FirmPicker";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { ErrorText, Loading } from "../components/Status";
import { plural } from "../format";
import type { Firm, ParticipantsPage } from "../types";
import { useApi } from "../useApi";

export default function Participants() {
  const { tenderId } = useParams();
  const [params] = useSearchParams();
  const search = params.get("q") ?? "";
  const base = `/api/v1/projects/${tenderId}`;
  const { data, error, reload } = useApi<ParticipantsPage>(`${base}/participants?q=${encodeURIComponent(search)}`);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `Participants · ${data.project.name}`);
  if (!data) return <Loading error={error} />;

  // Every write on this screen: show its error, or reload the lists after it.
  async function act(send: () => Promise<unknown>, after: (reply: unknown) => void = reload) {
    setBusy(true);
    setActionError(null);
    try {
      after(await send());
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const deleteFirm = (firm: Firm) => {
    if (window.confirm(`Delete ${firm.legal_name} from the firm list? It is removed from every project.`)) {
      act(() => del(`/api/v1/firms/${firm.bidder_id}`));
    }
  };
  const { submissions, ready, approved } = data;

  return (
    <>
      <main className="page">
        <ProjectHead project={data.project} steps={data.steps} />
        <ErrorText error={actionError} />
        <div className="two">
          <FirmPicker data={data} search={search} busy={busy}
            onSave={(ids) => act(() => post(`${base}/participants`, { bidder_ids: ids }))}
            onAdd={(firm) => act(() => post(`${base}/firms`, firm))} onDelete={deleteFirm} />
          <BidUploads submissions={submissions} busy={busy}
            onUpload={(id, form) => act(() => post(`/api/v1/submissions/${id}/file`, form))} />
        </div>
      </main>
      <div className="actions">
        <Link to={`/projects/${tenderId}/criteria`}>Back to criteria</Link>
        <div className="row">
          {!approved ? <span className="small muted">Criteria must be approved first.</span>
            : !ready ? <span className="small muted">Upload at least one bid.</span>
            : <span className="small muted">{plural(ready, "bid")} uploaded; each is checked for eligibility as it arrives.</span>}
          {approved && ready > 0 ? (
            <Link className="btn primary" to={`/projects/${tenderId}/eligibility`}>Check Eligibility</Link>
          ) : <button className="btn primary" type="button" disabled>Check Eligibility</button>}
        </div>
      </div>
    </>
  );
}
