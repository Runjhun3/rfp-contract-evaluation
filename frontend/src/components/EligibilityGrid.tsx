import { Link } from "react-router-dom";
import { CHIP, MARK, titled, word } from "../eligibility";
import type { EligibilityCell, EligibilityFirm, Requirement } from "../types";

type Props = { requirements: Requirement[]; firms: EligibilityFirm[] };

// Clear AI findings are shown plainly; only an unresolved AI-uncertain finding is highlighted.
function Cell({ cell, firm }: { cell: EligibilityCell; firm: string }) {
  if (!cell.check_id || !cell.result) return <span className="muted">—</span>;
  const shown = cell.decision ?? cell.result;
  const said = word(cell.stage, shown);
  const pending = !cell.decision && cell.result === "UNSURE";
  const title = `${firm} · ${cell.number}: ${cell.decision ? `committee override: ${said}`
    : pending ? "AI unsure; committee decision needed" : `AI: ${said}`}`;
  return (
    <Link className={`cell mark ${MARK[shown].cls}${cell.decision ? " decided" : ""}${pending ? " pending" : ""}`}
      to={`/eligibility/${cell.check_id}`} title={title}>
      <span aria-hidden="true">{MARK[shown].sign}</span><span className="sr-only">{title}</span>
    </Link>
  );
}

// Firms × considered eligibility criteria. Clear AI results count automatically; only
// unsure results wait for the committee.
// table scrolls sideways inside its card, with the firm and status columns kept in view.
export default function EligibilityGrid({ requirements, firms }: Props) {
  return (
    <div className="grid-scroll" role="region" aria-label="Eligibility checks by firm" tabIndex={0}>
      <table className="table grid">
        <thead>
          <tr>
            <th className="col-firm">Firm</th>
            {requirements.map((r) => (
              <th key={r.criterion_id} className="req"
                title={`${titled(r.number, r.title)}\n${r.meaning}`}>
                <span className="code">{r.number}</span>
                <span className="req-title">{r.title}</span>
              </th>
            ))}
            <th className="col-status">Status</th>
          </tr>
        </thead>
        <tbody>
          {firms.map((f) => (
            <tr key={f.submission_id}>
              <td className="col-firm"><strong>{f.name}</strong></td>
              {f.cells.map((c) => (
                <td key={c.code} className="center">
                  <Cell cell={c} firm={f.name} />
                </td>
              ))}
              <td className="col-status">
                <span className={CHIP[f.status]}>{f.label}</span>
                {f.checking && f.status !== "checking" && <><br /><span className="small muted">Checking again…</span></>}
                {f.error && <><br /><span className="small muted">{f.error}</span></>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
