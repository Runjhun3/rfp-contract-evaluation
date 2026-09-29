import { useState } from "react";
import { Link } from "react-router-dom";
import { marks } from "../format";
import type { ItemGroup } from "../types";

type Props = { groups: ItemGroup[]; selected: string | null; summary: string };

// The items claimed under the criterion, one line each, grouped by outcome. Only the
// group holding the selected item (and "Counted") starts open.
export default function ItemList({ groups, selected, summary }: Props) {
  const [attentionOnly, setAttentionOnly] = useState(false);
  const total = groups.reduce((n, g) => n + g.items.length, 0);
  return (
    <section className="list" aria-label="Items">
      <span className="small muted">{summary}</span>
      <label className="small">
        <input type="checkbox" checked={attentionOnly} onChange={(e) => setAttentionOnly(e.target.checked)} />{" "}
        Only items needing attention
      </label>
      {groups.map((g) => {
        const rows = attentionOnly ? g.items.filter((i) => i.attention) : g.items;
        const holdsSelected = g.items.some((i) => i.item_id === selected);
        return (
          <details key={g.key} className="group" open={g.key === "counted" || holdsSelected}>
            <summary>{g.label} ({attentionOnly ? `${rows.length} of ${g.items.length}` : g.items.length})</summary>
            {rows.map((i) => (
              <Link key={i.item_id} to={`?item=${i.item_id}`} title={i.title}
                className={`item${i.item_id === selected ? " selected" : ""}`}>
                <span className="dot">
                  {i.attention && <><span aria-hidden="true">●</span><span className="sr-only">Needs attention: </span></>}
                </span>
                <span className="name">{i.title}<span className="small muted"> · {i.pages}</span></span>
                <span className={`badge${i.decision || i.marks === null ? "" : " pending"}`} title={i.decision === "OVERRIDE" ? "Overridden by the committee"
                  : i.decision === "ACCEPT" ? "Accepted by the committee" : "Not approved yet"}>
                  {marks(i.marks)}{i.decision && <span aria-hidden="true"> ✓</span>}
                  {i.decision && <span className="sr-only"> (decided)</span>}
                </span>
              </Link>
            ))}
          </details>
        );
      })}
      {total === 0 && <p className="muted">No items were claimed under this criterion.</p>}
    </section>
  );
}
