import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import BidPage from "../components/BidPage";
import DecisionForm from "../components/DecisionForm";
import EvidenceChecks from "../components/EvidenceChecks";
import ItemList from "../components/ItemList";
import { usePageTitle } from "../components/Layout";
import { Loading } from "../components/Status";
import { marks } from "../format";
import type { EvidencePage, ItemGroup } from "../types";
import { useApi } from "../useApi";

// The counted item to decide next: the first one without a decision after `current`,
// then from the top of the list; null when every other counted item is decided.
export function nextCounted(groups: ItemGroup[], current: string | null): string | null {
  const counted = groups.find((g) => g.key === "counted")?.items ?? [];
  const at = counted.findIndex((i) => i.item_id === current);
  const order = [...counted.slice(at + 1), ...counted.slice(0, Math.max(at, 0))];
  return order.find((i) => !i.decision)?.item_id ?? null;
}

// One criterion score of one participant: what needs a decision, the items claimed,
// the chosen item's verdict and checks, the committee decision, and the bid page.
export default function Evidence() {
  const { scoreId } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const itemParam = params.get("item") ?? "";
  const { data, error, reload } = useApi<EvidencePage>(`/api/v1/scores/${scoreId}?item=${encodeURIComponent(itemParam)}`);
  usePageTitle(data && `${data.score.short_name} ${data.score.code} · evidence`);
  const next = data ? nextCounted(data.groups, data.item?.item_id ?? null) : null;
  if (!data) return <Loading error={error} />;
  const { score, item } = data;
  const pageNo = Number(params.get("page")) || item?.from_page || 1;
  const at = (page: number) => `?item=${item ? item.item_id : ""}&page=${page}`;
  const { counted, decided } = data.progress;
  // After a decision, go on to the next counted item that still needs one (the move is
  // marked as following a save, so it is not taken for leaving unsaved text); with none
  // left, stay and show who decided in the form.
  const saved = () => {
    const after = item && nextCounted(data.groups, item.item_id);
    if (after) navigate(`?item=${after}`, { state: { afterSave: true } });
    else reload();
  };

  return (
    <>
      <div className="page">
        <div className="back-row">
          <BackLink to={`/projects/${score.tender_id}/results`} label="results" />
          <nav className="crumbs" aria-label="Breadcrumb">
            <Link to="/projects">Projects</Link> / <Link to={`/projects/${score.tender_id}/results`}>{data.project.name} · results</Link> / {score.short_name}
          </nav>
        </div>
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
          {counted > 0 && (
            <div className="decide-bar">
              <progress max={counted} value={decided} aria-label="Counted items decided" />
              <span className="small num">{decided} of {counted} counted items decided</span>
              {next ? <Link className="btn small primary" to={`?item=${next}`}>Next undecided item →</Link>
                : decided >= counted ? <span className="small accepted-text">All counted items decided</span>
                  : <span className="small muted">This is the last one left</span>}
            </div>
          )}
          {item && <EvidenceChecks item={item} checks={data.checks} pageLink={at} />}
          <DecisionForm key={item?.item_id ?? "criterion"} score={score} item={item} onSaved={saved} />
        </section>
        <BidPage submissionId={score.submission_id} firm={score.short_name} pageNo={pageNo} pageLink={at} />
      </main>
    </>
  );
}
