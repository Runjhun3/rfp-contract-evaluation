import { Link, useSearchParams } from "react-router-dom";
import ActivityFilters from "../components/ActivityFilters";
import ActivityTable, { ActivityTabs, activityQuery } from "../components/ActivityTable";
import BackLink from "../components/BackLink";
import { usePageTitle } from "../components/Layout";
import { Loading } from "../components/Status";
import type { ActivityLog } from "../recordTypes";
import { useApi } from "../useApi";

// Administrators only: the central activity log. Every action a person took, in every
// project and on the accounts: projects created, RFPs and bids uploaded, criteria edited
// and approved, evaluations started, committee decisions, accounts created or switched
// off, sign-ins and sign-outs. What the AI or the worker did on its own is left out.
export default function Activity() {
  usePageTitle("Activity");
  const [params] = useSearchParams();
  const query = activityQuery(params, params.get("area") ?? "");
  const { data, error } = useApi<ActivityLog>(`/api/v1/activity?${query}`);
  if (!data) return <Loading error={error} />;

  return (
    <main className="page">
      <div className="back-row">
        <BackLink to="/projects" label="projects" />
        <nav className="crumbs" aria-label="Breadcrumb"><Link to="/projects">Projects</Link> / Activity</nav>
      </div>
      <div>
        <h1>Activity</h1>
        <p className="sub">Everything people did in BidLens, newest first. Nothing here is ever edited or removed.</p>
      </div>
      <ActivityTabs log={data} current={data.category} />
      <ActivityFilters key={query} log={data} csv={`/api/v1/activity.csv?${query}`} />
      <ActivityTable log={data} current={data.category} showProject />
    </main>
  );
}
