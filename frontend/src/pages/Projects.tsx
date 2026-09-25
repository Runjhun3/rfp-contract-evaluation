import { Link, useSearchParams } from "react-router-dom";
import { usePageTitle } from "../components/Layout";
import { Loading } from "../components/Status";
import { titleCase } from "../format";
import type { ProjectList } from "../types";
import { useApi } from "../useApi";

export default function Projects() {
  usePageTitle("Projects");
  const [params] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const { data, error } = useApi<ProjectList>(`/api/v1/projects?page=${page}`);
  if (!data) return <Loading error={error} />;

  return (
    <main className="page">
      <div className="spread">
        <div>
          <h1>Projects</h1>
          <p className="sub">Each project is one tender cycle: its RFP, its participants and every evaluation run.</p>
        </div>
        <Link className="btn primary" to="/projects/new">+ New project</Link>
      </div>
      {data.projects.length ? (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>Project</th><th>GeM bid no.</th><th className="right">Participants</th>
                <th>Stage</th><th>Open reviews</th><th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data.projects.map((p) => (
                <tr className="link-row" key={p.tender_id}>
                  <td>
                    <Link to={`/projects/${p.tender_id}`}><strong>{p.name}</strong></Link>
                    <br /><span className="small muted">bids closed {p.due}</span>
                  </td>
                  <td className="num">{p.gem_bid_no || "—"}</td>
                  <td className="right num">{p.participants}</td>
                  <td>
                    <span className={`chip${["REVIEW", "EVALUATING"].includes(p.status) ? " blue" : ""}`}>
                      {titleCase(p.status)}
                    </span>
                  </td>
                  <td>
                    {p.open_reviews ? <span className="chip amber">{p.open_reviews} to review</span>
                      : <span className="muted">—</span>}
                  </td>
                  <td className="muted">{p.created}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row">
            {page > 1 && <Link className="btn small" to={`/projects?page=${page - 1}`}>Previous</Link>}
            {data.more && <Link className="btn small" to={`/projects?page=${page + 1}`}>Next</Link>}
          </div>
        </>
      ) : (
        <div className="card">
          <h2>No projects yet</h2>
          <p className="muted">Create a project for a tender, upload its RFP, add the participants and evaluate.</p>
        </div>
      )}
    </main>
  );
}
