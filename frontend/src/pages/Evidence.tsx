import { Link, useParams, useSearchParams } from "react-router-dom";
import DecisionForm from "../components/DecisionForm";
import EvidenceChecks from "../components/EvidenceChecks";
import { usePageTitle } from "../components/Layout";
import { Loading } from "../components/Status";
import { marks, reasons } from "../format";
import type { EvidencePage } from "../types";
import { useApi } from "../useApi";

// One criterion score of one participant: the items claimed, what Python checked,
// the committee decision, and the bid page itself.
export default function Evidence() {
  const { scoreId } = useParams();
  const [params] = useSearchParams();
  const itemParam = params.get("item") ?? "";
  const { data, error } = useApi<EvidencePage>(`/api/v1/scores/${scoreId}?item=${encodeURIComponent(itemParam)}`);
  usePageTitle(data && `${data.score.short_name} ${data.score.code} · evidence`);
  if (!data) return <Loading error={error} />;
  const { score, items, item } = data;
  const pageNo = Number(params.get("page")) || item?.from_page || 1;
  const at = (page: number) => `?item=${item ? item.item_id : ""}&page=${page}`;

  return (
    <>
      <div className="page">
        <nav className="crumbs" aria-label="Breadcrumb">
          <Link to="/projects">Projects</Link> / <Link to={`/runs/${score.run_id}/results`}>{data.project.name} · results</Link> / {score.short_name}
        </nav>
        <div className="spread">
          <h1 className="project">{score.short_name} · {score.code} {score.title}</h1>
          <div className="row num">
            <span><span className="small muted">Suggested</span> <strong>{marks(score.checked_marks)} / {marks(score.max_marks)}</strong></span>
            {score.reviewed ? <span className="chip blue">Decided: {marks(score.final_marks)}</span>
              : score.needs_review ? <span className="chip amber">Needs decision · {reasons(score.review_reasons)}</span> : null}
          </div>
        </div>
      </div>
      <main className="evidence">
        <section className="list" aria-label="Items">
          <span className="small muted">
            {items.length} claimed{score.max_items ? ` · max ${score.max_items} counted` : ""} · {score.summary}
          </span>
          {items.map((i) => (
            <Link key={i.item_id} className={`item${item && i.item_id === item.item_id ? " selected" : ""}`} to={`?item=${i.item_id}`}>
              <span>{i.title || i.label}<span className="why">{!i.counted && i.count_reason ? i.count_reason : i.reason}</span></span>
              {i.counted ? <span className="counted">Counted · {marks(i.marks)}</span> : <span className="excluded">Excluded</span>}
            </Link>
          ))}
        </section>
        <section aria-label="Checks and decision">
          {item && <EvidenceChecks item={item} checks={data.checks} pageLink={at} />}
          <DecisionForm score={score} />
          {data.history.length > 0 && (
            <ul className="history">
              {data.history.map((h, i) => (
                <li key={i}>{h.decided} · {h.full_name} · {h.action.toLowerCase()} {marks(h.final_marks)} — {h.reason}</li>
              ))}
            </ul>
          )}
        </section>
        <section className="viewer" aria-label={`Bid page ${pageNo}`}>
          <div className="spread">
            <strong>Bid page {pageNo}</strong>
            <span className="row">
              {pageNo > 1 && <Link className="btn small" to={at(pageNo - 1)} aria-label="Previous page">‹</Link>}
              <Link className="btn small" to={at(pageNo + 1)} aria-label="Next page">›</Link>
            </span>
          </div>
          <img className="pageimg" src={`/api/v1/submissions/${score.submission_id}/pages/${pageNo}.png`}
            alt={`Page ${pageNo} of ${score.short_name}'s bid`} />
        </section>
      </main>
    </>
  );
}
