import { marks } from "../format";
import type { Criterion } from "../types";

type Props = {
  group: Criterion; span: number; open: boolean; edited: boolean; scoredBy: string;
  onToggle: () => void; onScoredBy: (value: string) => void;
};

// The RFP check beside the computed total. Totals come from the saved rows, so after
// an edit the check says to save first rather than show an out-of-date result.
function Check({ group, edited }: { group: Criterion; edited: boolean }) {
  if (edited) return <span className="chip">Save to recheck</span>;
  if (group.rfp_matches === true) return <span className="chip blue">✓ {marks(group.parts_total)} · matches RFP</span>;
  if (group.rfp_matches === false) {
    return <span className="chip amber">⚠ Sub-rows add to {marks(group.parts_total)}, RFP says {marks(group.max_marks)}</span>;
  }
  return null;
}

// A group heading such as "A · Consultant Experience": no marks of its own to edit.
// Its total is its sub-rows' marks; "Scored by" here applies to every sub-row.
export default function GroupHead({ group, span, open, edited, scoredBy, onToggle, onScoredBy }: Props) {
  const id = `g-${group.code}`;
  return (
    <tr className="group-head">
      <td colSpan={span}>
        <div className="group-bar">
          <button type="button" className="toggle" aria-expanded={open} onClick={onToggle}
            aria-label={`${open ? "Collapse" : "Expand"} ${group.code}`}>{open ? "▾" : "▸"}</button>
          <span className="group-name">
            <strong>{group.code} · {group.title}</strong>
            <span className="muted"> · {marks(group.max_marks)} marks{group.rfp_page ? ` · p.${group.rfp_page}` : ""}</span>
          </span>
          <span className="num" title="Sum of the sub-rows' marks, as last saved">
            {marks(group.parts_total)} ({(group.parts ?? []).map((p) => marks(p)).join(" + ")})
          </span>
          <Check group={group} edited={edited} />
          <label className="row small" htmlFor={`${id}-s`}>Scored by
            <select id={`${id}-s`} value={scoredBy} onChange={(e) => onScoredBy(e.target.value)}>
              {scoredBy === "MIXED" && <option value="MIXED" disabled>Mixed</option>}
              <option value="LLM">AI + committee</option>
              <option value="COMMITTEE">Committee only</option>
            </select>
          </label>
        </div>
      </td>
    </tr>
  );
}
