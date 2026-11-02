import { useState, type FormEvent } from "react";
import { post } from "../api";
import { useUnsavedWarning } from "../useUnsaved";
import { ErrorText } from "./Status";

type Props = { roles: { key: string; label: string }[]; onSaved: () => void };

// An administrator creates a sign-in account. The API checks every field again; the
// password is sent once and stored only as a hash.
export default function NewUserForm({ roles, onSaved }: Props) {
  const empty = { username: "", full_name: "", role: roles[roles.length - 1]?.key ?? "", password: "" };
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useUnsavedWarning(Boolean(form.username || form.full_name || form.password));
  const set = (key: keyof typeof empty) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/api/v1/users", form);
      setForm(empty);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>New account</h2>
      <ErrorText error={error} />
      <div className="two">
        <label className="field" htmlFor="new-username">Username
          <input id="new-username" type="text" autoComplete="off" autoCapitalize="none" spellCheck={false}
            value={form.username} onChange={set("username")} required minLength={3} maxLength={40} />
        </label>
        <label className="field" htmlFor="new-name">Full name
          <input id="new-name" type="text" autoComplete="off" value={form.full_name}
            onChange={set("full_name")} required maxLength={100} />
        </label>
        <label className="field" htmlFor="new-role">Role
          <select id="new-role" value={form.role} onChange={set("role")}>
            {roles.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
          </select>
        </label>
        <label className="field" htmlFor="new-password">Password (at least 12 characters)
          <input id="new-password" type="password" autoComplete="new-password" value={form.password}
            onChange={set("password")} required minLength={12} />
        </label>
      </div>
      <p className="hint">Administrators can also manage accounts. Give the person their password in person or by phone, not by email.</p>
      <div className="row">
        <button className="btn primary" type="submit" disabled={busy}>Create account</button>
      </div>
    </form>
  );
}
