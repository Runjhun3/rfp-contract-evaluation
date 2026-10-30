import { Link, useParams, useSearchParams } from "react-router-dom";
import ActivityFilters from "../components/ActivityFilters";
import ActivityTable, { ActivityTabs, activityQuery } from "../components/ActivityTable";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { Loading } from "../components/Status";
import type { Approval, AuditPage } from "../recordTypes";
import { useApi } from "../useApi";

const APPROVED = "approved";

function Approvals({ approvals }: { approvals: Approval[] }) {
  if (!approvals.length) return <div className="card"><p className="muted">The criteria have not been approved yet.</p></div>;
  return (
    <>
      {approvals.map((a) => (
        <details key={a.version} className="card section" open={a === approvals[0]}>
          <summary><h2>Version {a.version} · approved {a.stamp}{a.full_name && ` by ${a.full_name}`}</h2></summary>
          {a.approved_criteria ? (
            <table className="table">
              <thead><tr><th>Code</th><th>Title</th><th>Stage</th><th className="right">Max marks</th><th>Scored by</th><th>Counts</th></tr></thead>
              <tbody>
                {a.approved_criteria.map((c) => (
                  <tr key={c.code}>
                    <td>{c.code}</td><td>{c.title ?? "—"}</td><td>{c.stage ?? "—"}</td>
                    <td className="right num">{c.max_marks ?? "—"}</td><td>{c.scored_by ?? "—"}</td><td>{c.considered ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="muted">Criteria not recorded (approved before they were kept).</p>}
        </details>
      ))}
    </>
  );
}

// Administrators only: the project's activity log, one page at a time, newest first:
// every action a person took on the project (never the AI's or the worker's), by area,
// and the criteria as each version was approved. The committee's decisions have their
// own page (Decisions.tsx). The record is append-only; this screen only reads it.
export default function AuditTrail() {
  const { tenderId } = useParams();
  const [params] = useSearchParams();
  const area = params.get("area") ?? "";
  const query = activityQuery(params, area === APPROVED ? "" : area);
  const { data, error } = useApi<AuditPage>(`/api/v1/projects/${tenderId}/audit?${query}`);
  usePageTitle(data && `Activity log · ${data.project.name}`);
  if (!data) return <Loading error={error} />;
  const current = area === APPROVED ? APPROVED : data.category;
  const extra = { key: APPROVED, label: `Approved criteria (${data.approvals.length})` };

  return (
    <main className="page">
      <ProjectHead project={data.project} steps={data.steps} page="Activity log"
        back={{ to: `/projects/${data.project.tender_id}`, label: "the project" }} />
      <div>
        <h2>Activity log</h2>
        <p className="sub">What people did on this project, and when. Nothing here is ever edited or removed.
          The committee's decisions are on the <Link to={`/projects/${data.project.tender_id}/decisions`}>Committee decisions</Link> page.</p>
      </div>
      <ActivityTabs log={data} extra={extra} current={current} />
      {area === APPROVED ? <Approvals approvals={data.approvals} /> : (
        <>
          <ActivityFilters key={query} log={data} csv={`/api/v1/projects/${tenderId}/audit.csv?${query}`} />
          <ActivityTable log={data} current={current} />
        </>
      )}
    </main>
  );
}
