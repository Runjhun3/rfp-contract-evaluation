import { Link } from "react-router-dom";
import { GROUPS, MARK, titled, word } from "../eligibility";
import type { EligibilityFirm } from "../types";

type Props = { firm: EligibilityFirm; titles: Record<string, string>; selected: string | null };

// A firm's screening checks, grouped as eligibility criteria and required documents,
// one line each, like the items of a score on the evidence page: the badge is the
// committee's decision (✓) once made, else the AI's finding, highlighted until decided.
export default function CheckList({ firm, titles, selected }: Props) {
  return (
    <section className="list" aria-label="Checks">
      {GROUPS.map((g) => {
        const cells = firm.cells.filter((c) => c.stage === g.stage);
        return cells.length > 0 && (
          <div key={g.stage}>
            <strong className="small">{g.label}</strong> <span className="small muted">· {g.note}</span>
            {cells.map((c) => {
              const name = titled(c.number, titles[c.code]);
              if (!c.check_id || !c.result) {
                return (
                  <div key={c.code} className="item muted">
                    <span /><span className="name">{name}</span><span className="badge">not checked</span>
                  </div>
                );
              }
              const decided = c.decision !== null;
              const shown = c.decision ?? c.result;
              const said = `${word(c.stage, shown)}${decided ? ", decided by the committee" : ", not decided yet"}`;
              return (
                <Link key={c.code} to={`/eligibility/${c.check_id}`} title={name}
                  className={`item${c.check_id === selected ? " selected" : ""}`}>
                  <span />
                  <span className="name">{name}</span>
                  <span className={`badge ${MARK[shown].cls}${decided ? "" : " pending"}`} title={said}>
                    <span aria-hidden="true">{MARK[shown].sign}</span><span className="sr-only">{said}</span>
                  </span>
                </Link>
              );
            })}
          </div>
        );
      })}
      <span className="small muted">
        ✓ met / submitted · ✗ not met / not submitted · ? AI unsure · highlighted = the AI's finding, not decided yet
      </span>
    </section>
  );
}
