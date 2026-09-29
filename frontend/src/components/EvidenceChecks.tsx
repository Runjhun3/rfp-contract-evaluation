import { Link } from "react-router-dom";
import { marks } from "../format";
import type { CheckView, Verdict } from "../types";

type Props = { item: Verdict; checks: CheckView[]; pageLink: (page: number) => string };

const STATUS = { counted: "Counted", not_counted: "Not counted", not_scored: "Not scored" };

function CheckRow({ c, pageLink }: { c: CheckView; pageLink: Props["pageLink"] }) {
  return (
    <div className={`chk ${c.state}`}>
      <strong aria-hidden="true">{c.state === "passed" ? "✓" : c.state === "problem" ? "!" : "i"}</strong>
      <span>
        <strong>{c.label}</strong> <span className="small muted">{c.detail}</span>
        {c.quote && <q>{c.quote}</q>}
      </span>
      {c.page ? <Link className="small" to={pageLink(c.page)}>p. {c.page}</Link> : <span />}
    </div>
  );
}

// One item: the verdict, what the committee must decide, then only the checks that
// need a look. Passed checks fold into one line.
export default function EvidenceChecks({ item, checks, pageLink }: Props) {
  const open = checks.filter((c) => c.state !== "passed");
  const passed = checks.filter((c) => c.state === "passed");
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
      {open.map((c, i) => <CheckRow key={i} c={c} pageLink={pageLink} />)}
      {passed.length > 0 && (
        <details className="passed">
          <summary>✓ {passed.length} check{passed.length === 1 ? "" : "s"} passed</summary>
          {passed.map((c, i) => <CheckRow key={i} c={c} pageLink={pageLink} />)}
        </details>
      )}
      {!checks.length && <p className="muted">No checks recorded for this item.</p>}
    </>
  );
}
