import { titleCase } from "../format";
import type { Criterion } from "../types";

type Props = { rows: Criterion[]; onChange: (rows: Criterion[]) => void };

// The editable criteria table. Values stay strings; the API parses them as Decimal.
export default function CriteriaTable({ rows, onChange }: Props) {
  const edit = (i: number, key: keyof Criterion) =>
    (e: { target: { value: string } }) =>
      onChange(rows.map((r, j) => (j === i ? { ...r, [key]: e.target.value } : r)));

  return (
    <table className="table">
      <thead>
        <tr>
          <th>Code</th><th>What the bidder must show</th><th>Scored per</th><th className="right">Marks</th>
          <th className="right">Max items</th><th>Marks per item</th><th>Scored by</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c, i) => (
          <tr key={c.criterion_id}>
            <td>
              <strong>{c.code}</strong><br />
              <span className="small muted">{titleCase(c.stage)}{c.rfp_page ? ` · p.${c.rfp_page}` : ""}</span>
            </td>
            <td>
              <label className="sr-only" htmlFor={`m${i}`}>Meaning of {c.code}</label>
              <textarea id={`m${i}`} rows={2} value={c.meaning ?? ""} onChange={edit(i, "meaning")} />
              <details><summary className="small">RFP text</summary><p className="small">{c.rfp_text}</p></details>
            </td>
            <td>
              <label className="sr-only" htmlFor={`k${i}`}>Scored per</label>
              <select id={`k${i}`} value={c.kind ?? ""} onChange={edit(i, "kind")}>
                <option value="">—</option>
                <option value="PROJECT">Project</option>
                <option value="CV">CV</option>
              </select>
            </td>
            <td className="right">
              <label className="sr-only" htmlFor={`x${i}`}>Max marks</label>
              <input id={`x${i}`} className="narrow num" type="text" value={c.max_marks ?? ""} onChange={edit(i, "max_marks")} />
            </td>
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
          </tr>
        ))}
      </tbody>
    </table>
  );
}
