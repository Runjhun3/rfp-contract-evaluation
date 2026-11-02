import { Link, useSearchParams } from "react-router-dom";
import type { ActivityLog } from "../recordTypes";
import Pager from "./Pager";

const PER_PAGE = 50; // as the API pages it (app/db/q_activity.py)

type Props = {
  log: ActivityLog;
  extra?: { key: string; label: string }; // a further tab after the areas (e.g. approved criteria)
  current: string | null;                // the chosen tab: an area, the extra one, or null for all
  showProject?: boolean;                 // the central log names each action's project
};

// A link to the log with some of its settings changed (area, page, who, since, until),
// keeping the others: a filter stays on while moving between tabs and pages.
export function useLogLink(): (changes: Record<string, string | null>) => string {
  const [params] = useSearchParams();
  return (changes) => {
    const q = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) q.set(key, value);
      else q.delete(key);
    }
    return `?${q}`;
  };
}

// What to ask the API for: the page's own settings, with the area as its category.
export function activityQuery(params: URLSearchParams, area: string): string {
  const q = new URLSearchParams();
  if (area) q.set("category", area);
  for (const key of ["page", "who", "since", "until"]) {
    const value = params.get(key);
    if (value) q.set(key, value);
  }
  return q.toString();
}

// The area tabs of an activity log, newest first.
export function ActivityTabs({ log, extra, current }: Props) {
  const link = useLogLink();
  const tabs = [{ key: "", label: "All" }, ...log.categories, ...(extra ? [extra] : [])];
  return (
    <nav className="row wrap" aria-label="Areas of the activity log">
      {tabs.map((t) => (
        <Link key={t.key} to={link({ area: t.key || null, page: null })} className={`chip${(current ?? "") === t.key ? " blue" : ""}`}
          aria-current={(current ?? "") === t.key ? "page" : undefined}>{t.label}</Link>
      ))}
    </nav>
  );
}

// One page of actions people took, as a plain table with date and time, and numbered
// pages below it.
export default function ActivityTable({ log, showProject }: Props) {
  const link = useLogLink();
  if (!log.rows.length) return <div className="card"><p className="muted">Nothing recorded here for these filters.</p></div>;
  return (
    <>
      <table className="table audit activity">
        <thead>
          <tr><th>Date &amp; time</th><th>Who</th><th>Area</th><th>What</th>{showProject && <th>Project</th>}<th>Details</th></tr>
        </thead>
        <tbody>
          {log.rows.map((r, i) => (
            <tr key={i}>
              <td className="num nowrap">{r.stamp}</td>
              <td>{r.who}</td>
              <td>{r.area}</td>
              <td>{r.what}</td>
              {showProject && <td>{r.project ?? "—"}</td>}
              <td>{r.details ? <div className={`audit-text${r.details.length > 240 ? " long" : ""}`}>{r.details}</div>
                : <span className="muted">—</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Pager page={log.page} pages={log.pages} total={log.total} perPage={PER_PAGE}
        link={(p) => link({ page: p > 1 ? String(p) : null })} />
    </>
  );
}
