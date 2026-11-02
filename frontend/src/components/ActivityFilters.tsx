import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { ActivityLog } from "../recordTypes";
import { useLogLink } from "./ActivityTable";

type Props = { log: ActivityLog; csv: string }; // csv: the API path of the log's CSV file

// Who and when: narrow the log to one person and a date range (both days included), and
// download what is shown (every matching row, not only this page) as a CSV file.
export default function ActivityFilters({ log, csv }: Props) {
  const navigate = useNavigate();
  const link = useLogLink();
  // The boxes start from the address (the filters asked for), so they show the right
  // values at once, before the filtered log arrives.
  const [params] = useSearchParams();
  const [who, setWho] = useState(params.get("who") ?? "");
  const [since, setSince] = useState(params.get("since") ?? "");
  const [until, setUntil] = useState(params.get("until") ?? "");
  const filtered = Boolean(params.get("who") || params.get("since") || params.get("until"));

  function apply(e: FormEvent) {
    e.preventDefault();
    navigate(link({ who: who || null, since: since || null, until: until || null, page: null }));
  }
  function clear() {
    setWho("");
    setSince("");
    setUntil("");
    navigate(link({ who: null, since: null, until: null, page: null }));
  }

  return (
    <form className="filters" onSubmit={apply}>
      <label className="field" htmlFor="f-who">Person
        <select id="f-who" value={who} onChange={(e) => setWho(e.target.value)}>
          <option value="">Everyone</option>
          {log.people.map((p) => <option key={p.user_id} value={p.user_id}>{p.name}</option>)}
        </select>
      </label>
      <label className="field" htmlFor="f-since">From
        <input id="f-since" type="date" value={since} max={until || undefined} onChange={(e) => setSince(e.target.value)} />
      </label>
      <label className="field" htmlFor="f-until">To
        <input id="f-until" type="date" value={until} min={since || undefined} onChange={(e) => setUntil(e.target.value)} />
      </label>
      <button className="btn small primary" type="submit">Apply</button>
      {filtered && <button className="btn small" type="button" onClick={clear}>Clear filters</button>}
      {/* A file download, not an API call: the browser saves the CSV. */}
      <a className="btn small download" href={csv} download>Download CSV</a>
    </form>
  );
}
