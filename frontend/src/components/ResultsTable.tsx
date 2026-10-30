import { Link } from "react-router-dom";
import { marks } from "../format";
import type { Cell, ResultsPage } from "../types";

type Props = {
  data: ResultsPage;
  entered: Record<string, string>;             // "criterion id/submission id" -> typed marks
  onEnter: (values: Record<string, string>) => void;
};

function ScoreCell({ cell }: { cell: Cell | undefined }) {
  if (!cell) return <span className="muted">—</span>;
  // Every mark stays highlighted until the committee approves it; a flagged one also
  // carries a dot. Approved marks are underlined.
  const flagged = cell.needs_review && !cell.reviewed;
  const cls = cell.reviewed ? "cell decided" : flagged ? "cell review" : "cell pending";
  return <Link className={cls} to={`/scores/${cell.score_id}`}>{flagged && "● "}{marks(cell.marks)}</Link>;
}

// The ranked matrix: one row per participant, one column per criterion with marks. AI-scored
// columns link to the evidence; committee-scored ones (e.g. a presentation) take marks here.
export default function ResultsTable({ data, entered, onEnter }: Props) {
  return (
    <div className="results-scroll" role="region" aria-label="Results by participant" tabIndex={0}>
      <table className="table num results">
        <thead>
          <tr>
            <th className="col-rank">Rank</th><th className="col-name">Participant</th>
            {/* The criterion's title shows on hover, as in the eligibility grid. */}
            {data.codes.map((c) => (
              <th key={c.code} className="right" title={`${c.code} · ${c.title}`}>{c.code} /{marks(c.max_marks)}</th>
            ))}
            <th className="right">Docs /{marks(data.docs_max)}</th>
            {data.committee.map((c) => (
              <th key={c.criterion_id} className="right" title={c.title}>{c.code} (committee) /{marks(c.max_marks)}</th>
            ))}
            <th className="right col-total">Total</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r, i) => (
            // A firm found not qualified is never evaluated: greyed, with the reason, no rank.
            <tr key={r.submission_id} className={r.eligibility === "not_qualified" ? "out" : undefined}>
              <td className="col-rank"><strong>{r.rank ?? "—"}</strong></td>
              <td className="col-name">
                <strong>{r.name}</strong>
                {r.status && <><br /><span className="small muted">{r.status}</span></>}
              </td>

              {data.codes.map((c) => <td key={c.code} className="right"><ScoreCell cell={r.cells[c.code]} /></td>)}
              <td className="right"><strong>{marks(r.docs)}</strong></td>
              {data.committee.map((c, j) => {
                const key = `${c.criterion_id}/${r.submission_id}`;
                if (r.eligibility === "not_qualified") return <td key={c.criterion_id} className="right muted">—</td>;
                return (
                  <td key={c.criterion_id} className="right" title={r.manual_notes?.[c.criterion_id]}>
                    <label className="sr-only" htmlFor={`m${i}-${j}`}>{c.code} marks for {r.name}</label>
                    <input id={`m${i}-${j}`} className="narrow" type="text" inputMode="decimal"
                      value={entered[key] ?? ""} onChange={(e) => onEnter({ ...entered, [key]: e.target.value })} />
                  </td>
                );
              })}
              <td className="right total col-total">{marks(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
