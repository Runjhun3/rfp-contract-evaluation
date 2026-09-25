import { Link } from "react-router-dom";
import type { Project, Step } from "../types";

// Breadcrumb, project title and the five-step stepper shown on every project screen.
export default function ProjectHead({ project, steps }: { project: Project; steps: Step[] }) {
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/projects">Projects</Link> / {project.name}
      </nav>
      <div>
        <h1 className="project">{project.name}</h1>
        <p className="sub">
          {project.gem_bid_no && `${project.gem_bid_no} · `}
          {project.department && `${project.department} · `}
          bids closed {project.due}
        </p>
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
