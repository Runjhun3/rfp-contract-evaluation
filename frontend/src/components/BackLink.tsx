import { Link } from "react-router-dom";

// "← Back to …" at the top of a page that is not a step of the project: always to the
// same place (not the browser's history, which also holds every item, filter and page
// opened here), so it is clear where it leads.
export default function BackLink({ to, label }: { to: string; label: string }) {
  return <Link className="btn small back" to={to}>← Back to {label}</Link>;
}
