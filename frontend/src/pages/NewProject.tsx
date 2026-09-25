import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { post } from "../api";
import { usePageTitle } from "../components/Layout";
import { ErrorText } from "../components/Status";

export default function NewProject() {
  usePageTitle("New project");
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", gem: "", due: "", department: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const { tender_id } = await post<{ tender_id: string }>("/api/v1/projects", form);
      navigate(`/projects/${tender_id}/rfp`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb"><Link to="/projects">Projects</Link> / New project</nav>
      <h1>New project</h1>
      <form className="card" onSubmit={submit}>
        <ErrorText error={error} />
        <h2>Project details</h2>
        <label className="field">Project name
          <input type="text" value={form.name} onChange={set("name")} required />
        </label>
        <div className="two">
          <label className="field">GeM bid number
            <input type="text" value={form.gem} onChange={set("gem")} placeholder="GEM/2026/B/…" />
          </label>
          <label className="field">Final bid closing date
            <input type="date" value={form.due} onChange={set("due")} required />
          </label>
        </div>
        <p className="hint">
          Use the date after any extension. Rules like "awarded at least 12 months before bid
          submission" are counted from it.
        </p>
        <label className="field">Department
          <input type="text" value={form.department} onChange={set("department")} />
        </label>
        <div className="row">
          <button className="btn primary" type="submit" disabled={busy}>Create project and upload RFP</button>
          <Link to="/projects">Cancel</Link>
        </div>
      </form>
    </main>
  );
}
