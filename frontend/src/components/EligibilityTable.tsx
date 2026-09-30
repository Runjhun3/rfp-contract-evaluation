import { GROUPS } from "../eligibility";
import type { Criterion, ScreenStage } from "../types";
import Section from "./Section";

type Props = { stage: ScreenStage; rows: Criterion[]; onChange: (rows: Criterion[]) => void };

const STAGE_NAME: Record<ScreenStage, string> = {
  ELIGIBILITY: "Eligibility criterion", DOCUMENT: "Required document",
};

// What screening checks, read from the RFP: eligibility criteria (pass/fail) or the
// documents every bid must include (flagged if missing). Each is checked by the AI on
// the pages that prove it and decided by the committee. The plain-words meaning is what
// the bid's pages are matched against, so it can be corrected here.
export default function EligibilityTable({ stage, rows, onChange }: Props) {
  const group = GROUPS.find((g) => g.stage === stage)!;
  const edit = (i: number, key: "meaning" | "stage") => (e: { target: { value: string } }) =>
    onChange(rows.map((r, j) => (j === i ? { ...r, [key]: e.target.value } : r)));
  return (
    <Section title={`${group.label} · ${group.note}`}
      aside={<span className="chip blue">{rows.length} · checked by the AI, decided by the committee</span>}>
      <table className="table">
        <thead>
          <tr><th>Code</th><th>What the bidder must show</th><th>Counts as</th></tr>
        </thead>
        <tbody>
          {rows.map((c, i) => (
            <tr key={c.criterion_id}>
              <td>
                <strong>{c.rfp_no ?? c.code}</strong><br />
                <span className="small muted">{c.title}{c.rfp_page ? ` · p.${c.rfp_page}` : ""}</span>
              </td>
              <td>
                <label className="sr-only" htmlFor={`m-${c.criterion_id}`}>Meaning of {c.title}</label>
                <textarea id={`m-${c.criterion_id}`} rows={2} value={c.meaning ?? ""} onChange={edit(i, "meaning")} />
                <details><summary className="small">RFP text</summary><p className="small">{c.rfp_text}</p></details>
              </td>
              <td>
                {/* The committee may treat a required document as an eligibility criterion, or the
                    other way round; the row moves to the other table, saved with the criteria. */}
                <label className="sr-only" htmlFor={`s-${c.criterion_id}`}>{c.title} counts as</label>
                <select id={`s-${c.criterion_id}`} value={c.stage} onChange={edit(i, "stage")}>
                  {GROUPS.map((g) => <option key={g.stage} value={g.stage}>{STAGE_NAME[g.stage]}</option>)}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}
