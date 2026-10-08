import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import BidPage from "../components/BidPage";
import CheckDecisionForm from "../components/CheckDecisionForm";
import CheckList from "../components/CheckList";
import { CheckGroups } from "../components/EvidenceChecks";
import { usePageTitle } from "../components/Layout";
import { Loading } from "../components/Status";
import { CHIP, titled, word } from "../eligibility";
import { pageRanges } from "../format";
import type { CheckPage } from "../types";
import { useApi } from "../useApi";

// One firm's eligibility: its checks, the chosen check's finding and proof with the
// committee decision, and the bid page beside it, like the evidence page of a score.
export default function EligibilityCheck() {
  const { checkId } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { data, error, reload } = useApi<CheckPage>(`/api/v1/eligibility/${checkId}`);
  usePageTitle(data && `${data.firm.name} · eligibility`);
  if (!data) return <Loading error={error} />;
  const { firm, check, project } = data;
  const pageNo = Number(params.get("page")) || check?.first_page || 1;
  const at = (page: number) => `?page=${page}`;
  // After a decision, go on to the next AI-uncertain check.
  const saved = () => {
    const next = firm.cells.find((c) => c.check_id && c.effective === "UNSURE" && !c.decision
      && c.check_id !== check?.check_id);
    if (next?.check_id) navigate(`/eligibility/${next.check_id}`);
    else reload();
  };

  return (
    <>
      <div className="page">
        <nav className="crumbs" aria-label="Breadcrumb">
          <Link to="/projects">Projects</Link> / <Link to={`/projects/${project.tender_id}/eligibility`}>{project.name} · eligibility</Link> / {firm.name}
        </nav>
        <div className="evidence-head">
          <div>
            <span className="small muted">{firm.legal_name}</span>
            <h1 className="criterion">{firm.name} · Eligibility</h1>
          </div>
          <span>
            <span className={CHIP[firm.status]}>{firm.label}</span>
            {firm.checking && firm.status !== "checking" && <span className="small muted"> · Checking again…</span>}
          </span>
        </div>
      </div>
      <main className="evidence">
        <CheckList firm={firm} titles={data.titles} selected={check?.check_id ?? null} />
        <section aria-label="Finding and decision">
          {check ? (
            <>
              <h2>{titled(check.number, check.title)}</h2>
              <div className="verdict">
                <strong>Eligibility criterion · AI: {word(check.stage, check.result)}</strong>
                <span className="muted"> · checked {check.checked}{check.pages.length ? ` · ${check.pages.length === 1 ? "page" : "pages"} ${pageRanges(check.pages)}` : ""}</span>
              </div>
              <div className={check.result === "UNSURE" || check.flagged ? "callout" : undefined}>
                {(check.result === "UNSURE" || check.flagged) && (
                  <strong>
                    For the committee to decide
                    {check.flagged && check.result !== "UNSURE" && ": a document check flagged its proof"}
                  </strong>
                )}
                <p>{check.finding}</p>
              </div>
              <CheckGroups checks={check.proof} pageLink={at} />
              <details>
                <summary className="small">What the RFP requires</summary>
                <p className="small">{check.rfp_text}</p>
              </details>
              <CheckDecisionForm key={check.check_id} check={check} onSaved={saved} />
            </>
          ) : <p className="muted">This requirement has not been checked for {firm.name} yet.</p>}
        </section>
        <BidPage submissionId={data.submission_id} firm={firm.name} pageNo={pageNo} pageLink={at} />
      </main>
    </>
  );
}
