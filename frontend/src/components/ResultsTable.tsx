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
    <table className="table num">
      <thead>
        <tr>
          <th>Rank</th><th>Participant</th>
          {data.codes.map((c) => <th key={c.code} className="right">{c.code} /{marks(c.max_marks)}</th>)}
          <th className="right">Docs /{marks(data.docs_max)}</th>
          {data.committee.map((c) => (
            <th key={c.criterion_id} className="right" title={c.title}>{c.code} (committee) /{marks(c.max_marks)}</th>
          ))}
          <th className="right">Total</th>
        </tr>
      </thead>
      <tbody>
        {data.rows.map((r, i) => (
          <tr key={r.submission_id}>
            <td><strong>{r.rank ?? "—"}</strong></td>
            <td>
              <strong>{r.name}</strong>
              {r.status && <><br /><span className="small muted">{r.status}</span></>}
            </td>

            {data.codes.map((c) => <td key={c.code} className="right"><ScoreCell cell={r.cells[c.code]} /></td>)}
            <td className="right"><strong>{marks(r.docs)}</strong></td>
            {data.committee.map((c, j) => {
              const key = `${c.criterion_id}/${r.submission_id}`;
              return (
                <td key={c.criterion_id} className="right">
                  <label className="sr-only" htmlFor={`m${i}-${j}`}>{c.code} marks for {r.name}</label>
                  <input id={`m${i}-${j}`} className="narrow" type="text" inputMode="decimal"
                    value={entered[key] ?? ""} onChange={(e) => onEnter({ ...entered, [key]: e.target.value })} />
                </td>
              );
            })}
            <td className="right total">{marks(r.total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
