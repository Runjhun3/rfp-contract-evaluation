import { Link, useParams, useSearchParams } from "react-router-dom";
import BidPage from "../components/BidPage";
import DecisionForm from "../components/DecisionForm";
import EvidenceChecks from "../components/EvidenceChecks";
import ItemList from "../components/ItemList";
import { usePageTitle } from "../components/Layout";
import { Loading } from "../components/Status";
import { marks } from "../format";
import type { EvidencePage } from "../types";
import { useApi } from "../useApi";

// One criterion score of one participant: what needs a decision, the items claimed,
// the chosen item's verdict and checks, the committee decision, and the bid page.
export default function Evidence() {
  const { scoreId } = useParams();
  const [params] = useSearchParams();
  const itemParam = params.get("item") ?? "";
  const { data, error, reload } = useApi<EvidencePage>(`/api/v1/scores/${scoreId}?item=${encodeURIComponent(itemParam)}`);
  usePageTitle(data && `${data.score.short_name} ${data.score.code} · evidence`);
  if (!data) return <Loading error={error} />;
  const { score, item } = data;
  const pageNo = Number(params.get("page")) || item?.from_page || 1;
  const at = (page: number) => `?item=${item ? item.item_id : ""}&page=${page}`;

  return (
    <>
      <div className="page">
        <nav className="crumbs" aria-label="Breadcrumb">
          <Link to="/projects">Projects</Link> / <Link to={`/projects/${score.tender_id}/results`}>{data.project.name} · results</Link> / {score.short_name}
        </nav>
        <div className="evidence-head">
          <div>
            <span className="small muted">{score.short_name}</span>
            <h1 className="criterion">{score.code} · {score.title}</h1>
          </div>
          <div className="score-box num">
            <strong>{marks(score.final_marks)} / {marks(score.max_marks)}</strong>
            <span className="small muted">
              final{score.final_marks !== score.checked_marks ? ` · AI suggested ${marks(score.checked_marks)}` : ""}
            </span>
            {score.reviewed ? <span className="chip blue">Approved</span> : (
              <span className="chip amber">
                {score.needs_review ? "Needs decision" : "Awaiting approval"}
                {data.progress.counted > 0 ? ` · ${data.progress.decided} of ${data.progress.counted} counted items decided` : ""}
              </span>
            )}
          </div>
        </div>
      </div>
      <main className="evidence">
        <ItemList groups={data.groups} selected={item?.item_id ?? null} summary={score.summary ?? ""} />
        <section aria-label="Checks and decision">
          {item && <EvidenceChecks item={item} checks={data.checks} pageLink={at} />}
          <DecisionForm key={item?.item_id ?? "criterion"} score={score} item={item} onSaved={reload} />
        </section>
        <BidPage submissionId={score.submission_id} firm={score.short_name} pageNo={pageNo} pageLink={at} />
      </main>
    </>
  );
}
