import { useState } from "react";
import { useParams } from "react-router-dom";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import Section from "../components/Section";
import { Loading } from "../components/Status";
import type { DecisionRow, DecisionsPage } from "../recordTypes";
import { useApi } from "../useApi";

function Rows({ rows }: { rows: DecisionRow[] }) {
  return (
    <table className="table audit decisions">
      <thead>
        <tr><th>Date &amp; time</th><th>Area</th><th>Criterion</th><th>Decision</th><th className="right">Marks</th><th>AI said</th><th>Reason</th><th>By</th></tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="num nowrap">{r.stamp}</td>
            <td>{r.area}</td>
            <td>{r.criterion}</td>
            <td><span className={r.tone ? `key ${r.tone}` : undefined}>{r.decision}</span></td>
            <td className="right num">{r.value ?? "—"}</td>
            <td>{r.ai ?? "—"}</td>
            <td>{r.reason ? <div className="audit-text">{r.reason}</div> : <span className="muted">—</span>}</td>
            <td>{r.who}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// The decisions where the committee went against the AI, firm by firm, newest first:
// marks overridden, and eligibility decided otherwise than the AI found. Every account
// can see it; the activity log keeps every decision, accepting the AI included.
export default function Decisions() {
  const { tenderId } = useParams();
  const { data, error } = useApi<DecisionsPage>(`/api/v1/projects/${tenderId}/decisions`);
  const [closed, setClosed] = useState<Set<string>>(new Set());   // firms folded away
  const [code, setCode] = useState("");                            // the criterion filter
  usePageTitle(data && `Committee decisions · ${data.project.name}`);
  if (!data) return <Loading error={error} />;
  const firms = data.firms.map((f) => ({ ...f, rows: code ? f.rows.filter((r) => r.code === code) : f.rows }))
    .filter((f) => f.rows.length);
  const toggle = (firm: string, open: boolean) => setClosed((was) => {
    const now = new Set(was);
    if (open) now.delete(firm);
    else now.add(firm);
    return now;
  });

  return (
    <>
      <main className="page">
        <ProjectHead project={data.project} steps={data.steps} page="Committee decisions"
          back={{ to: `/projects/${data.project.tender_id}/results`, label: "results & review" }} />
        <div>
          <h2>Committee overrides</h2>
          <p className="sub">Where the committee went against the AI, by firm: marks overridden, and eligibility decided otherwise than the AI found.
            Nothing is edited or removed: a changed decision is a new line.</p>
        </div>
        {data.firms.length > 0 && (
          <div className="filters">
            <label className="field" htmlFor="d-code">Criterion
              <select id="d-code" value={code} onChange={(e) => setCode(e.target.value)}>
                <option value="">All criteria</option>
                {data.criteria.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
              </select>
            </label>
            <span className="row download">
              <button className="btn small" type="button" onClick={() => setClosed(new Set())}>Expand all</button>
              <button className="btn small" type="button" onClick={() => setClosed(new Set(data.firms.map((f) => f.firm)))}>Collapse all</button>
            </span>
          </div>
        )}
        {firms.length ? firms.map((f) => (
          <Section key={f.firm} title={f.firm} open={!closed.has(f.firm)} onToggle={(open) => toggle(f.firm, open)}
            aside={<span className="chip num">{f.summary}</span>}>
            <Rows rows={f.rows} />
          </Section>
        )) : <div className="card"><p className="muted">{data.firms.length ? "No override on this criterion."
          : "The committee has not overridden the AI on this project."}</p></div>}
      </main>
    </>
  );
}
