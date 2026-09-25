import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { post } from "../api";
import CriteriaTable from "../components/CriteriaTable";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { ErrorText, Loading } from "../components/Status";
import { marks } from "../format";
import type { CriteriaPage, Criterion } from "../types";
import { useApi } from "../useApi";

// While the worker is still reading the RFP there are no criteria: check again every 10 s.
const waitForCriteria = (d: CriteriaPage) => (d.criteria.length ? null : 10000);

export default function Criteria() {
  const { tenderId } = useParams();
  const navigate = useNavigate();
  const { data, error, reload } = useApi<CriteriaPage>(`/api/v1/projects/${tenderId}/criteria`, waitForCriteria);
  const [rows, setRows] = useState<Criterion[]>([]);
  const [block, setBlock] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `Criteria · ${data.project.name}`);

  useEffect(() => {
    if (!data) return;
    setRows(data.criteria);
    setBlock(data.prompt?.criteria_block ?? "");
  }, [data]);

  if (!data) return <Loading error={error} />;
  const { prompt } = data;
  const approved = prompt?.status === "APPROVED";

  async function act(path: string, body: unknown, after: () => void) {
    setBusy(true);
    setSaveError(null);
    try {
      await post(path, body);
      after();
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const save = (e: FormEvent) => {
    e.preventDefault();
    act(`/api/v1/projects/${tenderId}/criteria`, { criteria: rows, block }, reload);
  };
  const approve = () =>
    act(`/api/v1/projects/${tenderId}/criteria/approve`, undefined, () => navigate(`/projects/${tenderId}/participants`));

  return (
    <>
      <main className="page">
        <ProjectHead project={data.project} steps={data.steps} />
        <ErrorText error={saveError} />
        {!data.criteria.length ? (
          <div className="notice info" role="status">
            <strong>Reading the RFP and finding the criteria.</strong> This page refreshes by itself.
          </div>
        ) : (
          <>
            <div className="spread">
              <p className="sub">Check each criterion against the RFP. Marks, limits and the rule text below are what the evaluator applies.</p>
              <span className="chip blue num">Scored criteria total {marks(data.technical_total)}</span>
            </div>
            <form className="page-form" onSubmit={save}>
              <CriteriaTable rows={rows} onChange={setRows} />
              <section className="card">
                <h2>Rule text used by the evaluator{prompt && ` · version ${prompt.version} (${prompt.status.toLowerCase()})`}</h2>
                <p className="small muted">Only criteria marked "Scored per: Project/CV" and "AI + committee" are evaluated from the bids.</p>
                <label className="sr-only" htmlFor="block">Rule text</label>
                <textarea id="block" rows={16} value={block} onChange={(e) => setBlock(e.target.value)} />
              </section>
              <div><button className="btn" type="submit" disabled={busy}>Save changes</button></div>
            </form>
          </>
        )}
      </main>
      {data.criteria.length > 0 && (
        <div className="actions">
          <span className="small muted">
            {approved ? "Approved. Editing creates a new version to approve." : "Approval is recorded with the time."}
          </span>
          {prompt && !approved && (
            <button className="btn primary" type="button" onClick={approve} disabled={busy}>Approve criteria</button>
          )}
          {approved && <Link className="btn primary" to={`/projects/${tenderId}/participants`}>Continue to participants</Link>}
          {!prompt && <span className="small muted">Save the criteria to create the rule text, then approve it.</span>}
        </div>
      )}
    </>
  );
}
