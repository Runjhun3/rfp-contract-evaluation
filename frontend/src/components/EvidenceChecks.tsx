import { Link } from "react-router-dom";
import { boxParam } from "./BidPage";
import { marks } from "../format";
import type { CheckView, Verdict } from "../types";

type Props = { item: Verdict; checks: CheckView[]; pageLink: (page: number) => string };

const STATUS = { counted: "Counted", not_counted: "Not counted", not_scored: "Not scored" };

// One check in plain words, with a link to its page (a document check's finding opens
// with its box outlined). Also lists an eligibility check's proof.
export function CheckRow({ c, pageLink }: { c: CheckView; pageLink: Props["pageLink"] }) {
  const to = c.page ? pageLink(c.page) + (c.region ? boxParam(c.region) : "") : "";
  return (
    <div className={`chk ${c.state}`}>
      <strong aria-hidden="true">{c.state === "passed" ? "✓" : c.state === "problem" ? "!" : "i"}</strong>
      <span>
        <strong>{c.label}</strong> <span className="small muted">{c.detail}</span>
        {c.quote && <q>{c.quote}</q>}
      </span>
      {c.page ? <Link className="small" to={to}>p. {c.page}</Link> : <span />}
    </div>
  );
}

// The checks in three folds, each one line until opened: problems (open at first, they
// need a look), notes, and passed checks.
const GROUPS = [
  { state: "problem", icon: "!", one: "problem to look at", many: "problems to look at", open: true },
  { state: "note", icon: "i", one: "note", many: "notes", open: false },
  { state: "passed", icon: "✓", one: "check passed", many: "checks passed", open: false },
] as const;

export function CheckGroups({ checks, pageLink }: { checks: CheckView[]; pageLink: Props["pageLink"] }) {
  return (
    <>
      {GROUPS.map((g) => {
        const rows = checks.filter((c) => c.state === g.state);
        return rows.length > 0 && (
          <details key={g.state} className={`checks ${g.state}`} open={g.open}>
            <summary>{g.icon} {rows.length} {rows.length === 1 ? g.one : g.many}</summary>
            {rows.map((c, i) => <CheckRow key={i} c={c} pageLink={pageLink} />)}
          </details>
        );
      })}
    </>
  );
}

// One item: the verdict, what the committee must decide, then its checks, folded.
export default function EvidenceChecks({ item, checks, pageLink }: Props) {
  return (
    <>
      <h2>{item.title}</h2>
      <div className="verdict">
        <strong>{STATUS[item.status]}</strong>
        {(item.status === "counted") !== item.counted_by_ai && item.status !== "not_scored" && (
          <span className="muted"> (by the committee)</span>
        )}
        {item.status === "counted" && <span> · {item.count_based ? "qualifies" : `${marks(item.marks)} marks`}</span>}
        {item.confidence !== null && <span className="muted"> · confidence {item.confidence}%</span>}
        <span className="muted"> · {item.pages}</span>
      </div>
      <div className={item.judgement_call ? "callout" : undefined}>
        {item.judgement_call && <strong>For the committee to decide</strong>}
        <p>{item.reason}</p>
      </div>
      <CheckGroups checks={checks} pageLink={pageLink} />
      {!checks.length && <p className="muted">No checks recorded for this item.</p>}
    </>
  );
}
