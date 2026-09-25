import { Link, useParams } from "react-router-dom";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { Loading } from "../components/Status";
import type { RunPage } from "../types";
import { useApi } from "../useApi";

const finished = (status: string) => status === "DONE" || status === "FAILED";
// Live progress: ask again every 5 s until the run is DONE or FAILED.
const whileRunning = (d: RunPage) => (finished(d.run.status) ? null : 5000);

export default function RunProgress() {
  const { runId } = useParams();
  const { data, error } = useApi<RunPage>(`/api/v1/runs/${runId}`, whileRunning);
  usePageTitle(data && `Evaluating · ${data.project.name}`);
  if (!data) return <Loading error={error} />;
  const { run } = data;

  return (
    <main className="page">
      <ProjectHead project={data.project} steps={data.steps} />
      <div className="spread">
        <div>
          <h2>Run started {run.started} · criteria v{run.prompt_version}</h2>
          <p className="sub">You can close this page. Results appear per participant as each one finishes.</p>
        </div>
        {finished(run.status) && <Link className="btn primary" to={`/runs/${run.run_id}/results`}>View results</Link>}
      </div>
      {error && <p className="small muted" role="status">Lost contact with the server; retrying…</p>}
      <table className="table">
        <thead><tr><th>Participant</th><th>Progress</th><th>Now</th></tr></thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.submission_id}>
              <td><strong>{r.short_name}</strong></td>
              <td>
                <label className="sr-only" htmlFor={`bar-${r.submission_id}`}>Progress of {r.short_name}</label>
                <progress id={`bar-${r.submission_id}`} max={100} value={r.percent}>{r.percent}%</progress>
              </td>
              <td>
                <span aria-live="polite">{r.label}</span>
                {r.error && <><br /><span className="small muted">{r.error}</span></>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="two">
        <div className="card">
          <h2>Check each item</h2>
          <p className="muted">Each credential or CV is read on its own pages against the approved rules, with the exact words it relied on.</p>
        </div>
        <div className="card">
          <h2>Verify and score</h2>
          <p className="muted">Every quote is found on its page again and its value or date re-read. Totals are re-added independently of the AI.</p>
        </div>
      </div>
    </main>
  );
}
