import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import BidPage from "../components/BidPage";
import CheckDecisionForm from "../components/CheckDecisionForm";
import CheckList from "../components/CheckList";
import { CheckRow } from "../components/EvidenceChecks";
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
  const passed = check ? check.proof.filter((c) => c.state === "passed") : [];
  // After a decision, go on to the firm's next undecided check.
  const saved = () => {
    const next = firm.cells.find((c) => c.check_id && !c.decision && c.check_id !== check?.check_id);
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
            {firm.missing.length > 0 && <span className="small warn-text"> · Missing document{firm.missing.length > 1 ? "s" : ""} {firm.missing.join(", ")}</span>}
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
                <strong>{check.stage === "DOCUMENT" ? "Required document" : "Eligibility criterion"} · AI: {word(check.stage, check.result)}</strong>
                <span className="muted"> · checked {check.checked}{check.pages.length ? ` · ${check.pages.length === 1 ? "page" : "pages"} ${pageRanges(check.pages)}` : ""}</span>
              </div>
              <div className={check.result === "UNSURE" ? "callout" : undefined}>
                {check.result === "UNSURE" && <strong>For the committee to decide</strong>}
                <p>{check.finding}</p>
              </div>
              {/* Only the checks that need a look stay open; passed ones fold into one line. */}
              {check.proof.filter((c) => c.state !== "passed").map((c, i) => <CheckRow key={i} c={c} pageLink={at} />)}
              {passed.length > 0 && (
                <details className="passed">
                  <summary>✓ {passed.length} check{passed.length === 1 ? "" : "s"} passed</summary>
                  {passed.map((c, i) => <CheckRow key={i} c={c} pageLink={at} />)}
                </details>
              )}
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
