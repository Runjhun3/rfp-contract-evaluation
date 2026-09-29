import { Link } from "react-router-dom";
import { marks, titleCase } from "../format";
import type { Cell, GroupTotal, ResultsPage } from "../types";

type Props = {
  data: ResultsPage;
  presentation: Record<string, string>;
  onPresentation: (values: Record<string, string>) => void;
};

function ScoreCell({ cell }: { cell: Cell | undefined }) {
  if (!cell) return <span className="muted">—</span>;
  const open = cell.needs_review && !cell.reviewed;
  const cls = open ? "cell review" : cell.reviewed ? "cell decided" : "cell";
  return <Link className={cls} to={`/scores/${cell.score_id}`}>{open && "● "}{marks(cell.marks)}</Link>;
}

// A capped group's total: "38 → 36" with a note when the cap trimmed marks, so the
// committee sees both numbers. Information only; it needs no decision.
function GroupCell({ group }: { group: GroupTotal | undefined }) {
  if (!group) return <span className="muted">—</span>;
  if (!group.flags.includes("CAP_APPLIED")) return <>{marks(group.total)}</>;
  return (
    <>
      <span className="muted">{marks(group.sum)} → </span><strong>{marks(group.total)}</strong>
      <br /><span className="small muted">cap applied</span>
    </>
  );
}

// The ranked matrix: one row per participant, one column per scored criterion.
export default function ResultsTable({ data, presentation, onPresentation }: Props) {
  const pres = data.presentation;
  return (
    <table className="table num">
      <thead>
        <tr>
          <th>Rank</th><th>Participant</th>
          {data.codes.map((c) => <th key={c.code} className="right">{c.code} /{marks(c.max_marks)}</th>)}
          {data.caps.map((g) => <th key={g.code} className="right" title={g.title}>{g.code} total /{marks(g.cap)} cap</th>)}
          <th className="right">Docs /{marks(data.docs_max)}</th>
          {pres && <th className="right">{pres.code} presentation /{marks(pres.max_marks)}</th>}
          <th className="right">Total</th>
        </tr>
      </thead>
      <tbody>
        {data.rows.map((r, i) => (
          <tr key={r.submission_id}>
            <td><strong>{r.rank}</strong></td>
            <td>
              <strong>{r.name}</strong>
              {r.stage !== "DONE" && <><br /><span className="small muted">{titleCase(r.stage)}</span></>}
            </td>
            {data.codes.map((c) => <td key={c.code} className="right"><ScoreCell cell={r.cells[c.code]} /></td>)}
            {data.caps.map((g) => <td key={g.code} className="right"><GroupCell group={r.groups[g.code]} /></td>)}
            <td className="right"><strong>{marks(r.docs)}</strong></td>
            {pres && (
              <td className="right">
                <label className="sr-only" htmlFor={`p${i}`}>Presentation marks for {r.name}</label>
                <input id={`p${i}`} className="narrow" type="text" inputMode="decimal"
                  value={presentation[r.submission_id] ?? ""}
                  onChange={(e) => onPresentation({ ...presentation, [r.submission_id]: e.target.value })} />
              </td>
            )}
            <td className="right total">{marks(r.total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
