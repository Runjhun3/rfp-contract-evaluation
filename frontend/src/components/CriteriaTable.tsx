import { useState } from "react";
import { titleCase } from "../format";
import { ancestors, groupEdited, groupScoredBy, setGroupScoredBy } from "../tree";
import type { Criterion } from "../types";
import GroupHead from "./GroupHead";

type Props = { rows: Criterion[]; saved: Criterion[]; onChange: (rows: Criterion[]) => void };

// Scored per, Max items, Marks per item and Scored by can be hidden (owner's request,
// 2026-09-28); Marks stays visible. Saved values are kept either way, because hidden
// fields are sent back unchanged.
const SHOW_SCORING_SETTINGS = true;
const SPAN = SHOW_SCORING_SETTINGS ? 7 : 3;

// The editable criteria table. Values stay strings; the API parses them as Decimal.
// A group heading (e.g. A, whose marks are the sum of A.1-A.3) is a full-width band
// (GroupHead); its sub-criteria are indented under it and can be collapsed.
export default function CriteriaTable({ rows, saved, onChange }: Props) {
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const edit = (i: number, key: keyof Criterion) =>
    (e: { target: { value: string } }) =>
      onChange(rows.map((r, j) => (j === i ? { ...r, [key]: e.target.value } : r)));
  const before = new Map(saved.map((r) => [r.criterion_id, r]));
  // The items check was computed from the saved row; hide it once those values change.
  const unchanged = (c: Criterion) => (["max_marks", "max_items", "allowed"] as const)
    .every((k) => String(c[k] ?? "") === String(before.get(c.criterion_id)?.[k] ?? ""));
  const toggle = (code: string) =>
    setClosed((s) => (s.has(code) ? new Set([...s].filter((c) => c !== code)) : new Set([...s, code])));

  return (
    <table className="table">
      <thead>
        <tr>
          <th>Code</th><th>What the bidder must show</th>
          {SHOW_SCORING_SETTINGS && <th>Scored per</th>}
          <th className="right">Marks</th>
          {SHOW_SCORING_SETTINGS && <><th className="right">Max items</th><th>Marks per item</th><th>Scored by</th></>}
        </tr>
      </thead>
      <tbody>
        {rows.map((c, i) => {
          const above = ancestors(c, rows);
          if (above.some((code) => closed.has(code))) return null;
          if (c.is_group) {
            return (
              <GroupHead key={c.criterion_id} group={c} span={SPAN} open={!closed.has(c.code)}
                edited={groupEdited(c.code, rows, saved)} scoredBy={groupScoredBy(c.code, rows)}
                onToggle={() => toggle(c.code)}
                onScoredBy={(v) => onChange(setGroupScoredBy(c.code, v, rows))} />
            );
          }
          return (
            <tr key={c.criterion_id} className={above.length ? `sub-row depth-${Math.min(above.length, 3)}` : undefined}>
              <td>
                <strong>{c.code}</strong><br />
                <span className="small muted">{titleCase(c.stage)}{c.rfp_page ? ` · p.${c.rfp_page}` : ""}</span>
              </td>
              <td>
                <label className="sr-only" htmlFor={`m${i}`}>Meaning of {c.code}</label>
                <textarea id={`m${i}`} rows={2} value={c.meaning ?? ""} onChange={edit(i, "meaning")} />
                <details><summary className="small">RFP text</summary><p className="small">{c.rfp_text}</p></details>
              </td>
              {SHOW_SCORING_SETTINGS && (
                <td>
                  <label className="sr-only" htmlFor={`k${i}`}>Scored per</label>
                  <select id={`k${i}`} value={c.kind ?? ""} onChange={edit(i, "kind")}>
                    <option value="">—</option>
                    <option value="PROJECT">Project</option>
                    <option value="CV">CV</option>
                  </select>
                </td>
              )}
              <td className="right">
                <label className="sr-only" htmlFor={`x${i}`}>Max marks</label>
                <input id={`x${i}`} className="narrow num" type="text" value={c.max_marks ?? ""} onChange={edit(i, "max_marks")} />
                {c.items_warning && unchanged(c) && <p className="warn small">⚠ {c.items_warning}</p>}
              </td>
              {SHOW_SCORING_SETTINGS && (
                <>
                  <td className="right">
                    <label className="sr-only" htmlFor={`n${i}`}>Max items</label>
                    <input id={`n${i}`} className="narrow num" type="text" value={c.max_items ?? ""} onChange={edit(i, "max_items")} />
                  </td>
                  <td>
                    <label className="sr-only" htmlFor={`a${i}`}>Allowed marks per item</label>
                    <input id={`a${i}`} type="text" value={c.allowed ?? ""} placeholder="e.g. 1, 1.5, 2" onChange={edit(i, "allowed")} />
                  </td>
                  <td>
                    <label className="sr-only" htmlFor={`s${i}`}>Scored by</label>
                    <select id={`s${i}`} value={c.scored_by} onChange={edit(i, "scored_by")}>
                      <option value="LLM">AI + committee</option>
                      <option value="COMMITTEE">Committee only</option>
                    </select>
                  </td>
                </>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
