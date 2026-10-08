import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { get, post } from "../api";
import CriteriaTable from "../components/CriteriaTable";
import EligibilityTable from "../components/EligibilityTable";
import RuleText from "../components/RuleText";
import Section from "../components/Section";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { ErrorText, Loading } from "../components/Status";
import { marks } from "../format";
import type { CriteriaPage, Criterion } from "../types";
import { useApi } from "../useApi";

// While the worker is still reading the RFP there are no criteria: check again every 10 s.
const waitForCriteria = (d: CriteriaPage) => (d.criteria.length ? null : 10000);
const isScreened = (c: Criterion) => c.stage === "ELIGIBILITY";
const REBUILT = "Rebuilt from the saved criteria. Review it, then Save changes "
  + "(reload the page to discard it).";
const READ_BACK = " The RFP's general conditions were copied from the current rule text "
  + "(this project was read before they were kept): check them.";

export default function Criteria() {
  const { tenderId } = useParams();
  const navigate = useNavigate();
  const { data, error, reload } = useApi<CriteriaPage>(`/api/v1/projects/${tenderId}/criteria`, waitForCriteria);
  const [rows, setRows] = useState<Criterion[]>([]);
  const [block, setBlock] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
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
  const base = `/api/v1/projects/${tenderId}`;
  const approved = prompt?.status === "APPROVED";

  async function act<T>(send: () => Promise<T>, after: (reply: T) => void) {
    setBusy(true);
    setSaveError(null);
    try {
      after(await send());
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const save = (e: FormEvent) => {
    e.preventDefault();
    act(() => post<{ notice: string | null }>(`${base}/criteria`, { criteria: rows, block }),
      (reply) => { setNotice(reply?.notice ?? null); reload(); });
  };
  const approve = () =>
    act(() => post(`${base}/criteria/approve`),
      () => navigate(`/projects/${tenderId}/participants`));
  // Fills the box only; the committee reviews the text and saves it.
  const rebuild = () =>
    act(() => get<{ text: string; recorded: boolean }>(`${base}/criteria/rule-text`), (reply) => {
      setBlock(reply.text);
      setNotice(REBUILT + (reply.recorded ? "" : READ_BACK));
    });
  const unsaved = JSON.stringify(rows) !== JSON.stringify(data.criteria);

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
            <p className="sub">Check each criterion against the RFP. Marks, limits and the rule text below are what the evaluator applies.</p>
            <form className="page-form" onSubmit={save}>
              {rows.some(isScreened) && <EligibilityTable rows={rows.filter(isScreened)}
                onChange={(changed) => setRows([...changed, ...rows.filter((c) => !isScreened(c))])} />}
              <Section title="Evaluation criteria · marks"
                aside={<span className="chip blue num">Scored criteria total {marks(data.technical_total)}</span>}>
                <CriteriaTable rows={rows.filter((c) => !isScreened(c))}
                  saved={data.criteria.filter((c) => !isScreened(c))}
                  onChange={(changed) => setRows([...rows.filter(isScreened), ...changed])} />
              </Section>
              <RuleText prompt={prompt} text={block} onChange={setBlock} notice={notice}
                onRebuild={rebuild} canRebuild={!unsaved} busy={busy} />
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
