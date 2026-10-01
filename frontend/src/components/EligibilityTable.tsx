import type { Criterion } from "../types";
import Section from "./Section";

type Props = { rows: Criterion[]; onChange: (rows: Criterion[]) => void };

// Enough lines to show the wording without a scrollbar, within reason.
const lines = (text: string | null) =>
  Math.min(5, Math.max(2, Math.ceil((text ?? "").length / 60)));

const source = (c: Criterion) =>
  `${c.source_reference ?? c.rfp_no ?? c.code}${c.rfp_page ? ` · p.${c.rfp_page}` : ""}`;

// Extracted eligibility rows may be left out before approval. Left-out rows never
// reach the LLM or any later stage; the wording stays editable. A row the AI could
// not classify starts left out and asks the committee to choose.
export default function EligibilityTable({ rows, onChange }: Props) {
  const set = (i: number, patch: Partial<Criterion>) =>
    onChange(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const considered = rows.filter((r) => r.considered).length;
  const aside = (
    <span className="chip blue num">
      {considered} of {rows.length} considered · checked by the AI
    </span>
  );
  return (
    <Section title="Eligibility criteria · pass or fail" aside={aside}>
      <table className="table">
        <thead>
          <tr>
            <th>Criterion</th><th>What the bidder must show</th><th>Counts for qualification</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c, i) => (
            <tr key={c.criterion_id} className={c.considered ? undefined : "out"}>
              <td>
                <strong>{c.title}</strong><br />
                <span className="small muted">{source(c)}</span>
              </td>
              <td>
                <label className="sr-only" htmlFor={`m-${c.criterion_id}`}>
                  Meaning of {c.title}
                </label>
                <textarea id={`m-${c.criterion_id}`} rows={lines(c.meaning)}
                  value={c.meaning ?? ""} onChange={(e) => set(i, { meaning: e.target.value })} />
                <details>
                  <summary className="small">RFP text</summary>
                  <p className="small">{c.rfp_text}</p>
                </details>
              </td>
              <td>
                <fieldset className="seg">
                  <legend className="sr-only">Does {c.title} count for qualification?</legend>
                  {[true, false].map((on) => (
                    <label key={String(on)}
                      className={c.considered === on ? `on${on ? "" : " off"}` : undefined}>
                      <input type="radio" name={`c-${c.criterion_id}`}
                        checked={c.considered === on} onChange={() => set(i, { considered: on })} />
                      {on ? "Consider" : "Leave out"}
                    </label>
                  ))}
                </fieldset>
                {c.classification_unsure && (
                  <p className="small warn-text">
                    The AI is unsure this decides qualification. Please choose.
                  </p>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}
