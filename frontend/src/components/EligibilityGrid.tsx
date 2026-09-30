import { Link } from "react-router-dom";
import { CHIP, GROUPS, MARK, titled, word } from "../eligibility";
import type { EligibilityCell, EligibilityFirm, Requirement } from "../types";

type Props = { requirements: Requirement[]; firms: EligibilityFirm[] };

// One check: the committee's decision once made, else the AI's finding, highlighted
// until decided. Opens the firm's page on that check.
function Cell({ cell, firm }: { cell: EligibilityCell; firm: string }) {
  if (!cell.check_id || !cell.result) return <span className="muted">—</span>;
  const shown = cell.decision ?? cell.result;
  const said = word(cell.stage, shown);
  const title = `${firm} · ${cell.number}: ${cell.decision ? `decided ${said}` : `${said}, not decided yet`}`;
  return (
    <Link className={`cell mark ${MARK[shown].cls} ${cell.decision ? "decided" : "pending"}`}
      to={`/eligibility/${cell.check_id}`} title={title}>
      <span aria-hidden="true">{MARK[shown].sign}</span><span className="sr-only">{title}</span>
    </Link>
  );
}

// Firms × screening requirements: eligibility criteria (pass/fail) then required
// documents. A firm gets its status only when the committee has decided every
// eligibility check; a document decided as not submitted is flagged under it. The
// table scrolls sideways inside its card, with the firm and status columns kept in view.
export default function EligibilityGrid({ requirements, firms }: Props) {
  const groups = GROUPS.map((g) => ({ ...g, reqs: requirements.filter((r) => r.stage === g.stage) }))
    .filter((g) => g.reqs.length);
  const first = new Set(groups.slice(1).map((g) => g.reqs[0].code)); // where a new group starts
  return (
    <div className="grid-scroll" role="region" aria-label="Eligibility checks by firm" tabIndex={0}>
      <table className="table grid">
        <thead>
          <tr>
            <th className="col-firm" rowSpan={2}>Firm</th>
            {groups.map((g, i) => (
              <th key={g.stage} colSpan={g.reqs.length} className={`band${i ? " group-start" : ""}`}>
                {g.label} <span className="muted">· {g.note}</span>
              </th>
            ))}
            <th className="col-status" rowSpan={2}>Status</th>
          </tr>
          <tr>
            {groups.flatMap((g) => g.reqs).map((r) => (
              <th key={r.criterion_id} className={`req${first.has(r.code) ? " group-start" : ""}`}
                title={`${titled(r.number || r.code, r.title)}\n${r.meaning}`}>
                <span className="code">{r.number || r.code}</span>
                <span className="req-title">{r.title}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {firms.map((f) => (
            <tr key={f.submission_id}>
              <td className="col-firm"><strong>{f.name}</strong></td>
              {f.cells.map((c) => (
                <td key={c.code} className={`center${first.has(c.code) ? " group-start" : ""}`}>
                  <Cell cell={c} firm={f.name} />
                </td>
              ))}
              <td className="col-status">
                <span className={CHIP[f.status]}>{f.label}</span>
                {f.checking && f.status !== "checking" && <><br /><span className="small muted">Checking again…</span></>}
                {f.missing.length > 0 && <><br /><span className="small warn-text">Missing document{f.missing.length > 1 ? "s" : ""} {f.missing.join(", ")}</span></>}
                {f.error && <><br /><span className="small muted">{f.error}</span></>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
