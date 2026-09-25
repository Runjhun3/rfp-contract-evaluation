import { Link } from "react-router-dom";
import type { Check, Item } from "../types";

type Props = { item: Item; checks: Check[]; pageLink: (page: number) => string };

// What Python verified for one item: each quote found on its page, each value re-read.
export default function EvidenceChecks({ item, checks, pageLink }: Props) {
  return (
    <>
      <h2>{item.title || item.label}</h2>
      <p className="muted">Pages {item.from_page}–{item.to_page} · {item.reason}</p>
      <span className="small muted">Checked independently</span>
      {checks.length ? checks.map((c, i) => {
        const good = c.quote_found && c.value_matches !== false;
        return (
          <div key={i} className={`chk${good ? "" : " bad"}`}>
            <strong>{good ? "✓" : "!"}</strong>
            <span>
              <strong>{c.fact.replace(/_/g, " ")}</strong>
              {c.quote ? <q>{c.quote}</q> : " "}
              <span className="small muted">
                {c.note ? c.note : c.parsed_value ? `read as ${c.parsed_value}` : `found on page (${c.match_score}% match)`}
              </span>
            </span>
            {c.pdf_page_no ? <Link className="small" to={pageLink(c.pdf_page_no)}>p. {c.pdf_page_no}</Link> : <span />}
          </div>
        );
      }) : <p className="muted">No checks recorded for this item.</p>}
    </>
  );
}
