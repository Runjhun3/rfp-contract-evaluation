import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { post } from "../api";
import EligibilityGrid from "../components/EligibilityGrid";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { ErrorText, Loading } from "../components/Status";
import { plural } from "../format";
import type { EligibilityPage } from "../types";
import { useApi } from "../useApi";

// While any bid is being checked, ask again every 10 s so its row fills in.
const whileChecking = (d: EligibilityPage) => (d.checking > 0 ? 10000 : null);

// Eligibility screening: every firm's checks, highlighted until the committee decides
// them. Only firms decided as meeting every requirement go on to evaluation.
export default function Eligibility() {
  const { tenderId } = useParams();
  const navigate = useNavigate();
  const base = `/api/v1/projects/${tenderId}`;
  const { data, error, reload } = useApi<EligibilityPage>(`${base}/eligibility`, whileChecking);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `Eligibility · ${data.project.name}`);
  if (!data) return <Loading error={error} />;

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
  const evaluate = () => act(() => post(`${base}/runs`),
    (reply) => navigate(`/runs/${(reply as { run_id: string }).run_id}`));
  const waiting = data.firms.filter((f) => f.checking || (f.status !== "qualified" && f.status !== "not_qualified"));
  const out = data.firms.filter((f) => f.status === "not_qualified");
  const note = [waiting.length ? `${waiting.map((f) => f.name).join(", ")} ${waiting.length > 1 ? "wait" : "waits"} for eligibility` : "",
    out.length ? `${out.map((f) => f.name).join(", ")} not qualified` : ""].filter(Boolean).join(" · ");

  return (
    <>
      <main className="page">
        <ProjectHead project={data.project} steps={data.steps} />
        <div className="spread">
          <div>
            <h2>Eligibility screening</h2>
            <p className="sub">Only firms the committee finds meet every eligibility criterion go on to technical evaluation.</p>
          </div>
          {data.requirements.length > 0 && data.firms.length > 0 && (
            <button className="btn small" type="button" disabled={busy}
              onClick={() => act(() => post(`${base}/eligibility`))}>Check eligibility again</button>
          )}
        </div>
        <ErrorText error={actionError} />
        {data.checking > 0 && (
          <div className="notice info" role="status">
            <strong>Checking {plural(data.checking, "bid")}.</strong> Results appear here as each one finishes.
          </div>
        )}
        {data.open > 0 && (
          <div className="notice"><strong>{plural(data.open, "check")} awaiting committee decision.</strong></div>
        )}
        {!data.requirements.length ? (
          <div className="notice info">This project has no eligibility criteria or required documents: every firm with a bid goes on to evaluation.</div>
        ) : !data.firms.length ? (
          <div className="notice info">No bids yet. Upload them on the <Link to={`/projects/${tenderId}/participants`}>Participants</Link> step.</div>
        ) : (
          <section className="card">
            <EligibilityGrid requirements={data.requirements} firms={data.firms} />
            <p className="small muted">
              ✓ met / submitted · ✗ not met / not submitted · ? AI unsure · Highlighted = the AI's finding,
              not decided by the committee yet · green / red with a dotted underline = decided
            </p>
          </section>
        )}
      </main>
      <div className="actions">
        <Link to={`/projects/${tenderId}/participants`}>Participants</Link>
        <div className="row">
          {note && <span className="small muted">{note}</span>}
          <button className="btn primary" type="button" onClick={evaluate} disabled={busy || !data.qualified}>
            Evaluate {plural(data.qualified, "qualified firm")}
          </button>
        </div>
      </div>
    </>
  );
}
