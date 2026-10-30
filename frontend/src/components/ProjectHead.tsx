import { Link } from "react-router-dom";
import BackLink from "./BackLink";
import { useAccount } from "./RequireAuth";
import type { Project, Step } from "../types";

type Props = {
  project: Project; steps: Step[];
  page?: string;                          // a page that is not a step (e.g. "Activity log")
  back?: { to: string; label: string };   // where its back button leads
};

// Back button (pages that are not steps), breadcrumb, project title (with, for
// administrators, a link to its activity log) and the stepper on every project screen.
export default function ProjectHead({ project, steps, page, back }: Props) {
  const { role } = useAccount();
  return (
    <>
      <div className="back-row">
        {back && <BackLink to={back.to} label={back.label} />}
        <nav className="crumbs" aria-label="Breadcrumb">
          <Link to="/projects">Projects</Link> /{" "}
          {page ? <><Link to={`/projects/${project.tender_id}`}>{project.name}</Link> / {page}</> : project.name}
        </nav>
      </div>
      <div className="spread">
        <div>
          <h1 className="project">{project.name}</h1>
          <p className="sub">
            {project.gem_bid_no && `${project.gem_bid_no} · `}
            {project.department && `${project.department} · `}
            bids closed {project.due}
          </p>
        </div>
        {role === "ADMIN" && <Link className="btn small" to={`/projects/${project.tender_id}/audit`}>Activity log</Link>}
      </div>
      <ol className="steps">
        {steps.map((s) => {
          const text = `${s.done ? "✓ " : ""}${s.n} · ${s.label}`;
          return (
            <li key={s.key} className={s.current ? "current" : s.done ? "done" : undefined}
                aria-current={s.current ? "step" : undefined}>
              {s.url && !s.current ? <Link to={s.url}>{text}</Link> : text}
            </li>
          );
        })}
      </ol>
    </>
  );
}
